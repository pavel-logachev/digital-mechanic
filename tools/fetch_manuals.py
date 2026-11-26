"""Скачать 6 руководств заказчика с его публичной папки Яндекс Диска в data/manuals/ под именами из app/manuals.py.

python -m tools.fetch_manuals
"""
import json
import urllib.parse
import urllib.request

from app import config

PUBLIC = "https://disk.yandex.ru/d/QdAA8p4m0ySe8Q"
NAMES = {  # имя файла на Диске заказчика -> id руководства
    "ЯМЗ_236_руководство по эксплуатации.pdf": "yamz-236_re_2010",
    "ЯМЗ_236_руководство по РЕМОНТУ.pdf": "yamz-236_rk_2014",
    "yamz-536_re_2016.pdf": "yamz-536_re_2016",
    "yamz-536_rk_2013.pdf": "yamz-536_rk_2013",
    "zmz-5234_rk_2025.pdf": "zmz-5234_rk_2025",
    "zmz-40904-40905_rk_2025.pdf": "zmz-40904-40905_rk_2025",
}


def main():
    q = urllib.parse.urlencode({"public_key": PUBLIC, "limit": 200})
    items = json.load(urllib.request.urlopen(f"https://cloud-api.yandex.net/v1/disk/public/resources?{q}", timeout=60))
    config.MANUALS_DIR.mkdir(parents=True, exist_ok=True)
    for it in items["_embedded"]["items"]:
        mid = NAMES.get(it["name"])
        if not mid:
            continue
        dst = config.MANUALS_DIR / f"{mid}.pdf"
        if dst.exists() and dst.stat().st_size == it.get("size"):
            print("есть", dst.name)
            continue
        print("скачиваю", it["name"], "→", dst.name, flush=True)
        urllib.request.urlretrieve(it["file"], dst)


if __name__ == "__main__":
    main()
