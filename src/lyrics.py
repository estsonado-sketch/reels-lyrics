import re
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


def transcribe(audio_path, total):
    from faster_whisper import WhisperModel
    model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
    segs, _ = model.transcribe(audio_path, language="es", word_timestamps=True,
                               vad_filter=False, condition_on_previous_text=False)
    words = []
    for s in segs:
        for w in (s.words or []):
            t = CLEAN.sub("", w.word).strip().upper()
            if t:
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
