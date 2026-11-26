# Контракт между модулями (внутренний документ спринта)

## Поиск по руководствам — `app/search.py`, `app/ingest.py`

```python
from app.search import Searcher
s = Searcher.load()                       # индекс из data/index/
hits = s.search(query: str, engine_model: str, k: int = 5, rewrites: list[str] | None = None) -> list[Hit]
# Hit: dict(manual_id, page:int (физическая страница PDF с 1), score:float, text:str (полный текст страницы), snippet:str)
s.page_text(manual_id: str, page: int) -> str           # текст страницы (текстовый слой + OCR картинок)
s.page_png(manual_id: str, page: int) -> pathlib.Path   # рендер страницы, кэш data/pages/<id>/<page>.png
```
Поиск только по `app.manuals.manuals_for_engine(engine_model)`. Сборка индекса: `python -m app.ingest`.

## HTTP API бэкенда — `app/main.py` (FastAPI), фронт — `web/` (статические файлы, без сборки)

- `GET /api/vehicles` → `[{vehicle_id, garage_no, make, model, vehicle_type, engine_model, fuel, last_check: {session_id, checked_at, status, anomaly_type, anomaly_title, anomaly_score, confidence, signal_quality} , fleet_status: "ok"|"attention"|"quarantine", open_ticket: str|null}]`
- `GET /api/vehicles/{vehicle_id}` → карточка + `sessions: [...]` (как в vehicles.json, с `checked_at`, от ранней к поздней) + `tickets: [{ticket_id, session_id, anomaly_type, urgency, created_at}]` + `manuals: [{id, title, designation}]`
- `GET /api/fleet` → `{counts: {ok, attention, quarantine}, priority: [vehicle summaries, отсортированы по срочности]}`
- `GET /api/manuals/{manual_id}/pages/{page}.png` → картинка страницы PDF; `GET /api/manuals/{manual_id}/pages/{page}` → `{manual_id, title, designation, page, pages_total, text}`
- `POST /api/chat` (ответ `text/event-stream`), тело `{conversation_id: str, vehicle_id: str, session_id: str|null, message: str, action: null|"diagnose"|"draft_ticket"}`. События (`data: <json>\n\n`):
  - `{"type":"step","tool":"get_diagnosis","title":"Запрос результата проверки в ML-сервис","status":"running"|"done"|"error","detail":str}` — журнал шагов агента
  - `{"type":"diagnosis","data":{...ответ /diagnose..., "verdict":"normal"|"anomaly"|"check_failed", "urgency":"low"|"medium"|"high"|null, "urgency_reasons":[str], "action":str}}` — карточка вердикта (данные из кода, не из модели)
  - `{"type":"message","text":markdown,"citations":[{"n":1,"manual_id":str,"title":str,"designation":str,"page":int,"quote":str}]}` — ответ агента; в тексте ссылки вида `[1]`
  - `{"type":"draft","draft":{"draft_id":str,"vehicle_id","session_id","anomaly_type","conclusion","urgency","urgency_reasons":[str],"operations":[str],"spare_parts":[str],"references":[{"manual","pdf_page","manual_id","title"}]}}` — черновик заявки, требует подтверждения человеком
  - `{"type":"error","text":str}`, `{"type":"done"}`
- `POST /api/tickets/confirm` `{draft_id, conclusion?, urgency?, operations?, spare_parts?}` → `{"ticket_id":"TKT-0001","status":"created"}` или 4xx `{detail}`. Только этот вызов отправляет заявку в ТОиР.
- `GET /api/health`
