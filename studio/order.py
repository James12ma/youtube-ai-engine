"""Read a film order. Telegram orders carry only a private file reference + SHA-256; the script is
downloaded on the runner with the bot token and verified, so it never enters the public repository.

    python -m studio.order studio/orders/<id>.json   # prints GitHub step outputs, writes <film>/script.txt
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path


def fetch_telegram_document(file_id: str, token: str) -> bytes:
    with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}", timeout=60) as r:
        meta = json.loads(r.read())
    if not meta.get("ok"):
        raise SystemExit("Telegram getFile refused the order's file reference")
    with urllib.request.urlopen(f"https://api.telegram.org/file/bot{token}/{meta['result']['file_path']}", timeout=120) as r:
        return r.read()


def read_order(path: Path, fetch=fetch_telegram_document) -> dict:
    o = json.loads(path.read_text())
    fid = re.sub(r"[^a-z0-9_-]", "", str(o.get("id", "")).lower())[:60]
    if not fid:
        raise SystemExit("order id required")
    film = o.get("film") or f"studio/films/{fid}"
    if not re.fullmatch(r"studio/films/[A-Za-z0-9_-]+", film):
        raise SystemExit("bad film path")
    script, language, voice, title = o.get("script"), o.get("language", "en"), o.get("voice", ""), o.get("title", fid)
    if o.get("telegram_file_id"):
        doc = json.loads(fetch(o["telegram_file_id"], os.environ["TELEGRAM_BOT_TOKEN"]))
        script = doc["script"]
        if hashlib.sha256(script.encode()).hexdigest() != o.get("source_sha256"):
            raise SystemExit("script hash mismatch: refusing to render a script the owner did not send")
        language, voice = doc.get("language", language), doc.get("voice", voice) or voice
        title = doc.get("title", title)
    Path(film).mkdir(parents=True, exist_ok=True)
    if script:
        (Path(film) / "script.txt").write_text(script.strip() + "\n")
    return {"id": fid, "film": film, "lang": re.sub(r"[^a-z]", "", language) or "en",
            "voice": re.sub(r"[^a-z_]", "", voice or ""), "title": str(title).replace("\n", " ")[:120]}


if __name__ == "__main__":
    for k, v in read_order(Path(sys.argv[1])).items():
        print(f"{k}={v}")
