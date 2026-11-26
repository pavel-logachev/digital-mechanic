"""Сборка ролика из одной непрерывной записи: ускоряются только ожидания ответа модели, монтажа нет.

python render_demo.py [--clean]
Вход (каталог DEMO_OUT, по умолчанию video/build): main-raw.mp4, main-marks.json, main-callouts.json.
Выход в video/:
  demo-video-captions-no-voice.mp4 – кадр 1920x1080: телефон по центру, слева чек-лист сценариев и функций,
                                      справа текущий шаг и пояснение, рамки-подсказки на элементах экрана;
  demo-video-no-voice.mp4 (--clean)   – только экран телефона на фоне, без подписей;
  timeline.json                       – время каждого шага в готовом ролике (для текста озвучки).
Звук: вопрос механика (q-c2.wav), который в записи подавался в браузер как микрофон, ставится на то же место.
Ничего не вырезается и не переставляется: отрезки идут встык по порядку, меняется только скорость ожидания.
"""
import json, os, shutil, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CLEAN = "--clean" in sys.argv
HERE = Path(__file__).resolve().parent
V = HERE.parent
B = Path(os.environ.get("DEMO_OUT", V / "build"))
raw = B / "main-raw.mp4"
marks = json.loads((B / "main-marks.json").read_text(encoding="utf-8"))
calls = json.loads((B / "main-callouts.json").read_text(encoding="utf-8"))
SPEED = 3.0
FPS = 30
WIN = "C:/Windows/Fonts/"
F = lambda size, bold=False: ImageFont.truetype(WIN + ("segoeuib.ttf" if bold else "segoeui.ttf"), size)
FS = lambda size: ImageFont.truetype(WIN + "seguisb.ttf", size)

dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(raw)],
                           capture_output=True, text=True).stdout.strip())
end = min(dur, next(m["t"] for m in marks if m["kind"] == "end") + 0.3)

# ---------- ускорение: только интервалы ожидания модели (первые 1,0 с и последние 0,6 с – в реальном времени) ----------
waits, opened = [], None
for m in marks:
    if m["kind"] == "wait<":
        opened = m["t"]
    elif m["kind"] == "wait>" and opened is not None:
        a, b = opened + 1.0, m["t"] - 0.6
        if b - a > 2.0:
            waits.append((a, b))
        opened = None
segments, cur = [], 0.0
for a, b in waits:
    segments += [(cur, a, 1.0), (a, b, SPEED)]
    cur = b
segments.append((cur, end, 1.0))


def out_time(t):
    acc = 0.0
    for a, b, k in segments:
        if t <= b:
            return acc + max(0.0, t - a) / k
        acc += (b - a) / k
    return acc


total = out_time(end)
for m in marks:
    m["out"] = round(out_time(m["t"]), 2)
for c in calls:
    c["out"], c["out_end"] = out_time(c["t"]), out_time(c["end"])
(V / "timeline.json").write_text(json.dumps({
    "duration": round(total, 2), "speed": SPEED,
    "speedups": [{"from": round(out_time(a), 2), "to": round(out_time(b), 2), "real_seconds": round(b - a, 1)} for a, b in waits],
    "marks": marks}, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"длительность {total:.1f} с, ускорений {len(waits)}: " + ", ".join(f"{b - a:.1f}→{(b - a) / SPEED:.1f}" for a, b in waits))
if total > 179:
    sys.exit(f"ролик длиннее 3 минут: {total:.1f} с")

# ---------- геометрия кадра ----------
CW, CH = 1920, 1080
PH = 1040 if CLEAN else 1000                # высота экрана телефона в кадре
PW = round(PH * 390 / 844 / 2) * 2
PX, PY = (CW - PW) // 2, (CH - PH) // 2
SC = PH / 844                               # CSS px телефона -> px кадра
R = 34                                      # скругление экрана

NAVY, INK, MUTED, DIM, YELLOW, GREEN = (16, 27, 38), (255, 255, 255), (190, 205, 218), (126, 146, 164), (249, 206, 73), (120, 214, 160)

# ---------- шаги: подпись справа и отметки слева ----------
SCEN = [("С1", "Отклонение → заявка в ТОиР"), ("С2", "Вопрос по руководству"), ("С3", "Сбой записи"), ("С4", "Сводка главного механика")]
EXTRA = [("guide", "Инструкция и крупный шрифт"), ("detail", "Ответ коротко или по шагам"), ("lang", "7 языков"),
         ("history", "История и график проверок"), ("pdf", "Ссылка → страница руководства"),
         ("voice", "Вопрос голосом с правкой текста"), ("r3", "Ошибка программы: чужой узел")]
# (метка записи, номер появления) -> (сценарий, доп. функция, заголовок, пояснение)
STEPS = {
    ("Инструкция", 1): (None, "guide", "Первый запуск", "Инструкция из 6 шагов на настоящих кнопках – для мастера любого возраста."),
    ("Крупный шрифт", 1): (None, "guide", "Крупный шрифт", "Включается одной кнопкой уже на первом шаге."),
    ("Шаги инструкции", 1): (None, "guide", "6 коротких шагов", "Метки машин, результат проверки, вопрос голосом, заявка, язык и шрифт."),
    ("Как объяснять ответы", 1): (None, "detail", "Как объяснять ответы", "Опытному – только суть. Новичку – по шагам: где узел, чем откручивать, что должно получиться."),
    ("Парк: кому нужна дефектовка", 1): (None, None, "Парк из 50 машин", "Сверху – кому нужна дефектовка до рейса. Метки и цветом, и словами."),
    ("7 языков", 1): (None, "lang", "7 языков", "Русский, узбекский, таджикский, кыргызский, казахский, хинди, английский."),
    ("С1: поиск Т792", 1): ("С1", None, "Урал Т792", "Поиск по части госномера или гаражному номеру."),
    ("Карточка машины", 1): ("С1", "history", "Карточка машины", "История проверок и график: насколько звук отличается от нормы."),
    ("Сервис диагностики и помощник", 1): ("С1", None, "Результат проверки", "Помощник вызывает сервис диагностики и ищет нормы в руководстве именно этого двигателя."),
    ("Карточка результата", 1): ("С1", None, "Дефектовка до рейса", "Приоритет и порог заявки считает код по правилам. Модель только объясняет."),
    ("Объяснение со ссылками", 1): ("С1", None, "Что проверить", "Простыми словами, каждая цифра – со ссылкой на страницу."),
    ("Страница руководства", 1): ("С1", "pdf", "Страница руководства", "Ссылка открывает страницу заводского PDF. Сверху – цитата, которую нашел помощник."),
    ("Скан страницы", 1): ("С1", "pdf", "Скан самой страницы", "Цитату можно сверить с книгой, страницу – увеличить."),
    ("С2: вопрос голосом", 1): ("С2", "voice", "Вопрос голосом", "Руки в масле – спрашиваем голосом. Перед первой записью – согласие."),
    ("Запись голоса", 1): ("С2", "voice", "Говорит механик", "«Можно ли своим ходом перегнать машину на базу?»"),
    ("Распознавание речи", 1): ("С2", "voice", "Распознавание речи", "Голос превращается в текст. Звук нигде не сохраняется."),
    ("Текст вопроса в поле", 1): ("С2", "voice", "Текст можно поправить", "Само ничего не уходит: механик проверяет текст и жмет «Отправить»."),
    ("Помощник ищет ответ", 1): ("С2", None, "Поиск по руководству", "Только книги двигателя этой машины. Цифры сверяются со страницей."),
    ("Ответ с источниками", 1): ("С2", None, "Ответ с источниками", "Под ответом – книга и страницы. Нет ответа в книге – помощник так и скажет."),
    ("Подробный ответ", 1): ("С2", "detail", "Объяснить подробнее", "Один раз подробнее, без смены настройки."),
    ("Подробно, по шагам", 1): ("С2", "detail", "Подробно, по шагам", "Где узел, чем проверять и что должно получиться – с теми же ссылками на книгу."),
    ("Заявка: черновик", 1): ("С1", None, "Заявка на дефектовку", "Помощник собирает черновик: заключение, приоритет, работы по руководству."),
    ("Помощник собирает черновик", 1): ("С1", None, "Черновик заявки", "Только если в руководстве есть страница про этот узел."),
    ("Черновик заявки", 1): ("С1", None, "Механик проверяет", "Любое поле можно поправить, приоритет – изменить с причиной."),
    ("Заявка в ТОиР: номер", 1): ("С1", None, "Заявка в ТОиР", "Номер вернула система ремонта. Его можно скопировать."),
    ("С3: сбой записи", 1): ("С3", None, "МАЗ Р456", "У этой машины запись испорчена: микрофон перегружен."),
    ("Результат проверки", 1): ("С3", None, "Результат проверки", ""),
    ("Карточка результата", 2): ("С3", None, "Запись не подошла", "Ни диагноза, ни заявки – подсказка, как и где перезаписать звук."),
    ("Ошибка программы: чужой узел", 1): (None, "r3", "МАЗ Р854", "В истории машины есть проверка, где сервис назвал узел, которого у этого двигателя нет."),
    ("Результат проверки Р854", 1): (None, "r3", "Проверка 1 ноября", "Цепь ГРМ – а у ЯМЗ‑236М2 привод шестернями."),
    ("Карточка результата", 3): (None, "r3", "Ошибка программы, не диагноз", "Без приоритета, без заявки и без норм чужого узла: повторить проверку или дефектовка."),
    ("Сообщение для разработчиков", 1): (None, "r3", "Текст рекомендации", "Готовый текст на дефектовку с результатом проверки – одной кнопкой."),
    ("С4: сводка главного механика", 1): ("С4", None, "Сводка парка", "Сколько машин на дефектовку, сколько требуют внимания, какие заявки в работе."),
    ("Очередь на дефектовку", 1): ("С4", None, "Очередь на дефектовку", "Сначала самые срочные."),
    ("История проверок машины", 1): ("С4", "history", "История машины", "Все проверки и заявки по машине в одном месте."),
}
seen, steps = {}, []
for m in marks:
    if m["kind"] == "end":
        continue
    k = (m["label"], seen.get(m["label"], 0) + 1)
    seen[m["label"]] = k[1]
    if k in STEPS:
        steps.append((m["out"],) + STEPS[k])
    elif m["kind"] in ("step", "event"):
        print("нет подписи для", k)

times = sorted({0.0, round(total, 3)} | {s[0] for s in steps} | {round(c["out"], 3) for c in calls} | {round(c["out_end"], 3) for c in calls}
               | {round(out_time(a), 3) for a, b in waits} | {round(out_time(b), 3) for a, b in waits})
times = [t for t in times if 0 <= t <= total]


def wrap(draw, text, font, width):
    words, lines, line = text.split(), [], ""
    for w in words:
        test = (line + " " + w).strip()
        if draw.textlength(test, font=font) <= width:
            line = test
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def state_at(t):
    step = None
    scen_seen, extra_seen = [], []
    for s in steps:
        if s[0] <= t + 1e-6:
            step = s
            if s[1] and s[1] not in scen_seen:
                scen_seen.append(s[1])
            if s[2] and s[2] not in extra_seen:
                extra_seen.append(s[2])
    call = next((c for c in calls if c["out"] <= t < c["out_end"]), None)
    wait = next((b - a for a, b in waits if out_time(a) <= t < out_time(b)), None)
    return step, scen_seen, extra_seen, call, wait


def draw_state(t):
    img = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    step, scen_seen, extra_seen, call, wait = state_at(t)
    cur_scen = step[1] if step else None
    cur_extra = step[2] if step else None
    # --- левая колонка: что уже показано ---
    LX, LW = 90, 530
    d.text((LX, 92), "Цифровой механик", font=F(50, True), fill=INK)
    d.text((LX, 156), "помощник механика у машины", font=F(28), fill=MUTED)
    d.text((LX, 196), "ИИкузница · задача НейроДВС", font=F(22), fill=DIM)
    y = 278
    d.text((LX, y), "СЦЕНАРИИ ТЗ", font=FS(20), fill=DIM)
    y += 40
    for key, name in SCEN:
        state = "cur" if key == cur_scen else "done" if key in scen_seen else "todo"
        col = INK if state == "cur" else (214, 224, 232) if state == "done" else DIM
        if state == "cur":
            d.rounded_rectangle((LX - 14, y - 8, LX + LW, y + 46), 12, fill=(255, 255, 255, 20))
            d.rounded_rectangle((LX, y + 8, LX + 20, y + 28), 6, fill=YELLOW)
        elif state == "done":
            d.rounded_rectangle((LX, y + 8, LX + 20, y + 28), 6, fill=GREEN)
            d.line([(LX + 5, y + 18), (LX + 9, y + 23), (LX + 16, y + 13)], fill=NAVY, width=3)
        else:
            d.rounded_rectangle((LX, y + 8, LX + 20, y + 28), 6, outline=DIM, width=2)
        d.text((LX + 36, y), key, font=F(28, True), fill=col)
        d.text((LX + 84, y), name, font=F(28), fill=col)
        y += 54
    y += 28
    d.text((LX, y), "СВЕРХ ОБЯЗАТЕЛЬНОГО", font=FS(20), fill=DIM)
    y += 40
    for key, name in EXTRA:
        state = "cur" if key == cur_extra else "done" if key in extra_seen else "todo"
        col = INK if state == "cur" else (214, 224, 232) if state == "done" else DIM
        if state == "cur":
            d.rounded_rectangle((LX - 14, y - 6, LX + LW, y + 40), 12, fill=(255, 255, 255, 20))
            d.ellipse((LX + 3, y + 10, LX + 17, y + 24), fill=YELLOW)
        elif state == "done":
            d.ellipse((LX + 3, y + 10, LX + 17, y + 24), fill=GREEN)
        else:
            d.ellipse((LX + 3, y + 10, LX + 17, y + 24), outline=DIM, width=2)
        d.text((LX + 36, y), name, font=F(25), fill=col)
        y += 46
    d.text((LX, 950), "Реальный стенд, данные задачи, один дубль", font=F(22), fill=DIM)
    d.text((LX, 980), "mechanic.logachev.net", font=FS(24), fill=YELLOW)
    # --- правая колонка: текущий шаг ---
    RX = PX + PW + 90
    RW = CW - RX - 80
    yy = 136
    if step:
        tag = {"С1": "С1 · ОТКЛОНЕНИЕ", "С2": "С2 · ВОПРОС МЕХАНИКА", "С3": "С3 · СБОЙ ЗАПИСИ", "С4": "С4 · ГЛАВНЫЙ МЕХАНИК"}.get(cur_scen, "СВЕРХ ОБЯЗАТЕЛЬНОГО")
        d.text((RX, 96), tag, font=FS(22), fill=YELLOW)
        yy = 136
        for line in wrap(d, step[3], F(46, True), RW):
            d.text((RX, yy), line, font=F(46, True), fill=INK)
            yy += 58
        yy += 10
        for line in wrap(d, step[4], F(29), RW):
            d.text((RX, yy), line, font=F(29), fill=MUTED)
            yy += 40
    if call:
        x, y0, w, h = call["box"]
        bx0, by0 = PX + x * SC, PY + y0 * SC
        bx1, by1 = bx0 + w * SC, by0 + h * SC
        bx0, by0, bx1, by1 = max(bx0, PX + 3), max(by0, PY + 3), min(bx1, PX + PW - 3), min(by1, PY + PH - 3)
        glow = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle((bx0 - 2, by0 - 2, bx1 + 2, by1 + 2), 14, outline=YELLOW + (150,), width=10)
        img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(6)))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((bx0, by0, bx1, by1), 12, outline=YELLOW, width=4)
        lines = wrap(d, call["text"], F(30, True), RW - 48)
        ch_ = 36 + 42 * len(lines)
        cy = int(min(yy + 34, CH - 170 - ch_))
        d.rounded_rectangle((RX, cy, RX + RW, cy + ch_), 16, fill=YELLOW + (255,))
        for i, line in enumerate(lines):
            d.text((RX + 24, cy + 14 + i * 42), line, font=F(30, True), fill=NAVY)
        ax, ay = bx1 + 2, (by0 + by1) / 2
        ex, ey = RX - 2, cy + ch_ / 2
        d.line([(ax + 14, ay), (ex - 28, ey), (ex, ey)], fill=YELLOW, width=4, joint="curve")
        d.polygon([(ax + 2, ay), (ax + 22, ay - 10), (ax + 22, ay + 10)], fill=YELLOW)
    if wait:
        bx, by = RX, CH - 132
        d.rounded_rectangle((bx, by, bx + RW, by + 64), 32, fill=(255, 255, 255, 24))
        for i in range(2):
            ox = bx + 26 + i * 16
            d.polygon([(ox, by + 20), (ox + 16, by + 32), (ox, by + 44)], fill=YELLOW)
        d.text((bx + 72, by + 13), f"Ждем ответ модели · ускорено ×{SPEED:g}", font=F(28, True), fill=INK)
    return img


def phone_assets():
    bg = Image.new("RGB", (CW, CH), NAVY)
    g = Image.new("L", (CW, CH), 0)
    ImageDraw.Draw(g).ellipse((CW // 2 - 900, -500, CW // 2 + 900, CH + 300), fill=70)
    g = g.filter(ImageFilter.GaussianBlur(160))
    bg = Image.composite(Image.new("RGB", (CW, CH), (32, 52, 72)), bg, g).convert("RGBA")
    sh = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((PX - 10, PY + 14, PX + PW + 10, min(CH, PY + PH + 30)), R + 14, fill=(0, 0, 0, 150))
    bg.alpha_composite(sh.filter(ImageFilter.GaussianBlur(24)))
    dd = ImageDraw.Draw(bg)
    dd.rounded_rectangle((PX - 12, PY - 12, PX + PW + 12, PY + PH + 12), R + 12, fill=(8, 12, 16))
    dd.rounded_rectangle((PX - 12, PY - 12, PX + PW + 12, PY + PH + 12), R + 12, outline=(70, 88, 104), width=2)
    bg.convert("RGB").save(B / "bg.png")
    mask = Image.new("L", (PW, PH), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, PW - 1, PH - 1), R, fill=255)
    mask.save(B / "mask.png")


if __name__ == "__main__":
    phone_assets()
    if "--frames" in sys.argv:          # только проверить подписи: кадры-слои в build/preview
        P = B / "preview"
        P.mkdir(exist_ok=True)
        for t in [float(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(",")]:
            base = Image.open(B / "bg.png").convert("RGBA")
            base.alpha_composite(draw_state(t))
            base.convert("RGB").save(P / f"t{t:06.1f}.png")
        sys.exit(0)
    if not CLEAN:
        L = B / "layers"
        shutil.rmtree(L, ignore_errors=True)
        L.mkdir()
        lst = []
        for i in range(len(times) - 1):
            a, b = times[i], times[i + 1]
            if b - a < 1 / FPS:
                continue
            draw_state((a + b) / 2).save(L / f"{i:04d}.png")
            lst.append(f"file 'layers/{i:04d}.png'\nduration {b - a:.4f}")
        lst.append(lst[-1].split("\n")[0])
        (B / "layers.txt").write_text("\n".join(lst) + "\n", encoding="utf-8")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "layers.txt", "-vf", f"fps={FPS},format=argb",
                        "-c:v", "qtrle", "layers.mov"], cwd=B, check=True)
    n = len(segments)
    parts = [f"[0:v]fps={FPS},split={n}" + "".join(f"[in{i}]" for i in range(n))]
    for i, (a, b, k) in enumerate(segments):
        parts.append(f"[in{i}]trim=start={a:.3f}:end={b:.3f},setpts=(PTS-STARTPTS)/{k}[s{i}]")
    parts.append("".join(f"[s{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[phone]")
    parts.append(f"[phone]scale={PW}:{PH}:flags=lanczos,format=yuva420p[ph0];[2:v]format=gray,scale={PW}:{PH}[m];[ph0][m]alphamerge[ph]")
    parts.append(f"[1:v]loop=-1:size=1,fps={FPS},trim=duration={total:.3f}[bg];[bg][ph]overlay={PX}:{PY}:shortest=1" + ("[v]" if CLEAN else "[base]"))
    if not CLEAN:
        parts.append("[base][4:v]overlay=0:0:eof_action=repeat,format=yuv420p[v]")
    # звук: вопрос механика – на то место, где он звучал в записи (метка «Запись голоса» + 0,3 с)
    q_at = out_time(next(m["t"] for m in marks if m["label"] == "Запись голоса")) + 0.3
    parts.append(f"[3:a]adelay={int(q_at * 1000)}|{int(q_at * 1000)},apad,atrim=duration={total:.3f},aformat=sample_rates=48000:channel_layouts=stereo[a]")
    (B / "render-filter.txt").write_text(";".join(parts), encoding="utf-8")
    inputs = ["-i", str(raw), "-i", "bg.png", "-i", "mask.png", "-i", str(HERE / "q-c2.wav")] + ([] if CLEAN else ["-i", "layers.mov"])
    name = "demo-video-no-voice.mp4" if CLEAN else "demo-video-captions-no-voice.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-/filter_complex", "render-filter.txt", "-map", "[v]", "-map", "[a]",
                    "-r", str(FPS), "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart", "-t", f"{total:.3f}", str(V / name)], cwd=B, check=True)
    print(V / name, f"{total:.1f} с, вопрос механика на {q_at:.1f} с")
