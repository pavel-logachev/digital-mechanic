"""Агент «Цифровой механик»: цикл LLM с инструментами.

Модель сама выбирает инструменты (ML, поиск по руководствам, заявка) — сценарий не зашит if-else (F5).
Всё, что можно проверить кодом, проверяет код: приоритет, привязку руководства к двигателю,
существование страниц и цифр, состав заявки. Отправка в ТОиР — только по кнопке человека.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable

from . import clients, data, llm, verify
from .faults import FAULTS, SEVERITY_RU, applicability
from .manuals import BY_ID, manual_ids_for_engine, manuals_for_engine
from .priority import evaluate

MAX_STEPS = 8

SYSTEM = """Ты — «Цифровой механик», помощник механика автопарка. Отвечай по-русски, коротко и по делу, простыми словами, как опытный моторист коллеге. Без канцелярита.

Машина в работе: {vehicle}. Двигатель: {engine}. Выбранная проверка: {session}.
Руководства на этот двигатель (других использовать нельзя): {manuals}.

Инструменты:
- get_diagnosis — результат акустической проверки из ML-сервиса и приоритет, рассчитанный программой. Вызывай, когда механик просит результат диагностики или спрашивает о состоянии двигателя по проверке.
- get_vehicle_history — карточка машины, прошлые проверки и заявки.
- search_manual — поиск по руководствам двигателя этой машины. Передавай 1–3 формулировки: техническую («момент затяжки болтов крышек коренных подшипников») и разговорную. Если первый поиск не дал ответа — переформулируй и поищи ещё раз.
- read_page — полный текст страницы, когда нужно уточнить норматив или порядок работ.
- get_fault_reference — справка о классе неисправности F01–F14: тяжесть, риски, применимость к двигателю.
- prepare_ticket — подготовить черновик заявки на дефектовку. Заявку отправляет механик кнопкой, ты не отправляешь и никогда не пишешь, что заявка создана.

Жёсткие правила:
1. Цифры нормативов, моменты, зазоры, давления, порядок работ — только со страниц, которые ты получил инструментами. После каждого такого утверждения ставь ссылку в формате {{manual_id#страница}}, например {{yamz-236_rk_2014#123}}. Страница — номер страницы PDF из результатов поиска.
2. Не придумывай. Если в руководствах ответа нет — так и скажи: «В руководстве на {engine} этого нет», и посоветуй дефектовку/очный осмотр.
3. Приоритет и действие (снять с линии, плановое ТО, повторить запись) берёшь из get_diagnosis — не меняй и не придумывай свой.
4. Если проверка «check_failed» или запись непригодна — никаких выводов о двигателе, никаких причин неисправности и заявки; попроси повторить запись (двигатель на холостом ходу, микрофон в яме под двигателем, без посторонних шумов).
5. Если программа сообщила, что класс неисправности не подходит к двигателю — объясни это механику и предложи очный осмотр, не выдавай неисправность за подтверждённую.
6. ML даёт гипотезу по звуку, а не диагноз. Пиши «вероятно», «признаки указывают».
7. На вопросы не про эту машину и не про ремонт/эксплуатацию — вежливо верни разговор к машине.

Карточку вердикта (статус, оценка отклонения, уверенность, качество записи, приоритет и его основания) механик уже видит на экране — не пересказывай эти цифры и не повторяй вердикт. После get_diagnosis при отклонении сразу переходи к сути, коротко (до ~180 слов), в формате:
**Что, вероятно, не так** — 1–2 предложения.
**Чем грозит** — 1 предложение.
**Что проверить** — 3–5 нумерованных шагов с нормативами и ссылками.
**Ремонт и запчасти** — что заменить/отрегулировать, запчасти названиями из руководства со ссылкой.
**Ограничения** — одной строкой, чего нет в руководстве или что не известно.
Для нормы — 1–2 предложения (можно работать по данным этой проверки; если были прошлые отклонения — сказать). Для сбоя записи — как правильно перезаписать, 2–3 строки.
Для ответов на вопросы: только нужное из «наблюдения → гипотезы → проверки → возможный ремонт → источник → ограничения», без воды.
"""

TOOLS = [
    {"type": "function", "function": {
        "name": "get_diagnosis", "description": "Получить результат акустической проверки двигателя из ML-сервиса и приоритет, рассчитанный программой",
        "parameters": {"type": "object", "properties": {
            "session_id": {"type": "string", "description": "id проверки; по умолчанию выбранная механиком"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "get_vehicle_history", "description": "Карточка машины, история проверок и созданные заявки",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "search_manual", "description": "Поиск по руководствам двигателя этой машины. Возвращает страницы PDF с текстом",
        "parameters": {"type": "object", "properties": {
            "queries": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3,
                        "description": "1–3 формулировки запроса: техническая и разговорная"}}, "required": ["queries"]}}},
    {"type": "function", "function": {
        "name": "read_page", "description": "Полный текст страницы руководства этого двигателя",
        "parameters": {"type": "object", "properties": {
            "manual_id": {"type": "string"}, "page": {"type": "integer"}}, "required": ["manual_id", "page"]}}},
    {"type": "function", "function": {
        "name": "get_fault_reference", "description": "Справка о классе неисправности F01–F14: тяжесть, риски, применимость к двигателю, что искать в руководстве",
        "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "prepare_ticket", "description": "Подготовить черновик заявки на дефектовку по текущей проверке. Не отправляет — отправляет механик кнопкой",
        "parameters": {"type": "object", "properties": {
            "conclusion": {"type": "string", "description": "Диагноз для заявки: что выявлено и что подозревается, 1–2 предложения"},
            "operations": {"type": "array", "items": {"type": "string"}, "minItems": 1, "description": "Работы по дефектовке/ремонту из руководства"},
            "spare_parts": {"type": "array", "items": {"type": "string"}, "description": "Запчасти и материалы названиями из руководства, может быть пусто"},
            "references": {"type": "array", "minItems": 1, "items": {"type": "object", "properties": {
                "manual_id": {"type": "string"}, "page": {"type": "integer"}}, "required": ["manual_id", "page"]}}},
            "required": ["conclusion", "operations", "spare_parts", "references"]}}},
]

STEP_TITLES = {
    "get_diagnosis": "Запрос результата проверки в ML-сервис",
    "get_vehicle_history": "История машины и прошлые заявки",
    "search_manual": "Поиск в руководстве",
    "read_page": "Чтение страницы руководства",
    "get_fault_reference": "Справка по классу неисправности",
    "prepare_ticket": "Подготовка черновика заявки",
}


@dataclass
class Conversation:
    id: str
    vehicle_id: str
    session_id: str | None
    messages: list[dict] = field(default_factory=list)
    seen: set = field(default_factory=set)          # (manual_id, page), полученные инструментами
    diagnosis: dict | None = None
    verdict: dict | None = None
    drafts: dict = field(default_factory=dict)
    usage: llm.Usage = field(default_factory=llm.Usage)
    lock: threading.Lock = field(default_factory=threading.Lock)


_convs: dict[str, Conversation] = {}
_searcher = None


def searcher():
    global _searcher
    if _searcher is None:
        from .search import Searcher
        _searcher = Searcher.load()
    return _searcher


def get_conversation(cid: str, vehicle_id: str, session_id: str | None) -> Conversation:
    c = _convs.get(cid)
    if c is None or c.vehicle_id != vehicle_id or (session_id and c.session_id != session_id):
        c = Conversation(cid, vehicle_id, session_id)
        _convs[cid] = c
    return c


def find_draft(draft_id: str) -> tuple[Conversation, dict] | None:
    for c in _convs.values():
        if draft_id in c.drafts:
            return c, c.drafts[draft_id]
    return None


class Agent:
    def __init__(self, conv: Conversation, emit: Callable[[dict], None]):
        self.c = conv
        self.emit = emit
        self.v = data.vehicle(conv.vehicle_id)
        if not self.v:
            raise ValueError("машина не найдена")
        if not self.c.session_id and self.v["sessions"]:
            self.c.session_id = self.v["sessions"][-1]["session_id"]
        self.engine = self.v["engine_model"]
        self.allowed = set(manual_ids_for_engine(self.engine))

    # ---------- инструменты ----------
    def t_get_diagnosis(self, session_id: str | None = None) -> dict:
        sid = session_id or self.c.session_id
        if not data.session(self.v["vehicle_id"], sid):
            return {"error": f"проверка {sid} не относится к машине {self.v['vehicle_id']}"}
        res = clients.diagnose(self.v["vehicle_id"], sid)
        verdict = evaluate(res, self.engine, self.v["sessions"], data.tickets(self.v["vehicle_id"])).as_dict()
        if sid == self.c.session_id:
            self.c.diagnosis, self.c.verdict = res, verdict
        self.emit({"type": "diagnosis", "data": {**res, **verdict, "engine_model": self.engine}})
        out = {"ml_result": res, "program_verdict": verdict}
        code = res.get("anomaly_type")
        if code and code in FAULTS:
            out["fault_reference"] = self._fault(code)
        return out

    def t_get_vehicle_history(self) -> dict:
        d = data.detail(self.v["vehicle_id"])
        keep = ("session_id", "checked_at", "status", "anomaly_type", "anomaly_title", "anomaly_score", "confidence", "signal_quality", "description")
        return {"vehicle": {k: d[k] for k in ("vehicle_id", "garage_no", "make", "model", "vehicle_type", "engine_model", "fuel")},
                "sessions": [{k: s.get(k) for k in keep} for s in d["sessions"]],
                "tickets": d["tickets"]}

    def t_search_manual(self, queries: list[str]) -> dict:
        queries = [q for q in (queries or []) if q and q.strip()][:3] or ["двигатель"]
        hits = searcher().search(queries[0], self.engine, k=5, rewrites=queries[1:])
        pages = []
        for h in hits:
            if h["manual_id"] not in self.allowed:
                continue
            self.c.seen.add((h["manual_id"], int(h["page"])))
            pages.append({"ref": f"{{{h['manual_id']}#{h['page']}}}", "manual": BY_ID[h["manual_id"]].title,
                          "page": h["page"], "text": (h.get("text") or h.get("snippet") or "")[:2200]})
        return {"engine": self.engine, "pages": pages,
                "note": "Ссылайся только на эти страницы в формате ref. Если ответа нет — переформулируй или скажи, что в руководстве этого нет."}

    def t_read_page(self, manual_id: str, page: int) -> dict:
        page = int(page)
        if manual_id not in self.allowed:
            return {"error": f"руководство {manual_id} не относится к двигателю {self.engine}"}
        if page < 1 or page > BY_ID[manual_id].pages:
            return {"error": "нет такой страницы"}
        self.c.seen.add((manual_id, page))
        return {"ref": f"{{{manual_id}#{page}}}", "manual": BY_ID[manual_id].title, "page": page,
                "text": searcher().page_text(manual_id, page)[:6000]}

    def _fault(self, code: str) -> dict:
        f = FAULTS[code]
        return {"code": code, "title": data.fault_titles().get(code), "severity": SEVERITY_RU[f["severity"]],
                "risk": f["risk"], "applicable_to_engine": applicability(code, self.engine), "search_hint": f["search"]}

    def t_get_fault_reference(self, code: str) -> dict:
        code = (code or "").upper().strip()
        return self._fault(code) if code in FAULTS else {"error": "неизвестный код"}

    def t_prepare_ticket(self, conclusion: str, operations: list[str], spare_parts: list[str], references: list[dict]) -> dict:
        if not self.c.diagnosis or self.c.diagnosis.get("session_id") != self.c.session_id:
            self.t_get_diagnosis()
        res, verdict = self.c.diagnosis, self.c.verdict
        if res["status"] != "anomaly" or not verdict["ticket_allowed"]:
            why = "проверка в норме" if res["status"] == "normal" else "запись непригодна — нужна повторная запись"
            return {"error": f"Заявку по этой проверке создавать нельзя: {why}."}
        refs, bad = [], []
        for r in references or []:
            mid, page = r.get("manual_id"), int(r.get("page", 0))
            if mid in self.allowed and (mid, page) in self.c.seen and 1 <= page <= BY_ID[mid].pages:
                if not any(x["manual_id"] == mid and x["pdf_page"] == page for x in refs):
                    refs.append({"manual": BY_ID[mid].designation, "pdf_page": page, "manual_id": mid, "title": BY_ID[mid].title})
            else:
                bad.append(f"{mid} стр. {page}")
        ops = [o.strip() for o in operations or [] if o and o.strip()]
        if not refs:
            return {"error": "Нужна хотя бы одна ссылка на страницу руководства этого двигателя, найденную поиском. "
                             f"Отклонены: {', '.join(bad) or 'нет ссылок'}. Сначала найди процедуру через search_manual."}
        if not ops or not (conclusion or "").strip():
            return {"error": "Нужны диагноз и хотя бы одна работа."}
        draft = {"draft_id": "D-" + uuid.uuid4().hex[:8], "vehicle_id": self.v["vehicle_id"], "session_id": res["session_id"],
                 "anomaly_type": res["anomaly_type"], "conclusion": conclusion.strip(), "urgency": verdict["urgency"],
                 "urgency_reasons": verdict["urgency_reasons"], "warnings": verdict.get("warnings", []),
                 "operations": ops, "spare_parts": [p.strip() for p in spare_parts or [] if p and p.strip()],
                 "references": refs, "engine_model": self.engine}
        self.c.drafts[draft["draft_id"]] = draft
        self.emit({"type": "draft", "draft": draft})
        out = {"draft_id": draft["draft_id"], "status": "черновик показан механику, ждёт его подтверждения кнопкой",
               "urgency": draft["urgency"]}
        if bad:
            out["rejected_references"] = bad
        return out

    # ---------- цикл ----------
    def _system(self) -> dict:
        v = self.v
        mans = "; ".join(f"{m.id} — {m.title} ({m.designation})" for m in manuals_for_engine(self.engine))
        return {"role": "system", "content": SYSTEM.format(
            vehicle=f"{v['vehicle_id']} (гаражный {v.get('garage_no')}), {v.get('make')} {v.get('model') or ''}, {v.get('vehicle_type')}",
            engine=self.engine, session=self.c.session_id, manuals=mans)}

    def _context_numbers(self) -> set[str]:
        nums = set()
        for s in self.v["sessions"]:
            for k in ("anomaly_score", "confidence"):
                if s.get(k) is not None:
                    nums.add(verify._norm_num(str(s[k])))
        for s in [self.v["vehicle_id"], self.v.get("garage_no") or "", self.engine, self.c.session_id or ""]:
            nums |= verify.page_numbers(s)
        for m in manuals_for_engine(self.engine):
            nums |= verify.page_numbers(m.designation + " " + m.title)
        nums |= {"1", "0"}
        return nums

    def run(self, user_text: str) -> None:
        with self.c.lock:
            msgs = self.c.messages
            if not msgs:
                msgs.append(self._system())
            msgs.append({"role": "user", "content": user_text})
            retried = False
            for _ in range(MAX_STEPS):
                m = llm.chat(msgs, TOOLS, self.c.usage)
                if m.tool_calls:
                    msgs.append({"role": "assistant", "content": m.content or "",
                                 "tool_calls": [tc.model_dump() for tc in m.tool_calls]})
                    for tc in m.tool_calls:
                        msgs.append({"role": "tool", "tool_call_id": tc.id, "content": self._call(tc)})
                    continue
                answer = (m.content or "").strip()
                checked = verify.check(answer, self.allowed, self.c.seen, searcher().page_text, self._context_numbers())
                if checked.problems and not retried:
                    retried = True
                    msgs.append({"role": "assistant", "content": answer})
                    self.emit({"type": "step", "tool": "verify", "title": "Проверка цифр и ссылок", "status": "error",
                               "detail": "; ".join(checked.problems)[:400]})
                    msgs.append({"role": "user", "content": "[Проверка программы] В ответе найдены проблемы: "
                                 + "; ".join(checked.problems)
                                 + ". Исправь ответ: каждую цифру подтверди страницей, которую получил инструментом "
                                   "(при необходимости поищи ещё), или убери её и честно скажи, что в руководстве этого нет. "
                                   "Пришли исправленный ответ целиком."})
                    continue
                if checked.problems:
                    checked.text += "\n\n_Часть сведений не удалось подтвердить по руководству: проверьте по ссылкам перед работой._"
                msgs.append({"role": "assistant", "content": answer})
                self.emit({"type": "step", "tool": "verify", "title": "Проверка цифр и ссылок", "status": "done",
                           "detail": f"ссылок: {len(checked.citations)}" + (f", замечаний: {len(checked.problems)}" if checked.problems else ", всё подтверждено")})
                self.emit({"type": "message", "text": checked.text, "citations": checked.citations,
                           "usage": self.c.usage.as_dict()})
                return
            self.emit({"type": "message", "text": "Не успел собрать ответ, уточните вопрос.", "citations": []})

    def _call(self, tc) -> str:
        name = tc.function.name
        try:
            args = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        detail = ", ".join(args.get("queries", [])) if name == "search_manual" else (
            f"{args.get('manual_id')} стр. {args.get('page')}" if name == "read_page" else "")
        self.emit({"type": "step", "tool": name, "title": STEP_TITLES.get(name, name), "status": "running", "detail": detail})
        t0 = time.time()
        try:
            fn = getattr(self, "t_" + name, None)
            if fn is None:
                raise ValueError("неизвестный инструмент")
            out = fn(**args)
            status = "error" if isinstance(out, dict) and out.get("error") else "done"
            summ = out.get("error") if status == "error" else _summary(name, out)
        except clients.ServiceError as e:
            out, status, summ = {"error": f"{e.service}: {e.detail}"}, "error", f"{e.service} недоступен"
        except TypeError as e:
            out, status, summ = {"error": f"неверные аргументы: {e}"}, "error", "неверные аргументы"
        self.emit({"type": "step", "tool": name, "title": STEP_TITLES.get(name, name), "status": status,
                   "detail": (detail + " → " if detail else "") + summ + f" ({time.time() - t0:.1f} с)"})
        return json.dumps(out, ensure_ascii=False)


def _summary(name: str, out: dict) -> str:
    if name == "search_manual":
        return "найдено: " + ", ".join(f"стр. {p['page']}" for p in out.get("pages", [])) if out.get("pages") else "ничего не найдено"
    if name == "get_diagnosis":
        r, v = out["ml_result"], out["program_verdict"]
        return {"normal": "норма", "anomaly": f"отклонение {r.get('anomaly_type')}", "check_failed": "сбой записи"}[r["status"]] + \
            (f", приоритет {v['urgency']}" if v.get("urgency") else "")
    if name == "prepare_ticket":
        return f"черновик {out.get('draft_id')}"
    if name == "get_vehicle_history":
        return f"проверок: {len(out['sessions'])}, заявок: {len(out['tickets'])}"
    return "готово"


def confirm_ticket(draft_id: str, edits: dict) -> dict:
    """Единственный путь в ТОиР: вызывается кнопкой механика. Повторная проверка всех полей кодом."""
    found = find_draft(draft_id)
    if not found:
        raise ValueError("Черновик не найден или устарел. Попросите агента подготовить заявку заново.")
    conv, d = found
    if d.get("ticket_id"):
        return {"ticket_id": d["ticket_id"], "status": "created", "duplicate": True}
    payload = {
        "vehicle_id": d["vehicle_id"], "session_id": d["session_id"], "anomaly_type": d["anomaly_type"],
        "conclusion": (edits.get("conclusion") or d["conclusion"]).strip(),
        "urgency": edits.get("urgency") or d["urgency"],
        "operations": [o for o in (edits.get("operations") or d["operations"]) if str(o).strip()],
        "spare_parts": [p for p in (edits.get("spare_parts") if edits.get("spare_parts") is not None else d["spare_parts"]) if str(p).strip()],
        "references": [{"manual": r["manual"], "pdf_page": r["pdf_page"]} for r in d["references"]],
    }
    if payload["urgency"] not in ("low", "medium", "high"):
        raise ValueError("Приоритет должен быть low, medium или high.")
    if not payload["operations"] or not payload["conclusion"]:
        raise ValueError("Нужны диагноз и хотя бы одна работа.")
    res = clients.create_ticket(payload)
    d["ticket_id"] = res.get("ticket_id")
    manual_change = payload["urgency"] != d["urgency"]
    data.add_ticket({"ticket_id": d["ticket_id"], "vehicle_id": d["vehicle_id"], "session_id": d["session_id"],
                     "anomaly_type": d["anomaly_type"], "urgency": payload["urgency"], "conclusion": payload["conclusion"],
                     "urgency_changed_by_mechanic": manual_change})
    conv.messages.append({"role": "user", "content": f"[Система] Механик подтвердил черновик {draft_id}. "
                          f"ТОиР создал заявку {d['ticket_id']} (приоритет {payload['urgency']})."})
    return res
