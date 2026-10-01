import glob, math, os, subprocess
import numpy as np
from PIL import Image
from . import config as C

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def audio_duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "default=nw=1:nk=1", path])
    return float(out.strip())


def prepare_backgrounds(workdir, files=None):
    if not files:   # respaldo: fotos del repo
        files = sorted(f for ext in ("jpg", "jpeg", "png", "webp")
                       for f in glob.glob(os.path.join(ROOT, "assets", "backgrounds", f"*.{ext}")))
    if not files:
        raise SystemExit("No hay fotos de fondo (ni en Drive ni en assets/backgrounds/)")
    files = (files * 4)[:4]
    outs = []
    for i, f in enumerate(files):
        im = Image.open(f).convert("RGB")
        # cubrir 1080x1920 con zoom extra, recorte centrado
        scale = max(C.W / im.width, C.H / im.height) * C.ZOOM
        im = im.resize((math.ceil(im.width * scale), math.ceil(im.height * scale)), Image.LANCZOS)
        l, t = (im.width - C.W) // 2, (im.height - C.H) // 2
        a = np.asarray(im.crop((l, t, l + C.W, t + C.H))).astype(np.float32)
        a *= C.DARKEN
        a = a * (1 - C.PURPLE_AMOUNT) + np.array(C.PURPLE, np.float32) * C.DARKEN * C.PURPLE_AMOUNT * 1.6
        a = np.clip(a, 0, 255).astype(np.uint8)
        variants = [a, a[:, ::-1]] if C.FLIP == "alternate" else [a[:, ::-1]] if C.FLIP == "all" else [a]
        for j, v in enumerate(variants):          # a[:, ::-1] = volteado horizontal
            p = os.path.join(workdir, f"bg{i}_{j}.png")
            Image.fromarray(np.ascontiguousarray(v)).save(p)
            outs.append(p)
    return outs


def _t(s):
    h, m = int(s // 3600), int(s % 3600 // 60)
    return f"{h}:{m:02d}:{s % 60:05.2f}"


def write_ass(lines, dur, path):
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {C.W}
PlayResY: {C.H}
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Lyric,{C.FONT_NAME},{C.LYRIC_SIZE},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,{C.LYRIC_ITALIC},0,0,100,100,1,0,1,3,4,5,40,40,0,1
Style: Mark,{C.WATERMARK_FONT},{C.WATERMARK_SIZE},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,14,0,1,0,0,5,40,40,0,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    ev = [f"Dialogue: 0,{_t(0)},{_t(dur)},Mark,,0,0,0,,{{\\an5\\pos({C.W // 2},{C.WATERMARK_Y})\\alpha&H70&}}{C.WATERMARK}"]
    for text, a, b in lines:
        if b - a < 0.15:
            continue
        ev.append(f"Dialogue: 1,{_t(a)},{_t(b)},Lyric,,0,0,0,,{{\\an5\\pos({C.W // 2},{C.LYRIC_Y})\\fad(90,90)}}{text}")
    open(path, "w", encoding="utf-8").write(hdr + "\n".join(ev) + "\n")


def render(audio, start, dur, lines, workdir, out, photos=None):
    bgs = prepare_backgrounds(workdir, photos)
    lst = os.path.join(workdir, "bg.txt")
    n = math.ceil(dur / C.BG_SECONDS) + 4
    with open(lst, "w") as f:
        for i in range(n):
            f.write(f"file '{bgs[i % len(bgs)]}'\nduration {C.BG_SECONDS}\n")
        f.write(f"file '{bgs[(n - 1) % len(bgs)]}'\n")
    ass = os.path.join(workdir, "lyrics.ass")
    write_ass(lines, dur, ass)
    fonts = os.path.join(ROOT, "fonts")
    af = "aresample=48000"
    if dur >= C.MAX_SECONDS - 0.05:          # si se cortó a 25 s, fade-out suave
        af += f",afade=t=out:st={dur - 0.6:.2f}:d=0.6"
    z = f"(1+({C.ZOOM_END}-1)*min(t/{dur:.3f},1))"   # zoom animado 1.0 -> ZOOM_END
    cmd = ["ffmpeg", "-y", "-v", "error",
           "-f", "concat", "-safe", "0", "-i", lst,
           "-ss", str(start), "-t", f"{dur:.3f}", "-i", audio,
           "-vf", (f"fps={C.FPS},"
                   f"scale=w='2*trunc({C.W // 2}*{z})':h='2*trunc({C.H // 2}*{z})':eval=frame:flags=bicubic,"
                   f"crop={C.W}:{C.H},"
                   f"ass={ass}:fontsdir={fonts},format=yuv420p"),
           "-af", af, "-t", f"{dur:.3f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-profile:v", "high",
           "-g", str(C.FPS * 2), "-keyint_min", str(C.FPS * 2), "-sc_threshold", "0",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
           "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    return out
