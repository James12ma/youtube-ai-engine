"""LogicScript brand assets: profile image, channel banner, first-video thumbnail concept."""
from PIL import Image, ImageDraw, ImageFont

NAVY, NAVY2, MINT, AMBER, WHITE, RED, MUTED = '#0B1021', '#17354A', '#7BF1D0', '#F7BF75', '#FFFFFF', '#FF6B6B', '#9FB3C8'
FD = '/usr/share/fonts/opentype/inter/'
def f(name, size): return ImageFont.truetype(FD + name, size)
BOLD, XB, MED = 'InterDisplay-Bold.otf', 'Inter-ExtraBold.otf', 'InterDisplay-Medium.otf'
OUT = 'brand/'


def check(d, x, y, s, color, width):
    d.line([(x, y + s * 0.55), (x + s * 0.38, y + s * 0.9), (x + s, y + s * 0.1)], fill=color, width=width, joint='curve')


def mark(d, cx, cy, s, stroke):
    """Bracketed check: [ ✓ ] — 'logic you can verify'."""
    h = s * 0.5
    for side in (-1, 1):
        x = cx + side * s * 0.62
        d.line([(x - side * s * 0.16, cy - h), (x, cy - h), (x, cy + h), (x - side * s * 0.16, cy + h)],
               fill=WHITE, width=stroke, joint='curve')
    check(d, cx - s * 0.36, cy - s * 0.38, s * 0.72, MINT, int(stroke * 1.25))


# ---- Profile picture 800x800 (shown as a circle) ----
S = 3
img = Image.new('RGB', (800 * S, 800 * S), NAVY); d = ImageDraw.Draw(img)
d.ellipse((60 * S, 60 * S, 740 * S, 740 * S), fill=NAVY2)
mark(d, 400 * S, 400 * S, 300 * S, 30 * S)
img.resize((800, 800), Image.LANCZOS).save(OUT + 'LogicScript_profile_800.png')

# ---- Banner 2560x1440; everything important inside the 1546x423 safe area ----
img = Image.new('RGB', (2560, 1440), NAVY); d = ImageDraw.Draw(img)
for x in range(0, 2560, 80):       # faint spreadsheet grid
    d.line([(x, 0), (x, 1440)], fill='#111833', width=2)
for y in range(0, 1440, 48):
    d.line([(0, y), (2560, y)], fill='#111833', width=2)
safe = (507, 508, 2053, 931)
d.rounded_rectangle((safe[0] - 10, safe[1] + 40, safe[2] + 10, safe[3] - 40), 36, fill=NAVY)
mark(d, 720, 720, 150, 16)
d.text((860, 640), 'LogicScript', font=f(XB, 120), fill=WHITE, anchor='lm')
d.text((866, 760), 'Spreadsheets & automations you can trust', font=f(MED, 54), fill=MINT, anchor='lm')
d.text((866, 840), 'New practical tutorial every week', font=f(MED, 38), fill=MUTED, anchor='lm')
img.save(OUT + 'LogicScript_banner_2560x1440.png', optimize=True)

# ---- Thumbnail concept for video 1 (1280x720) ----
S = 2
img = Image.new('RGB', (1280 * S, 720 * S), NAVY); d = ImageDraw.Draw(img)
def R(*v): return tuple(int(x * S) for x in v)
d.rounded_rectangle(R(60, 150, 760, 640), 18 * S, fill='#F8FAFC')
cols = [60, 250, 470, 620, 760]
rows = [('Date', 'Category', 'Amount', ''), ('Jan 05', 'Supplies', '48.20', 'ok'),
        ('Jan 12', 'Software', '59.99', 'ok'), ('Feb 14', 'Meal', '38.75', 'bad'), ('Mar 15', 'Rent', '1,200.00', 'ok')]
for i, (a, b, c, state) in enumerate(rows):
    y = 150 + i * 98
    if state == 'bad':
        d.rectangle(R(60, y, 760, y + 98), fill='#FDE2E1'); d.rectangle(R(60, y, 72, y + 98), fill=RED)
    if i:
        d.line(R(60, y, 760, y), fill='#CBD5E1', width=2 * S)
    fnt = f(BOLD if i == 0 else MED, 40 * S)
    for x, t in zip(cols, (a, b, c)):
        d.text(R(x + 24, y + 49), t, font=fnt, fill='#475569' if i == 0 else '#0F172A', anchor='lm')
    if state == 'ok':
        check(d, *R(700, y + 30), 36 * S, '#16A34A', 7 * S)
    if state == 'bad':
        d.line(R(700, y + 30, 736, y + 66), fill=RED, width=8 * S); d.line(R(736, y + 30, 700, y + 66), fill=RED, width=8 * S)
size = 140
while f(XB, size * S).getlength('CAUGHT') > 420 * S:   # fit between x=810 and 1230
    size -= 2
d.text(R(810, 250), 'IT', font=f(XB, 150 * S), fill=WHITE, anchor='lm')
d.text(R(810, 400), 'CAUGHT', font=f(XB, size * S), fill=AMBER, anchor='lm')
d.text(R(810, 535), 'IT', font=f(XB, 150 * S), fill=WHITE, anchor='lm')
d.text(R(60, 90), 'LOGICSCRIPT', font=f(BOLD, 34 * S), fill=MINT, anchor='lm')
img.resize((1280, 720), Image.LANCZOS).save(OUT + 'Video1_thumbnail_concept.jpg', quality=92)
print('ok')
