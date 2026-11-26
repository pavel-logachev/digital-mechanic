"""Агент «Цифровой механик»: цикл LLM с инструментами.

Модель сама выбирает инструменты (ML, поиск по руководствам, заявка) – сценарий не зашит if-else (F5).
Всё, что можно проверить кодом, проверяет код: приоритет, привязку руководства к двигателю,
существование страниц и цифр, состав заявки. Отправка в ТОиР – только по кнопке человека.
"""
from __future__ import annotations

import json
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable

from . import clients, config, data, llm, verify
from .conflicts import conflicts_for
from .faults import FAULTS, SEVERITY_RU, applicability, page_covers_unit
from .manuals import BY_ID, manual_ids_for_engine, manuals_for_engine
from .priority import evaluate

MAX_STEPS = 8
LANGS = {"ru": "русском", "uz": "узбекском (латиница)", "tg": "таджикском (кириллица)", "ky": "киргизском",
         "kk": "казахском", "hi": "хинди", "en": "английском"}


def _dash(ev):
    """Длинное тире – признак машинного текста; в интерфейсе везде короткое."""
    if isinstance(ev, str):
        return ev.replace(" — ", " – ").replace("—", "–")
    if isinstance(ev, list):
        return [_dash(x) for x in ev]
    if isinstance(ev, dict):
        return {k: _dash(v) for k, v in ev.items()}
    return ev

SYSTEM = """Ты «Цифровой механик», помощник механика автопарка. Отвечай по-русски (или на языке из пометки [Язык ответа]), коротко и по делу, простыми словами, как опытный моторист коллеге. Без канцелярита. Тире пиши только коротким «–».

Машина в работе: {vehicle}. Двигатель: {engine}. Выбранная проверка: {session}.
Руководства на этот двигатель (других использовать нельзя): {manuals}.

Инструменты:
- get_diagnosis – результат акустической проверки из ML-сервиса и приоритет, рассчитанный программой. Вызывай, когда механик просит результат диагностики или спрашивает о состоянии двигателя по проверке.
- get_vehicle_history – карточка машины, прошлые проверки и заявки.
- search_manual – поиск по руководствам выбранного двигателя. Для вопроса о книге, норме, процедуре, запчасти или причинах симптома сначала вызови поиск, даже если в карточке есть проверка. Запросы по-русски, 1–3 короткие фразы: название узла и нужный параметр, затем синоним или заголовок раздела. Не закрепляй в запросе предложенную пользователем цифру как правильную. Если нужна вторая часть ответа, не достаёт строки таблицы или найден другой узел/режим – сделай один новый целевой поиск.
- read_page – полный текст конкретной страницы; читай продолжение на соседней странице, если отсутствует нужная строка, условия, единицы, этап процедуры или предупреждение.
- get_fault_reference – справка о классе неисправности F01–F14: тяжесть, риски, применимость к двигателю.
- prepare_ticket – подготовить черновик заявки на дефектовку. Вызывай только когда механик просит заявку (кнопка «Создать заявку» или слова), при объяснении результата не вызывай. Заявку отправляет механик кнопкой, ты не отправляешь и никогда не пишешь, что заявка создана. Готовь черновик, только когда нашёл в руководстве этого двигателя процедуру проверки, регулировки или ремонта именно узла из типа неисправности; работы и их порядок – из этих страниц. Если такой процедуры нет, черновик не готовь: скажи, что заявку продукт не отправляет, потому что в руководстве на этот двигатель нет инструкции по этому узлу, и дай короткий текст рекомендации на дефектовку с результатом проверки (машина, проверка, класс, оценка, уверенность).

Жёсткие правила:
1. После каждого существенного факта о норме, устройстве, причине или порядке работ ставь ссылку {{manual_id#страница}}, например {{yamz-236_rk_2014#123}}. Бери строки именно про запрошенную деталь, модификацию и режим; сверяй единицы, знаки, условия и исключения. Не добавляй лишние нормы, которых не спросили. Не смешивай одноимённые болты, соседние строки таблиц и эксплуатационные пределы с ремонтными.
2. Не придумывай. Различай: «этого нет в руководстве» (например, индивидуальное измерение, склад, ресурс по звуку, другой двигатель) и «не нашёл в доступных страницах». Если возможно, ответь на подтверждённую часть вопроса и явно назови недостающую. Когда технического ответа по двигателю (норматива, предела, причины) в руководстве нет, так и скажи и порекомендуй дефектовку – осмотр и замеры на посту, при необходимости заявку; для вопросов не про двигатель (пароли, цены, склад) дефектовку не советуй. Не выдавай диагностическую гипотезу за причину, установленную у этой машины.
3. Приоритет и действие по выбранной акустической проверке берёшь из get_diagnosis – не меняй. Это рекомендации программы: высокий – дефектовка до выпуска в рейс, средний – дефектовка на ближайшем ТО, машина работает под наблюдением, низкий – узел проверяется на следующей проверке. Приоритет механику называй словами «высокий», «средний», «низкий», а не кодами high/medium/low. Слова «нельзя», «запрещено», «эксплуатация не допускается» пиши, только если руководство на этот двигатель прямо запрещает эксплуатацию в таком состоянии, – и тогда ссылайся на эту страницу. Прежде чем написать, что прямого запрета нет, сделай целевой поиск запрета по этому узлу или признаку (search_manual: «не допускается эксплуатация …», «запрещается …», «немедленно остановить двигатель …»): если запрет нашелся – это запрет со ссылкой на страницу. Если и после поиска запрета нет – формулируй как рекомендацию («не рекомендую», «рекомендация – дефектовка до выпуска») и прямо скажи, что прямого запрета в руководстве нет. Не вызывай его и не рассказывай о текущей записи, когда спрашивают только о правилах из книги или возможных причинах описанного симптома. Для смешанного вопроса разделяй данные записи и справку: сбой записи не запрещает отвечать на отдельный вопрос о руководстве.
4. Если проверка «check_failed» или запись непригодна – никаких выводов о двигателе по этой записи и никакой заявки; попроси повторить запись. Для явно опасного предложенного действия сначала скажи, можно ли так делать, затем приведи предупреждение или условия из руководства. Не советуй работы на работающем двигателе или тестовую поездку по общей таблице неисправностей, если процедура этого не разрешает. Если страницы руководств этого двигателя противоречат друг другу, не выбирай одну формулировку как бесспорную: приведи обе со ссылками, прямо назови противоречие, предложи более осторожный вариант и посоветуй уточнить у специалиста или производителя для этой модификации; если условия безопасности неясны, не советуй начинать работу. Если search_manual вернул conflicts – это противоречие уже подтверждено заказчиком: покажи обе формулировки со ссылками refs и назови принятое правило из rule как консервативный вариант, а не как цитату руководства.
5. Если программа сообщила, что класс неисправности не подходит к двигателю – объясни это механику и предложи очный осмотр, не выдавай неисправность за подтверждённую.
6. ML даёт гипотезу по звуку, а не диагноз. Пиши «вероятно», «признаки указывают». Гипотезы о причинах и рисках явно помечай («вероятно», «возможная причина») и отделяй от того, что взято из руководства; гипотезу не оформляй как цитату и не ставь к ней ссылку. Числа (нормативы, допуски, моменты затяжки, давления) и порядок работ – только из руководства этого двигателя со ссылкой.
7. Если в руководстве есть порядок или последовательность (затяжки, регулировки, разборки) – перечисли её в чате нумерованным списком со ссылкой. Если порядок показан только цифрами на рисунке и текстом его прочитать нельзя – так и скажи и дай ссылку на страницу с рисунком.
8. На вопросы не про эту машину и не про ремонт/эксплуатацию – вежливо верни разговор к машине.
9. К механику обращайся на «вы», как к опытному коллеге: без панибратства и без сюсюканья. Букву «ё» не используй, тире – короткое «–».

Карточку вердикта (статус, оценка отклонения, уверенность, качество записи, приоритет и его основания) механик уже видит на экране – не пересказывай эти цифры и не повторяй вердикт. После get_diagnosis при отклонении сразу переходи к сути, коротко (до ~180 слов), в формате:
**Что, вероятно, не так** – 1–2 предложения.
**Чем грозит** – 1 предложение.
**Что проверить** – 3–5 нумерованных шагов с нормативами и ссылками.
**Ремонт и запчасти** – что заменить/отрегулировать, запчасти названиями из руководства со ссылкой.
**Ограничения** – одной строкой, чего нет в руководстве или что не известно.
Для нормы – 1–2 предложения (можно работать по данным этой проверки; если были прошлые отклонения – сказать). Для сбоя записи – 1–2 предложения: по этой записи о двигателе судить нельзя, нужна новая запись на посту при работе на холостом ходу; советы под причину отбраковки механик уже видит на карточке – не повторяй их и не придумывай методику записи, которой нет в данных.
Для ответов на вопросы: только нужное из «наблюдения → гипотезы → проверки → возможный ремонт → источник → ограничения», без воды.
"""

def _ref(r) -> tuple[str | None, int]:
    """Ссылка из аргументов модели: {"manual_id", "page"} или строка вида «{manual_id#page}»."""
    if isinstance(r, dict):
        try:
            return r.get("manual_id"), int(r.get("page") or r.get("pdf_page") or 0)
        except (TypeError, ValueError):
            return r.get("manual_id"), 0
    m = re.search(r"([a-z0-9_-]+)#(\d+)", str(r))
    return (m.group(1), int(m.group(2))) if m else (None, 0)


TICKET_INTENT = re.compile(r"заявк|ariza|дархост|арыз|өтінім|आवेदन|ticket|repair request", re.I)

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
        "name": "prepare_ticket", "description": "Подготовить черновик заявки на дефектовку по текущей проверке. Не отправляет – отправляет механик кнопкой",
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


URGENCY_RU = {"low": "низкий", "medium": "средний", "high": "высокий"}
_convs: dict[str, Conversation] = {}
_searcher = None
_confirm_lock = threading.Lock()


# Разговоры и черновики переживают перезапуск сервиса: после каждого ответа пишем их в STATE_DIR/conversations.
def _conv_path(cid: str):
    safe = "".join(ch for ch in cid if ch.isalnum() or ch in "-_")[:80] or "x"
    return config.STATE_DIR / "conversations" / f"{safe}.json"


def save_conversation(c: Conversation) -> None:
    try:
        path = _conv_path(c.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"id": c.id, "vehicle_id": c.vehicle_id, "session_id": c.session_id, "messages": c.messages,
                                   "seen": sorted([list(x) for x in c.seen]), "diagnosis": c.diagnosis, "verdict": c.verdict,
                                   "drafts": c.drafts}, ensure_ascii=False, default=str), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass  # потеря копии разговора не должна ломать ответ механику


def _load_conversation(cid: str) -> Conversation | None:
    try:
        raw = json.loads(_conv_path(cid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return Conversation(raw["id"], raw["vehicle_id"], raw.get("session_id"), raw.get("messages") or [],
                        {tuple(x) for x in raw.get("seen") or []}, raw.get("diagnosis"), raw.get("verdict"), raw.get("drafts") or {})


def searcher():
    global _searcher
    if _searcher is None:
        from .search import Searcher
        _searcher = Searcher.load()
    return _searcher


def get_conversation(cid: str, vehicle_id: str, session_id: str | None) -> Conversation:
    c = _convs.get(cid) or _load_conversation(cid)
    if c is not None:
        _convs[cid] = c
    if c is None or c.vehicle_id != vehicle_id or (session_id and c.session_id != session_id):
        c = Conversation(cid, vehicle_id, session_id)
        _convs[cid] = c
    return c


def find_draft(draft_id: str) -> tuple[Conversation, dict] | None:
    for c in _convs.values():
        if draft_id in c.drafts:
            return c, c.drafts[draft_id]
    # после перезапуска сервиса черновик ищем в сохраненных разговорах
    folder = config.STATE_DIR / "conversations"
    if folder.exists():
        for path in sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:500]:
            c = _load_conversation(path.stem)
            if c and draft_id in c.drafts:
                _convs[c.id] = c
                return c, c.drafts[draft_id]
    return None


class Agent:
    def __init__(self, conv: Conversation, emit: Callable[[dict], None], lang: str = "ru", detail: str = "brief"):
        self.c = conv
        self.detail = detail if detail in ("brief", "detailed") else "brief"
        self.lang = lang if lang in LANGS else "ru"
        self.emit = lambda ev: emit(_dash(ev))
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
        from .search import _passage, _tokens

        queries = [q for q in (queries or []) if isinstance(q, str) and q.strip()][:3] or ["двигатель"]
        terms = set(_tokens(" ".join(queries)))
        hits = searcher().search(queries[0], self.engine, k=7, rewrites=queries[1:])
        pages = []
        for h in hits:
            if h["manual_id"] not in self.allowed:
                continue
            self.c.seen.add((h["manual_id"], int(h["page"])))
            raw = h.get("text") or h.get("snippet") or ""
            pages.append({"ref": f"{{{h['manual_id']}#{h['page']}}}", "manual": BY_ID[h["manual_id"]].title,
                          "page": h["page"], "text": raw if len(raw) <= 3800 else _passage(raw, terms, 3800),
                          "excerpt": len(raw) > 3800})
        rr = getattr(searcher(), "rerank_stats", {}) or {}
        self._last_rerank = rr.get("status")
        out = {"engine": self.engine, "pages": pages,
               "reranked": rr.get("status") == "applied",
               "note": "Ссылайся на ref после факта. При excerpt=true нужный фрагмент может быть за пределами выдачи: вызови read_page. Если узел или раздел не совпадает – уточни запрос."}
        found = {(h["manual_id"], int(h["page"])) for h in hits if h["manual_id"] in self.allowed}
        if conflicts := conflicts_for(found, " ".join(queries), set(self.allowed)):
            for c in conflicts:   # ссылки обеих сторон противоречия считаются показанными агенту
                for ref in c["refs"]:
                    m, p = ref.strip("{}").split("#")
                    self.c.seen.add((m, int(p)))
            out["conflicts"] = conflicts
        return out

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
        if not getattr(self, "ticket_requested", True):
            return {"error": "Черновик заявки готовится только по просьбе механика – кнопкой «Создать заявку» или словами. "
                             "Сейчас его не готовь и не пиши, что он готов; закончи ответ, механик сам решит."}
        if not self.c.diagnosis or self.c.diagnosis.get("session_id") != self.c.session_id:
            self.t_get_diagnosis()
        res, verdict = self.c.diagnosis, self.c.verdict
        if res["status"] != "anomaly" or not verdict["ticket_allowed"]:
            if verdict.get("defect_note"):
                return {"error": "Заявку продукт не отправляет: в руководстве на этот двигатель нет инструкции по этому узлу. "
                                 "Передай механику текст рекомендации на дефектовку.", "defect_note": verdict["defect_note"]}
            why = "проверка в норме" if res["status"] == "normal" else "запись непригодна – нужна повторная запись"
            return {"error": f"Заявку по этой проверке создавать нельзя: {why}."}
        refs, bad = [], []
        for r in references or []:
            mid, page = _ref(r)
            if mid in self.allowed and (mid, page) in self.c.seen and 1 <= page <= BY_ID[mid].pages:
                if not any(x["manual_id"] == mid and x["pdf_page"] == page for x in refs):
                    refs.append({"manual": BY_ID[mid].designation, "pdf_page": page, "manual_id": mid, "title": BY_ID[mid].title})
            else:
                bad.append(f"{mid} стр. {page}")
        ops = [o.strip() for o in operations or [] if o and o.strip()]
        code = res.get("anomaly_type")
        if refs and not any(page_covers_unit(code, searcher().page_text(r["manual_id"], r["pdf_page"])) for r in refs):
            title = data.fault_titles().get(code) or code
            return {"error": f"Среди ссылок нет страницы с проверкой, регулировкой или ремонтом узла «{title}» для {self.engine}. "
                             "Найди такую процедуру через search_manual и сошлись на нее. Если в руководстве ее нет – черновик не готовь: "
                             "скажи механику, что заявку продукт не отправляет, и дай текст рекомендации на дефектовку."}
        if not refs:
            return {"error": "Нужна хотя бы одна ссылка на страницу руководства этого двигателя, найденную поиском. "
                             f"Отклонены: {', '.join(bad) or 'нет ссылок'}. Сначала найди процедуру через search_manual."}
        if not ops or not (conclusion or "").strip():
            return {"error": "Нужны диагноз и хотя бы одна работа."}
        draft = {"draft_id": "D-" + uuid.uuid4().hex[:8], "vehicle_id": self.v["vehicle_id"], "session_id": res["session_id"],
                 "anomaly_type": res["anomaly_type"], "conclusion": conclusion.strip(), "urgency": verdict["urgency"],
                 "urgency_reasons": verdict["urgency_reasons"], "warnings": verdict.get("warnings", []),
                 "operations": ops, "spare_parts": [p.strip() for p in spare_parts or [] if p and p.strip()],
                 "references": refs, "engine_model": self.engine,
                 # сомнительный сигнал: заявка уходит только с отметкой механика, что осмотр подтвердил признак
                 "needs_inspection": bool(verdict.get("inspect_first"))}
        self.c.drafts[draft["draft_id"]] = draft
        self.emit({"type": "draft", "draft": draft})
        out = {"draft_id": draft["draft_id"], "status": "черновик показан механику, ждет его подтверждения кнопкой",
               "urgency": draft["urgency"]}
        if bad:
            out["rejected_references"] = bad
        return out

    # ---------- цикл ----------
    def _system(self) -> dict:
        v = self.v
        mans = "; ".join(f"{m.id} – {m.title} ({m.designation})" for m in manuals_for_engine(self.engine))
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

    def run(self, user_text: str, ticket_requested: bool | None = None) -> None:
        # Черновик заявки – только по явной просьбе механика (кнопка «Создать заявку» или слова о заявке).
        # Набор инструментов не меняем (история вызовов должна оставаться валидной для любой модели) –
        # запрет проверяет сам инструмент.
        if ticket_requested is None:
            ticket_requested = bool(TICKET_INTENT.search(user_text))
        self.ticket_requested = ticket_requested
        with self.c.lock:
            msgs = self.c.messages
            if not msgs:
                msgs.append(self._system())
            note = "" if self.lang == "ru" else (
                f"\n\n[Язык ответа: отвечай на {LANGS[self.lang]} языке. Запросы в search_manual – по-русски. "
                "Цитаты из руководства оставляй по-русски в кавычках и сразу поясняй смысл на языке ответа. Цифры – арабские.]")
            if self.detail == "detailed":
                note += ("\n\n[Режим «Подробно»: механик начинающий. Объясняй каждый шаг простыми словами: где находится узел, "
                         "чем откручивать и что должно получиться; термины поясняй в скобках. Объём можно больше, точность и ссылки – те же.]")
            msgs.append({"role": "user", "content": user_text + note})
            retried = False
            first_problems: list[str] = []
            for _ in range(MAX_STEPS):
                m = llm.chat(msgs, TOOLS, self.c.usage)
                if m.tool_calls:
                    msgs.append({"role": "assistant", "content": m.content or "",
                                 "tool_calls": [tc.model_dump() for tc in m.tool_calls]})
                    for tc in m.tool_calls:
                        msgs.append({"role": "tool", "tool_call_id": tc.id, "content": self._call(tc)})
                    continue
                answer = (m.content or "").strip()
                # цифры из вопросов механика – его данные, а не нормативы: их не требуем подтверждать страницей
                asked = " ".join(m["content"] for m in msgs if m["role"] == "user" and isinstance(m.get("content"), str)
                                 and not m["content"].startswith("[Проверка программы]"))
                checked = verify.check(answer, self.allowed, self.c.seen, searcher().page_text,
                                       self._context_numbers() | verify.page_numbers(asked))
                if checked.problems and not retried:
                    retried = True
                    first_problems = checked.problems
                    msgs.append({"role": "assistant", "content": answer})
                    self.emit({"type": "step", "tool": "verify", "title": "Проверка цифр и ссылок", "status": "error",
                               "detail": "; ".join(checked.problems)[:400]})
                    msgs.append({"role": "user", "content": "[Проверка программы] В ответе найдены проблемы: "
                                 + "; ".join(checked.problems)
                                 + ". Исправь ответ: каждую цифру подтверди страницей, которую получил инструментом "
                                   "(при необходимости поищи ещё), или убери её и честно скажи, что в руководстве этого нет. "
                                   "Пришли исправленный ответ целиком, как будто пишешь впервые – без слов «исправленный ответ», «перепроверил» и т. п."})
                    continue
                if checked.problems:
                    checked.text += "\n\n_Часть сведений не удалось подтвердить по руководству: проверьте по ссылкам перед работой._"
                msgs.append({"role": "assistant", "content": answer})
                self.emit({"type": "step", "tool": "verify", "title": "Проверка цифр и ссылок", "status": "done",
                           "detail": f"ссылок: {len(checked.citations)}" + (f", замечаний: {len(checked.problems)}" if checked.problems else ", все подтверждено")})
                self.emit({"type": "message", "text": checked.text, "citations": checked.citations,
                           "usage": self.c.usage.as_dict(), "unverified": checked.problems,
                           "first_pass_problems": first_problems})
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
        found = "найдено: " + ", ".join(f"стр. {p['page']}" for p in out.get("pages", [])) if out.get("pages") else "ничего не найдено"
        return found + (" · ранжирование Jev" if out.get("reranked") else "")
    if name == "get_diagnosis":
        r, v = out["ml_result"], out["program_verdict"]
        return {"normal": "норма", "anomaly": f"отклонение {r.get('anomaly_type')}", "check_failed": "сбой записи"}[r["status"]] + \
            (f", приоритет {v['urgency']}" if v.get("urgency") else "")
    if name == "prepare_ticket":
        return f"черновик {out.get('draft_id')}"
    if name == "get_vehicle_history":
        return f"проверок: {len(out['sessions'])}, заявок: {len(out['tickets'])}"
    return "готово"


def confirm_ticket(draft_id: str, edits: dict, author: str | None = None) -> dict:
    """Единственный путь в ТОиР: вызывается кнопкой механика. Повторная проверка всех полей кодом.
    Двойное нажатие и повтор запроса не создают вторую заявку: подтверждения идут по одному."""
    with _confirm_lock:
        return _confirm(draft_id, edits, author)


def _confirm(draft_id: str, edits: dict, author: str | None = None) -> dict:
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
    if d.get("needs_inspection") and edits.get("inspection_confirmed") is not True:
        raise ValueError("Сигнал сомнительный: сначала осмотрите узел и отметьте, что осмотр подтвердил признак.")
    if payload["urgency"] not in ("low", "medium", "high"):
        raise ValueError("Приоритет должен быть low, medium или high.")
    if not payload["operations"] or not payload["conclusion"]:
        raise ValueError("Нужны диагноз и хотя бы одна работа.")
    res = clients.create_ticket(payload)
    d["ticket_id"] = res.get("ticket_id")
    manual_change = payload["urgency"] != d["urgency"]
    data.add_ticket({"ticket_id": d["ticket_id"], "vehicle_id": d["vehicle_id"], "session_id": d["session_id"],
                     "anomaly_type": d["anomaly_type"], "urgency": payload["urgency"], "conclusion": payload["conclusion"],
                     "urgency_changed_by_mechanic": manual_change, "created_by": author,
                     "inspection_confirmed": bool(edits.get("inspection_confirmed"))})
    conv.messages.append({"role": "user", "content": f"[Система] Механик подтвердил черновик {draft_id}. "
                          f"ТОиР создал заявку {d['ticket_id']} (приоритет {URGENCY_RU.get(payload['urgency'], payload['urgency'])})."})
    save_conversation(conv)
    return res
