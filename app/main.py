"""HTTP API и веб-интерфейс «Цифрового механика» (FastAPI). Контракт: docs/CONTRACT.md."""
from __future__ import annotations

import hashlib
import json
import logging
import queue
import secrets
import threading
import time
from collections import deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agent, audit, clients, config, data, stt, users
from .manuals import BY_ID

log = logging.getLogger("mechanic")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")



def _warm_up() -> None:
    try:
        agent.searcher()
        log.info("индекс руководств загружен")
    except Exception:   # без индекса сервис работает (карточки, заявки), поиск сообщит об ошибке сам
        log.exception("индекс руководств не загружен")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # индекс руководств и модель E5 грузятся в фоне при старте, а не на первом вопросе механика
    threading.Thread(target=_warm_up, daemon=True).start()
    yield


app = FastAPI(title="Цифровой механик", version="1.0", lifespan=lifespan)

# --- заголовки безопасности: только свои скрипты и стили, без встраивания в чужие сайты ---
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
       "media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("Content-Security-Policy", CSP)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "microphone=(self), camera=(), geolocation=()")
    # интерфейс всегда сверяется с сервером (по ETag): после выкладки телефон не показывает старую версию
    response.headers.setdefault("Cache-Control", "no-cache")
    return response


# --- вход: учетные записи с ролями (users.json), общий пароль стенда или открытый доступ ---
COOKIE = "dm_access"
OPEN_PATHS = ("/api/health", "/login", "/api/login", "/privacy.html", "/favicon.svg", "/demo.mp4")


def current_user(request: Request) -> users.User | None:
    return getattr(request.state, "user", None)


@app.middleware("http")
async def access_gate(request: Request, call_next):
    path = request.url.path
    request.state.user = None
    if users.enabled():
        request.state.user = users.from_session(request.cookies.get(COOKIE, ""))
        ok = request.state.user is not None
    elif config.ACCESS_PASSWORD:
        ok = secrets.compare_digest(request.cookies.get(COOKIE, ""), _token(config.ACCESS_PASSWORD))
    else:
        ok = True
    if ok or path in OPEN_PATHS:
        return await call_next(request)
    if path.startswith("/api/"):
        return JSONResponse({"detail": "Нужно войти"}, status_code=401)
    return Response(_login_html(), media_type="text/html; charset=utf-8", headers={
        "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'"})


def _token(pw: str) -> str:
    return hashlib.sha256(("dm:" + pw).encode()).hexdigest()


class RateLimit:
    """Скользящее окно по адресу и суммарно. Потокобезопасно; адреса без событий в окне забываются."""

    def __init__(self, per_key: int, window: float, total: int | None = None, total_window: float = 0):
        self.per_key, self.window, self.total, self.total_window = per_key, window, total, total_window
        self._keys: dict[str, deque] = {}
        self._all: deque = deque()
        self._lock = threading.Lock()

    @staticmethod
    def _trim(q: deque, horizon: float) -> None:
        while q and q[0] < horizon:
            q.popleft()

    def blocked(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._keys.get(key)
            if q is not None:
                self._trim(q, now - self.window)
            self._trim(self._all, now - self.total_window)
            return bool((q and len(q) >= self.per_key) or (self.total and len(self._all) >= self.total))

    def hit(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._keys.setdefault(key, deque()).append(now)
            if self.total:
                self._all.append(now)
            if len(self._keys) > 10_000:   # не копим память на разовых адресах
                horizon = now - self.window
                self._keys = {k: q for k, q in self._keys.items() if q and q[-1] >= horizon}


class LoginIn(BaseModel):
    login: str = ""
    password: str


LOGIN_FAILS = RateLimit(per_key=10, window=900)


@app.post("/api/login")
def login(body: LoginIn, request: Request):
    ip = _client_ip(request)
    if LOGIN_FAILS.blocked(ip):
        raise HTTPException(429, "Слишком много попыток входа, подождите 15 минут")
    if users.enabled():
        user = users.authenticate(body.login, body.password)
        token = users.make_session(user) if user else None
    elif config.ACCESS_PASSWORD and secrets.compare_digest(body.password, config.ACCESS_PASSWORD):
        user, token = None, _token(config.ACCESS_PASSWORD)
    else:
        token = None
    if not token:
        LOGIN_FAILS.hit(ip)
        raise HTTPException(401, "Неверный логин или пароль")
    audit.write("login", user=body.login or None, ip=ip)
    r = JSONResponse({"ok": True})
    r.set_cookie(COOKIE, token, max_age=config.SESSION_DAYS * 86400, httponly=True, samesite="lax",
                 secure=request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https")
    return r


@app.post("/api/logout")
def logout():
    r = JSONResponse({"ok": True})
    r.delete_cookie(COOKIE)
    return r


@app.get("/api/me")
def me(request: Request):
    u = current_user(request)
    return {"auth": users.enabled() or bool(config.ACCESS_PASSWORD),
            "user": {"login": u.login, "name": u.name, "role": u.role, "role_name": users.ROLES[u.role]} if u else None}


def _login_html() -> str:
    login_field = '<label for=l>Логин</label><input id=l autocomplete=username autocapitalize=none autofocus>' if users.enabled() else ""
    focus = "" if users.enabled() else " autofocus"
    return _LOGIN_HTML.replace("{login}", login_field).replace("{focus}", focus)


_LOGIN_HTML = """<!doctype html><html lang=ru><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Цифровой механик – вход</title><style>body{font-family:system-ui,sans-serif;display:flex;min-height:100vh;align-items:center;justify-content:center;background:#eef1f4;margin:0;padding:16px;box-sizing:border-box;color:#14202b}
form{background:#fff;padding:24px;border:1px solid #c9d2db;border-radius:10px;width:min(360px,100%);display:grid;gap:8px}h1{font-size:22px;margin:0 0 8px}
label{font-weight:700;font-size:16px;margin-top:6px}input,button{width:100%;font-size:18px;min-height:56px;padding:0 14px;border-radius:8px;border:1px solid #6b7b8a;box-sizing:border-box}
input:focus{outline:3px solid #173a5e;outline-offset:1px;border-color:#173a5e}button{background:#173a5e;color:#fff;border:0;font-weight:700;margin-top:12px}
p{margin:0;color:#4d5b68;font-size:15px}#m{color:#a1261b;min-height:1.2em}</style>
<form onsubmit="event.preventDefault();var l=document.getElementById('l');fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({login:l?l.value:'',password:p.value})}).then(function(r){if(r.ok)location.reload();else r.json().then(function(j){m.textContent=j.detail||'Не удалось войти'})})">
<h1>Цифровой механик</h1>{login}<label for=p>Пароль</label><input id=p type=password autocomplete=current-password{focus}><button>Войти</button><div id=m role=alert></div><p>Нет доступа или забыли пароль – обратитесь к главному механику.</p></form></html>"""


def _client_ip(request: Request) -> str:
    # адрес клиента уже восстановлен uvicorn из X-Forwarded-For (--proxy-headers); сам заголовок не читаем – его можно подделать
    return request.client.host if request.client else "?"


@app.api_route("/demo.mp4", methods=["GET", "HEAD"])   # HEAD – для проверок ссылки и предпросмотра в мессенджерах
def demo_video():
    """Демо-видео для жюри (STATE_DIR/public/demo.mp4, в Git не входит). Открыто и при включенных учетных записях."""
    f = config.STATE_DIR / "public" / "demo.mp4"
    if not f.is_file():
        raise HTTPException(404, "Видео еще не загружено")
    return FileResponse(f, media_type="video/mp4", headers={"Cache-Control": "public, max-age=300"})


# --- данные ---
@app.get("/api/health")
def health():
    return {"status": "ok", "services": clients.health(), "llm_model": config.LLM_MODEL}


@app.get("/api/vehicles")
def vehicles():
    return data.summaries()


@app.get("/api/vehicles/{vehicle_id}")
def vehicle(vehicle_id: str):
    d = data.detail(vehicle_id)
    if not d:
        raise HTTPException(404, "Машина не найдена")
    return d


@app.get("/api/fleet")
def fleet(request: Request):
    u = current_user(request)
    if u and u.role != "chief":
        raise HTTPException(403, "Сводка парка доступна главному механику")
    return data.fleet()


@app.get("/api/manuals/{manual_id}/pages/{page}.png")
def page_png(manual_id: str, page: int):
    _check_page(manual_id, page)
    return FileResponse(agent.searcher().page_png(manual_id, page), media_type="image/png",
                        headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/manuals/{manual_id}/pages/{page}")
def page_json(manual_id: str, page: int):
    _check_page(manual_id, page)
    m = BY_ID[manual_id]
    return {"manual_id": manual_id, "title": m.title, "designation": m.designation, "page": page,
            "pages_total": m.pages, "text": agent.searcher().page_text(manual_id, page)}


def _check_page(manual_id: str, page: int):
    if manual_id not in BY_ID or not 1 <= page <= BY_ID[manual_id].pages:
        raise HTTPException(404, "Нет такой страницы")


# --- агент ---
# Стенд открыт для жюри без пароля, поэтому ограничиваем частоту запросов к LLM: с одного адреса и суммарно.
LLM_RATE = RateLimit(per_key=int(config.env("RATE_PER_IP_10MIN", "40")), window=600,
                     total=int(config.env("RATE_GLOBAL_PER_HOUR", "600")), total_window=3600)


def _rate_limit(request: Request) -> None:
    ip = _client_ip(request)
    if LLM_RATE.blocked(ip):
        raise HTTPException(429, "Слишком много запросов, подождите несколько минут.")
    LLM_RATE.hit(ip)


class ChatIn(BaseModel):
    conversation_id: str
    vehicle_id: str
    session_id: str | None = None
    message: str = ""
    action: str | None = None
    lang: str = "ru"
    detail: str = "brief"


ACTION_TEXT = {
    "diagnose": "Получить результат диагностики по выбранной проверке и объяснить, что делать.",
    "draft_ticket": "Создай заявку на дефектовку по этой проверке.",
}


@app.post("/api/chat")
def chat(body: ChatIn, request: Request):
    _rate_limit(request)
    if not data.vehicle(body.vehicle_id):
        raise HTTPException(404, "Машина не найдена")
    if body.session_id and not data.session(body.vehicle_id, body.session_id):
        raise HTTPException(404, "Проверка не относится к этой машине")
    text = (body.message or "").strip() or ACTION_TEXT.get(body.action or "", "")
    if not text:
        raise HTTPException(422, "Пустое сообщение")
    conv = agent.get_conversation(body.conversation_id, body.vehicle_id, body.session_id)
    user = current_user(request).login if current_user(request) else None
    q: queue.Queue = queue.Queue()

    def work():
        t0 = time.time()
        shown: set = set()
        trace = {"answer": None, "citations": [], "tools": [], "diagnosis": None, "error": None}

        def put(ev: dict) -> None:
            t = ev.get("type")
            if t == "message":
                trace["answer"], trace["citations"] = ev.get("text"), [f"{c.get('manual_id')}#{c.get('page')}" for c in ev.get("citations") or []]
            elif t == "step" and ev.get("status") == "done":
                trace["tools"].append(ev.get("tool"))
            elif t == "diagnosis":
                dd = ev.get("data") or {}
                trace["diagnosis"] = {k: dd.get(k) for k in ("session_id", "status", "anomaly_type", "urgency", "rule")}
            elif t == "error":
                trace["error"] = ev.get("text")
            # карточка вердикта по одной проверке – один раз за запрос
            if ev.get("type") == "diagnosis":
                key = (ev.get("data") or {}).get("session_id")
                if key in shown:
                    return
                shown.add(key)
            q.put(ev)

        try:
            a = agent.Agent(conv, put, lang=body.lang, detail=body.detail)
            if body.action == "diagnose":
                # кнопка «Получить результат» всегда показывает карточку, даже если разговор уже был
                a.t_get_diagnosis()
            a.run(text[:2000], ticket_requested=True if body.action == "draft_ticket" else None)
        except Exception as e:
            log.exception("agent failed")
            q.put({"type": "error", "text": f"Не получилось выполнить запрос ({type(e).__name__}). Попробуйте еще раз."})
        finally:
            agent.save_conversation(conv)
            log.info("chat %s %s %.1fs usage=%s", body.vehicle_id, body.action or "msg", time.time() - t0, conv.usage.as_dict())
            audit.write("chat", user=user, conversation=body.conversation_id, vehicle=body.vehicle_id, session=body.session_id,
                        action=body.action, lang=body.lang, detail=body.detail, question=(body.message or "")[:2000],
                        seconds=round(time.time() - t0, 1), **trace)
            q.put({"type": "done"})

    threading.Thread(target=work, daemon=True).start()

    def stream():
        while True:
            try:
                ev = q.get(timeout=15)
            except queue.Empty:
                yield ": keep-alive\n\n"
                continue
            yield "data: " + json.dumps(ev, ensure_ascii=False) + "\n\n"
            if ev["type"] == "done":
                break

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/transcribe")
async def transcribe(request: Request, audio: UploadFile = File(...), lang: str = Form("ru")):
    _rate_limit(request)
    data_ = await audio.read(stt.MAX_BYTES + 1)   # больше лимита не читаем: запись длиннее отклоняет stt
    try:
        text = stt.transcribe(data_, stt.audio_format(audio.content_type or "", audio.filename or ""), lang)
        audit.write("voice", user=current_user(request).login if current_user(request) else None, lang=lang, bytes=len(data_), text=text)
    except stt.SttError as e:
        raise HTTPException(502, f"Не удалось распознать речь: {e}") from e
    return {"text": text, "lang": lang}


class ConfirmIn(BaseModel):
    draft_id: str
    conclusion: str | None = None
    urgency: str | None = None
    operations: list[str] | None = None
    spare_parts: list[str] | None = None
    inspection_confirmed: bool | None = None
    urgency_reason: str | None = None   # обязательна, если механик изменил приоритет программы (#111)


@app.post("/api/tickets/confirm")
def confirm(body: ConfirmIn, request: Request):
    u = current_user(request)
    try:
        res = agent.confirm_ticket(body.draft_id, body.model_dump(exclude={"draft_id"}, exclude_none=True),
                                   author=u.name if u else None)
        audit.write("ticket", user=u.login if u else None, draft=body.draft_id, result=res)
        return res
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except clients.ServiceError as e:
        raise HTTPException(502, f"{e.service}: {e.detail}") from e


# --- статика (веб-интерфейс) ---
_web = config.ROOT / "web"
if _web.exists():
    app.mount("/", StaticFiles(directory=str(_web), html=True), name="web")
