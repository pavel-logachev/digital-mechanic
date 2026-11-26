"""Приоритет (urgency) заявки и рекомендуемое действие – детерминированно, в коде.

Модель приоритет не выбирает: она только объясняет механику результат этой функции.
Пороги – политика команды (версия PRIO-2), не норматив заказчика.

Смысл приоритетов – по разъяснению заказчика (чат задачи #102):
  high   – машина ставится на дефектовку до выпуска в рейс;
  medium – дефектовка на ближайшем ТО, машина работает под наблюдением;
  low    – машина работает, узел проверяется на следующей проверке.
Это рекомендации. Запрет эксплуатации формулирует только агент и только когда руководство на этот двигатель
прямо его содержит – со ссылкой на страницу.
Схема: базовая тяжесть класса F01–F14 (faults.py) + ограниченная поправка по оценке, уверенности, качеству записи,
повторам и росту по истории. Порог сомнительного сигнала CONF_MIN = 0,60: ниже него и при записи с помехами
заявка возможна только после того, как механик осмотрел узел и подтвердил признак (разъяснение #101).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .faults import ENGINE_DRIVE_NOTE, FAULTS, SEVERITY_RU, applicability

POLICY_VERSION = "PRIO-2"
SCORE_HIGH = Decimal("0.70")
CONF_HIGH = Decimal("0.80")
CONF_MIN = Decimal("0.60")
TREND_DELTA = Decimal("0.15")
HISTORY_LIMIT = 5

QUALITY_RU = {"good": "хорошая", "warning": "с помехами", "bad": "непригодна"}


def d(x) -> Decimal:
    return Decimal(str(x))


def fmt(x) -> str:
    return "нет" if x is None else f"{x:.2f}".replace(".", ",")


@dataclass
class Verdict:
    verdict: str                 # normal | anomaly | check_failed
    urgency: str | None          # low | medium | high | None (заявка не нужна/запрещена)
    action: str                  # что делать механику сейчас, одной фразой
    ticket_allowed: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    rule: str = ""
    severity: str | None = None
    applicable: str | None = None
    inspect_first: bool = False     # сигнал сомнительный: заявка только после подтверждения осмотром
    policy: str = POLICY_VERSION
    defect_note: str | None = None  # текст рекомендации на дефектовку, когда продукт заявку не отправляет

    def as_dict(self) -> dict:
        return {
            "verdict": self.verdict, "urgency": self.urgency, "action": self.action,
            "ticket_allowed": self.ticket_allowed, "urgency_reasons": self.reasons,
            "warnings": self.warnings, "rule": self.rule, "severity": self.severity,
            "applicable": self.applicable, "policy": self.policy, "inspect_first": self.inspect_first,
            "defect_note": self.defect_note, "conf_threshold": float(CONF_MIN),
        }


def _history_window(sessions: list[dict], session_id: str) -> list[dict]:
    """Проверки до выбранной включительно, последние HISTORY_LIMIT. Будущие не учитываем."""
    idx = next((i for i, s in enumerate(sessions) if s["session_id"] == session_id), None)
    if idx is None:
        return []
    return sessions[max(0, idx - HISTORY_LIMIT + 1): idx + 1]


def _usable(s: dict) -> bool:
    return (s["status"] in ("normal", "anomaly") and s.get("signal_quality") in ("good", "warning")
            and s.get("confidence") is not None and d(s["confidence"]) >= CONF_MIN)


def evaluate(result: dict, engine: str, sessions: list[dict], tickets: list[dict] | None = None) -> Verdict:
    """result – ответ /diagnose; sessions – история этой машины по времени; tickets – уже созданные заявки."""
    tickets = tickets or []
    status, quality = result["status"], result.get("signal_quality")
    window = _history_window(sessions, result["session_id"]) or [result]
    past = [s for s in window if s["session_id"] != result["session_id"]]

    # 1. Плохая запись – абсолютный приоритет: никаких выводов о двигателе и заявки.
    if status == "check_failed" or quality == "bad":
        return Verdict("check_failed", None, "Запишите звук двигателя еще раз: по этой записи судить нельзя.",
                       False, ["Запись непригодна для анализа, оценка и уверенность не используются.",
                               "Заявка по этой проверке не создается."], rule="R1-bad")

    score, conf = result.get("anomaly_score"), result.get("confidence")
    hist_note = _history_note(past)

    if status == "normal":
        v = Verdict("normal", None, "По звуку двигателя отклонений нет. Работайте по обычному графику ТО.", False,
                    [f"Оценка отклонения {fmt(score)} из 1 – низкая, уверенность модели {fmt(conf)}, запись {QUALITY_RU.get(quality, quality)}.",
                     "Это результат одной акустической проверки, а не акт технического состояния."], rule="R2-normal")
        if quality == "warning" or (conf is not None and d(conf) < CONF_MIN):
            v.action = "Результат «норма» под сомнением: запись с помехами или низкая уверенность. Лучше повторить запись."
            v.rule = "R2-normal-doubt"
            v.warnings.append(_doubt_text(quality, conf))
        unresolved = _unresolved_critical(past, tickets)
        if unresolved:
            s = unresolved[-1]
            v.warnings.append(
                f"Раньше ({_date(s)}, {s['session_id']}) было критичное отклонение {s['anomaly_type']} «{s['anomaly_title']}», "
                "заявки по нему нет. Текущая «норма» не подтверждает, что неисправность устранена – нужен осмотр.")
            v.action = "Проверка в норме, но прошлое критичное отклонение не закрыто: осмотрите машину перед выпуском."
            v.rule = "R2-normal-unresolved"
        if hist_note:
            v.reasons.append(hist_note)
        return v

    # status == anomaly
    code = result.get("anomaly_type")
    f = FAULTS.get(code)
    appl = applicability(code, engine) if code else "no"
    sev = f["severity"] if f else None
    reasons: list[str] = []
    warnings: list[str] = []

    if appl == "no":
        note = ENGINE_DRIVE_NOTE.get(code, "Такой класс неисправности не соответствует этому двигателю.")
        warnings.append(f"Класс {code} «{result.get('anomaly_title')}» не подходит к двигателю {engine}. {note} "
                        "Вероятна ошибка ML-модели или карточки машины – нужен очный осмотр, диагноз по этой записи не подтвержден.")
        if quality == "warning" or (conf is not None and d(conf) < CONF_MIN):
            warnings.append(_doubt_text(quality, conf))   # #101: при warning предупреждение показывается всегда
        # в руководстве на этот двигатель нет инструкции по такому узлу – продукт заявку не отправляет (разъяснение #103)
        defect = (f"Рекомендация на дефектовку. Машина {result.get('vehicle_id')}, двигатель {engine}, "
                  f"проверка {result.get('session_id')}: ML-сервис указал {code} «{result.get('anomaly_title')}» "
                  f"(оценка {fmt(score)}, уверенность {fmt(conf)}, запись {QUALITY_RU.get(quality, quality)}). "
                  f"Класс не подходит к двигателю {engine}, инструкции по этому узлу в руководстве нет. "
                  "Нужен очный осмотр двигателя и дефектовка по его результату.")
        return Verdict("anomaly", None, "Нужен очный осмотр: тип отклонения не соответствует двигателю этой машины. "
                       "Заявку продукт не отправляет – оформите дефектовку по порядку парка.", False,
                       [f"Отклонение {fmt(score)} из 1, уверенность {fmt(conf)}, но класс {code} неприменим к {engine}.",
                        f"В руководстве на {engine} нет инструкции по узлу «{result.get('anomaly_title')}», поэтому заявка не отправляется."],
                       warnings, "R3-not-applicable", sev, appl, defect_note=defect)

    repeated = [s for s in past if s["status"] == "anomaly" and s.get("anomaly_type") == code and _usable(s)]
    growing = _growing(past + [result], code)
    strong = score is not None and conf is not None and d(score) >= SCORE_HIGH and d(conf) >= CONF_HIGH and quality == "good"
    doubtful = quality == "warning" or (conf is not None and d(conf) < CONF_MIN)

    reasons.append(f"Код по справочнику: {code}.")
    reasons.append(f"Оценка отклонения {fmt(score)} из 1 ({_band(score)}), уверенность модели {fmt(conf)}, запись {QUALITY_RU.get(quality, quality)}.")
    if repeated:
        reasons.insert(0, f"Такое же отклонение уже было: {', '.join(_date(s) for s in repeated)}.")
    if growing:
        reasons.insert(0, "Отклонение растет от проверки к проверке.")
    if appl == "check":
        warnings.append(f"Убедитесь, что на этой машине есть узел «{result.get('anomaly_title')}»: для {engine} это зависит от комплектации.")
    if doubtful:
        warnings.append(_doubt_text(quality, conf) + " Перезапись не нужна: сначала осмотрите узел на машине. "
                        "Подтвердился признак – оформляйте заявку, отметив это в черновике; не подтвердился – машина идет в рейс.")

    if sev == "C":
        urg, rule = "high", "R4-critical"
        action = ("Рекомендация: дефектовка до выпуска в рейс. Если машина уже в рейсе – остановитесь в безопасном месте "
                  "и заглушите двигатель.")
        reasons.insert(0, f"«{result.get('anomaly_title')}» – критичная неисправность: работа с ней может закончиться тяжелой поломкой двигателя.")
    elif sev == "S" and (strong or growing or (repeated and not doubtful)):
        urg, rule = "high", "R5-significant-strong"
        action = "Рекомендация: дефектовка до выпуска в рейс."
        why = "сильный и уверенный сигнал" if strong else ("рост отклонения" if growing else "повторяющееся отклонение")
        reasons.insert(0, f"Значимая неисправность и {why}.")
    elif sev == "L" and not repeated and not growing and not doubtful and conf is not None and d(conf) >= CONF_HIGH \
            and score is not None and d(score) < SCORE_HIGH:
        urg, rule = "low", "R7-minor"
        action = "Машина работает, узел проверить на следующей проверке."
        reasons.insert(0, "Малозначимая неисправность: отклонение умеренное, сигнал уверенный и разовый.")
    else:
        urg, rule = "medium", "R6-planned"
        action = "Дефектовка на ближайшем ТО, машина работает под наблюдением."
        reasons.insert(0, "Отклонение есть, но признаков, требующих дефектовки до выпуска, нет.")
    if hist_note and not repeated:
        reasons.append(hist_note)
    return Verdict("anomaly", urg, action, True, reasons, warnings, rule, sev, appl, inspect_first=doubtful)


def _doubt_text(quality, conf) -> str:
    parts = []
    if quality == "warning":
        parts.append("запись с помехами")
    if conf is not None and d(conf) < CONF_MIN:
        parts.append(f"уверенность модели {fmt(conf)} – ниже порога {fmt(CONF_MIN)}")
    return "Сигнал сомнительный: " + " и ".join(parts) + "."


def _band(score) -> str:
    if score is None:
        return "нет данных"
    s = d(score)
    return "высокая" if s >= SCORE_HIGH else ("средняя" if s >= Decimal("0.5") else "низкая")


def _date(s: dict) -> str:
    c = s.get("checked_at", "")
    return f"{c[8:10]}.{c[5:7]}" if len(c) >= 10 else s["session_id"]


def _history_note(past: list[dict]) -> str:
    if not past:
        return "Предыдущих проверок в системе нет."
    parts = []
    for s in past[-4:]:
        st = {"normal": "норма", "anomaly": f"отклонение {s.get('anomaly_type')}", "check_failed": "сбой записи"}[s["status"]]
        parts.append(f"{_date(s)} – {st}")
    return "Прошлые проверки: " + "; ".join(parts) + "."


def _growing(seq: list[dict], code: str) -> bool:
    pts = [s for s in seq if s["status"] == "anomaly" and s.get("anomaly_type") == code
           and s.get("signal_quality") == "good" and s.get("anomaly_score") is not None]
    if len(pts) < 3:
        return False
    pts = pts[-HISTORY_LIMIT:]
    inc = all(d(b["anomaly_score"]) > d(a["anomaly_score"]) for a, b in zip(pts, pts[1:]))
    return inc and d(pts[-1]["anomaly_score"]) - d(pts[0]["anomaly_score"]) >= TREND_DELTA


def _unresolved_critical(past: list[dict], tickets: list[dict]) -> list[dict]:
    ticketed = {t["session_id"] for t in tickets}
    return [s for s in past if s["status"] == "anomaly" and FAULTS.get(s.get("anomaly_type"), {}).get("severity") == "C"
            and s["session_id"] not in ticketed and _usable(s)]
