from channel.visual_qa import FrameResult, classify, closeness, evaluate
from scripts.footage_discover import best_windows


def fr(t, scene='underwater', present=True, distance='close', subj=None):
    return FrameResult(t=t, scene=scene, underwater_p=1.0 if scene == 'underwater' else 0.0, subject_p=0.9 if present else 0.1,
                       present=present, distance=distance, subjects=subj or {'humpback whale': 0.9 if present else 0.0})


def test_closeness_thresholds():
    assert closeness(0.2, True) == 'close'
    assert closeness(0.05, True) == 'medium'
    assert closeness(0.0, True) == 'far'
    assert closeness(0.0, False) == 'none'


def test_classify_card_has_no_distance():
    raw = {'scene': {'underwater': 0.1, 'surface': 0.1, 'land': 0.1, 'card': 0.7}, 'subjects': {'whale': 0.1},
           'subject_p': 0.1, 'box_area': 0.0, 'box_label': ''}
    f = classify(raw, 3.5)
    assert f.scene == 'card' and f.distance == 'none' and not f.present


def test_good_edit_passes_and_empty_edit_fails():
    kinds = [('underwater', 'close'), ('surface', 'medium'), ('underwater', 'medium'), ('surface', 'close'), ('underwater', 'far')]
    frames, shots = [], []
    for i in range(10):
        scene, dist = kinds[i % len(kinds)]
        for k in range(4):
            frames.append(fr(i * 4 + k + 0.5, scene, True, dist))
        shots.append({'index': i, 'clip': f'c{i % 6}', 'seconds': 4.0, 'expect': 'humpback whale'})
    good = evaluate(frames, shots)
    assert good['passed'], good['failed']
    empty = [fr(t + 0.5, 'surface', False, 'none') for t in range(40)]
    bad = evaluate(empty, [{'index': 0, 'clip': 'a', 'seconds': 40.0, 'expect': 'humpback whale'}])
    assert not bad['passed']
    assert {'subject_visible', 'empty', 'max_shot', 'variety', 'narration_match', 'hook'} <= set(bad['failed'])


def test_best_windows_prefers_close_underwater():
    per = [{'scene': 'surface', 'present': False, 'distance': 'none'}] * 10 + \
          [{'scene': 'underwater', 'present': True, 'distance': 'close'}] * 6 + \
          [{'scene': 'surface', 'present': True, 'distance': 'far'}] * 10
    w = best_windows(per, window=5, top=2)
    assert w[0]['start_s'] in (10, 11) and 'underwater/close' in w[0]['types']
