import datetime as dt, json, os, random, tempfile, time
from . import config as C, drive, lyrics, render

STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "used.json")


def seconds_until_slot(now):
    """Segundos a esperar hasta el horario de publicación más cercano (0 si ya pasó)."""
    best = None
    for day in (-1, 0, 1):
        for h, m in C.SLOTS_UTC:
            slot = (now + dt.timedelta(days=day)).replace(hour=h, minute=m, second=0, microsecond=0)
            d = (slot - now).total_seconds()
            if -90 * 60 <= d <= C.MAX_WAIT_MIN * 60 and (best is None or abs(d) < abs(best)):
                best = d
    return max(best, 0) if best is not None else 0


def load_used():
    try:
        return json.load(open(STATE))["used"]
    except Exception:
        return []


def save_used(used):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump({"used": used}, open(STATE, "w"), indent=1)


def main():
    t0 = dt.datetime.now(dt.timezone.utc)
    dry = os.getenv("DRY_RUN") == "1"
    now_mode = os.getenv("PUBLISH_NOW") == "true"
    work = tempfile.mkdtemp()

    files = drive.list_files()
    audios = [f for f in files if drive.is_audio(f)]
    if not audios:
        raise SystemExit("No hay audios en la carpeta de Drive")
    used = load_used()
    pool = [a for a in audios if a["id"] not in used]
    if not pool:                                # ya sonaron todos: reinicia la rotación
        used, pool = [], audios
    song = random.choice(pool)
    print("Canción elegida:", song["name"])

    audio = drive.download(song, os.path.join(work, "audio" + os.path.splitext(song["name"])[1]))
    start = drive.start_offset(song["name"])
    total = audio_len = render.audio_duration(audio)
    dur = min(C.MAX_SECONDS, audio_len - start)
    if dur < 3:
        raise SystemExit("El audio (o el tramo elegido) dura menos de 3 s")

    srt = drive.find_srt(song["name"], files)
    if srt:
        print("Usando letra manual (.srt)")
        lines = lyrics.parse_srt(drive.download(srt, os.path.join(work, "l.srt")), 0, dur)
    else:
        clip = os.path.join(work, "clip.wav")
        os.system(f'ffmpeg -y -v error -ss {start} -t {dur} -i "{audio}" -ac 1 -ar 16000 "{clip}"')
        lines = lyrics.transcribe(clip, dur)
    print("Líneas de letra:", len(lines))

    photo_folder = os.getenv("DRIVE_PHOTOS_FOLDER_ID", "").strip()
    pfiles = drive.list_files(photo_folder) if photo_folder else files
    imgs = [f for f in pfiles if drive.is_image(f)]
    print(f"Archivos en la carpeta de fotos: {len(pfiles)} | fotos válidas (jpg/png/webp): {len(imgs)}")
    if photo_folder and not imgs:
        raise SystemExit("No encontré fotos en la carpeta de fotos de Drive. Revisá que esté compartida "
                         "con el email de la cuenta de servicio y que las fotos sean jpg, png o webp (no HEIC).")
    if len(imgs) > 4:
        imgs = random.sample(imgs, 4)           # cada reel usa 4 fotos distintas
    photos = []
    for i, im in enumerate(imgs):
        photos.append(drive.download(im, os.path.join(work, f"foto{i}{os.path.splitext(im['name'])[1] or '.jpg'}")))
    print("Fotos de fondo desde Drive:", len(photos))

    out = os.path.join(work, "reel.mp4")
    render.render(audio, start, dur, lines, work, out, photos)
    tags = ""   # descripción vacía (sin hashtags)

    if dry:
        os.replace(out, "reel_preview.mp4")
        print("DRY_RUN: guardado reel_preview.mp4")
        return

    if not now_mode:
        wait = seconds_until_slot(t0) - (dt.datetime.now(dt.timezone.utc) - t0).total_seconds()
        if wait > 0:
            print(f"Esperando {wait / 60:.1f} min hasta el horario de publicación...")
            time.sleep(wait)

    from . import facebook
    vid = facebook.publish_reel(out, tags)
    print("Publicado, video id:", vid)
    used.append(song["id"])
    save_used(used)


if __name__ == "__main__":
    main()
