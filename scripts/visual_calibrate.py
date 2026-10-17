"""Calibrate the visual-QA scene detector on hand-labelled public-domain footage (NOAA B-roll).

Labels come from a person watching the frame sheets. The script scores every
labelled second once with CLIP, then tries several prompt sets / aggregation
rules and prints the accuracy of each, so the choice in channel/visual_qa.py
rests on numbers instead of guesses. Re-run when the prompts change.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

# (start_s, end_s, scene) on the source file's own timeline
LABELS = {
    3911325489001: [(9, 76, 'underwater'), (88, 139, 'underwater'), (143, 180, 'surface'), (181, 220, 'surface'),
                    (226, 237, 'surface'), (241, 299, 'surface')],
    4084488077001: [(10, 47, 'underwater'), (54, 82, 'underwater'), (83, 92, 'land'), (93, 102, 'land'),
                    (115, 164, 'land')],
}

VARIANTS = {
    'v1': {'underwater': ['an underwater photo in the ocean', 'an underwater photo of a coral reef',
                          'an underwater photo of a large animal swimming in blue water'],
           'surface': ['a photo of the ocean surface', 'an aerial drone photo of the sea from above',
                       'a photo of an animal at the surface of the sea seen from a boat'],
           'land': ['a photo of a sandy beach', 'a photo of a rocky coastline', 'a photo of snowy mountains and icebergs',
                    'a photo of a forest or green hills', 'an aerial photo of an island']},
    'v2': {'underwater': ['an underwater photo in the ocean', 'an underwater photo of a coral reef',
                          'an underwater photo of a large animal swimming in blue water',
                          'a murky green underwater photo of an animal swimming over rocks',
                          'a scuba diver photo of a sea animal close up'],
           'surface': ['a photo of the ocean surface with waves', 'an aerial drone photo of the sea from above',
                       "a photo of a whale's back and fin above the waves"],
           'land': ['a photo of a sandy beach', 'a photo of a rocky coastline', 'a photo of snowy mountains and icebergs',
                    'a photo of a forest or green hills', 'an aerial photo of an island']},
    'v3': {'underwater': ['a photo taken underwater', 'an underwater photo with light rays from the surface above',
                          'an underwater photo of an animal swimming in the water column'],
           'surface': ['a photo of the sea surface and the sky taken from a boat', 'an aerial drone photo of the sea from above',
                       'a photo of waves on the ocean'],
           'land': ['a photo of an animal resting on a beach', 'a photo of a sandy or rocky beach',
                    'a photo of a coastline or mountains']},
    'v4': {'underwater': ['a photo taken underwater', 'an underwater photo with light rays from the surface above',
                          'an underwater photo of an animal swimming in the water column'],
           'surface': ['a photo of the ocean surface', 'an aerial drone photo of the sea from above',
                       'a photo of a whale at the surface of the sea seen from a boat', 'a photo of waves on the ocean'],
           'land': ['a photo of an animal resting on a beach', 'a photo of a sandy or rocky beach',
                    'a photo of a coastline or mountains']},
}
for v in list(VARIANTS):
    VARIANTS[v]['card'] = ['white text on a plain black background']


def frames_for(path: Path, labels, tmp: Path):
    import subprocess
    from PIL import Image
    tmp.mkdir(parents=True, exist_ok=True)
    out = []
    for a, b, scene in labels:
        for t in range(a, b, 2):
            f = tmp / f'{path.stem}_{t}.jpg'
            subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-ss', f'{t + 0.5}', '-i', str(path),
                            '-frames:v', '1', '-vf', 'scale=640:-2', str(f)], check=True)
            out.append((Image.open(f).convert('RGB'), scene, f'{path.stem}@{t}'))
    return out


def main() -> None:
    import httpx
    import torch
    from transformers import CLIPModel, CLIPProcessor
    from channel import noaa
    torch.set_grad_enabled(False)
    work = Path(sys.argv[1] if len(sys.argv) > 1 else 'outputs/calibrate')
    samples = []
    with httpx.Client(trust_env=True) as client:
        for vid, labels in LABELS.items():
            p = noaa.download(client, vid, work / f'{vid}.mp4')
            samples += frames_for(p, labels, work / 'frames')
            p.unlink()
    results = {}
    for model_id in ('openai/clip-vit-base-patch16', 'openai/clip-vit-large-patch14'):
        model, proc = CLIPModel.from_pretrained(model_id).eval(), CLIPProcessor.from_pretrained(model_id)
        img = []
        for i in range(0, len(samples), 16):
            inp = proc(images=[s[0] for s in samples[i:i + 16]], return_tensors='pt')
            e = model.get_image_features(**inp)
            img.append(e / e.norm(dim=-1, keepdim=True))
        img = torch.cat(img)
        for vname, groups in VARIANTS.items():
            prompts = [p for ps in groups.values() for p in ps]
            names = [g for g, ps in groups.items() for _ in ps]
            t = model.get_text_features(**proc(text=prompts, return_tensors='pt', padding=True))
            t = t / t.norm(dim=-1, keepdim=True)
            probs = (model.logit_scale.exp() * img @ t.T).softmax(dim=-1)
            for agg in ('sum', 'max', 'mean'):
                ok, conf = 0, {}
                for row, (_, truth, _) in zip(probs, samples):
                    score = {}
                    for g in groups:
                        vals = [row[k].item() for k, n in enumerate(names) if n == g]
                        score[g] = sum(vals) if agg == 'sum' else max(vals) if agg == 'max' else sum(vals) / len(vals)
                    pred = max(score, key=score.get)
                    ok += pred == truth
                    conf[f'{truth}->{pred}'] = conf.get(f'{truth}->{pred}', 0) + 1
                key = f'{model_id.split("/")[1]}|{vname}|{agg}'
                results[key] = {'accuracy': round(ok / len(samples), 3), 'confusion': conf}
                print(key, json.dumps(results[key]))
    table = sorted(((r['accuracy'], k) for k, r in results.items()), reverse=True)
    print('::notice title=ranking::' + json.dumps(table)[:3900])
    for acc, k in table[:3]:
        print(f'::notice title={k}::' + json.dumps(results[k]))
    (work / 'calibration.json').write_text(json.dumps({'n': len(samples), 'results': results}, indent=1))


if __name__ == '__main__':
    main()
