import os, re, requests

API = "https://www.googleapis.com/drive/v3/files"
AUDIO_EXT = (".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac", ".opus")


def list_files():
    key, folder = os.environ["GOOGLE_API_KEY"], os.environ["DRIVE_FOLDER_ID"]
    out, token = [], None
    while True:
        p = {"q": f"'{folder}' in parents and trashed=false", "key": key,
             "fields": "nextPageToken,files(id,name,mimeType)", "pageSize": 1000}
        if token:
            p["pageToken"] = token
        r = requests.get(API, params=p, timeout=60)
        r.raise_for_status()
        d = r.json()
        out += d["files"]
        token = d.get("nextPageToken")
        if not token:
            return out


def list_audios():
    return [f for f in list_files() if f["name"].lower().endswith(AUDIO_EXT)]


def find_srt(audio_name, files):
    base = os.path.splitext(audio_name)[0].lower()
    for f in files:
        if f["name"].lower() == base + ".srt":
            return f
    return None


def download(file, dest):
    r = requests.get(f"{API}/{file['id']}", params={"alt": "media", "key": os.environ["GOOGLE_API_KEY"]},
                     stream=True, timeout=120)
    r.raise_for_status()
    with open(dest, "wb") as fh:
        for chunk in r.iter_content(1 << 20):
            fh.write(chunk)
    return dest


def start_offset(name):
    """Si el archivo se llama 'tema__s45.mp3' el clip empieza en el segundo 45."""
    m = re.search(r"__s(\d+(?:\.\d+)?)", name)
    return float(m.group(1)) if m else 0.0
