import os, time, requests
from . import config as C


def publish_reel(video_path, description):
    page, token = os.environ["FB_PAGE_ID"], os.environ["FB_PAGE_TOKEN"]
    base = f"https://graph.facebook.com/{C.GRAPH_VERSION}/{page}/video_reels"

    r = requests.post(base, data={"upload_phase": "start", "access_token": token}, timeout=60)
    if not r.ok:    # Facebook explica el motivo en el cuerpo de la respuesta
        raise SystemExit(f"Facebook rechazó el inicio de la subida ({r.status_code}): {r.text[:600]}")
    video_id, upload_url = r.json()["video_id"], r.json()["upload_url"]

    size = os.path.getsize(video_path)
    with open(video_path, "rb") as fh:
        u = requests.post(upload_url, data=fh, timeout=600, headers={
            "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)})
    if not u.ok:
        raise RuntimeError(f"Fallo la subida: {u.status_code} {u.text}")

    data = {"access_token": token, "video_id": video_id, "upload_phase": "finish",
            "video_state": "PUBLISHED"}
    if description:
        data["description"] = description
    f = requests.post(base, timeout=120, data=data)
    if not f.ok:
        raise RuntimeError(f"Fallo el publish: {f.status_code} {f.text}")

    for _ in range(20):                       # espera al procesamiento (hasta ~5 min)
        time.sleep(15)
        s = requests.get(f"https://graph.facebook.com/{C.GRAPH_VERSION}/{video_id}",
                         params={"fields": "status", "access_token": token}, timeout=60).json()
        st = s.get("status", {})
        print("Estado:", st)
        if st.get("video_status") in ("ready", "published") or st.get("publishing_phase", {}).get("status") == "complete":
            break
        if st.get("video_status") == "error":
            raise RuntimeError(f"Facebook rechazó el video: {s}")
    return video_id
