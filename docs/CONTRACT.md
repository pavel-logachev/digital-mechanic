# Контракт между модулями (внутренний документ спринта)

## Поиск по руководствам – `app/search.py`, `app/ingest.py`

```python
from app.search import Searcher
s = Searcher.load()                       # индекс из data/index/
hits = s.search(query: str, engine_model: str, k: int = 5, rewrites: list[str] | None = None) -> list[Hit]
# Hit: dict(manual_id, page:int (физическая страница PDF с 1), score:float, text:str (полный текст страницы), snippet:str)
s.page_text(manual_id: str, page: int) -> str           # текст страницы (текстовый слой + OCR картинок)
s.page_png(manual_id: str, page: int) -> pathlib.Path   # рендер страницы, кэш data/pages/<id>/<page>.png
```
Поиск только по `app.manuals.manuals_for_engine(engine_model)`. Сборка индекса: `python -m app.ingest`.

## HTTP API бэкенда – `app/main.py` (FastAPI), фронт – `web/` (статические файлы, без сборки)

- `GET /api/vehicles` → `[{vehicle_id, garage_no, make, model, vehicle_type, engine_model, fuel, last_check: {session_id, checked_at, status, anomaly_type, anomaly_title, anomaly_score, confidence, signal_quality} , fleet_status: "ok"|"attention"|"quarantine", open_ticket: str|null}]`
- `GET /api/vehicles/{vehicle_id}` → карточка + `sessions: [...]` (как в vehicles.json, с `checked_at`, от ранней к поздней) + `tickets: [{ticket_id, session_id, anomaly_type, urgency, created_at}]` + `manuals: [{id, title, designation}]`
- `GET /api/fleet` → `{counts: {ok, attention, quarantine}, priority: [vehicle summaries, отсортированы по срочности]}`
- `GET /api/manuals/{manual_id}/pages/{page}.png` → картинка страницы PDF; `GET /api/manuals/{manual_id}/pages/{page}` → `{manual_id, title, designation, page, pages_total, text}`
- `POST /api/chat` (ответ `text/event-stream`), тело `{conversation_id: str, vehicle_id: str, session_id: str|null, message: str, action: null|"diagnose"|"draft_ticket"}`. События (`data: <json>\n\n`):
  - `{"type":"step","tool":"get_diagnosis","title":"Запрос результата проверки в ML-сервис","status":"running"|"done"|"error","detail":str}` – журнал шагов агента
  - `{"type":"diagnosis","data":{...ответ /diagnose..., "verdict":"normal"|"anomaly"|"check_failed", "urgency":"low"|"medium"|"high"|null, "urgency_reasons":[str], "action":str}}` – карточка вердикта (данные из кода, не из модели)
  - `{"type":"message","text":markdown,"citations":[{"n":1,"manual_id":str,"title":str,"designation":str,"page":int,"quote":str}]}` – ответ агента; в тексте ссылки вида `[1]`
  - `{"type":"draft","draft":{"draft_id":str,"vehicle_id","session_id","anomaly_type","conclusion","urgency","urgency_reasons":[str],"operations":[str],"spare_parts":[str],"references":[{"manual","pdf_page","manual_id","title"}]}}` – черновик заявки, требует подтверждения человеком
  - `{"type":"error","text":str}`, `{"type":"done"}`
- `POST /api/tickets/confirm` `{draft_id, conclusion?, urgency?, operations?, spare_parts?}` → `{"ticket_id":"TKT-0001","status":"created"}` или 4xx `{detail}`. Только этот вызов отправляет заявку в ТОиР.
- `GET /api/health`

## Дополнения 26.11 (после кик-оффа)
- `POST /api/chat` принимает поле `lang`: `"ru"|"uz"|"tg"|"ky"|"kk"|"hi"|"en"` (по умолчанию `"ru"`). Агент отвечает на этом языке; цитаты из руководств остаются на русском (оригинал), рядом агент дает перевод смысла. Текст карточки вердикта (`action`, `urgency_reasons`, `warnings`) пока на русском, интерфейс переводит свои подписи сам.
- `POST /api/transcribe` (multipart/form-data, поле `audio` – webm/ogg/mp4/wav до 60 с, поле `lang` – подсказка) → `{"text": str, "lang": str}`. Голосовой вопрос: интерфейс записывает звук через MediaRecorder, получает текст, показывает его в поле ввода, механик может поправить и отправить.
- Во всех текстах интерфейса – короткое тире «–», не длинное «—».

## Дополнения 26.11, после разбора записи кик-оффа
- `POST /api/chat` принимает `detail`: `"brief"` (по умолчанию) | `"detailed"` – режим «Подробно» для начинающего механика: агент объясняет каждый шаг простыми словами.
- В карточке вердикта (`diagnosis.data`) новое поле `inspect_first: bool` – сигнал сомнительный (запись с помехами или уверенность ниже 0,6). Перезапись не нужна, но заявку можно отправлять только после того, как механик подтвердил признак осмотром (чекбокс в черновике). CTO заказчика на кик-оффе: «уверенность 0,56 – новая запись не нужна, можно идти смотреть мотор».
- Журнал: каждое обращение, голосовой вопрос (только текст) и отправленная заявка пишутся в `STATE_DIR/audit.jsonl`.
