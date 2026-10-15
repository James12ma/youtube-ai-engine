"""Optional YouTube uploader: private-only by default, offline import-safe, explicit owner approval.

Google OAuth user authorization is external to this module. Credentials are read
from a local token path in the environment, never stored in release artifacts.
There is no exactly-once guarantee across API upload and receipt persistence.
"""
from __future__ import annotations
import hashlib,hmac,json,os
from datetime import datetime,timezone
from pathlib import Path
from typing import Callable
from .release import ReleaseError, check_approval
from .metadata import ReleaseMetadata

class UploadBlocked(ReleaseError):pass


def _require_authorization(release_dir:Path, privacy:str)->dict:
    manifest=check_approval(release_dir)
    if os.environ.get('YOUTUBE_UPLOAD_ALLOWED')!='1':
        raise UploadBlocked('YouTube uploads disabled; require YOUTUBE_UPLOAD_ALLOWED=1')
    if os.environ.get('OWNER_APPROVED_RELEASE_DIGEST')!=manifest['release_digest']:
        raise UploadBlocked('Exact owner-approved digest must be supplied independently via environment')
    if privacy!='private':
        if privacy not in ('public','unlisted') or os.environ.get('YOUTUBE_PUBLIC_ALLOWED')!='1':
            raise UploadBlocked('Public/unlisted uploads disabled')
    token=os.environ.get('YOUTUBE_TOKEN_FILE','')
    if token:
        if not Path(token).is_file():raise UploadBlocked('OAuth token file not provided')
    elif not all(os.environ.get(name, '').strip() for name in
                 ('YOUTUBE_CLIENT_ID','YOUTUBE_CLIENT_SECRET','YOUTUBE_REFRESH_TOKEN')):
        raise UploadBlocked('OAuth token file or three cloud secrets required')
    # Approval JSON is an audit artifact, not a cryptographic signature. A
    # second out-of-band environment gate is required to authorize uploads.
    return manifest


def upload_youtube(release_dir:Path, *,privacy:str='private',
                   api_factory:Callable|None=None, upload_captions:bool=False,
                   sleep:Callable|None=None)->dict:
    release_dir=Path(release_dir)
    manifest=_require_authorization(release_dir,privacy)
    receipt=release_dir/'youtube_receipt.json'
    if receipt.exists():
        raise UploadBlocked('Receipt already exists; inspect the YouTube video before retrying')
    metadata=ReleaseMetadata.model_validate_json((release_dir/'metadata.json').read_text(encoding='utf-8'))
    if metadata.contains_synthetic_media is None:
        raise UploadBlocked('Owner must explicitly decide synthetic-media disclosure before packaging')
    try:
        if api_factory is None:
            from .oauth import load_upload_credentials, OAuthConfigurationError
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            creds=load_upload_credentials(os.environ.get('YOUTUBE_TOKEN_FILE') or None)
            youtube=build('youtube','v3',credentials=creds,cache_discovery=False)
            make_media=lambda path: MediaFileUpload(str(path),mimetype='video/mp4',resumable=True,chunksize=8*1024*1024)
            make_image=lambda path,mime: MediaFileUpload(str(path),mimetype=mime,resumable=False)
        else:
            made=api_factory()
            youtube,make_media=made[0],made[1]
            make_image=made[2] if len(made)>2 else (lambda path,mime: (str(path),mime))
    except UploadBlocked:raise
    except (ImportError,ValueError,KeyError,OAuthConfigurationError) as e:
        raise UploadBlocked('YouTube client/OAuth configuration incomplete') from e
    body={'snippet':{'title':metadata.title,'description':metadata.description,
                     'tags':metadata.tags,'categoryId':metadata.category_id,
                     'defaultLanguage':metadata.language,'defaultAudioLanguage':metadata.language},
          'status':{'privacyStatus':privacy,'selfDeclaredMadeForKids':metadata.made_for_kids,
                    'containsSyntheticMedia':metadata.contains_synthetic_media}}
    request=youtube.videos().insert(part='snippet,status',body=body,media_body=make_media(release_dir/'video.mp4'))
    response=_resumable(request,sleep=sleep)
    video_id=response.get('id') if isinstance(response,dict) else None
    if not isinstance(video_id,str) or not video_id:
        raise UploadBlocked('Upload response did not include a video ID; inspect channel before retry')
    result={'release_digest':manifest['release_digest'],'youtube_video_id':video_id,
            'requested_privacy':privacy,'requires_manual_review':True,
            'uploaded_at':datetime.now(timezone.utc).isoformat(),
            'thumbnail':'not_attempted','captions':'not_attempted'}
    # Receipt FIRST: if anything after this fails, a re-run is refused instead of re-uploading.
    _write_receipt(receipt,result)
    thumbs=sorted(release_dir.glob('thumbnail.*'))
    if thumbs:
        try:
            mime='image/png' if thumbs[0].suffix.lower()=='.png' else 'image/jpeg'
            youtube.thumbnails().set(videoId=video_id,media_body=make_image(thumbs[0],mime)).execute()
            result['thumbnail']='set'
        except Exception as e:  # noqa: BLE001 - video already exists; report, never retry the upload
            result['thumbnail']='failed: '+_safe_error(e)+' (set it manually in YouTube Studio)'
    else:
        result['thumbnail']='no thumbnail in release'
    captions=sorted(release_dir.glob('captions.*'))
    if not captions:
        result['captions']='no captions in release'
    elif not upload_captions:
        result['captions']='skipped: upload captions.srt in YouTube Studio (captions API needs the broader youtube.force-ssl scope)'
    else:
        try:
            cap_body={'snippet':{'videoId':video_id,'language':metadata.language,'name':'English','isDraft':False}}
            youtube.captions().insert(part='snippet',body=cap_body,
                                      media_body=make_image(captions[0],'application/octet-stream')).execute()
            result['captions']='uploaded'
        except Exception as e:  # noqa: BLE001
            result['captions']='failed: '+_safe_error(e)+' (upload captions.srt in YouTube Studio)'
    _write_receipt(receipt,result)
    return result


RETRYABLE_STATUS={500,502,503,504}
MAX_RETRIES=5


def _status_of(exc)->int|None:
    resp=getattr(exc,'resp',None)
    status=getattr(resp,'status',None)
    try:return int(status) if status is not None else None
    except (TypeError,ValueError):return None


def _safe_error(exc)->str:
    """HTTP status / exception class only; never response bodies that might echo request data."""
    status=_status_of(exc)
    return f'HTTP {status}' if status else type(exc).__name__


def _resumable(request,*,sleep=None)->dict|None:
    """Drive a resumable upload, retrying only transient failures with bounded backoff."""
    import random,time
    sleep=sleep or time.sleep
    response=None;retries=0
    while response is None:
        try:
            _,response=request.next_chunk()
            retries=0
        except Exception as e:  # noqa: BLE001
            transient=_status_of(e) in RETRYABLE_STATUS or isinstance(e,(ConnectionError,TimeoutError,OSError))
            if not transient or retries>=MAX_RETRIES:
                raise UploadBlocked('Upload failed ('+_safe_error(e)+'); no receipt written, check Studio before retrying') from None
            retries+=1
            sleep(min(64,2**retries)+random.random())
    return response


def _write_receipt(path:Path,data:dict)->None:
    path.write_text(json.dumps(data,indent=2),encoding='utf-8')
