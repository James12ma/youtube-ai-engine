"""Write a grounded "What's new in <AI>" plan from the AI's OFFICIAL pages (free LLM, no publishing).

1. Load each official page in a real browser (Playwright) and keep its visible text.
2. Ask a free-tier model (Gemini -> Groq -> OpenRouter) for a ~10 minute English script, split in
   segments; every segment lists the official page it relies on and short quotes copied from it.
3. Grounding gate (no model involved): a quote counts only if it appears VERBATIM on that page;
   a segment needs >= 1 valid quote, and every number it speaks must appear in its quotes.
   Failing segments are dropped and reported, never "fixed" by the model.
Output: plan.json for scripts/render_web_explainer.py + grounding_report.json.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from channel.ai_sources import AI_SOURCES


class Segment(BaseModel):
    title: str
    narration: str
    url: str
    quotes: list[str] = Field(min_length=1)


class Plan(BaseModel):
    video_title: str
    segments: list[Segment] = Field(min_length=1)


def norm(t: str) -> str:
    t = unicodedata.normalize('NFKC', t).replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    t = t.replace('–', '-').replace('—', '-')
    return ' '.join(t.casefold().split())


NUM = re.compile(r'\b\d[\d,.]*\b')
SPELLED = {'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'twenty', 'thirty',
           'forty', 'fifty', 'hundred', 'thousand', 'million', 'billion', 'percent'}


def page_texts(urls: list[str]) -> dict[str, str]:
    from playwright.sync_api import sync_playwright
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1920, 'height': 1080}, locale='en-US')
        for u in urls:
            page = ctx.new_page()
            try:
                page.goto(u, wait_until='domcontentloaded', timeout=60000)
                page.wait_for_timeout(4000)
                out[u] = page.inner_text('body')[:60000]
                # one level of links to the newest official articles on the same site
                links = page.eval_on_selector_all('a[href]', 'as => as.map(a => [a.href, a.innerText.trim()])')
                out[u + '#links'] = json.dumps([l for l in links if urlparse(l[0]).hostname == urlparse(u).hostname][:150])
            except Exception as exc:  # a blocked page is reported, not guessed
                out[u] = ''
                out[u + '#error'] = f'{type(exc).__name__}: {str(exc)[:200]}'
            page.close()
        b.close()
    return out


def ask_model(prompt: str, small_prompt: str) -> Plan:
    from adapters import GeminiAdapter, GroqAdapter, OpenRouterAdapter
    from adapters.base import LLMRequest
    errors = []
    for cls, key in ((GeminiAdapter, 'GEMINI_API_KEY'), (GroqAdapter, 'GROQ_API_KEY'), (OpenRouterAdapter, 'OPENROUTER_API_KEY')):
        if not os.environ.get(key):
            continue
        try:
            # Groq's free tier rejects very long requests (HTTP 413): it gets the shorter corpus
            text = small_prompt if cls is GroqAdapter else prompt
            with cls() as ad:
                r = ad.complete(LLMRequest(messages=[{'role': 'user', 'content': text}], schema=Plan,
                                           temperature=0.3, max_tokens=4096))
            return r.parsed if getattr(r, 'parsed', None) else Plan.model_validate_json(r.text)
        except Exception as exc:
            errors.append(f'{cls.__name__}: {type(exc).__name__}: {str(exc)[:200]}')
    raise SystemExit('no free model produced a valid plan: ' + ' | '.join(errors))


def ground(plan: Plan, texts: dict[str, str]) -> tuple[list[dict], list[dict]]:
    kept, dropped = [], []
    for s in plan.segments:
        page = norm(texts.get(s.url, ''))
        good = [q for q in s.quotes if len(q.split()) >= 3 and norm(q) in page]
        nums_spoken = set(NUM.findall(s.narration))
        nums_quoted = set(NUM.findall(' '.join(good)))
        why = ('page not loaded' if not page else
               'no verbatim quote on the page' if not good else
               f'numbers not in quotes: {sorted(nums_spoken - nums_quoted)}' if nums_spoken - nums_quoted else '')
        row = {**s.model_dump(), 'valid_quotes': good}
        (dropped if why else kept).append({**row, 'reason': why} if why else row)
    return kept, dropped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--ai', required=True, choices=sorted(AI_SOURCES))
    ap.add_argument('--since', default='', help='e.g. "August 2026" (the period the video covers)')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    src = AI_SOURCES[a.ai]
    a.out.mkdir(parents=True, exist_ok=True)
    texts = page_texts(src['pages'])
    # also load the newest linked official articles (titles mentioning the AI, same hosts)
    extra = []
    for u in src['pages']:
        for href, label in json.loads(texts.get(u + '#links', '[]')):
            path = urlparse(href).path
            if (len(label) > 20 and href not in src['pages'] and href not in extra and href.count('/') > 3
                    and re.search(r'/(news|blog|articles?|resources|release|changelog|product)', path)
                    and not re.search(r'/(collections|tag|category|careers|legal|privacy|terms)', path)):
                extra.append(href.split('#')[0])
    texts.update(page_texts(extra[:16]))
    usable = {u: t for u, t in texts.items() if '#' not in u and len(t) > 500}
    corpus = '\n\n'.join(f'=== PAGE {u} ===\n{t[:12000]}' for u, t in usable.items())
    prompt = f"""You write a factual YouTube script for the channel LogicScript: "What's new in {src['name']}"{(' since ' + a.since) if a.since else ''}.
Use ONLY the official {src['company']} pages below. Never add facts from memory. Prefer the newest updates.
Return JSON: {{"video_title": str, "segments": [{{"title": str, "narration": str, "url": str, "quotes": [str]}}]}}
Rules:
- In total the video has 12 to 14 segments of 100 to 130 words each (about 1,400 words), plain spoken English, no lists, no markdown. Explain each update: what it does, who gets it, how to use it, when the page says so.
- Segment 1 is a hook (what changed and why it matters); the last segment says which features to try first and asks viewers to subscribe.
- "url" must be one of the page URLs below (the page the segment is about). "quotes" = 1-3 short phrases (4-15 words)
  COPIED EXACTLY, character for character, from that page; they prove the segment's facts.
- Every date, number, plan name and price you say must appear inside your quotes.
- Say which plans get a feature when the page says it. Do not invent benefits, comparisons or opinions about competitors.
- Do not imitate any person; do not claim you used the product.

CORPUS"""
    # the adapters cap output at 4,096 tokens, so the ~1,400-word script is written in four parts
    def part(extra: str) -> Plan:
        p = prompt + ('\n\n' + extra + ' Return EXACTLY the number of segments asked, never more.')
        return ask_model(p.replace('CORPUS', corpus[:150000]), p.replace('CORPUS', corpus[:18000]))
    parts = ['WRITE ONLY PART 1 of 4: exactly 4 segments - the hook, then the 3 newest, biggest updates.',
             'WRITE ONLY PART 2 of 4: exactly 3 segments about OTHER updates. No hook, no closing.',
             'WRITE ONLY PART 3 of 4: exactly 3 segments about OTHER updates. No hook, no closing.',
             'WRITE ONLY PART 4 of 4: exactly 3 segments about OTHER updates, the last one being the closing segment. No hook.']
    segs, title = [], ''
    for i, extra in enumerate(parts):
        if segs:
            extra += ' Already covered (do NOT repeat these updates): ' + '; '.join(x.title for x in segs)
        got = part(extra)
        title = title or got.video_title
        segs += got.segments[:4 if i == 0 else 3]
    plan = Plan(video_title=title, segments=segs)
    kept, dropped = ground(plan, usable)
    report = {'ai': a.ai, 'pages_loaded': sorted(usable), 'page_errors': {u: e for u, e in texts.items() if u.endswith('#error')},
              'segments_kept': len(kept), 'segments_dropped': dropped,
              'words_kept': sum(len(s['narration'].split()) for s in kept)}
    (a.out / 'grounding_report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
    if len(kept) < 4:
        raise SystemExit('grounding gate: fewer than 4 verified segments — no video (see grounding_report.json)')
    out = {'ai': a.ai, 'title': plan.video_title, 'language': 'en', 'segments': kept}
    (a.out / 'plan.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    (a.out / 'narration_texts.json').write_text(json.dumps([s['narration'] for s in kept], ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'segments_dropped'} | {'dropped': len(dropped)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
