# LENA test clip on Kaggle (one generation). Native output only: no upscaling, no frame interpolation.
# Model: Wan2.2-TI2V-5B (Apache-2.0) via diffusers. Writes lena.mp4 + report.json to /kaggle/working.
import json, os, shutil, subprocess, sys, time
T0 = time.time()
CFG = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lena_config.json')))
report = {'config': CFG, 'started': T0}
def save():
    report['elapsed_s'] = round(time.time() - T0, 1)
    json.dump(report, open('/kaggle/working/report.json', 'w'), indent=1)

subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'diffusers>=0.35.1', 'accelerate', 'ftfy', 'imageio-ffmpeg'], check=True)
import torch
from diffusers import AutoencoderKLWan, WanPipeline, WanImageToVideoPipeline
from diffusers.utils import export_to_video, load_image
cache = '/tmp/hf'
report['disk_free_tmp_gb'] = round(shutil.disk_usage('/tmp').free / 2**30, 1)
mid = 'Wan-AI/Wan2.2-TI2V-5B-Diffusers'
vae = AutoencoderKLWan.from_pretrained(mid, subfolder='vae', torch_dtype=torch.float32, cache_dir=cache)
Pipe = WanImageToVideoPipeline if CFG['mode'] == 'a' else WanPipeline
pipe = Pipe.from_pretrained(mid, vae=vae, torch_dtype=torch.float16, cache_dir=cache)  # T4: no native bf16
pipe.enable_model_cpu_offload()
try:
    pipe.vae.enable_tiling()
except Exception:
    pass
report['load_s'] = round(time.time() - T0, 1); save()
kw = dict(prompt=CFG['prompt'], negative_prompt=CFG['negative_prompt'], height=CFG['height'], width=CFG['width'],
          num_frames=CFG['frames'], guidance_scale=CFG['guidance'], num_inference_steps=CFG['steps'],
          generator=torch.Generator('cpu').manual_seed(CFG['seed']))
if CFG['mode'] == 'a':
    kw['image'] = load_image(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ref_0.png')).resize((CFG['width'], CFG['height']))
step_times = []
last = [time.time()]
def cb(p, i, t, kwargs):
    now = time.time(); step_times.append(round(now - last[0], 1)); last[0] = now
    report['steps_done'] = i + 1; report['step_times'] = step_times; save()
    return kwargs
t1 = time.time()
try:
    frames = pipe(**kw, callback_on_step_end=cb).frames[0]
except torch.cuda.OutOfMemoryError:
    report['error'] = 'CUDA out of memory at native size'; save(); raise
report['generate_s'] = round(time.time() - t1, 1)
export_to_video(frames, '/kaggle/working/lena.mp4', fps=24)
report['max_vram_gb'] = round(torch.cuda.max_memory_allocated() / 2**30, 2)
report['ok'] = True; save()
print(json.dumps({k: report.get(k) for k in ('generate_s', 'load_s', 'max_vram_gb', 'elapsed_s')}))
