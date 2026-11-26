"""HTTP API и веб-интерфейс «Цифрового механика» (FastAPI). Контракт: docs/CONTRACT.md."""
from __future__ import annotations

import json
import queue
import secrets
import threading
import time
import logging

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agent, audit, clients, config, data, stt
from .manuals import BY_ID

log = logging.getLogger("mechanic")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="Цифровой механик", version="1.0")

# --- простая защита стенда паролем (ACCESS_PASSWORD в .env; пусто – открыт) ---
COOKIE = "dm_access"


@app.middleware("http")
async def access_gate(request: Request, call_next):
    pw = config.ACCESS_PASSWORD
    path = request.url.path
    if not pw or path in ("/api/health", "/login", "/api/login") or path.startswith("/static/login"):
        return await call_next(request)
    if secrets.compare_digest(request.cookies.get(COOKIE, ""), _token(pw)):
        return await call_next(request)
    if path.startswith("/api/"):
        return JSONResponse({"detail": "Нужен пароль стенда"}, status_code=401)
    return Response(_LOGIN_HTML, media_type="text/html; charset=utf-8")


def _token(pw: str) -> str:
    import hashlib
    return hashlib.sha256(("dm:" + pw).encode()).hexdigest()


class LoginIn(BaseModel):
    password: str


@app.post("/api/login")
def login(body: LoginIn):
    if not config.ACCESS_PASSWORD or not secrets.compare_digest(body.password, config.ACCESS_PASSWORD):
        raise HTTPException(401, "Неверный пароль")
    r = JSONResponse({"ok": True})
    r.set_cookie(COOKIE, _token(config.ACCESS_PASSWORD), max_age=60 * 60 * 24 * 30, httponly=True, samesite="lax")
    return r


_LOGIN_HTML = """<!doctype html><html lang=ru><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Цифровой механик</title><style>body{font-family:system-ui;display:flex;min-height:100vh;align-items:center;justify-content:center;background:#f3f4f6;margin:0}
form{background:#fff;padding:24px;border-radius:14px;box-shadow:0 2px 12px #0001;width:min(340px,90vw)}input,button{width:100%;font-size:17px;padding:12px;margin-top:10px;border-radius:10px;border:1px solid #ccc;box-sizing:border-box}
button{background:#1f6feb;color:#fff;border:0}</style><form onsubmit="event.preventDefault();fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:p.value})}).then(r=>r.ok?location.reload():(m.textContent='Неверный пароль'))">
<b>Цифровой механик</b><div>Стенд хакатона. Введите пароль из описания решения.</div><input id=p type=password autofocus><button>Войти</button><div id=m style="color:#c00;margin-top:8px"></div></form></html>"""


# --- данные ---
@app.get("/api/health")
def health():
    return {"status": "ok", "services": clients.health(), "llm_model": config.LLM_MODEL}


@app.get("/api/vehicles")
def vehicles():
    return [data.summary(v) for v in data.vehicles()]


@app.get("/api/vehicles/{vehicle_id}")
def vehicle(vehicle_id: str):
    d = data.detail(vehicle_id)
    if not d:
        raise HTTPException(404, "Машина не найдена")
    return d


@app.get("/api/fleet")
def fleet():
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
_hits: dict[str, list[float]] = {}
_all: list[float] = []
PER_IP_10MIN = int(config.env("RATE_PER_IP_10MIN", "40"))
GLOBAL_PER_HOUR = int(config.env("RATE_GLOBAL_PER_HOUR", "600"))


def _rate_limit(request: Request) -> None:
    now = time.time()
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0].strip()
    h = [t for t in _hits.get(ip, []) if now - t < 600]
    _all[:] = [t for t in _all if now - t < 3600]
    if len(h) >= PER_IP_10MIN or len(_all) >= GLOBAL_PER_HOUR:
        raise HTTPException(429, "Слишком много запросов, подождите несколько минут.")
    h.append(now)
    _hits[ip] = h
    _all.append(now)


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
            a.run(text[:2000])
        except Exception as e:  # noqa: BLE001 – показываем механику понятную ошибку, детали в лог
            log.exception("agent failed")
            q.put({"type": "error", "text": f"Не получилось выполнить запрос ({type(e).__name__}). Попробуйте ещё раз."})
        finally:
            log.info("chat %s %s %.1fs usage=%s", body.vehicle_id, body.action or "msg", time.time() - t0, conv.usage.as_dict())
            audit.write("chat", conversation=body.conversation_id, vehicle=body.vehicle_id, session=body.session_id,
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
    data_ = await audio.read()
    try:
        text = stt.transcribe(data_, stt.audio_format(audio.content_type or "", audio.filename or ""), lang)
        audit.write("voice", lang=lang, bytes=len(data_), text=text)
    except stt.SttError as e:
        raise HTTPException(502, f"Не удалось распознать речь: {e}")
    return {"text": text, "lang": lang}


class ConfirmIn(BaseModel):
    draft_id: str
    conclusion: str | None = None
    urgency: str | None = None
    operations: list[str] | None = None
    spare_parts: list[str] | None = None


@app.post("/api/tickets/confirm")
def confirm(body: ConfirmIn):
    try:
        res = agent.confirm_ticket(body.draft_id, body.model_dump(exclude={"draft_id"}, exclude_none=True))
        audit.write("ticket", draft=body.draft_id, result=res)
        return res
    except ValueError as e:
        raise HTTPException(400, str(e))
    except clients.ServiceError as e:
        raise HTTPException(502, f"{e.service}: {e.detail}")


# --- статика (веб-интерфейс) ---
_web = config.ROOT / "web"
if _web.exists():
    app.mount("/", StaticFiles(directory=str(_web), html=True), name="web")
