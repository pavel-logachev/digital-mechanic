"""Тексты интерфейса не расходятся с самим интерфейсом.

Инструкция ссылается на кнопки по названию («Отправить заявку», «Как пользоваться»). Если кнопку убрали или
переименовали, тест падает: в инструкции не должно остаться упоминаний того, чего на экране нет.
"""
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
DYNAMIC = ("guide", "fault")   # ключи, которые собираются в коде: t(`guide${n}Text`), t(`fault${code}`)


def entries() -> list[tuple[str, list[str]]]:
    out = []
    for line in (WEB / "i18n.js").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Za-z0-9]+)\|(.*)$", line)
        if m:
            out.append((m.group(1), m.group(2).split("|")))
    return out


def dictionary() -> dict[str, list[str]]:
    return dict(entries())


def test_keys_are_unique():
    # повтор ключа молча перекрывает первую строку – правка первой ни на что не влияет
    keys = [k for k, _ in entries()]
    assert not {k for k in keys if keys.count(k) > 1}


def ui_source() -> str:
    return (WEB / "app.js").read_text(encoding="utf-8") + (WEB / "index.html").read_text(encoding="utf-8")


def test_every_language_has_every_string():
    rows = dictionary()
    widths = {len(v) for v in rows.values()}
    assert widths == {7}, {k: len(v) for k, v in rows.items() if len(v) != 7}
    assert not [k for k, v in rows.items() if any(not s.strip() for s in v)]


def test_no_dead_strings():
    src = ui_source()
    dead = [k for k in dictionary() if not k.startswith(DYNAMIC) and not re.search(rf"['\"`]{k}['\"`]", src)]
    assert not dead, f"строки без места в интерфейсе: {dead}"


def test_guide_mentions_only_existing_buttons():
    rows, src = dictionary(), ui_source()
    used = {k for k in rows if re.search(rf"['\"`]{k}['\"`]", src) and not k.startswith("guide")}
    for lang in range(7):
        labels = {v[lang] for k, v in rows.items() if k in used}
        for key in (k for k in rows if re.fullmatch(r"guide\d+Text", k)):
            for quoted in re.findall(r"«([^»]+)»", rows[key][lang]):
                if quoted.endswith("?"):   # пример вопроса механика, а не кнопка
                    continue
                assert quoted in labels, f"{key}[{lang}]: «{quoted}» – такой кнопки в интерфейсе нет"
