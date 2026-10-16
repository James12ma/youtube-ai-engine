import httpx
import pytest
from channel import pixabay
from channel.documentary import DocumentaryPlan, license_gate

VIDEOS = {'large': {'url': 'https://cdn.pixabay.com/video/x_large.mp4', 'width': 3840, 'height': 2160, 'size': 9, 'thumbnail': 't'},
          'medium': {'url': 'https://cdn.pixabay.com/video/x_medium.mp4', 'width': 1920, 'height': 1080, 'size': 5},
          'tiny': {'url': 'https://cdn.pixabay.com/video/x_tiny.mp4', 'width': 640, 'height': 360, 'size': 1}}


def hit(**over):
    h = {'id': 7, 'pageURL': 'https://pixabay.com/videos/id-7/', 'type': 'film', 'tags': 'whale, humpback, ocean',
         'duration': 12, 'videos': VIDEOS, 'user': 'Ann', 'user_id': 1}
    h.update(over)
    return h


def test_normalize_keeps_real_film_and_marks_species_unverified():
    clip, why = pixabay.normalize(hit(), 'humpback')
    assert why == '' and clip['best']['height'] == 2160 and clip['review']['name'] == 'tiny'
    assert clip['species_verified'] is False and clip['ai_checked_on_page'] is False


@pytest.mark.parametrize('h,why', [(hit(tags='whale, ai generated, ocean'), 'ai_or_cgi_tag'),
                                    (hit(tags='whale, 3d, render'), 'ai_or_cgi_tag'),
                                    (hit(type='animation'), 'not_film'),
                                    (hit(videos={'large': {'url': 'https://evil.example/x.mp4', 'height': 1080}}), 'no_download')])
def test_normalize_rejects(h, why):
    assert pixabay.normalize(h, 'q') == (None, why)


def test_errors_never_reveal_the_key(monkeypatch):
    monkeypatch.setenv('PIXABAY_API_KEY', 'SECRET123')
    transport = httpx.MockTransport(lambda req: httpx.Response(400, text='[ERROR 400] invalid key SECRET123'))
    with httpx.Client(transport=transport) as client:
        with pytest.raises(pixabay.PixabayError) as exc:
            pixabay.search(client, 'whale')
    assert 'SECRET123' not in str(exc.value)


def test_missing_key(monkeypatch):
    monkeypatch.delenv('PIXABAY_API_KEY', raising=False)
    with pytest.raises(pixabay.PixabayError):
        pixabay.api_key()


def test_license_gate_blocks_unverified_sources():
    plan = DocumentaryPlan.model_validate({
        'series': 'S', 'title': 'T',
        'clips': {'c': {'title': 'File:A.webm'}, 'p': {'kind': 'pixabay', 'pixabay_id': 7}},
        'beats': [{'narration': 'x', 'shots': [{'clip': 'c', 'in_s': 0, 'out_s': 5}, {'clip': 'p', 'in_s': 0, 'out_s': 5}]}]})
    gate = license_gate(plan, {'c': {'license_review_pending': True}, 'p': {}})
    assert not gate['passed'] and len(gate['issues']) == 3
    plan.clips['p'].species_verified = plan.clips['p'].ai_checked = True
    assert license_gate(plan, {'c': {'license_review_pending': False}, 'p': {}})['passed']
