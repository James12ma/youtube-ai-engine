"""Build a hand-authored lesson's review candidate, then (after owner approval) its release.

    # 1. Review candidate (no approval, no manifest)
    python -m scripts.lesson_release candidate --artifact <lesson-polished dir> \
        --lesson content/expense-rule-lesson --out out/candidate \
        --topic "boundary testing for an expense approval rule" \
        --thumbnail-text "THE ONE-CENT BOUNDARY TEST $100.00 $100.01" [--title "..."] [--practice-url https://...]

    # 2. After the owner explicitly approved THIS video (sha256 printed in step 1)
    python -m scripts.lesson_release finalize --candidate out/candidate --out out/release \
        --approval "Owner approved after full review on 2026-10-20" --synthetic-media no \
        --video-sha256 <sha256> --zip out/release.zip

Nothing here uploads or publishes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from channel.lesson_release import build_candidate, finalize_release, zip_folder
from channel.packaging_lint import QualityPolicy


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog='python -m scripts.lesson_release')
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('candidate')
    c.add_argument('--artifact', type=Path, required=True)
    c.add_argument('--lesson', type=Path, required=True)
    c.add_argument('--out', type=Path, required=True)
    c.add_argument('--topic', required=True)
    c.add_argument('--thumbnail-text', required=True)
    c.add_argument('--title')
    c.add_argument('--practice-url')
    c.add_argument('--quality-policy', type=Path)
    f = sub.add_parser('finalize')
    f.add_argument('--candidate', type=Path, required=True)
    f.add_argument('--out', type=Path, required=True)
    f.add_argument('--approval', required=True, help='Owner approval statement, recorded verbatim')
    f.add_argument('--synthetic-media', choices=('yes', 'no'), required=True)
    f.add_argument('--video-sha256', required=True)
    f.add_argument('--zip', type=Path)
    args = p.parse_args(argv)
    if args.command == 'candidate':
        result = build_candidate(args.artifact, args.lesson, args.out, title=args.title, topic=args.topic,
                                 thumbnail_text=args.thumbnail_text, practice_url=args.practice_url,
                                 policy=QualityPolicy.load(args.quality_policy))
    else:
        manifest = finalize_release(args.candidate, args.out, owner_approval_statement=args.approval,
                                    contains_synthetic_media=args.synthetic_media == 'yes',
                                    video_sha256=args.video_sha256)
        result = {'release': str(args.out), 'release_digest': manifest['release_digest'],
                  'status': manifest['status']}
        if args.zip:
            result['zip'] = str(zip_folder(args.out, args.zip))
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
