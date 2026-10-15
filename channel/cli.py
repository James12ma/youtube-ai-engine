"""Work handoff CLI. Publishing is never automatic and disabled by default."""
from __future__ import annotations
import argparse,json,os
from pathlib import Path
from pipeline.models import ResearchArtifact,ScriptArtifact,StoryboardOutput
from verification.models import VerificationGateReport
from .metadata import ReleaseMetadata,generate_metadata
from .thumbnail import make_thumbnail,read_thumbnail_text,thumbnail_text_path
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
    r.add_argument('--allow-edge-fallback',action='store_true')
    t=sub.add_parser('thumbnail');t.add_argument('--text',required=True);t.add_argument('--out',type=Path,required=True)
    t.add_argument('--screenshot',type=Path)
    t.add_argument('--title',help='Video title; records pairing advisories (blocks only if the policy says so)')
    t.add_argument('--quality-policy',type=Path,help='JSON QualityPolicy overrides')
    b=sub.add_parser('package');b.add_argument('--draft',type=Path,required=True)
    b.add_argument('--video',type=Path,required=True);b.add_argument('--thumbnail',type=Path,required=True)
    b.add_argument('--editorial-report',type=Path,required=True);b.add_argument('--out',type=Path,required=True)
    b.add_argument('--captions',type=Path)
    b.add_argument('--contains-synthetic-media',choices=('yes','no'),
                   help='Owner decision on YouTube synthetic-media disclosure')
    b.add_argument('--title',help='Owner-reviewed title override (default: script title)')
    b.add_argument('--thumbnail-text',help='Exact text on the thumbnail (default: read from the thumbnail sidecar)')
    b.add_argument('--chapters',type=Path,help='Chapter timeline JSON, or a render report with a "chapters" list')
    b.add_argument('--quality-policy',type=Path,help='JSON QualityPolicy overrides (default: advisory project rules)')
    k=sub.add_parser('quality-check',help='Offline title/thumbnail/chapter gates plus advisory hook score; writes nothing')
    k.add_argument('--draft',type=Path,required=True);k.add_argument('--title')
    k.add_argument('--thumbnail-text');k.add_argument('--thumbnail',type=Path)
    k.add_argument('--chapters',type=Path);k.add_argument('--video',type=Path)
    k.add_argument('--quality-policy',type=Path)
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
             height=1920 if args.format=='portrait' else 1080,
             allow_edge_fallback=args.allow_edge_fallback)
    elif args.command=='thumbnail':
        from .packaging_lint import QualityPolicy
        path=make_thumbnail(args.text,args.out,genuine_screenshot=args.screenshot,title=args.title,
                            policy=QualityPolicy.load(args.quality_policy))
        result={'thumbnail':str(path),**json.loads(thumbnail_text_path(path).read_text())}
    elif args.command in ('package','quality-check'):
        from .quality import evaluate_release_quality,require_quality,probe_duration
        from .chapters import load_timeline
        from .packaging_lint import QualityPolicy
        script=_json_model(args.draft/'script.json',ScriptArtifact)
        thumb_text=args.thumbnail_text
        if thumb_text is None and args.thumbnail is not None:thumb_text=read_thumbnail_text(args.thumbnail)
        duration=probe_duration(args.video) if args.video is not None else None
        timeline=load_timeline(args.chapters) if args.chapters is not None else None
        report,chapters=evaluate_release_quality(script,title=args.title,thumbnail_text=thumb_text,
                                                 timeline=timeline,video_duration_s=duration,
                                                 policy=QualityPolicy.load(args.quality_policy))
        if args.command=='quality-check':
            result=report
        elif report['blocking']:
            print(json.dumps({'packaged':False,**report},indent=2,default=str))
            return 2
        else:
            require_quality(report)
            meta=generate_metadata(script,
                  _json_model(args.draft/'research.json',ResearchArtifact),
                  _json_model(args.draft/'verification_gate.json',VerificationGateReport),
                  chapters=chapters,video_duration_s=duration)
            meta.title=report['title']
            if args.contains_synthetic_media is not None:
                meta.contains_synthetic_media=args.contains_synthetic_media=='yes'
            result=build_release(args.out,args.video,args.thumbnail,meta,
                     editorial_report=args.editorial_report,caption_file=args.captions,
                     quality_report=report)
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
