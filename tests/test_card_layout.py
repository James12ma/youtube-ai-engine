"""Card text must fit inside the frame in both orientations (visual review found overflow)."""
from PIL import Image, ImageDraw
from production.assets import card, fit_text


def test_fit_text_never_exceeds_width_and_keeps_line_limit():
    d = ImageDraw.Draw(Image.new('RGB', (1080, 1920)))
    long = 'Selecting Core Controls from the NIST CSF 2.0 and a much longer heading than usual for this card'
    f, lines = fit_text(d, long, 800, 92, 18, 3)
    assert len(lines) <= 3 and all(d.textlength(l, font=f) <= 800 for l in lines)


def test_portrait_and_landscape_cards_render(tmp_path):
    for size in [(1080, 1920), (1920, 1080)]:
        p = card('text_overlay', 'Los animales más peligrosos del Amazonas', 'La anaconda verde.', size, tmp_path / f'{size[0]}.png')
        assert Image.open(p).size == size
