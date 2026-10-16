# LENA test clip on Kaggle — ONE generation, native output only (no upscaling, no frame interpolation).
# Model: Wan2.2-TI2V-5B (Apache-2.0) via diffusers.
# Mode "a": image-to-video from the owner's private reference. The reference never lives in GitHub in
# readable form: an encrypted copy is fetched and decrypted here with a key that exists only in a
# PRIVATE Kaggle dataset; the decrypted image stays in /tmp (not in the notebook output).
# Hard limits: a watchdog ends the process at CFG['max_seconds']; NaN latents abort immediately.
import glob, json, os, shutil, subprocess, sys, threading, time, urllib.request
os.environ.setdefault('PYTORCH_CUDA_ALLOC_CONF', 'expandable_segments:True')
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
    import gc
    # Kaggle T4 box: 14.6 GB GPU, 31 GB RAM. Holding the text encoder (11 GB) and the transformer (10 GB)
    # in RAM together got the process killed (run 38974674232). So: encode the prompts first on the GPU,
    # free the text encoder, then load the transformer with block-level offloading (no pinned copies).
    te = UMT5EncoderModel.from_pretrained(mid, subfolder='text_encoder', torch_dtype=torch.bfloat16, cache_dir=cache)
    enc = WanPipeline.from_pretrained(mid, text_encoder=te, transformer=None, vae=None, cache_dir=cache)
    te.to('cuda')
    with torch.no_grad():
        pe, ne = enc.encode_prompt(prompt=CFG['prompt'], negative_prompt=CFG['negative_prompt'],
                                   do_classifier_free_guidance=True, num_videos_per_prompt=1,
                                   max_sequence_length=512, device=torch.device('cuda'))
    pe, ne = pe.to('cpu', torch.float16), ne.to('cpu', torch.float16)
    del enc, te; gc.collect(); torch.cuda.empty_cache()
    report['encode_s'] = round(time.time() - T0, 1); save()
    vae = AutoencoderKLWan.from_pretrained(mid, subfolder='vae', torch_dtype=torch.float32, cache_dir=cache)
    tr = WanTransformer3DModel.from_pretrained(mid, subfolder='transformer', torch_dtype=torch.float16, cache_dir=cache)
    report['disk_free_tmp_gb'] = round(shutil.disk_usage('/tmp').free / 2**30, 1)
    Pipe = WanImageToVideoPipeline if CFG['mode'] == 'a' else WanPipeline
    extra = {'expand_timesteps': True} if CFG['mode'] == 'a' else {}
    pipe = Pipe.from_pretrained(mid, vae=vae, transformer=tr, text_encoder=None, tokenizer=None,
                                torch_dtype=torch.float16, cache_dir=cache, **extra)
    tr.enable_group_offload(onload_device=torch.device('cuda'), offload_device=torch.device('cpu'),
                            offload_type='block_level', num_blocks_per_group=1)
    vae.to('cuda')
    report['offload'] = 'prompts encoded first; transformer block-level group offload; VAE on GPU'
    try:
        vae.enable_tiling()
    except Exception:
        pass
    report['load_s'] = round(time.time() - T0, 1); save()
    kw = dict(prompt_embeds=pe.to('cuda'), negative_prompt_embeds=ne.to('cuda'), height=CFG['height'], width=CFG['width'],
              num_frames=CFG['frames'], guidance_scale=CFG['guidance'], num_inference_steps=CFG['steps'],
              generator=torch.Generator('cpu').manual_seed(CFG['seed']))
    if CFG['mode'] == 'a':
        if CFG.get('ref_file'):  # start frame from the PRIVATE Kaggle dataset alan7-lena-refs
            hits = glob.glob(f"/kaggle/input/**/{CFG['ref_file']}", recursive=True)
            if not hits:
                raise SystemExit('reference frame not found in the attached private dataset')
            img = load_image(hits[0])
        else:
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
        report['steps_done'] = i + 1; report['step_times'] = step_times
        if i + 1 == 3:  # projection after 3 steps: stop early (saves quota) if the clip cannot finish in time
            per = sum(step_times[1:]) / max(1, len(step_times) - 1)
            projected = (time.time() - T0) + per * (CFG['steps'] - 3) + 600
            report['projected_total_s'] = round(projected)
            if projected > CFG['max_seconds']:
                report['error'] = f'projected {round(projected)} s exceeds the {CFG["max_seconds"]} s limit — stopped early to save GPU quota'
                save(); os._exit(5)
        save()
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
