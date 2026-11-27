"""Настройки из окружения (.env). URL внешних сервисов меняются без правки кода (F6 ТЗ)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


ML_URL = env("ML_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/")
TOIR_URL = env("TOIR_SERVICE_URL", "http://127.0.0.1:8002").rstrip("/")
VEHICLES_PATH = Path(env("VEHICLES_PATH", str(ROOT / "mocks" / "data" / "vehicles.json")))
FAULT_TYPES_PATH = Path(env("FAULT_TYPES_PATH", str(ROOT / "mocks" / "data" / "fault_types.json")))
MANUALS_DIR = Path(env("MANUALS_DIR", str(ROOT / "data" / "manuals")))
INDEX_DIR = Path(env("INDEX_DIR", str(ROOT / "data" / "index")))
PAGES_DIR = Path(env("PAGES_DIR", str(ROOT / "data" / "pages")))
STATE_DIR = Path(env("STATE_DIR", str(ROOT / "data" / "state")))
# контрольные вопросы и трассы оценки содержат фрагменты руководств – хранятся вне Git (требование организаторов)
EVAL_DATA_DIR = Path(env("EVAL_DATA_DIR", str(ROOT / "data" / "eval")))

LLM_BASE_URL = env("LLM_BASE_URL", "https://api.deepseek.com")
LLM_API_KEY = env("LLM_API_KEY")
LLM_MODEL = env("LLM_MODEL", "deepseek-flash")

RERANK_ENABLED = env("RERANK_ENABLED", "1") == "1"
OPENROUTER_API_KEY = env("OPENROUTER_API_KEY")
OPENROUTER_PROXY = env("OPENROUTER_PROXY")  # например socks5h://atr-sing-box:1080
JEV_MODEL = env("JEV_MODEL", "typesafe/jev-1.13")
EMBED_MODEL = env("EMBED_MODEL", "intfloat/multilingual-e5-small")
STT_MODEL = env("STT_MODEL", "google/gemini-3.5-flash-lite")  # распознавание голосовых вопросов

ACCESS_PASSWORD = env("ACCESS_PASSWORD")  # общий пароль стенда; пусто = стенд открыт
# Учетные записи для работы в автопарке: механики и главные механики (tools/users.py). Если файл есть –
# вход по логину и паролю, роли и автор заявки в журнале; общий ACCESS_PASSWORD тогда не используется.
USERS_FILE = Path(env("USERS_FILE", str(STATE_DIR / "users.json")))
SESSION_DAYS = int(env("SESSION_DAYS", "30"))

# Резервная модель: если основная LLM не ответила (сбой, таймаут, лимит), запрос уходит сюда через OpenRouter.
# Пусто – резерв выключен. На контрольном наборе (72 вопроса) Gemini 3.5 Flash Lite – 69/72, DeepSeek Flash – 71/72 (eval/QUALITY.md).
LLM_FALLBACK_MODEL = env("LLM_FALLBACK_MODEL", "google/gemini-3.5-flash-lite")
# Сколько дней хранить журнал работы (STATE_DIR/audit/ГГГГ-ММ.jsonl, файл на месяц); старые файлы удаляются
AUDIT_RETENTION_DAYS = int(env("AUDIT_RETENTION_DAYS", "180"))
