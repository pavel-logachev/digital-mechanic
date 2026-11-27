"""Запись демо «Цифрового механика» одним дублем с экрана телефона (Playwright + CDP screencast, реальный стенд).

python record_demo.py [base_url] [--probe]
  --probe – прогон без записи кадров (проверить путь и тайминги).
Пишет <OUT>/main-raw.mp4, main-marks.json (шаги, интервалы ожидания модели) и main-callouts.json
(какой элемент экрана подсвечивать в версии с пояснениями и когда).
Голосовой вопрос подается в браузер как звук с микрофона (q-c2.wav) и распознается настоящим сервисом стенда.
"""
import base64
import bisect
import contextlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
BASE = ARGS[0] if ARGS else "https://mechanic.logachev.net"
PROBE = "--probe" in sys.argv
HERE = Path(__file__).resolve().parent
OUT = Path(os.environ.get("DEMO_OUT", HERE.parent / "build"))
NAME = "main"
W, H = 390, 844

TOUCH = """
(() => {
  const css = `.demo-touch{position:fixed;z-index:2147483647;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;
    background:rgba(255,196,0,.45);border:2px solid rgba(255,196,0,.95);pointer-events:none;animation:demo-touch .6s ease-out forwards}
    @keyframes demo-touch{from{transform:scale(.6);opacity:1}to{transform:scale(1.4);opacity:0}}`;
  const add = () => { const s = document.createElement('style'); s.textContent = css; document.head.appendChild(s); };
  if (document.head) add(); else document.addEventListener('DOMContentLoaded', add);
  addEventListener('pointerdown', e => { const d = document.createElement('div'); d.className = 'demo-touch';
    d.style.left = e.clientX + 'px'; d.style.top = e.clientY + 'px'; document.body.appendChild(d); setTimeout(() => d.remove(), 700); }, true);
})();
"""

marks, callouts = [], []
T0 = None
PAGE = None


def now():
    return round(time.monotonic() - T0, 2)


def mark(label, kind="step"):
    marks.append({"t": now(), "label": label, "kind": kind})
    print(f"{marks[-1]['t']:7.2f}  {kind:5} {label}", flush=True)


def pause(sec):
    PAGE.wait_for_timeout(int(sec * 1000))  # ждем через Playwright, чтобы кадры экрана продолжали приходить


def callout(locator, text, sec, pad=6):
    """Подсветка элемента в версии с пояснениями: рамка вокруг него на время паузы (экран в эту паузу не двигается)."""
    box = locator.bounding_box() if locator.count() else None
    t = now()
    if box:   # только видимая часть: от верха экрана до нижней панели
        top, bottom = locator.first.evaluate("""e => { const d = e.closest('dialog[open]');
            if (d) { const r = d.getBoundingClientRect(); return [r.top, r.bottom]; }
            const m = e.closest('#manual');
            if (m) { const h = m.querySelector('.manual-top'); return [h ? h.getBoundingClientRect().bottom : 0, innerHeight]; }
            const h = document.querySelector('#top'), k = document.querySelector('#dock');
            const inDock = k && k.contains(e);
            return [h ? h.getBoundingClientRect().bottom : 0, !inDock && k && k.offsetParent ? k.getBoundingClientRect().top : innerHeight]; }""")
        y0, y1 = max(box["y"], top + 2), min(box["y"] + box["height"], bottom - 2)
        box = {**box, "y": y0, "height": max(8, y1 - y0)}
        callouts.append({"t": t, "end": round(t + sec, 2), "text": text,
                         "box": [box["x"] - pad, box["y"] - pad, box["width"] + 2 * pad, box["height"] + 2 * pad]})
    else:
        print("!! нет элемента для подсветки:", text, flush=True)
    pause(sec)


def tap(locator):
    locator.scroll_into_view_if_needed()
    box = locator.bounding_box()
    PAGE.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)


def type_slow(locator, text):
    tap(locator)
    for ch in text:
        PAGE.keyboard.type(ch)
        PAGE.wait_for_timeout(150)


def scroll_main(dy, steps=14, delay=0.035):
    for _ in range(steps):
        PAGE.evaluate(f"document.querySelector('main').scrollBy(0, {dy / steps})")
        PAGE.wait_for_timeout(int(delay * 1000))


def scroll_to(locator, offset=12, steps=16):
    """Плавно прокрутить так, чтобы элемент оказался у верхнего края (под шапкой)."""
    dy = PAGE.evaluate("""([el, off]) => { const m = document.querySelector('main');
        return el.getBoundingClientRect().top - m.getBoundingClientRect().top - off; }""", [locator.element_handle(), offset])
    scroll_main(dy, steps=steps)


def wait_agent(timeout=150000):
    PAGE.wait_for_function("() => !document.querySelector('#chat-progress-row:not([hidden])') && !document.querySelector('.explain-pending')",
                           timeout=timeout)


def to_park():
    tap(PAGE.locator(".back-button"))
    pause(0.4)
    if PAGE.locator(".back-button").is_visible():
        tap(PAGE.locator(".back-button"))
    PAGE.wait_for_selector(".vehicle-row")


def open_vehicle(search, plate):
    clear = PAGE.get_by_role("button", name="Очистить поиск")
    if clear.is_visible():
        tap(clear)
        pause(0.4)
    type_slow(PAGE.locator("#vehicle-search"), search)
    pause(0.6)
    tap(PAGE.locator(f"[data-plate={plate}]"))
    PAGE.wait_for_selector("#diagnose")


def diagnose(label):
    tap(PAGE.locator("#diagnose"))
    mark(label, "wait<")
    PAGE.wait_for_selector(".verdict-head", timeout=60000)
    mark("Карточка результата", "event")
    wait_agent()
    mark("Объяснение готово", "wait>")


def pick_cite():
    # ссылка на страницу с нормой давления масла (стр. 19 РЭ ЯМЗ-236М2), иначе первая
    cites = PAGE.locator(".explain .inline-cite")
    labels = cites.evaluate_all("els => els.map(e => (e.getAttribute('aria-label') || '') + ' ' + e.textContent)")
    for want in ("страница 19", "стр. 19"):
        for i, label in enumerate(labels):
            if want in label:
                return cites.nth(i)
    return cites.first


def flow():
    page = PAGE
    page.goto(BASE + "/")
    page.wait_for_selector("#guide[open]")
    # ---------- первое знакомство: инструкция и крупный шрифт ----------
    mark("Инструкция")
    pause(2.2)
    tap(page.locator("#guide-size"))
    mark("Крупный шрифт")
    pause(2.0)
    tap(page.locator("#guide-size"))
    pause(0.6)
    mark("Шаги инструкции")
    for _ in range(4):
        tap(page.locator("#guide-next"))
        pause(1.5)
    tap(page.locator("#guide-next"))
    mark("Как объяснять ответы")
    callout(page.locator("#guide .detail-switch").first, "Коротко или подробно – по просьбе заказчика", 3.0)
    tap(page.locator("#guide-next"))
    page.wait_for_selector("#guide", state="hidden")
    page.wait_for_selector(".vehicle-row")
    # ---------- парк и языки ----------
    mark("Парк: кому нужна дефектовка")
    callout(page.locator(".vehicle-row").first, "Первой в списке – машина, которой нужна дефектовка", 3.6)
    tap(page.locator("#language"))
    page.wait_for_selector(".language-list")
    mark("7 языков")
    callout(page.locator(".language-list"), "Русский, узбекский, таджикский, киргизский, казахский, хинди, английский", 2.0)
    tap(page.locator(".language-list button", has_text="O‘zbekcha"))
    page.wait_for_selector(".vehicle-row")
    pause(2.4)
    tap(page.locator("#language"))
    page.wait_for_selector(".language-list")
    pause(0.6)
    tap(page.locator(".language-list button", has_text="Русский"))
    page.wait_for_selector(".vehicle-row")
    pause(0.6)
    # ---------- С1: отклонение -> объяснение со ссылками ----------
    mark("С1: поиск Т792")
    open_vehicle("Т792", "T792HO98")
    mark("Карточка машины")
    pause(0.6)
    scroll_to(page.locator(".score-chart"), offset=10)
    callout(page.locator(".score-chart"), "Отличие звука от нормы по проверкам", 3.2)
    diagnose("Сервис диагностики и помощник")
    pause(0.8)
    callout(page.locator(".next-action"), "Что делать и приоритет – правила в коде, не нейросеть", 5.2)
    callout(page.locator(".verdict-facts, .metrics").first, "Отличие звука, уверенность программы и порог заявки", 3.2)
    scroll_to(page.locator(".explain"))
    mark("Объяснение со ссылками")
    pause(3.6)
    cite = pick_cite()
    cite.scroll_into_view_if_needed()
    callout(cite, "Каждая цифра – со ссылкой на страницу руководства", 1.8)
    tap(cite)
    page.wait_for_selector("#manual-image", timeout=30000)
    page.wait_for_function("() => { const i = document.querySelector('#manual-image'); return i && i.complete && i.naturalWidth > 0; }", timeout=30000)
    mark("Страница руководства")
    pause(0.6)
    callout(page.locator("#manual .manual-text"), "Цитата из руководства, на которую опирается ответ", 3.0)
    dy = page.evaluate("() => { const m = document.querySelector('#manual'), f = document.querySelector('#manual .page-frame');"
                       " return f.getBoundingClientRect().top - m.getBoundingClientRect().top - 8; }")
    for _ in range(16):
        page.evaluate(f"document.querySelector('#manual').scrollBy(0, {dy / 16})")
        pause(0.035)
    mark("Скан страницы")
    pause(3.4)
    tap(page.locator("#close-manual"))
    pause(0.8)
    # ---------- С2: вопрос голосом ----------
    mark("С2: вопрос голосом")
    tap(page.locator("#mic"))
    dialog = page.locator("#data-dialog")
    dialog.wait_for(state="visible")
    pause(3.2)
    tap(dialog.get_by_role("checkbox"))
    pause(0.4)
    tap(dialog.get_by_role("button", name="Продолжить"))
    mark("Запись голоса")
    pause(4.3)
    tap(page.locator("#mic"))
    mark("Распознавание речи", "wait<")
    expect(page.locator("#question")).not_to_have_value("", timeout=30000)
    mark("Текст вопроса в поле", "wait>")
    callout(page.locator("#question"), "Распознанный текст можно поправить", 2.4)
    before = page.locator(".agent-message").count()
    tap(page.locator("#send-question"))
    mark("Помощник ищет ответ", "wait<")
    page.wait_for_function(f"() => document.querySelectorAll('.agent-message').length > {before}", timeout=150000)
    wait_agent()
    mark("Ответ с источниками", "wait>")
    scroll_to(page.locator(".agent-message").last)
    pause(6.0)
    scroll_main(300, steps=22, delay=0.05)
    pause(3.0)
    src = page.locator(".message-sources").last
    if src.count():
        src.scroll_into_view_if_needed()
        callout(src, "Источники: книга и страницы", 2.4)
    more = page.locator(".more-detail").last
    if more.count():
        more.scroll_into_view_if_needed()
        callout(more, "Новичку – подробнее, по шагам", 1.8)
        before = page.locator(".agent-message").count()
        tap(more)
        mark("Подробный ответ", "wait<")
        page.wait_for_function(f"() => document.querySelectorAll('.agent-message').length > {before}", timeout=150000)
        wait_agent()
        mark("Подробно, по шагам", "wait>")
        scroll_to(page.locator(".agent-message").last)
        pause(5.5)
        scroll_main(360, steps=24, delay=0.05)
        pause(3.0)
    # ---------- заявка ----------
    mark("Заявка: черновик")
    draft = page.locator("[data-command=draft]").first
    draft.scroll_into_view_if_needed()
    pause(0.4)
    tap(draft)
    mark("Помощник собирает черновик", "wait<")
    page.wait_for_selector("#confirm-ticket", timeout=120000)
    mark("Черновик заявки", "wait>")
    pause(2.2)
    scroll_main(420, steps=18)
    pause(2.0)
    page.locator("#confirm-ticket").scroll_into_view_if_needed()
    callout(page.locator("#confirm-ticket"), "Без нажатия механика заявка никуда не уходит", 2.4)
    tap(page.locator("#confirm-ticket"))
    page.wait_for_selector(".receipt-id", timeout=30000)
    mark("Заявка в ТОиР: номер")
    callout(page.locator(".receipt-id"), "Номер заявки из системы ремонта", 2.4)
    tap(page.locator("[data-command=copy-ticket]"))
    pause(1.6)
    tap(page.get_by_role("button", name="К списку машин"))
    page.wait_for_selector(".vehicle-row")
    # ---------- С3: сбой записи ----------
    mark("С3: сбой записи")
    open_vehicle("Р456", "P456AT178")
    pause(0.6)
    diagnose("Результат проверки")
    pause(0.6)
    callout(page.locator(".verdict-head .next-action, .verdict-head").first, "Запись плохая – ни диагноза, ни заявки", 4.6)
    to_park()
    # ---------- несовместимый узел ----------
    mark("Ошибка программы: чужой узел")
    open_vehicle("Р854", "P854BT78")
    pause(0.6)
    tap(page.locator("summary", has_text="Прошлые проверки").first)
    pause(0.8)
    past = page.locator('[data-session="S-0021"]')
    past.scroll_into_view_if_needed()
    callout(past, "Проверка 1 ноября из истории машины", 1.8)
    tap(past)
    mark("Результат проверки Р854", "wait<")
    page.wait_for_selector(".verdict-head", timeout=60000)
    mark("Карточка результата", "event")
    wait_agent()
    mark("Объяснение готово", "wait>")
    pause(0.6)
    callout(page.locator(".verdict-head .next-action, .verdict-head").first, "Такого узла у двигателя нет – ошибка программы", 5.0)
    note = page.locator("[data-command=copy-defect-note]")
    if note.count():
        note.scroll_into_view_if_needed()
        pause(0.4)
        tap(note)
        mark("Сообщение для разработчиков")
        pause(1.8)
    to_park()
    # ---------- С4: главный механик ----------
    mark("С4: сводка главного механика")
    clear = page.get_by_role("button", name="Очистить поиск")
    if clear.is_visible():
        tap(clear)
    pause(0.3)
    tap(page.locator(".wide-link").first)
    page.wait_for_selector(".tile")
    callout(page.locator(".tiles"), "Весь парк: дефектовка, внимание, норма", 3.0)
    tap(page.locator('[data-filter="quarantine"]'))
    mark("Очередь на дефектовку")
    pause(0.4)
    scroll_to(page.locator(".fleet-row").first, offset=16)
    callout(page.locator(".fleet-row").first, "Первой стоит самая срочная машина", 2.4)
    tap(page.locator(".fleet-row").first)
    page.wait_for_selector("#diagnose")
    pause(0.8)
    tap(page.locator("summary", has_text="Прошлые проверки").first)
    pause(0.6)
    scroll_to(page.locator(".score-chart"), offset=10)
    mark("История проверок машины")
    callout(page.locator(".score-chart"), "Как менялся звук от проверки к проверке", 2.6)
    pause(2.6)


def build_video(out_dir, fps=30):
    """Ровно 30 кадров в секунду по часам записи: на каждый тик – последний пришедший кадр экрана."""
    fr = json.loads((out_dir / f"{NAME}-frames.json").read_text(encoding="utf-8"))
    mk = json.loads((out_dir / f"{NAME}-marks.json").read_text(encoding="utf-8"))
    t0, frames = fr["t0"], fr["frames"]
    walls = [f["wall"] - t0 for f in frames]
    end = mk[-1]["t"] + 0.3
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "mjpeg", "-i", "-",
                             "-vf", "scale=780:1688:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-crf", "14", "-preset", "medium",
                             "-r", str(fps), f"{NAME}-raw.mp4"], cwd=out_dir, stdin=subprocess.PIPE)
    cache = {}
    for k in range(int(end * fps)):
        i = max(0, bisect.bisect_right(walls, k / fps) - 1)
        if i not in cache:
            cache.clear()
            cache[i] = (out_dir / f"frames-{NAME}" / frames[i]["file"]).read_bytes()
        proc.stdin.write(cache[i])
    proc.stdin.close()
    proc.wait()


def run():
    global T0, PAGE
    OUT.mkdir(parents=True, exist_ok=True)
    frames_dir = OUT / f"frames-{NAME}"
    shutil.rmtree(frames_dir, ignore_errors=True)
    frames_dir.mkdir(parents=True)
    frames = []
    wav = HERE / "q-c2.wav"
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                                                     f"--use-file-for-fake-audio-capture={wav}"])
        ctx = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=2, is_mobile=True, has_touch=True,
                            locale="ru-RU", timezone_id="Europe/Moscow", bypass_csp=True,
                            permissions=["microphone", "clipboard-read", "clipboard-write"])
        ctx.add_init_script(TOUCH)
        page = ctx.new_page()
        PAGE = page
        cdp = ctx.new_cdp_session(page)

        def on_frame(ev):
            n = len(frames)
            (frames_dir / f"{n:05d}.jpg").write_bytes(base64.b64decode(ev["data"]))
            frames.append({"file": f"{n:05d}.jpg", "wall": time.monotonic()})
            with contextlib.suppress(Exception):
                cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})

        if not PROBE:
            cdp.on("Page.screencastFrame", on_frame)
            cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": W * 2, "maxHeight": H * 2, "everyNthFrame": 1})
        T0 = time.monotonic()
        try:
            flow()
            pause(1)
        except Exception:
            page.screenshot(path=str(OUT / "fail.png"))
            raise
        finally:
            mark("Конец", "end")
            if not PROBE:
                with contextlib.suppress(Exception):
                    cdp.send("Page.stopScreencast")
                (OUT / f"{NAME}-frames.json").write_text(json.dumps({"t0": T0, "frames": frames}), encoding="utf-8")
            (OUT / f"{NAME}-marks.json").write_text(json.dumps(marks, ensure_ascii=False, indent=1), encoding="utf-8")
            (OUT / f"{NAME}-callouts.json").write_text(json.dumps(callouts, ensure_ascii=False, indent=1), encoding="utf-8")
            ctx.close()
            b.close()
    if not PROBE:
        build_video(OUT)
        print("frames:", len(frames))


if __name__ == "__main__":
    run()
