"""Проверка ответа агента кодом: ссылки на страницы и цифры нормативов.

Модель ставит ссылки в виде {manual_id#page}. Код:
1) оставляет только ссылки на руководства двигателя этой машины и только на страницы,
   которые агент действительно получил инструментами в этом диалоге;
2) проверяет, что каждое число из предложения со ссылкой есть на процитированной странице;
3) превращает ссылки в [1], [2] и подбирает точную цитату со страницы.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .manuals import BY_ID

TAG = re.compile(r"\{([a-z0-9\-_]+)#(\d{1,4})\}")
NUM = re.compile(r"(?<![\w.,])(\d+(?:[.,]\d+)?)(?![\w])")
LIST_MARK = re.compile(r"^\s*(?:\d+[.)]|[-*•])\s+", re.M)
# даты, коды проверок и классов, номера заявок — не нормативы
NOT_NORM = re.compile(r"\b\d{1,2}\.\d{1,2}(?:\.\d{2,4})?\b|\b[SF]-?\d{2,4}\b|TKT-\d+|\b(?:19|20)\d{2}\b(?:\s*г)?", re.I)


@dataclass
class Checked:
    text: str
    citations: list[dict] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def _norm_num(s: str) -> str:
    s = s.replace(",", ".")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def page_numbers(text: str) -> set[str]:
    t = re.sub(r"(?<=\d)[ \u00a0](?=\d{3}\b)", "", text)  # «1 500» -> «1500»
    return {_norm_num(m) for m in NUM.findall(t)}


def _significant(n: str) -> bool:
    v = n.replace(",", ".")
    try:
        f = float(v)
    except ValueError:
        return False
    return "." in v or "," in n or f >= 10


def check(answer: str, allowed: set[str], seen: set[tuple[str, int]], page_text, context_numbers: set[str]) -> Checked:
    """allowed — id руководств двигателя; seen — (id, page), полученные инструментами; page_text(id, page) -> str."""
    problems: list[str] = []
    order: dict[tuple[str, int], int] = {}
    cites: list[dict] = []

    def ref(mid: str, page: int) -> str:
        key = (mid, page)
        if mid not in allowed:
            problems.append(f"ссылка на чужое руководство {mid} (не для двигателя этой машины)")
            return ""
        if mid not in BY_ID or page < 1 or page > BY_ID[mid].pages:
            problems.append(f"несуществующая страница {mid} стр. {page}")
            return ""
        if key not in seen:
            problems.append(f"ссылка на страницу {mid} стр. {page}, которую агент не открывал")
            return ""
        if key not in order:
            order[key] = len(order) + 1
        return f"[{order[key]}]"

    # проверка чисел по предложениям/строкам
    for line in re.split(r"(?<=[.!?])\s+|\n", answer):
        tags = [(m, int(p)) for m, p in TAG.findall(line)]
        body = LIST_MARK.sub("", TAG.sub(" ", line))
        body_n = NOT_NORM.sub(" ", body)
        nums = [n for n in NUM.findall(body_n) if _significant(n)]
        nums = [n for n in nums if _norm_num(n) not in context_numbers]
        if not nums:
            continue
        valid = [(m, p) for m, p in tags if m in allowed and (m, p) in seen]
        if not valid:
            problems.append(f"цифры без ссылки на страницу руководства: «{body.strip()[:120]}»")
            continue
        on_pages = set().union(*(page_numbers(page_text(m, p)) for m, p in valid))
        missing = [n for n in nums if _norm_num(n) not in on_pages]
        if missing:
            problems.append(f"числа {', '.join(missing)} не найдены на указанных страницах: «{body.strip()[:120]}»")

    text = TAG.sub(lambda m: ref(m.group(1), int(m.group(2))), answer)
    text = re.sub(r"(\[\d+\])(?:\s*\1)+", r"\1", text)
    for (mid, page), n in sorted(order.items(), key=lambda kv: kv[1]):
        m = BY_ID[mid]
        cites.append({"n": n, "manual_id": mid, "title": m.title, "designation": m.designation, "page": page,
                      "quote": quote_for(answer, mid, page, page_text(mid, page))})
    return Checked(text, cites, problems)


def quote_for(answer: str, mid: str, page: int, ptext: str) -> str:
    """Точная цитата со страницы: фрагмент вокруг числа из ответа или самая похожая строка."""
    tag = f"{{{mid}#{page}}}"
    sents = [s for s in re.split(r"(?<=[.!?])\s+|\n", answer) if tag in s]
    flat = re.sub(r"\s+", " ", ptext)
    for s in sents:
        for n in NUM.findall(TAG.sub(" ", s)):
            if not _significant(n):
                continue
            for variant in {n, n.replace(".", ","), n.replace(",", ".")}:
                i = flat.find(variant)
                if i >= 0:
                    a, b = max(0, i - 140), min(len(flat), i + 120)
                    return ("…" if a else "") + flat[a:b].strip() + ("…" if b < len(flat) else "")
    words = {w for s in sents for w in re.findall(r"[а-яёa-z]{5,}", s.lower())}
    best, score = "", 0
    for line in re.split(r"(?<=[.;:])\s+|\n", ptext):
        lw = set(re.findall(r"[а-яёa-z]{5,}", line.lower()))
        sc = len(words & lw)
        if sc > score and 20 < len(line) < 400:
            best, score = line.strip(), sc
    return best or flat[:220]
