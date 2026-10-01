import json, os, re, requests

API = "https://www.googleapis.com/drive/v3/files"
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")
AUDIO_EXT = (".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac", ".opus")
_token = None


def _auth():
    """Cuenta de servicio (carpetas privadas) o, si no hay, clave de API (carpetas públicas)."""
    global _token
    sa = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if sa:
        if _token is None:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request
            creds = service_account.Credentials.from_service_account_info(
                json.loads(sa), scopes=["https://www.googleapis.com/auth/drive.readonly"])
            creds.refresh(Request())
            _token = creds.token
        return {"Authorization": f"Bearer {_token}"}, {}
    return {}, {"key": os.environ["GOOGLE_API_KEY"]}


def _get(url, params, **kw):
    headers, extra = _auth()
    r = requests.get(url, params={**params, **extra}, headers=headers, timeout=120, **kw)
    if not r.ok:   # sin imprimir la URL ni credenciales
        raise SystemExit(f"Error de Google Drive {r.status_code}: {r.text[:300]}")
    return r


def list_files(folder=None):
    folder = folder or os.environ["DRIVE_FOLDER_ID"].strip()
    out, token = [], None
    while True:
        p = {"q": f"'{folder}' in parents and trashed=false",
             "fields": "nextPageToken,files(id,name,mimeType)", "pageSize": 1000}
        if token:
            p["pageToken"] = token
        d = _get(API, p).json()
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
    r = _get(f"{API}/{file['id']}", {"alt": "media"}, stream=True)
    with open(dest, "wb") as fh:
        for chunk in r.iter_content(1 << 20):
            fh.write(chunk)
    return dest


def start_offset(name):
    """Si el archivo se llama 'tema__s45.mp3' el clip empieza en el segundo 45."""
    m = re.search(r"__s(\d+(?:\.\d+)?)", name)
    return float(m.group(1)) if m else 0.0
