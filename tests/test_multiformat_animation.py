import re
from pathlib import Path
from types import SimpleNamespace
import pytest
from narration_pro import WordTimestamp,build_ass_from_words
from scripts.enforce_gates import parse_ass,validate_captions
from channel.oauth import save_credentials
from production_pro.recorder import WorkflowRecorder,focus_element


def test_animated_captions_preserve_words_and_real_gaps(tmp_path):
    words=[WordTimestamp(word='Check',start_s=.1,end_s=.4),WordTimestamp(word='both',start_s=.7,end_s=.95),WordTimestamp(word='outcomes.',start_s=1,end_s=1.45)]
    path=tmp_path/'captions.ass'
    build_ass_from_words(words,path,width=1080,height=1920,animated=True,bottom_margin=300)
    text=path.read_text()
    assert '{\\kf30}Check' in text and '{\\k30}' in text
    assert validate_captions([w.model_dump() for w in words],parse_ass(path),2)==1
    assert ',80,80,300,1' in text


def test_vertical_browser_layout_and_real_focus(tmp_path):
    def actions(page):
        page.locator('#amount').fill('80');page.locator('#category').select_option('travel')
        page.locator('#submit').click();focus_element(page,'#result')
        assert 'AUTO-APPROVED' in page.locator('#result').inner_text()
        assert page.locator('html').get_attribute('data-focus')=='result'
        result=page.locator('#result').bounding_box()
        assert 0<=result['x'] and result['x']+result['width']<=1080
        assert result['y']+result['height']<1620
        assert page.evaluate('document.documentElement.scrollWidth')<=1080
    r=WorkflowRecorder('local-inline-demo',tmp_path/'rec',viewport=(1080,1920),
        initial_wait_ms=150,chapter_pause_ms=150).record([('Actual approval',actions)])
    assert (r.width,r.height)==(1080,1920)


def test_token_symlink_cannot_replace_destination(tmp_path):
    secret=tmp_path/'untouched';secret.write_text('unchanged')
    target=tmp_path/'token.json';target.symlink_to(secret)
    with pytest.raises(ValueError,match='symbolic link'):
        save_credentials(SimpleNamespace(to_json=lambda:'{}'),target)
    assert secret.read_text()=='unchanged'
