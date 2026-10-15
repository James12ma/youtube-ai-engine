from narration_pro import WordTimestamp,build_ass_from_words
from scripts.render_showcase import export_srt


def test_srt_export_preserves_real_alignment_cues_without_styling(tmp_path):
    ass=tmp_path/'captions.ass';srt=tmp_path/'captions.srt'
    words=[WordTimestamp(word='Review',start_s=.14,end_s=.4),WordTimestamp(word='first.',start_s=.65,end_s=1.2)]
    build_ass_from_words(words,ass,width=1080,height=1920,animated=True)
    export_srt(ass,srt);text=srt.read_text()
    assert '00:00:00,140 --> 00:00:01,200' in text
    assert 'Review first.' in text and '\\kf' not in text and '{' not in text
