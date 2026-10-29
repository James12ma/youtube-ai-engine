#!/usr/bin/env python3
"""Rend un épisode JSON en MP4 vertical 1080x1920 (voix FR, images d'archives, sous-titres).

Outils combinés : edge-tts (voix), API Wikimedia Commons (images libres),
Pillow (composition), ffmpeg (montage). Usage :
    python render.py episodes/001-yamaguchi.json            # rendu réel (internet requis)
    python render.py episodes/001-yamaguchi.json --offline  # test sans réseau
"""
import argparse, asyncio, io, json, math, os, re, subprocess, sys, tempfile, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H, FPS = 1080, 1920, 30
FONT_BOLD = next((p for p in [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
] if os.path.exists(p)), None)
UA = "HistoiresVraiesBot/1.0 (contact: goatgold393@gmail.com)"
OK_LICENSES = re.compile(r"(public domain|^pd|cc0)", re.I)  # sans obligation d'attribution
UNSAFE = re.compile(r"(nude|naked|nu |victim|corpse|dead|body|bodies|burn|wound|injur|blood|execution|skeleton|keloid|casualt)", re.I)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"Commande échouée : {' '.join(cmd[:4])}…\n{r.stderr[-1500:]}")
    return r.stdout


def duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "csv=p=0", str(path)]).strip())


# ---------- Voix ----------
async def tts(text, voice, rate, out_mp3):
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words = []
    with open(out_mp3, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append((chunk["offset"] / 1e7, (chunk["offset"] + chunk["duration"]) / 1e7, chunk["text"]))
    return words


def fake_tts(text, out_mp3):
    toks = text.split()
    dur = max(2.0, len(toks) / 2.6)
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{dur:.2f}",
         "-q:a", "9", str(out_mp3)])
    step = dur / len(toks)
    return [(i * step, (i + 1) * step, t) for i, t in enumerate(toks)]


# ---------- Images ----------
def commons_image(query, used, exact_file=None):
    """Image Wikimedia Commons libre (domaine public/CC0), sans contenu choquant. (PIL.Image, crédit) ou None."""
    import requests
    s = requests.Session(); s.headers["User-Agent"] = UA
    base = {"action": "query", "format": "json", "prop": "imageinfo",
            "iiprop": "url|extmetadata|size", "iiurlwidth": 1600}
    if exact_file:
        base.update(titles="File:" + exact_file.removeprefix("File:"))
    else:
        base.update(generator="search", gsrsearch=f"filetype:bitmap {query}", gsrnamespace=6, gsrlimit=15)
    r = s.get("https://commons.wikimedia.org/w/api.php", params=base, timeout=30).json()
    pages = sorted(r.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        url = ii.get("thumburl") or ii.get("url")
        meta = ii.get("extmetadata", {})
        lic = meta.get("LicenseShortName", {}).get("value", "")
        desc = re.sub("<[^>]+>", "", meta.get("ImageDescription", {}).get("value", ""))
        if not url or url in used or not OK_LICENSES.search(lic):
            continue
        if UNSAFE.search(p.get("title", "") + " " + desc):
            continue
        if ii.get("width", 0) < 500:
            continue
        try:
            img = Image.open(io.BytesIO(s.get(url, timeout=60).content)).convert("RGB")
        except Exception:
            continue
        used.add(url)
        artist = re.sub("<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()[:80]
        return img, f"{p['title'].replace('File:', '')} — {artist or 'auteur inconnu'} — {lic} — {ii.get('descriptionurl', '')}"
    return None


def fallback_card(text):
    img = Image.new("RGB", (W, H), (24, 20, 16))
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT_BOLD, 64)
    lines = textwrap.wrap(text.upper(), 18)
    y = H // 2 - len(lines) * 40
    for ln in lines:
        w = d.textlength(ln, font=f)
        d.text(((W - w) / 2, y), ln, font=f, fill=(235, 220, 190))
        y += 82
    return img


def compose(img):
    """Fond flou plein écran + image nette centrée, teinte « archive »."""
    bg = ImageOps.fit(img, (W, H)).filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.45)
    fg = ImageOps.contain(img, (W, int(H * 0.62)))
    frame = bg.copy()
    frame.paste(fg, ((W - fg.width) // 2, int(H * 0.16)))
    return frame


# ---------- Sous-titres ----------
def ass_time(t):
    h, rem = divmod(t, 3600); m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def build_ass(words, path, title):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,DejaVu Sans,78,&H00FFFFFF,&H0000D7FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,6,2,2,60,60,520,1
Style: Hook,DejaVu Sans,62,&H0000D7FF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,5,2,8,60,60,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = [f"Dialogue: 1,{ass_time(0)},{ass_time(3.5)},Hook,,0,0,0,,{title.upper()}"]
    for i in range(0, len(words), 3):
        grp = words[i:i + 3]
        end = words[i + 3][0] if i + 3 < len(words) else grp[-1][1] + 0.3
        txt = " ".join(w[2] for w in grp).replace("{", "").replace("}", "")
        ev.append(f"Dialogue: 0,{ass_time(grp[0][0])},{ass_time(end)},Cap,,0,0,0,,{txt}")
    Path(path).write_text(head + "\n".join(ev) + "\n", encoding="utf-8")


# ---------- Pipeline ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode"); ap.add_argument("--offline", action="store_true")
    ap.add_argument("--out", default="output")
    a = ap.parse_args()
    ep = json.loads(Path(a.episode).read_text(encoding="utf-8"))
    out_dir = Path(a.out); out_dir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=ep["id"] + "-"))
    all_words, clips, credits, used, t0 = [], [], [], set(), 0.0

    for i, sc in enumerate(ep["scenes"]):
        mp3 = tmp / f"s{i:02d}.mp3"
        words = fake_tts(sc["text"], mp3) if a.offline else asyncio.run(
            tts(sc["text"], ep.get("voice", "fr-FR-HenriNeural"), ep.get("rate", "+0%"), mp3))
        d = duration(mp3) + 0.25
        all_words += [(s + t0, e + t0, w) for s, e, w in words]
        found = None if a.offline else (commons_image(sc["query"], used, sc.get("file")) or commons_image(sc["query"], used))
        frame = compose(found[0]) if found else fallback_card(sc.get("label", ""))
        if found: credits.append(found[1])
        png = tmp / f"s{i:02d}.png"; frame.save(png)
        clip = tmp / f"s{i:02d}.mp4"
        n = math.ceil(d * FPS)
        zin = i % 2 == 0  # alterne zoom avant / arrière (mouvement « Ken Burns »)
        z = f"1+0.08*on/{n}" if zin else f"1.08-0.08*on/{n}"
        run(["ffmpeg", "-y", "-loop", "1", "-i", str(png), "-i", str(mp3), "-filter_complex",
             f"[0:v]scale={W*2}:{H*2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS}[v];"
             f"[1:a]apad=pad_dur=0.25,aresample=44100[a]",
             "-map", "[v]", "-map", "[a]", "-t", f"{d:.3f}", "-c:v", "libx264", "-preset", "veryfast",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", str(clip)])
        clips.append(clip); t0 += d

    lst = tmp / "list.txt"; lst.write_text("".join(f"file '{c}'\n" for c in clips))
    joined = tmp / "joined.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)])
    ass = tmp / "subs.ass"; build_ass(all_words, ass, ep["title"])
    final = out_dir / f"{ep['id']}.mp4"
    run(["ffmpeg", "-y", "-i", str(joined), "-vf", f"ass={ass}", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(final)])
    (out_dir / f"{ep['id']}.credits.txt").write_text("\n".join(credits) or "Aucune image externe.", encoding="utf-8")
    print(json.dumps({"video": str(final), "seconds": round(duration(final), 1), "images_libres": len(credits)}))


if __name__ == "__main__":
    main()
