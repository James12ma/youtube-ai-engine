"""Shorts are sentence-aligned excerpts of the long video's own narration."""
from __future__ import annotations
import json
import pytest
import channel.shorts as shorts
from narration_pro.aligner import WordTimestamp


def _words(sentences, wps=2.5, start=0.0):
    out=[];t=start
    for sentence in sentences:
        tokens=sentence.split()
        for i,tok in enumerate(tokens):
            out.append(WordTimestamp(word=tok,start_s=round(t,3),end_s=round(t+0.3,3)));t+=1/wps
    return out


def test_plan_starts_at_chapters_ends_on_sentence_and_respects_bounds():
    s=' '.join(['palabra']*29)+' fin.'   # 30 words = 12 s
    words=_words([s]*20)                     # 240 s total
    chapters=[{'start_s':0,'title':'Intro'},{'start_s':48,'title':'Uno'},{'start_s':120,'title':'Dos'},{'start_s':180,'title':'Tres'}]
    plans=shorts.plan_shorts(words,chapters,count=3)
    assert [p.chapter_title for p in plans]==['Uno','Dos','Tres']
    for p in plans:
        assert shorts.MIN_SHORT_S<=p.duration_s<=shorts.MAX_SHORT_S+0.3
        last=[w for w in words if w.end_s<=p.end_s][-1]
        assert last.word.endswith('.')


def test_no_sentence_end_in_window_gives_no_plan():
    words=_words([' '.join(['palabra']*400)])
    assert shorts.plan_shorts(words,[{'start_s':0,'title':'A'},{'start_s':10,'title':'B'}])==[]


def test_count_spreads_across_video():
    s=' '.join(['w']*59)+' end.'
    words=_words([s]*12)
    chapters=[{'start_s':0,'title':'Intro'}]+[{'start_s':24.0*i,'title':'C'+str(i)} for i in range(1,12)]
    plans=shorts.plan_shorts(words,chapters,count=3)
    assert len(plans)==3 and plans[0].start_s<plans[1].start_s<plans[2].start_s and [p.index for p in plans]==[0,1,2]


def test_cut_short_builds_vertical_command_with_shifted_captions(tmp_path,monkeypatch):
    src=tmp_path/'uncaptioned.mp4';src.write_bytes(b'x')
    words=_words(['Hola esto es una prueba.','Segunda frase aqui.'],start=100)
    plan=shorts.ShortPlan(index=0,chapter_title='C',start_s=100.0,end_s=words[-1].end_s+0.25,words=len(words))
    cmds=[]
    monkeypatch.setattr(shorts,'_run',lambda cmd:cmds.append(cmd))
    result=shorts.cut_short(src,words,plan,tmp_path/'out'/'short_1.mp4')
    cmd=cmds[0]
    assert cmd[cmd.index('-ss')+1]=='100.000' and 'crop=1080:1920' in cmd[cmd.index('-filter_complex')+1]
    ass=(tmp_path/'out'/'short_1_work'/'captions.ass').read_text()
    assert 'Dialogue: 0,0:00:00.00' in ass and result['height']==1920


def test_make_shorts_requires_some_excerpt(tmp_path):
    work=tmp_path/'w';work.mkdir()
    (work/'render_report.json').write_text(json.dumps({'chapters':[{'start_s':0,'title':'A'}]}))
    (work/'words.json').write_text(json.dumps({'words':[{'word':'sin','start_s':0,'end_s':0.3}]}))
    with pytest.raises(shorts.ShortsError,match='no sentence-aligned'):shorts.make_shorts(work,tmp_path/'o')
