import json,subprocess,hashlib
from tiktok_motion.media_qc import normalize_delivery

def test_full_range_render_becomes_canonical_without_changing_audio(tmp_path):
    path=tmp_path/'movie.mp4'
    subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','testsrc2=s=160x240:r=10:d=1','-f','lavfi','-i','sine=frequency=440:duration=1','-c:v','libx264','-pix_fmt','yuv420p','-color_range','pc','-c:a','aac','-shortest',str(path)],check=True)
    def probe():return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(path)]))
    def audio():return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:a','-c','copy','-f','adts','-'])
    assert probe()['streams'][0]['pix_fmt']=='yuvj420p'
    before=audio();normalize_delivery(path)
    assert probe()['streams'][0]['pix_fmt']=='yuv420p'
    assert before==audio()
    digest=hashlib.sha256(path.read_bytes()).hexdigest();normalize_delivery(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
