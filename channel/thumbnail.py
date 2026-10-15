"""Create original thumbnails without fabricated metrics or screenshots."""
from __future__ import annotations
from pathlib import Path
import re
import json
from PIL import Image, ImageDraw, ImageFont, ImageOps
from .packaging_lint import QualityPolicy,thumbnail_findings

FONT_CANDIDATES = [
 '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
 '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf',
]
def _font(size):
    for name in FONT_CANDIDATES:
        if Path(name).is_file(): return ImageFont.truetype(name,size)
    return ImageFont.load_default()

def thumbnail_text_path(image_path: Path) -> Path:
    """Sidecar that records the exact text drawn on a thumbnail, for packaging checks."""
    image_path=Path(image_path)
    return image_path.with_name(image_path.name+'.text.json')


def read_thumbnail_text(image_path: Path) -> str | None:
    side=thumbnail_text_path(image_path)
    if not side.is_file(): return None
    return json.loads(side.read_text(encoding='utf-8')).get('text')


def make_thumbnail(headline: str, output_path: Path, *, genuine_screenshot: Path | None = None,
                   width: int=1280,height: int=720, title: str | None = None,
                   policy: QualityPolicy | None = None) -> Path:
    headline=' '.join(headline.split())
    advisories=[]
    if title is not None:
        # Pairing rules are project policy (advisory by default), never YouTube requirements.
        for severity,finding in thumbnail_findings(title,headline,policy or QualityPolicy()):
            if severity=='block':raise ValueError('Thumbnail text rejected by project policy: '+finding.message)
            if severity=='warn':advisories.append(finding.model_dump())
    if not 3<=len(headline)<=90: raise ValueError('headline must contain 3-90 characters')
    # Numeric results must have a separate editorial review, not invented by template.
    if re.search(r'\b\d+(?:[.,]\d+)?\s*%|\$\s*\d+',headline):
        raise ValueError('Numeric thumbnail claims need a manually reviewed custom asset')
    im=Image.new('RGB',(width,height),(11,19,34)); d=ImageDraw.Draw(im)
    for y in range(height): d.line((0,y,width,y),fill=(11+y*12//height,19+y*18//height,34+y*24//height))
    d.rounded_rectangle((56,58,width-56,height-58),radius=38,fill=(28,43,67),outline=(95,178,235),width=4)
    d.rectangle((82,91,95,145),fill=(105,223,184))
    title_font=_font(84 if width>=1280 else 46); label_font=_font(26)
    d.text((118,96),'AI WORKFLOW  •  REAL EXPLANATION',fill=(110,225,190),font=label_font)
    from textwrap import wrap
    lines=wrap(headline,width=19,break_long_words=False)[:4]
    if genuine_screenshot:
        src=Path(genuine_screenshot)
        if not src.is_file() or src.suffix.lower() not in {'.png','.jpg','.jpeg'}:
            raise ValueError('Screenshot must be an actual PNG/JPEG file')
        with Image.open(src) as source:
            shot=ImageOps.contain(source.convert('RGB'),(int(width*.38),int(height*.65)))
        im.paste(shot,(int(width*.58),int(height*.22)))
    else:
        d.rounded_rectangle((int(width*.68),int(height*.22),int(width*.86),int(height*.52)),radius=22,fill=(60,103,154))
        d.text((int(width*.77),int(height*.38)),'AI',anchor='mm',font=_font(92),fill=(235,246,255))
    for i,line in enumerate(lines):
        d.text((98,210+i*110),line,fill=(238,246,255),font=title_font,stroke_width=1,stroke_fill=(28,43,67))
    d.text((92,height-122),'ORIGINAL EDUCATIONAL CONTENT',fill=(178,194,216),font=label_font)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    im.save(output_path,quality=89,optimize=True)
    if output_path.stat().st_size > 2*1024*1024:
        raise ValueError('Thumbnail exceeds 2MB; compress or simplify')
    thumbnail_text_path(output_path).write_text(json.dumps({'text':headline,'advisories':advisories}),encoding='utf-8')
    return output_path
