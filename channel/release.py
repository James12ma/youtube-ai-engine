"""Tamper-evident editorial handoff. The owner must explicitly approve a release digest."""
from __future__ import annotations
import hashlib,json,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from .metadata import ReleaseMetadata

class ReleaseError(RuntimeError): pass

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def _ffprobe(path:Path)->dict[str,Any]:
    p=subprocess.run(['ffprobe','-v','error','-of','json','-show_streams','-show_format',str(path)],text=True,capture_output=True)
    if p.returncode:raise ReleaseError('ffprobe failed; valid final MP4 required')
    try: return json.loads(p.stdout)
    except ValueError as e: raise ReleaseError('Invalid ffprobe output') from e

def build_release(out_dir:Path,video:Path,thumbnail:Path,metadata:ReleaseMetadata,
                  *, editorial_report:Path, caption_file:Path|None=None)->dict[str,Any]:
    out_dir=Path(out_dir); video=Path(video); thumbnail=Path(thumbnail)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ReleaseError('Release folder must be new or empty; do not overwrite approved artifacts')
    for name,path in [('video',video),('thumbnail',thumbnail),('editorial',Path(editorial_report))]:
        if not path.is_file() or path.stat().st_size<50: raise ReleaseError(f'{name} missing or empty')
    if thumbnail.suffix.lower() not in ('.jpg','.jpeg','.png'):
        raise ReleaseError('Thumbnail must be JPEG or PNG')
    try: review=json.loads(Path(editorial_report).read_text(encoding='utf-8'))
    except Exception as e:raise ReleaseError('Editorial report must be valid JSON') from e
    # Never accept a self-declared passing report if it has blocking flags.
    if review.get('gate_passed') is not True or review.get('human_reviewed') is not True:
        raise ReleaseError('Verified research and human editorial review required')
    if review.get('quality_passed') is not True:
        raise ReleaseError('Video/audio quality review required')
    p=_ffprobe(video)
    streams=p.get('streams',[])
    if not any(s.get('codec_type')=='video' for s in streams) or not any(s.get('codec_type')=='audio' for s in streams):
        raise ReleaseError('MP4 must contain audio and video')
    out_dir.mkdir(parents=True,exist_ok=True)
    assets={'video.mp4':video,'thumbnail'+thumbnail.suffix.lower():thumbnail,
            'editorial_review.json':Path(editorial_report)}
    if caption_file:
        cp=Path(caption_file)
        if not cp.is_file():raise ReleaseError('Caption file missing')
        assets['captions'+cp.suffix.lower()]=cp
    for filename,src in assets.items():shutil.copy2(src,out_dir/filename)
    (out_dir/'metadata.json').write_text(metadata.model_dump_json(indent=2),encoding='utf-8')
    digests={name:_sha(out_dir/name) for name in [*assets,'metadata.json']}
    manifest={'created_at':datetime.now(timezone.utc).isoformat(),'hashes':digests,
              'status':'NEEDS_OWNER_APPROVAL','privacy_default':'private'}
    # Approval digest is of file hashes only, so timestamps cannot change the approval.
    digest=hashlib.sha256(json.dumps(digests,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    manifest['release_digest']=digest
    (out_dir/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest

def _verify_manifest(folder:Path)->dict:
    folder=Path(folder)
    try: manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    except Exception as e:raise ReleaseError('Manifest absent or damaged') from e
    hashes=manifest.get('hashes',{})
    if not hashes:raise ReleaseError('Empty manifest')
    for name,digest in hashes.items():
        if Path(name).name != name or not (folder/name).is_file() or _sha(folder/name)!=digest:
            raise ReleaseError('Release file missing/changed: '+name)
    computed=hashlib.sha256(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if computed!=manifest.get('release_digest'):raise ReleaseError('Release digest mismatch')
    return manifest

def approve_release(folder:Path,typed_digest:str,*,human_confirmed:bool=False)->dict:
    manifest=_verify_manifest(folder)
    if not human_confirmed or typed_digest!=manifest['release_digest']:
        raise ReleaseError('Explicit human confirmation and exact release digest required')
    approval={'release_digest':typed_digest,'approved_at':datetime.now(timezone.utc).isoformat(),
              'approval_type':'owner_manual_confirmation'}
    (Path(folder)/'OWNER_APPROVAL.json').write_text(json.dumps(approval,indent=2),encoding='utf-8')
    return approval

def check_approval(folder:Path)->dict:
    manifest=_verify_manifest(folder)
    try: approval=json.loads((Path(folder)/'OWNER_APPROVAL.json').read_text(encoding='utf-8'))
    except Exception as e:raise ReleaseError('Missing owner approval') from e
    if approval.get('release_digest')!=manifest['release_digest']:
        raise ReleaseError('Owner approved a different release')
    return manifest
