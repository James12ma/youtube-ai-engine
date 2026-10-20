#!/usr/bin/env bash
# Reproducible local render of the "Focus" premium motion prototype (1080x1920, 30 fps, 13 s).
# CPU only, no paid services. Steps: Blender plates -> sound design -> Remotion composite -> QA.
#
#   ./render.sh                 # full quality (~3.5 h on 4 CPU cores)
#   PREVIEW=1 ./render.sh       # 25 % plates, 6 samples (~8 min) for timing checks
#
# Env overrides: BPY_PYTHON (python with `bpy` 5.2 installed), CHROME (headless shell), JOBS (parallel Blender procs).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
BPY_PYTHON="${BPY_PYTHON:-python3}"
JOBS="${JOBS:-2}"
FRAMES=$(python3 -c "import json;print(json.load(open('$HERE/timeline.json'))['frames'])")

if [[ "${PREVIEW:-0}" == "1" ]]; then
  PLATES="$HERE/remotion/public/plates_preview"; SCALE=25; SAMPLES=6; OUT="$HERE/out/focus_prototype_preview.mp4"
else
  PLATES="$HERE/remotion/public/plates"; SCALE=100; SAMPLES=16; OUT="$HERE/out/focus_prototype.mp4"
fi
mkdir -p "$PLATES" "$HERE/out"

echo "== 1/4 Blender plates -> $PLATES ($JOBS procs, resumable: existing frames are skipped)"
per=$(( (FRAMES + JOBS - 1) / JOBS ))
threads=$(( $(nproc) / JOBS )); (( threads < 1 )) && threads=1
pids=()
for ((j = 0; j < JOBS; j++)); do
  s=$(( j * per )); e=$(( s + per - 1 )); (( e > FRAMES - 1 )) && e=$(( FRAMES - 1 ))
  "$BPY_PYTHON" "$HERE/blender/focus_scene.py" --out "$PLATES" --start "$s" --end "$e" \
    --scale "$SCALE" --samples "$SAMPLES" --threads "$threads" > "$HERE/out/blender_$j.log" 2>&1 &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done
n=$(ls "$PLATES"/plate_*.png | wc -l)
[[ "$n" -eq "$FRAMES" ]] || { echo "expected $FRAMES plates, found $n"; exit 1; }

echo "== 2/4 Sound design"
python3 "$HERE/audio/make_score.py" --out "$HERE/remotion/public/audio/score.wav"

echo "== 3/4 Remotion composite -> $OUT"
cd "$HERE/remotion"
[[ -d node_modules ]] || npm ci --no-audit --no-fund
CHROME="${CHROME:-}"
args=()
[[ -n "$CHROME" ]] && args+=(--browser-executable="$CHROME")
npx remotion render src/index.ts PremiumPrototype "$OUT" \
  --props="{\"platesDir\":\"$(basename "$PLATES")\",\"withAudio\":true}" "${args[@]}"

echo "== 4/4 QA"
python3 "$HERE/qa.py" "$OUT"
