"""Work handoff CLI. Publishing is never automatic and disabled by default."""
from __future__ import annotations
import argparse,json,os
from pathlib import Path
from pipeline.models import ResearchArtifact,ScriptArtifact,StoryboardOutput
from verification.models import VerificationGateReport
from .metadata import ReleaseMetadata,generate_metadata
from .thumbnail import make_thumbnail
from .release import build_release,approve_release,check_approval

def _json_model(path,model):return model.model_validate_json(Path(path).read_text(encoding='utf-8'))

def main(argv=None):
    p=argparse.ArgumentParser(prog='python -m channel.cli',description='Owner-controlled YouTube AI Engine')
    sub=p.add_subparsers(dest='command',required=True)
    d=sub.add_parser('draft',help='Produce a source-backed draft with approved free-only LLM accounts')
    d.add_argument('--repo',type=Path,required=True);d.add_argument('--topic',required=True)
    d.add_argument('--url',action='append',required=True);d.add_argument('--out',type=Path,required=True)
    d.add_argument('--allow-free-live-api',action='store_true')
    q=sub.add_parser('next-draft',help='Run next owner-curated topic in the source queue, no uploads')
    q.add_argument('--queue',type=Path,required=True);q.add_argument('--repo',type=Path,required=True)
    q.add_argument('--out-root',type=Path,required=True);q.add_argument('--allow-free-live-api',action='store_true')
    r=sub.add_parser('render',help='Real Piper+WhisperX 1080p render. Explicit editorial approval required')
    r.add_argument('--draft',type=Path,required=True);r.add_argument('--voice-model',type=Path,required=True)
    r.add_argument('--out',type=Path,required=True);r.add_argument('--asset-map',type=Path)
    r.add_argument('--reviewed',action='store_true')
    r.add_argument('--format',choices=('landscape','portrait'),default='landscape')
    t=sub.add_parser('thumbnail');t.add_argument('--text',required=True);t.add_argument('--out',type=Path,required=True)
    t.add_argument('--screenshot',type=Path)
    b=sub.add_parser('package');b.add_argument('--draft',type=Path,required=True)
    b.add_argument('--video',type=Path,required=True);b.add_argument('--thumbnail',type=Path,required=True)
    b.add_argument('--editorial-report',type=Path,required=True);b.add_argument('--out',type=Path,required=True)
    b.add_argument('--captions',type=Path)
    b.add_argument('--contains-synthetic-media',choices=('yes','no'),
                   help='Owner decision on YouTube synthetic-media disclosure')
    a=sub.add_parser('approve');a.add_argument('--release',type=Path,required=True)
    a.add_argument('--digest',required=True);a.add_argument('--human-confirmed',action='store_true')
    u=sub.add_parser('upload');u.add_argument('--release',type=Path,required=True)
    u.add_argument('--privacy',choices=('private','unlisted','public'),default='private')
    c=sub.add_parser('check');c.add_argument('--release',type=Path,required=True)
    o=sub.add_parser('oauth-authorize',help='Owner-local Desktop OAuth consent; never uploads')
    o.add_argument('--client-secrets',type=Path,required=True)
    o.add_argument('--token-file',type=Path,required=True)
    s=sub.add_parser('oauth-status',help='Inspect local OAuth readiness without network calls')
    s.add_argument('--token-file',type=Path,required=True)
    args=p.parse_args(argv)
    if args.command=='draft':
        from .research import generate_draft
        result=generate_draft(args.repo,args.topic,args.url,args.out,allow_live=args.allow_free_live_api)
    elif args.command=='next-draft':
        from .queue import run_next
        result=run_next(args.queue,args.repo,args.out_root,allow_live=args.allow_free_live_api)
    elif args.command=='render':
        from .video import render_approved_video
        draft=args.draft
        assets={}
        if args.asset_map:assets={int(k):Path(v) for k,v in json.loads(args.asset_map.read_text()).items()}
        result=render_approved_video(_json_model(draft/'script.json',ScriptArtifact),
             _json_model(draft/'storyboard.json',StoryboardOutput),
             _json_model(draft/'verification_gate.json',VerificationGateReport),
             args.voice_model,args.out,actual_assets=assets,reviewed=args.reviewed,
             width=1080 if args.format=='portrait' else 1920,
             height=1920 if args.format=='portrait' else 1080)
    elif args.command=='thumbnail':
        path=make_thumbnail(args.text,args.out,genuine_screenshot=args.screenshot)
        result={'thumbnail':str(path)}
    elif args.command=='package':
        meta=generate_metadata(_json_model(args.draft/'script.json',ScriptArtifact),
              _json_model(args.draft/'research.json',ResearchArtifact),
              _json_model(args.draft/'verification_gate.json',VerificationGateReport))
        if args.contains_synthetic_media is not None:
            meta.contains_synthetic_media=args.contains_synthetic_media=='yes'
        result=build_release(args.out,args.video,args.thumbnail,meta,
                 editorial_report=args.editorial_report,caption_file=args.captions)
    elif args.command=='approve':result=approve_release(args.release,args.digest,human_confirmed=args.human_confirmed)
    elif args.command=='check':result=check_approval(args.release)
    elif args.command=='upload':
        from .youtube import upload_youtube
        result=upload_youtube(args.release,privacy=args.privacy)
    elif args.command=='oauth-authorize':
        from .oauth import authorize
        result=authorize(args.client_secrets,args.token_file)
    elif args.command=='oauth-status':
        from .oauth import oauth_status
        result=oauth_status(args.token_file)
    else:raise AssertionError('unreachable')
    print(json.dumps(result,indent=2,default=str))
    return 0

if __name__=='__main__':raise SystemExit(main())
