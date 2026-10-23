"""Render timeline.json with Concat (headless MCP, software GPU). Usage: concat_path.py OUT_DIR"""
import json
import sys
import time
from pathlib import Path

from mcp_client import ConcatMcp

here = Path(__file__).resolve().parent
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
tl = json.loads((here / "timeline.json").read_text())
TRANSITION = {"fade": "concat.dissolve", "slide": "concat.slide", "wipe": "concat.linear-wipe"}
POS_Y = {"top": -0.30, "center": 0.0, "bottom": 0.30}
log: list = []
t0 = time.time()


def created(r):
    if isinstance(r, dict):
        if r.get("createdId"):
            return r["createdId"]
        for v in r.values():
            c = created(v)
            if c:
                return c
    return None


def step(c, tool, args, timeout=600):
    t = time.time()
    r = c.call(tool, args, timeout)
    log.append({"tool": tool, "args": args, "s": round(time.time() - t, 3), "result": r})
    return r


c = ConcatMcp(env={"CONCAT_GPU": "software"})
c.initialize()
try:
    proj = out / "concat_film"
    step(c, "project_create", {"location": str(out), "name": "concat_film",
                               "video": {"width": tl["width"], "height": tl["height"], "rateNum": tl["fps"], "rateDen": 1,
                                         "colorSpace": "sdr"}})
    P = str(proj)
    ids = {}
    for clip in tl["clips"]:
        ids[clip["id"]] = created(step(c, "media_import", {"path": P, "file": str(here / clip["source"])}))
    voices = [created(step(c, "media_import", {"path": P, "file": str(here / f"media/voice{i + 1}.wav")}))
              for i in range(len(tl["clips"]))]
    music = created(step(c, "media_import", {"path": P, "file": str(here / tl["music"]["source"])}))

    # Picture: end to end, each cut to its slot (start of the next clip), transition on the cut into it.
    step(c, "clips_add_sequence", {"path": P, "mediaIds": [ids[x["id"]] for x in tl["clips"]], "start": 0})
    read = step(c, "timeline_read", {"path": P})
    vclips = [x for x in read["timeline"]["clips"] if x.get("kind") == "video"]
    vclips.sort(key=lambda x: x["start"])
    for k, (vc, clip) in enumerate(zip(vclips, tl["clips"])):
        nxt = tl["clips"][k + 1]["start_s"] if k + 1 < len(tl["clips"]) else tl["duration_s"]
        step(c, "clip_trim", {"path": P, "clipId": vc["id"], "edge": "end", "delta": (nxt - clip["start_s"]) - vc["duration"],
                              "ripple": True})
        if clip["transition_in"]:
            step(c, "clip_update", {"path": P, "clipId": vc["id"], "patch": {
                "transitionIn": {"id": TRANSITION[clip["transition_in"]["kind"]], "duration": clip["transition_in"]["duration_s"]}}})

    # Sound: narration lane (each line 0.2 s into its clip) and a music lane under it.
    vtrack = created(step(c, "track_add", {"path": P}))
    for clip, vid in zip(tl["clips"], voices):
        step(c, "clip_add", {"path": P, "mediaId": vid, "trackId": vtrack, "start": clip["start_s"] + 0.2})
    mtrack = created(step(c, "track_add", {"path": P}))
    m = created(step(c, "clip_add", {"path": P, "mediaId": music, "trackId": mtrack, "start": 0}))
    step(c, "clip_update", {"path": P, "clipId": m, "patch": {"volume": 10 ** (tl["music"]["gain_db"] / 20), "fadeOut": 1.5}})

    # Titles: rise + scale + fade in, fade out (keyframes are fractions of the title's length).
    for clip in tl["clips"]:
        t = clip["title"]
        dur = t["until_s"] - t["at_s"]
        y = POS_Y[t["position"]]
        # offsetY is keyed below, so the clip's own offset stays 0: Concat 0.2.8 adds a keyed offset to the clip's
        # base offset (a -0.30 title keyed to -0.30 drew at -0.60, off the frame; see title_probe.py).
        tid = created(step(c, "title_add", {"path": P, "start": t["at_s"], "duration": dur, "offsetY": 0.0, "above": True,
                                            "style": {"content": t["text"], "fontSize": 0.052, "fontWeight": 800,
                                                      "color": "#ffffff", "background": "#0b0b0c99", "shadow": True}}))
        ease = [0.2, 0.8, 0.2, 1.0]
        a = min(0.25, 0.35 / dur)
        for prop, keys in {"opacity": [(0, 0.0), (a, 1.0), (1 - a, 1.0), (1, 0.0)],
                           "scale": [(0, 0.86), (a * 1.4, 1.0)],
                           "offsetY": [(0, y + 0.025), (a * 1.4, y)]}.items():
            for at, v in keys:
                step(c, "keyframe_set", {"path": P, "clipId": tid, "property": prop, "at": at, "value": v, "ease": ease})

    final = step(c, "timeline_read", {"path": P})
    (out / "concat_timeline.json").write_text(json.dumps(final, indent=1))
    step(c, "project_save", {"path": P})
    for ts in (1.5, 3.0, 6.0, 9.0, 13.5):
        try:  # the engine's own compositor, independent of the export
            step(c, "preview_frame", {"path": P, "time": ts, "output": str(out / f"concat_preview_{ts:05.2f}.png")})
        except Exception as e:  # noqa: BLE001
            log.append({"tool": "preview_frame", "error": str(e)})
    t_edit = time.time() - t0
    job = step(c, "export_start", {"path": P, "output": str(out / "concat_15s.mp4"), "crf": 18, "preset": "medium"})
    jid = (job.get("job") or created(job) or job.get("id")) if isinstance(job, dict) else job
    te = time.time()
    status = None
    for _ in range(12):
        status = step(c, "export_wait", {"job": jid, "timeoutSeconds": 600}, timeout=700)
        s = json.dumps(status).lower()
        if any(w in s for w in ('"done"', '"failed"', '"cancelled"', "finished", "error")) or (out / "concat_15s.mp4").exists() and '"running"' not in s:
            break
    result = {"ok": (out / "concat_15s.mp4").exists(), "edit_s": round(t_edit, 2), "export_s": round(time.time() - te, 2),
              "total_s": round(time.time() - t0, 2), "export_status": status}
finally:
    c.close()
    (out / "concat_log.json").write_text(json.dumps({"steps": log, "stderr": c.stderr[-200:]}, indent=1, default=str))
print(json.dumps(result, default=str))
(out / "concat_result.json").write_text(json.dumps(result, indent=1, default=str))
sys.exit(0 if result["ok"] else 1)
