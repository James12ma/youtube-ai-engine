"""Private delivery to the owner's Telegram: the MP4 plus the Inspector's verdict. Never posts publicly.

    TELEGRAM_BOT_TOKEN=... TELEGRAM_OWNER_ID=... python -m studio.deliver film.mp4 --report film_inspection/inspection.json --title "..."
"""
from __future__ import annotations

import json
import os
import uuid
import urllib.request
from pathlib import Path

LIMIT_BYTES = 49 * 1024 * 1024  # Bot API upload limit is 50 MB


def _multipart(fields: dict[str, str], file_field: str, path: Path) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{path.name}\"\r\n"
                 f"Content-Type: video/mp4\r\n\r\n".encode() + path.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), boundary


def caption(title: str, report: dict) -> str:
    lines = [f"🎬 {title}", f"{report.get('width')}×{report.get('height')} · {report.get('duration_s')} s"]
    loud = report.get("loudness") or {}
    if loud.get("integrated_lufs") is not None:
        lines.append(f"Son: {loud['integrated_lufs']} LUFS · peak {loud['true_peak_dbtp']} dBTP")
    defects = report.get("defects", [])
    lines.append("Inspector: pa gen defo teknik" if not defects else "Inspector — defo: " + "; ".join(defects)[:500])
    lines.append("Se ou menm sèl ki ka apwouve videyo a. Pa gen anyen ki pibliye.")
    return "\n".join(lines)[:1024]


def send(mp4: Path, text: str) -> dict:
    token, chat = os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_OWNER_ID"]
    if mp4.stat().st_size > LIMIT_BYTES:
        raise SystemExit(f"{mp4.name} is {mp4.stat().st_size / 1e6:.1f} MB; Telegram bots can send at most 50 MB")
    body, boundary = _multipart({"chat_id": chat, "caption": text, "supports_streaming": "true"}, "video", mp4)
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendVideo", data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        res = json.loads(r.read())
    if not res.get("ok"):
        raise SystemExit(f"Telegram refused: {res.get('description')}")
    return {"message_id": res["result"]["message_id"]}


def notify(text: str) -> None:
    token, chat = os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_OWNER_ID"]
    data = json.dumps({"chat_id": chat, "text": text[:4000]}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=60).read()


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("mp4", type=Path, nargs="?")
    ap.add_argument("--report", type=Path)
    ap.add_argument("--title", default="Videyo")
    ap.add_argument("--message", help="send a text notification instead of a video")
    a = ap.parse_args()
    if a.message:
        notify(a.message)
    else:
        rep = json.loads(a.report.read_text()) if a.report and a.report.exists() else {}
        print(send(a.mp4, caption(a.title, rep)))
