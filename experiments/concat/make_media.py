"""Generate the test media for the 15 s comparison with ffmpeg alone (no committed binaries, no network):
five visually distinct 1080x1920 clips, one narration WAV per clip (espeak-ng) and a music bed."""
import json
import subprocess
import sys
from pathlib import Path

here = Path(__file__).parent
tl = json.loads((here / "timeline.json").read_text())
media = here / "media"
media.mkdir(exist_ok=True)
W, H, FPS = tl["width"], tl["height"], tl["fps"]
SOURCES = [  # lavfi generators with real motion and texture, each a different look
    f"mandelbrot=s={W//2}x{H//2}:rate={FPS}:start_scale=3:end_scale=0.3,scale={W}:{H}",
    f"gradients=s={W}x{H}:rate={FPS}:c0=0x0b1d3a:c1=0x1f6feb:c2=0x7ee0ff:speed=0.02:type=radial:seed=11",
    f"zoneplate=s={W}x{H}:rate={FPS}:kt2=2:kx2=60:ky2=60:kt=6,colorchannelmixer=rr=0.2:gg=0.9:bb=0.6",
    f"sierpinski=s={W}x{H}:rate={FPS}:type=carpet:jump=1:seed=14,colorchannelmixer=rr=1:gg=0.75:bb=0.3",
    f"gradients=s={W}x{H}:rate={FPS}:c0=0x0b3d2e:c1=0x12b76a:c2=0xe8fff4:speed=0.03:type=spiral:seed=15",
]


def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


for i, (clip, src) in enumerate(zip(tl["clips"], SOURCES)):
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", src, "-t", f"{clip['duration_s'] + 0.6}", "-r", str(FPS),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(here / clip["source"])])
    run(["espeak-ng", "-v", "en-us", "-s", "155", "-w", str(media / f"voice{i + 1}.wav"), clip["narration"]])
# Music bed: two detuned pads + soft pulse, 15 s, stereo 48 kHz.
run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=f=110:d=15", "-f", "lavfi", "-i", "sine=f=164.8:d=15",
     "-f", "lavfi", "-i", "sine=f=220.5:d=15", "-filter_complex",
     "[0][1][2]amix=inputs=3,volume=0.6,tremolo=f=2:d=0.4,afade=t=in:d=1,afade=t=out:st=13.5:d=1.5,aformat=channel_layouts=stereo",
     "-ar", "48000", str(here / tl["music"]["source"])])
print("media ready:", sorted(p.name for p in media.iterdir()))
sys.exit(0)
