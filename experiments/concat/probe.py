"""Probe Concat's headless MCP server: version, backend, every tool schema, effects/templates catalogues."""
import json
import sys
import time
from pathlib import Path

from mcp_client import ConcatMcp

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
t0 = time.time()
c = ConcatMcp(env={"CONCAT_GPU": "software"})
res = {"initialize": c.initialize()}
res["init_s"] = round(time.time() - t0, 2)
tools = c.request("tools/list")["tools"]
(out / "tools.json").write_text(json.dumps(tools, indent=1))
res["tools"] = [t["name"] for t in tools]
for name in ("concat_version", "effects_list", "template_list", "project_list"):
    try:
        res[name] = c.call(name, {})
    except Exception as e:  # noqa: BLE001
        res[name] = {"error": str(e)}
c.close()
res["stderr_tail"] = c.stderr[-40:]
(out / "probe.json").write_text(json.dumps(res, indent=1, default=str))
print(json.dumps({k: (v if k != "effects_list" else "...") for k, v in res.items() if k != "stderr_tail"}, default=str)[:3000])
