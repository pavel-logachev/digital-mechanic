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

LLM_BASE_URL = env("LLM_BASE_URL", "https://api.deepseek.com")
LLM_API_KEY = env("LLM_API_KEY")
LLM_MODEL = env("LLM_MODEL", "deepseek-flash")

RERANK_ENABLED = env("RERANK_ENABLED", "1") == "1"
OPENROUTER_API_KEY = env("OPENROUTER_API_KEY")
OPENROUTER_PROXY = env("OPENROUTER_PROXY")  # например socks5h://atr-sing-box:1080
JEV_MODEL = env("JEV_MODEL", "typesafe/jev-1.13")
EMBED_MODEL = env("EMBED_MODEL", "intfloat/multilingual-e5-small")

ACCESS_PASSWORD = env("ACCESS_PASSWORD")  # пусто = стенд открыт
