"""Isolate how Concat applies keyframes to a title placed off-centre (in the 15 s render, the three titles at
offsetY -0.30 did not appear while the two at 0.0 did). One title per second, each previewed with the engine's
own compositor. Usage: title_probe.py OUT_DIR"""
import json
import sys
from pathlib import Path

from mcp_client import ConcatMcp

here = Path(__file__).resolve().parent
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
CASES = [  # (label, offsetY, {property: [(at, value)]})
    ("top_no_keys", -0.30, {}),
    ("top_opacity_keys", -0.30, {"opacity": [(0, 0.0), (0.2, 1.0), (1, 1.0)]}),
    ("top_scale_keys", -0.30, {"scale": [(0, 0.86), (0.3, 1.0)]}),
    ("top_offsetY_keys", -0.30, {"offsetY": [(0, -0.275), (0.3, -0.30)]}),
    ("center_offsetY_keys", 0.0, {"offsetY": [(0, 0.025), (0.3, 0.0)]}),
]
c = ConcatMcp(env={"CONCAT_GPU": "software"})
c.initialize()
rows = []
try:
    r = c.call("project_create", {"location": str(out), "name": "title_probe",
                                  "video": {"width": 1080, "height": 1920, "rateNum": 30, "rateDen": 1}})
    P = str(out / "title_probe")
    m = c.call("media_import", {"path": P, "file": str(here / "media/clip2.mp4")})["createdId"]
    c.call("clips_add_sequence", {"path": P, "mediaIds": [m], "start": 0})
    for k, (label, y, keys) in enumerate(CASES):
        tid = c.call("title_add", {"path": P, "start": float(k), "duration": 1.0, "offsetY": y, "above": True,
                                   "style": {"content": label, "fontSize": 0.05, "background": "#0b0b0c99"}})["createdId"]
        for prop, ks in keys.items():
            for at, v in ks:
                c.call("keyframe_set", {"path": P, "clipId": tid, "property": prop, "at": at, "value": v})
        png = out / f"{k}_{label}.png"
        c.call("preview_frame", {"path": P, "time": k + 0.6, "output": str(png)})
        rows.append({"case": label, "offsetY": y, "keys": keys, "png": png.name})
    rows.append({"timeline": c.call("timeline_read", {"path": P})["timeline"]["clips"]})
finally:
    c.close()
(out / "title_probe.json").write_text(json.dumps(rows, indent=1))
print(json.dumps(rows[:-1], indent=1))
