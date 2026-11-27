"""Чистка и сведение озвучки под demo-video-captions-no-voice.mp4.

python process_voice.py voice/voice-<дата>.webm
1) шумоподавление по профилю пауз (фон, свист ~2,35 кГц, гул 150 Гц);
2) перестановка фраз, чтобы слова совпадали с экраном (список MOVES – время в ролике);
3) вырезаны посторонние звуки (CUT) и приглушены паузы между фразами;
4) эквалайзер, компрессия, громкость -16 LUFS; вопрос механика из ролика – чуть тише голоса.
Результат: voice-clean.wav и demo-final.mp4 (+ demo-final-clean.mp4 без подписей).
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
import noisereduce as nr

HERE = Path(__file__).resolve().parent
V = HERE.parent
SR = 48000
src = Path(sys.argv[1]).resolve()

# (начало, конец) фразы в записи -> новое начало; все времена – секунды ролика
MOVES = [
    (70.55, 72.85, 67.80),   # «Текст можно поправить перед отправкой» – когда текст появился в поле, а не после отправки
    (97.47, 99.56, 92.15),   # «Ожидание снова ускорено» – внутрь ускоренного ожидания, а не после ответа
    (92.33, 97.45, 94.85),   # «Тот же ответ по шагам…» – когда ответ по шагам уже на экране
]
CUT = [(42.40, 42.85),       # щелчок в паузе
       (47.84, 49.30),       # звонок телефона (~4 кГц) в паузе
       (116.35, 116.95),     # стук перед «Система ремонта…»
       (128.70, 129.20)]     # вдох/шорох после «…подсказывает как»
NOISE = [(8.9, 11.3), (22.3, 24.1), (60.3, 70.5), (99.6, 106.3), (154.9, 157.4)]


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def ramp(n):
    return 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n))


x = load(src)
dur = float(json.loads((V / "timeline.json").read_text(encoding="utf-8"))["duration"])
x = np.pad(x, (0, max(0, int(dur * SR) - len(x))))[: int(dur * SR)]

# 1. шумоподавление: профиль шума – только паузы
noise = np.concatenate([x[int(a * SR):int(b * SR)] for a, b in NOISE])
y = nr.reduce_noise(y=x, sr=SR, y_noise=noise, stationary=True, prop_decrease=0.9, n_fft=2048, freq_mask_smooth_hz=300)

# 2. перестановка фраз (с плавными краями 15 мс)
out = y.copy()
F = int(0.015 * SR)
pieces = []
for a, b, dst in MOVES:
    seg = y[int(a * SR):int(b * SR)].copy()
    seg[:F] *= ramp(F); seg[-F:] *= ramp(F)[::-1]
    pieces.append((dst, seg))
    out[int(a * SR):int(b * SR)] = 0
for dst, seg in pieces:
    i = int(dst * SR)
    out[i:i + len(seg)] += seg

# 3. посторонние звуки и паузы
for a, b in CUT:
    out[int(a * SR):int(b * SR)] = 0
hop, win = 480, 1440
frames = np.lib.stride_tricks.sliding_window_view(out, win)[::hop]
lev = 10 * np.log10(np.mean(frames ** 2, axis=1) + 1e-12)
speech = lev > np.percentile(lev, 95) - 32
t = np.arange(len(lev)) * hop / SR
mask = np.zeros_like(out)
spans, i = [], 0
while i < len(speech):
    if speech[i]:
        j = i
        while j < len(speech) and speech[j]:
            j += 1
        spans.append([t[i], t[j - 1] + win / SR]); i = j
    else:
        i += 1
merged = []
for a, b in spans:
    if merged and a - merged[-1][1] < 0.3:
        merged[-1][1] = b
    else:
        merged.append([a, b])
merged = [s for s in merged if s[1] - s[0] > 0.15]
for a, b in merged:
    mask[max(0, int((a - 0.12) * SR)):int((b + 0.18) * SR)] = 1
k = int(0.04 * SR)
mask = np.convolve(mask, np.ones(k) / k, mode="same")
out *= 0.03 + 0.97 * mask          # паузы тише на 30 дБ, не в ноль – без «дырок»
print("фразы:", " ".join(f"{a:.1f}-{b:.1f}" for a, b in merged))

clean = V / "build" / "voice-clean.wav"
clean.parent.mkdir(exist_ok=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                "-af", "highpass=f=75,equalizer=f=150:t=q:w=4:g=-6,equalizer=f=2355:t=q:w=12:g=-12,"
                       "equalizer=f=250:t=q:w=1:g=-1.5,equalizer=f=3500:t=q:w=1:g=2,deesser=i=0.4,"
                       "acompressor=threshold=-24dB:ratio=2.5:attack=8:release=150:makeup=4",
                "-c:a", "pcm_s24le", str(clean)], input=out.astype(np.float32).tobytes(), check=True)

# 4. громкость: двухпроходный loudnorm до -16 LUFS
st = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(clean), "-af", "loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json",
                     "-f", "null", "-"], capture_output=True, text=True).stderr
m = json.loads(st[st.rindex("{"):st.rindex("}") + 1])
ln = (f"loudnorm=I=-16:TP=-1.5:LRA=7:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
      f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
for video, name in (("demo-video-captions-no-voice.mp4", "demo-final.mp4"), ("demo-video-no-voice.mp4", "demo-final-clean.mp4")):
    fc = (f"[1:a]{ln},aresample={SR},aformat=channel_layouts=stereo[v];"
          f"[0:a]volume=-3dB,aformat=sample_rates={SR}:channel_layouts=stereo[q];"
          f"[q][v]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89:attack=2:release=60:level=false[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(V / video), "-i", str(clean), "-filter_complex", fc,
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                    str(V / name)], check=True)
    print(V / name)
