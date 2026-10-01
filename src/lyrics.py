import re, subprocess
import numpy as np
from . import config

CLEAN = re.compile(r"[¿?¡!,.;:\"“”()\[\]…]+")


def _group(words, total):
    """words: [(texto, ini, fin)] -> [(linea, ini, fin)] con líneas cortas."""
    lines, cur = [], []
    def flush():
        if cur:
            lines.append([" ".join(w[0] for w in cur), cur[0][1], cur[-1][2]])
            cur.clear()
    for w in words:
        if cur:
            gap = w[1] - cur[-1][2]
            length = len(" ".join(x[0] for x in cur)) + 1 + len(w[0])
            if gap > 0.55 or length > config.MAX_CHARS_LINE:
                flush()
        cur.append(w)
    flush()
    for i, l in enumerate(lines):           # cada línea dura hasta la siguiente (máx. 0.6 s de cola)
        nxt = lines[i + 1][1] if i + 1 < len(lines) else total
        l[2] = min(nxt, l[2] + 0.6, total)
    return [tuple(l) for l in lines]


def load_audio(path):
    """Decodifica con ffmpeg a float32 mono 16 kHz (evita el decodificador 'av' de faster-whisper)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def transcribe(audio_path, total):
    from faster_whisper import WhisperModel
    audio = load_audio(audio_path)
    model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
    segs, _ = model.transcribe(
        audio, language="es", word_timestamps=True, vad_filter=False,
        beam_size=5, best_of=5, condition_on_previous_text=False,
        initial_prompt="Letra de una canción de música urbana en español.",
        compression_ratio_threshold=2.2, no_speech_threshold=0.5,
        hallucination_silence_threshold=2.0)
    words = []
    for s in segs:
        if s.no_speech_prob > 0.85 and s.avg_logprob < -1.2:   # tramo sin voz / alucinación
            continue
        for w in (s.words or []):
            t = CLEAN.sub("", w.word).strip().upper()
            if t and w.probability >= 0.15:
                words.append((t, w.start, w.end))
    return _group(words, total)


def parse_srt(path, offset, total):
    txt = open(path, encoding="utf-8-sig").read().replace("\r", "")
    ts = lambda s: sum(float(x.replace(",", ".")) * m for x, m in zip(s.split(":"), (3600, 60, 1)))
    out = []
    for block in re.split(r"\n\s*\n", txt.strip()):
        rows = block.split("\n")
        for i, r in enumerate(rows):
            if "-->" in r:
                a, b = [ts(x.strip()) for x in r.split("-->")]
                text = CLEAN.sub("", " ".join(rows[i + 1:])).strip().upper()
                a, b = a - offset, b - offset
                if text and b > 0 and a < total:
                    out.append((text, max(a, 0), min(b, total)))
                break
    return out
