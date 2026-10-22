#!/usr/bin/env bash
# Run a WanGP request on the free Kaggle GPU and download its outputs.
#   KAGGLE_API_TOKEN=... studio/gpu/kaggle_run.sh <request.json> <out_dir> [kernel_slug]
# Needs: pip install 'kaggle>=1.8'. Waits up to ~5 h. Exit 0 if a report.json came back.
set -euo pipefail
req=$1 out=$2 slug=${3:-studio-gpu-job}
user=${KUSER:-goldgoat}
kernel="$user/$slug"
here=$(cd "$(dirname "$0")" && pwd)
d=$(mktemp -d)
python - "$req" "$here/wangp_job.py" "$d/script.py" <<'PY'
import json, sys
req = json.load(open(sys.argv[1]))
open(sys.argv[3], "w").write("REQUEST_JSON = " + repr(json.dumps(req)) + "\n" + open(sys.argv[2]).read())
PY
cat > "$d/kernel-metadata.json" <<JSON
{"id": "$kernel", "title": "$slug", "code_file": "script.py", "language": "python",
 "kernel_type": "script", "is_private": true, "enable_gpu": true, "enable_internet": true,
 "machine_shape": "NvidiaTeslaT4", "dataset_sources": [], "competition_sources": [], "kernel_sources": []}
JSON
kaggle kernels push -p "$d" 2>&1 | sed 's/[A-Za-z0-9_-]\{30,\}/***/g'
sleep 60
for i in $(seq 1 300); do
  s=$(kaggle kernels status "$kernel" 2>&1 | tail -1)
  case "$s" in *complete*|*COMPLETE*) echo "kaggle: $s"; break;;
    *error*|*ERROR*|*cancel*) echo "kaggle: $s"; break;; esac
  [ $((i % 10)) -eq 0 ] && echo "$i min: $s"
  sleep 60
done
mkdir -p "$out"
kaggle kernels output "$kernel" -p "$out" >/dev/null 2>&1 || true
r=$(find "$out" -name report.json | head -1)
[ -n "$r" ] || { echo "no report.json from Kaggle"; exit 1; }
# Flatten: outputs live in out/ (Kaggle may nest them under out/out/).
inner=$(dirname "$r"); [ "$inner" != "$out" ] && cp -r "$inner"/. "$out"/
python - "$out/report.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
print("env:", json.dumps(r.get("env"))[:600])
for t in r.get("tasks", []):
    print(f"{t['id']}: ok={t.get('success')} {t.get('seconds')}s vram={t.get('peak_vram_gb')}GB files={t.get('files')} err={str(t.get('errors'))[:300]}")
if r.get("error"): print("job error:", r["error"][-900:])
PY
