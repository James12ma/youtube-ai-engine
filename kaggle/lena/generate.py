# LENA test clip on Kaggle — ONE generation, native output only (no upscaling, no frame interpolation).
# Model: Wan2.2-TI2V-5B (Apache-2.0) via diffusers.
# Mode "a": image-to-video from the owner's private reference. The reference never lives in GitHub in
# readable form: an encrypted copy is fetched and decrypted here with a key that exists only in a
# PRIVATE Kaggle dataset; the decrypted image stays in /tmp (not in the notebook output).
# Hard limits: a watchdog ends the process at CFG['max_seconds']; NaN latents abort immediately.
import glob, json, os, shutil, subprocess, sys, threading, time, urllib.request
T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__))
# Kaggle script kernels upload only the code file, so the workflow prepends CFG_JSON to this script.
CFG = json.loads(CFG_JSON) if 'CFG_JSON' in globals() else json.load(open(os.path.join(HERE, 'lena_config.json')))
OUT = '/kaggle/working'
report = {'config': {k: v for k, v in CFG.items() if k != 'ref_branch'}, 'started': T0}

def save():
    report['elapsed_s'] = round(time.time() - T0, 1)
    json.dump(report, open(f'{OUT}/report.json', 'w'), indent=1)

def watchdog():
    report['error'] = f"watchdog: stopped at the {CFG['max_seconds']} s hard limit"; save()
    os._exit(3)
threading.Timer(CFG['max_seconds'], watchdog).start()

def private_reference():
    keys = glob.glob('/kaggle/input/**/private.pem', recursive=True)
    if not keys:
        raise SystemExit('private transfer key dataset not attached')
    work = '/tmp/ref'; os.makedirs(work, exist_ok=True)
    base = f"https://raw.githubusercontent.com/James12ma/youtube-ai-engine/{CFG['ref_branch']}/"
    for name in ('key.enc', 'ref.enc'):
        urllib.request.urlretrieve(base + name, f'{work}/{name}')
    subprocess.run(['openssl', 'pkeyutl', '-decrypt', '-inkey', keys[0], '-pkeyopt', 'rsa_padding_mode:oaep',
                    '-pkeyopt', 'rsa_oaep_md:sha256', '-in', f'{work}/key.enc', '-out', f'{work}/k'], check=True)
    subprocess.run(['openssl', 'enc', '-d', '-aes-256-cbc', '-pbkdf2', '-iter', '200000', '-pass', f'file:{work}/k',
                    '-in', f'{work}/ref.enc', '-out', f'{work}/ref.png'], check=True)
    os.remove(f'{work}/k')
    return f'{work}/ref.png'

try:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'diffusers>=0.35.1', 'accelerate', 'ftfy', 'imageio-ffmpeg'], check=True)
    import torch
    from diffusers import AutoencoderKLWan, WanTransformer3DModel, WanPipeline, WanImageToVideoPipeline
    from diffusers.utils import export_to_video, load_image
    from transformers import UMT5EncoderModel
    report['gpu'] = torch.cuda.get_device_name(0)
    cache = '/tmp/hf'
    mid = 'Wan-AI/Wan2.2-TI2V-5B-Diffusers'
    # T4 has no fast bf16: transformer in fp16; text encoder in bf16 (runs once; T5 overflows in fp16); VAE fp32.
    vae = AutoencoderKLWan.from_pretrained(mid, subfolder='vae', torch_dtype=torch.float32, cache_dir=cache)
    te = UMT5EncoderModel.from_pretrained(mid, subfolder='text_encoder', torch_dtype=torch.bfloat16, cache_dir=cache)
    tr = WanTransformer3DModel.from_pretrained(mid, subfolder='transformer', torch_dtype=torch.float16, cache_dir=cache)
    report['disk_free_tmp_gb'] = round(shutil.disk_usage('/tmp').free / 2**30, 1)
    if CFG['mode'] == 'a':
        pipe = WanImageToVideoPipeline.from_pretrained(mid, vae=vae, text_encoder=te, transformer=tr,
                                                       torch_dtype=torch.float16, cache_dir=cache, expand_timesteps=True)
    else:
        pipe = WanPipeline.from_pretrained(mid, vae=vae, text_encoder=te, transformer=tr, torch_dtype=torch.float16, cache_dir=cache)
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
        img = load_image(private_reference())
        if img.size != (CFG['width'], CFG['height']):
            raise SystemExit(f'reference must be {CFG["width"]}x{CFG["height"]}, got {img.size}')
        kw['image'] = img
    step_times, last = [], [time.time()]
    def cb(p, i, t, kwargs):
        now = time.time(); step_times.append(round(now - last[0], 1)); last[0] = now
        lat = kwargs.get('latents')
        if lat is not None and not torch.isfinite(lat).all():
            report['error'] = f'non-finite latents at step {i + 1} (fp16 overflow) — aborted, no retry'; save()
            os._exit(4)
        report['steps_done'] = i + 1; report['step_times'] = step_times; save()
        return kwargs
    t1 = time.time()
    frames = pipe(**kw, callback_on_step_end=cb, callback_on_step_end_tensor_inputs=['latents']).frames[0]
    report['generate_s'] = round(time.time() - t1, 1)
    export_to_video(frames, f'{OUT}/lena.mp4', fps=24)
    report['frames_out'] = len(frames)
    report['max_vram_gb'] = round(torch.cuda.max_memory_allocated() / 2**30, 2)
    report['ok'] = True
except SystemExit as e:
    report['error'] = str(e)
except Exception as e:
    report['error'] = f'{type(e).__name__}: {str(e)[:400]}'
finally:
    shutil.rmtree('/tmp/ref', ignore_errors=True)
    save()
    print(json.dumps({k: report.get(k) for k in ('ok', 'error', 'generate_s', 'load_s', 'max_vram_gb', 'elapsed_s')}))
    os._exit(0 if report.get('ok') else 1)
