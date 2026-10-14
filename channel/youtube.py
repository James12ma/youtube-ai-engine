"""Optional YouTube uploader: private-only by default, offline import-safe, explicit owner approval.

Google OAuth user authorization is external to this module. Credentials are read
from a local token path in the environment, never stored in release artifacts.
There is no exactly-once guarantee across API upload and receipt persistence.
"""
from __future__ import annotations
import hashlib,hmac,json,os
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
    if not token or not Path(token).is_file():raise UploadBlocked('OAuth token file not provided')
    # Approval JSON is an audit artifact, not a cryptographic signature. A
    # second out-of-band environment gate is required to authorize uploads.
    return manifest


def upload_youtube(release_dir:Path, *,privacy:str='private',
                   api_factory:Callable|None=None)->dict:
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
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            creds=Credentials.from_authorized_user_file(os.environ['YOUTUBE_TOKEN_FILE'],
                    ['https://www.googleapis.com/auth/youtube.upload'])
            if not creds.valid:
                raise UploadBlocked('OAuth access expired; refresh credentials using owner-controlled flow')
            youtube=build('youtube','v3',credentials=creds,cache_discovery=False)
            make_media=lambda path: MediaFileUpload(str(path),mimetype='video/mp4',resumable=True,chunksize=8*1024*1024)
        else:
            youtube,make_media=api_factory()
    except UploadBlocked:raise
    except (ImportError,ValueError,KeyError) as e:
        raise UploadBlocked('YouTube client/OAuth configuration incomplete') from e
    body={'snippet':{'title':metadata.title,'description':metadata.description,
                     'tags':metadata.tags,'categoryId':metadata.category_id,
                     'defaultLanguage':metadata.language},
          'status':{'privacyStatus':privacy,'selfDeclaredMadeForKids':metadata.made_for_kids,
                    'containsSyntheticMedia':metadata.contains_synthetic_media}}
    request=youtube.videos().insert(part='snippet,status',body=body,media_body=make_media(release_dir/'video.mp4'))
    response=None
    # Google resumable uploader resumes within one run; client errors fail closed.
    while response is None:
        _,response=request.next_chunk()
    video_id=response.get('id') if isinstance(response,dict) else None
    if not isinstance(video_id,str) or not video_id:
        raise UploadBlocked('Upload response did not include a video ID; inspect channel before retry')
    result={'release_digest':manifest['release_digest'],'youtube_video_id':video_id,
            'requested_privacy':privacy,'requires_manual_review':True}
    receipt.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
