"""Feasibility run: same media + timeline rendered by Concat (headless MCP) and by the existing engine path,
each under /usr/bin/time -v, then measured identically. Usage: render.py OUT_DIR"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

here = Path(__file__).resolve().parent
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
summary = {}


def timed(tag, cmd):
    t = time.time()
    p = subprocess.run(["/usr/bin/time", "-v", *cmd], capture_output=True, text=True, cwd=here)
    (out / f"{tag}.stdout.log").write_text(p.stdout)
    (out / f"{tag}.stderr.log").write_text(p.stderr)
    rss = re.findall(r"Maximum resident set size \(kbytes\): (\d+)", p.stderr)
    cpu = re.findall(r"Percent of CPU this job got: (\d+)%", p.stderr)
    summary[tag] = {"exit": p.returncode, "wall_s": round(time.time() - t, 2),
                    "peak_rss_mb": round(int(rss[-1]) / 1024, 1) if rss else None, "cpu_pct": int(cpu[-1]) if cpu else None}
    print(tag, summary[tag], flush=True)
    return p.returncode


timed("media", [sys.executable, "make_media.py"])
timed("concat", [sys.executable, "concat_path.py", str(out / "concat")])
timed("title_probe", [sys.executable, "title_probe.py", str(out / "title_probe")])
timed("baseline", [sys.executable, "baseline_path.py", str(out / "baseline")])
timed("compare", [sys.executable, "compare.py", str(out / "compare"), str(out / "concat/concat_15s.mp4"),
                  str(out / "baseline/baseline_15s.mp4")])
for tag in ("concat", "baseline"):
    r = out / tag / f"{tag}_result.json"
    if r.exists():
        summary[tag]["result"] = json.loads(r.read_text())
(out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
print(json.dumps(summary, indent=1, default=str))
