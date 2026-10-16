# Alan7 Kaggle GPU check: reports hardware only. No model download, no generation.
import json, os, shutil, subprocess, time, urllib.request
out = {'started': time.time()}
try:
    out['nvidia_smi'] = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader'],
                                       capture_output=True, text=True, timeout=60).stdout.strip()
except Exception as e:
    out['nvidia_smi'] = 'error: ' + type(e).__name__
try:
    import torch
    out['torch'] = torch.__version__
    out['cuda'] = torch.cuda.is_available()
    if out['cuda']:
        out['gpus'] = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
        out['vram_gb'] = [round(torch.cuda.get_device_properties(i).total_memory / 2**30, 1) for i in range(torch.cuda.device_count())]
        out['bf16_supported'] = torch.cuda.is_bf16_supported()
        out['compute_capability'] = list(torch.cuda.get_device_capability(0))
except Exception as e:
    out['torch_error'] = type(e).__name__
out['disk_free_gb'] = round(shutil.disk_usage('/kaggle/working').free / 2**30, 1)
try:
    with open('/proc/meminfo') as f:
        out['ram_gb'] = round(int(f.readline().split()[1]) / 2**20, 1)
except Exception:
    pass
for name, url in (('huggingface', 'https://huggingface.co/api/models/Wan-AI/Wan2.2-TI2V-5B'), ('github', 'https://api.github.com')):
    try:
        urllib.request.urlopen(url, timeout=20)
        out['internet_' + name] = True
    except Exception as e:
        out['internet_' + name] = 'error: ' + type(e).__name__
out['seconds'] = round(time.time() - out['started'], 1)
json.dump(out, open('/kaggle/working/gpu_check.json', 'w'), indent=1)
print(json.dumps(out))
