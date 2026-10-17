"""Readable title/credit cards (slates) inside NOAA B-roll packages + 1 fps contact sheets.

NOAA B-roll packages put a black card before each segment (location, credit, permit numbers).
Every second whose frame is mostly black is saved at 1280 px so the text can be read; the
whole package is also saved as a timestamped 1 fps sheet. Review material only (encrypted).
"""
from __future__ import annotations
import argparse
import subprocess
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageStat

from channel import noaa


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--ids', required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    with httpx.Client(trust_env=True) as client:
        for vid in [int(v) for v in a.ids.split(';') if v.strip()]:
            src = noaa.download(client, vid, a.out / f'{vid}.mp4')
            fr = a.out / f'f{vid}'
            fr.mkdir(exist_ok=True)
            subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(src), '-vf',
                            'fps=1,scale=1280:-2', '-q:v', '3', str(fr / '%05d.jpg')], check=True)
            frames = sorted(fr.glob('*.jpg'))
            prev_card = -10
            thumbs = []
            for i, f in enumerate(frames):
                im = Image.open(f).convert('L')
                if ImageStat.Stat(im).mean[0] < 22 and i - prev_card > 1:   # a new card
                    Image.open(f).save(a.out / f'card_{vid}_{i:04d}s.jpg', quality=90)
                if ImageStat.Stat(im).mean[0] < 22:
                    prev_card = i
                t = Image.open(f).convert('RGB'); t.thumbnail((256, 144))
                ImageDraw.Draw(t).rectangle([0, 0, 52, 14], fill=(0, 0, 0))
                ImageDraw.Draw(t).text((2, 1), f'{i // 60}:{i % 60:02d}', fill=(255, 255, 0))
                thumbs.append(t)
            cols = 10
            for p in range(0, len(thumbs), 100):
                chunk = thumbs[p:p + 100]
                sheet = Image.new('RGB', (cols * 256, ((len(chunk) + cols - 1) // cols) * 144))
                for k, t in enumerate(chunk):
                    sheet.paste(t, ((k % cols) * 256, (k // cols) * 144))
                sheet.save(a.out / f'sheet_{vid}_{p // 100}.jpg', quality=80)
            for f in frames:
                f.unlink()
            fr.rmdir()
            src.unlink()


if __name__ == '__main__':
    main()
