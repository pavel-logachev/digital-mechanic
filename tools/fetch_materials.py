"""Скачать материалы задачи из публичной папки заказчика: 6 руководств в data/manuals/ и заглушки ML и ТОиР в mocks/.

Ссылка на папку – из материалов задачи в личном кабинете ИИкузницы, в переменной окружения MATERIALS_URL
(.env или окружение). В коде и в Git ее нет: так просили организаторы, материалы задачи в открытый репозиторий не кладем.

python -m tools.fetch_materials
"""
import io
import json
import sys
import urllib.parse
import urllib.request
import zipfile

from app import config

MANUALS = {  # имя файла в папке заказчика -> id руководства из app/manuals.py
    "ЯМЗ_236_руководство по эксплуатации.pdf": "yamz-236_re_2010",
    "ЯМЗ_236_руководство по РЕМОНТУ.pdf": "yamz-236_rk_2014",
    "yamz-536_re_2016.pdf": "yamz-536_re_2016",
    "yamz-536_rk_2013.pdf": "yamz-536_rk_2013",
    "zmz-5234_rk_2025.pdf": "zmz-5234_rk_2025",
    "zmz-40904-40905_rk_2025.pdf": "zmz-40904-40905_rk_2025",
}
MOCKS_ZIP = "neurodvs_hackathon_mock_"  # начало имени архива с заглушками
MOCKS_DIR = config.ROOT / "mocks"
API = "https://cloud-api.yandex.net/v1/disk/public/resources"


def listing(public_url: str) -> list[dict]:
    q = urllib.parse.urlencode({"public_key": public_url, "limit": 200})
    with urllib.request.urlopen(f"{API}?{q}", timeout=60) as r:
        return json.load(r)["_embedded"]["items"]


def fetch_manuals(items: list[dict]) -> None:
    config.MANUALS_DIR.mkdir(parents=True, exist_ok=True)
    for it in items:
        mid = MANUALS.get(it["name"])
        if not mid:
            continue
        dst = config.MANUALS_DIR / f"{mid}.pdf"
        if dst.exists() and dst.stat().st_size == it.get("size"):
            print("есть", dst.name)
            continue
        print("скачиваю", it["name"], "->", dst.name, flush=True)
        urllib.request.urlretrieve(it["file"], dst)


def fetch_mocks(items: list[dict]) -> None:
    """Архив заглушек распаковывается в mocks/ без изменений (корневая папка архива срезается)."""
    archive = next((it for it in items if it["name"].startswith(MOCKS_ZIP) and it["name"].endswith(".zip")), None)
    if archive is None:
        sys.exit("в папке нет архива с заглушками " + MOCKS_ZIP + "*.zip")
    with urllib.request.urlopen(archive["file"], timeout=120) as r:
        zf = zipfile.ZipFile(io.BytesIO(r.read()))
    for info in zf.infolist():
        rel = info.filename.split("/", 1)[1] if "/" in info.filename else ""
        if not rel or info.is_dir():
            continue
        dst = (MOCKS_DIR / rel).resolve()
        if MOCKS_DIR.resolve() not in dst.parents:  # защита от путей вида ../ в архиве
            sys.exit("подозрительный путь в архиве: " + info.filename)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(zf.read(info))
    print("заглушки распакованы в", MOCKS_DIR)


def main() -> None:
    url = config.env("MATERIALS_URL")
    if not url:
        sys.exit("задайте MATERIALS_URL – ссылку на материалы задачи из личного кабинета (см. .env.example)")
    items = listing(url)
    fetch_manuals(items)
    fetch_mocks(items)


if __name__ == "__main__":
    main()
