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
import sys
import time
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


class Update(BaseModel):
    title: str
    url: str
    anchor: str
    detail_url: str = ''


class UpdateList(BaseModel):
    updates: list[Update] = Field(min_length=1)


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


# free models tried in order (OpenRouter list checked 2026-10-18 with scripts/llm_probe.py); the small
# default code model rambles past the 4,096-token cap on long scripts, so instruction models come first
CANDIDATES = [('groq', None), ('openrouter', 'google/gemma-4-31b-it:free'), ('openrouter', 'nvidia/nemotron-3-super-120b-a12b:free'),
              ('gemini', None), ('openrouter', None)]


def ask_model(prompt: str, small_prompt: str, schema=None):
    schema = schema or Plan
    import dataclasses
    from adapters import GeminiAdapter, GroqAdapter, OpenRouterAdapter
    from adapters.base import LLMRequest
    from adapters.config import GEMINI_CONFIG, GROQ_CONFIG, OPENROUTER_CONFIG
    kinds = {'gemini': (GeminiAdapter, GEMINI_CONFIG, 'GEMINI_API_KEY'), 'groq': (GroqAdapter, GROQ_CONFIG, 'GROQ_API_KEY'),
             'openrouter': (OpenRouterAdapter, OPENROUTER_CONFIG, 'OPENROUTER_API_KEY')}
    errors = []
    for kind, model in [c for _ in range(3) for c in CANDIDATES]:   # 3 rounds: free tiers often answer 400/429 for a minute
        if errors and kind == CANDIDATES[0][0] and model == CANDIDATES[0][1]:
            time.sleep(70)
        cls, cfg, key = kinds[kind]
        if not os.environ.get(key):
            continue
        try:
            # Groq's free tier rejects very long requests (HTTP 413): it gets the shorter corpus
            text = small_prompt if kind == 'groq' else prompt
            with cls(config=dataclasses.replace(cfg, request_timeout=240.0)) as ad:   # long answers take > 45 s
                r = ad.complete(LLMRequest(messages=[{'role': 'user', 'content': text}], schema=schema, model=model,
                                           temperature=0.3, max_tokens=4096))
            got = r.parsed if getattr(r, 'parsed', None) else schema.model_validate_json(r.text)
            print(f'plan part written by {kind}:{model or "default"}', file=sys.stderr)
            return got
        except Exception as exc:
            errors.append(f'{kind}:{model or "default"}: {type(exc).__name__}: {str(exc)[:160]}')
    raise SystemExit('no free model produced a valid plan: ' + ' | '.join(errors))


MONTHS = ('january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october',
          'november', 'december')
STOP = set('''the a an and or but of to in on for with by at from as is are was were be been it its this that these those
you your they them their we our can will now new also more most just into than then so not no all any each which who what
when where how about over after before while using use used lets let make makes made gives give get gets like only there
here have has had do does did one'''.split())


def _sentences(t: str) -> list[str]:
    return [x.strip() for x in re.split(r'(?<=[.!?])\s+', t.strip()) if x.strip()]


def _facts(t: str) -> set[str]:
    """Numbers (digits or spelled) and month names: these must be on the page next to the quoted text."""
    n = norm(t)
    return set(NUM.findall(n)) | {w for w in re.findall(r"[a-z]+", n) if w in SPELLED or w in MONTHS}


def _words(t: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z0-9]+", norm(t)) if len(w) >= 4 and w not in STOP}


def tok(t: str) -> str:
    """Words only (punctuation, quotes and dashes ignored): a quote matches the page if its words appear in order."""
    return ' '.join(re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", norm(t)))


DATE = re.compile(r'\b(' + '|'.join(MONTHS) + r') (\d{1,2}) (\d{4})\b')


def entry_date(page_tok: str, pos: int):
    """Date heading the release-notes entry that contains ``pos`` (the last full date before it), or None."""
    import datetime
    last = None
    for m in DATE.finditer(page_tok[:pos + 1]):
        last = m
    if not last:
        return None
    try:
        return datetime.date(int(last.group(3)), MONTHS.index(last.group(1)) + 1, int(last.group(2)))
    except ValueError:
        return None


def parse_since(since: str):
    import datetime
    m = re.search(r'(' + '|'.join(MONTHS) + r')\s+(\d{4})', since.lower())
    return datetime.date(int(m.group(2)), MONTHS.index(m.group(1)) + 1, 1) if m else None


class Entailment:
    """Does the official page support a sentence? A small free NLI model (runs on the CPU, no API).
    Premises are the page passages that share the most words with the sentence."""
    MODEL = 'cross-encoder/nli-deberta-v3-base'

    def __init__(self):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(self.MODEL)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.MODEL).eval()
        labels = {v.lower(): int(k) for k, v in self.model.config.id2label.items()}
        self.ent, self.con = labels['entailment'], labels['contradiction']

    def passages(self, page_raw: str, size: int = 3) -> list[str]:
        sents = [x for x in re.split(r'(?<=[.!?])\s+|\n+', page_raw) if len(x.split()) >= 3]
        return [' '.join(sents[i:i + size]) for i in range(0, len(sents), max(1, size - 1))]

    def score(self, sentence: str, passages: list[str], top: int = 4) -> tuple[float, float]:
        ws = _words(sentence)
        ranked = sorted(passages, key=lambda p: -len(ws & _words(p)))[:top]
        if not ranked:
            return 0.0, 0.0
        enc = self.tok(ranked, [sentence] * len(ranked), truncation=True, max_length=320, padding=True, return_tensors='pt')
        with self.torch.no_grad():
            pr = self.model(**enc).logits.softmax(-1)
        best = int(pr[:, self.ent].argmax())      # contradiction is read on the SAME passage (other passages talk about other things)
        return float(pr[best, self.ent]), float(pr[best, self.con])


ATTRIBUTION = re.compile(r"^(?:(?:on|in) [a-z]+ \d{1,2}(?:st|nd|rd|th)?,? \d{4},?\s*|according to [^,]{3,60},\s*|"
                         r"[a-z]+(?: [a-z]+)? (?:says|said|announced|notes|explains|reports|states|adds)(?: that)?\s+|"
                         r"the (?:release notes|announcement|page|update|entry) (?:says|states|notes|explains|adds)(?: that)?\s+)+", re.I)


def claim(sentence: str) -> str:
    """The claim itself, without "Anthropic says", "According to the release notes," or a leading date
    (the NLI model rightly finds "Anthropic says" unsupported when the page doesn't name Anthropic; dates are
    checked separately by the facts rule)."""
    c = ATTRIBUTION.sub('', sentence).strip()
    return (c[:1].upper() + c[1:]) if c else sentence


def raw_window(raw: str, quote: str, before: int = 900, after: int = 1500) -> str:
    words = re.findall(r"[A-Za-z0-9]+", quote)[:8]
    m = re.search(r'\W+'.join(map(re.escape, words)), raw, re.I) if words else None
    return raw[max(0, m.start() - before): m.end() + after] if m else ''


def ground(plan: Plan, texts: dict[str, str], nli: 'Entailment | None' = None, min_entail: float = 0.5,
           multi_entry: frozenset = frozenset()) -> tuple[list[dict], list[dict]]:
    """No generative model involved. A segment is kept when:
    - at least one quote is VERBATIM on its page;
    - every number, spelled number and month it says appears on the page near a verified quote (+-600 chars:
      on release-notes pages the date heads the entry);
    - each sentence is ENTAILED by a passage of the page (NLI model). Unsupported sentences are cut, never
      rewritten; the segment survives with >= 2 sentences and >= 35 words."""
    kept, dropped = [], []
    for s in plan.segments:
        raw = texts.get(s.url, '')
        page = tok(raw)
        good = [q for q in s.quotes if len(q.split()) >= 3 and tok(q) in page]
        row = {**s.model_dump(), 'valid_quotes': good}
        if not page or not good:
            dropped.append({**row, 'reason': 'page not loaded' if not page else 'no verbatim quote on the page'})
            continue
        near = ' '.join(page[max(0, i - 600):i + len(tok(q)) + 600] for q in good for i in [page.find(tok(q))])
        near_facts = _facts(near)
        # on a page that lists many updates (release notes, newsroom) a sentence may only be supported by
        # THIS update's entry, not by another update further down the page
        if s.url in multi_entry:
            premise = '\n'.join(raw_window(raw, q) for q in good)
        else:
            premise = raw
        premises = nli.passages(unicodedata.normalize('NFKC', premise)) if nli is not None else []
        keep, cut = [], []
        for sent in _sentences(s.narration):
            missing = sorted(_facts(sent) - near_facts)
            ent, con = nli.score(claim(sent), premises) if nli is not None else (1.0, 0.0)
            # a date line ("announced on July 10, 2026") is checked by the facts rule + words near the quote
            ws = _words(sent)
            dated = bool(_facts(sent)) and not missing and ws and sum(w in near for w in ws) / len(ws) >= 0.7
            if missing or (ent < min_entail and not dated):
                cut.append({'sentence': sent, 'facts_not_near_quote': missing, 'entail': round(ent, 2), 'contradict': round(con, 2)})
            else:
                keep.append(sent)
        text = ' '.join(keep)
        row.update(narration=text, cut_sentences=cut)
        first_ok = bool(keep) and keep[0] == _sentences(s.narration)[0]   # without its opening the segment makes no sense
        if first_ok and len(keep) >= 2 and len(text.split()) >= 35:
            kept.append(row)
        else:
            dropped.append({**row, 'narration_original': s.narration,
                            'reason': (f'only {len(keep)} supported sentences left after cutting {len(cut)}' if first_ok else 'opening sentence not supported')})
    return kept, dropped


def hook_and_close(name: str, company: str, kept: list[dict]) -> tuple[str, str]:
    """Intro and outro written by code (no facts, only the titles that passed the gate)."""
    titles = [k['title'] for k in kept]
    show = ', '.join(titles[:3])
    hook = (f"{name} keeps changing fast, so here is what is new, taken straight from {company}'s official pages. "
            f"In the next few minutes we cover {len(titles)} updates, starting with {show}. "
            "Every fact you hear is shown on the real page while we talk, and the links are in the description.")
    close = (f"That was what is new in {name}. If one of these updates fits your work, open the official page linked "
             "in the description and try it today. Tell me in the comments which update you want explained in detail, "
             "and subscribe to LogicScript for the next one.")
    return hook, close


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
    # Step A: the list of distinct updates (small answer). Step B: one short segment per update, written from
    # that update's own text only (small requests fit every free tier; no duplicates, no mixing of updates).
    since = parse_since(a.since)
    main_url = src['pages'][0]
    list_prompt = f"""List the newest DISTINCT updates to {src['name']}{(' since ' + a.since) if a.since else ''} from the official {src['company']} pages below.
Return JSON: {{"updates": [{{"title": str, "url": str, "anchor": str, "detail_url": str}}]}} with up to 16 updates, newest first.
"url" = the page that announces it; "anchor" = 5-15 words COPIED EXACTLY from that page's entry about the update;
"detail_url" = a page below that explains this update in more detail, or "" if none. Each update once.

CORPUS"""
    updates = ask_model(list_prompt.replace('CORPUS', corpus[:150000]),
                        list_prompt.replace('CORPUS', f"=== PAGE {main_url} ===\n{usable.get(main_url, '')[:14000]}"), UpdateList).updates
    toks = {u: tok(t) for u, t in usable.items()}
    chosen, skipped, spans = [], [], []
    for up in updates:
        page = toks.get(up.url, '')
        pos = page.find(tok(up.anchor)) if page and len(up.anchor.split()) >= 4 else -1
        if pos < 0:
            skipped.append({'title': up.title, 'reason': 'anchor not on the page'}); continue
        d = entry_date(page, pos)
        if since and d and d < since:
            skipped.append({'title': up.title, 'reason': f'older than {a.since} ({d})'}); continue
        if any(u == up.url and abs(pos - p0) < 150 for u, p0 in spans):
            skipped.append({'title': up.title, 'reason': 'same entry as another update'}); continue
        spans.append((up.url, pos))
        chosen.append((up, pos, d))
    print(f'updates listed {len(updates)}, chosen {len(chosen)}', file=sys.stderr)
    seg_prompt = """Write ONE segment of a factual YouTube video (channel LogicScript) about this {name} update: "{title}".
Use ONLY the official text below. Return JSON: {{"video_title": str, "segments": [{{"title": str, "narration": str, "url": str, "quotes": [str]}}]}}
with exactly one segment. narration = 80 to 130 words of plain spoken English, in your own words, in the third person
(say "{company}", never "we"; open with what the update is, not with "{company} says"), no lists, no markdown: what changed, who gets it (plans), how to use or turn it on - only
what the text says. Never add examples, benefits, opinions or steps the text does not state; if the text is short, write less.
Say a date only if it is in the text. "url" = "{url}". "quotes" = 1-3 phrases (4-15 words) COPIED EXACTLY from the text.

=== {url} ===
{text}"""
    kept, dropped, title = [], [], ''
    nli = Entailment()
    for k, (up, pos, d) in enumerate(chosen):
        if sum(len(x['narration'].split()) for x in kept) >= 1300:
            break
        raw = usable[up.url]
        # the update's entry: start near the anchor, ~2,500 characters of the page around it
        words = re.findall(r"[A-Za-z0-9]+", up.anchor)[:6]
        m = re.search(r'\W+'.join(map(re.escape, words)), raw, re.I) if words else None
        i = m.start() if m else -1
        entry = raw[max(0, i - 600): i + 1900] if i >= 0 else raw[:2500]
        detail = usable.get(up.detail_url, '') if up.detail_url and up.detail_url != up.url else ''
        text = entry + (f"\n\n=== {up.detail_url} ===\n{detail[:6000]}" if detail else '')
        url = up.detail_url if detail and len(detail) > 1500 else up.url
        p = seg_prompt.format(name=src['name'], title=up.title, company=src['company'], url=url, text=text)
        if k:
            time.sleep(20)   # stay under the free tiers' tokens-per-minute limits
        try:
            got = ask_model(p, p)
        except SystemExit as exc:
            dropped.append({'title': up.title, 'reason': f'no model answer: {str(exc)[:200]}'}); continue
        seg = got.segments[0].model_copy(update={'url': url if got.segments[0].url not in usable else got.segments[0].url})
        g_kept, g_dropped = ground(Plan(video_title='x', segments=[seg]), usable, nli, multi_entry=frozenset(src['pages']))
        for r in g_kept:
            r['entry_date'] = str(d) if d else ''
        kept += g_kept
        dropped += g_dropped
    dropped = skipped + dropped
    hook, close = hook_and_close(src['name'], src['company'], kept)
    first_url = kept[0]['url'] if kept else src['pages'][0]
    kept = ([{'title': 'What changed', 'narration': hook, 'url': first_url, 'quotes': [], 'valid_quotes': kept[0]['valid_quotes'] if kept else []}]
            + kept + [{'title': 'What to try first', 'narration': close, 'url': first_url, 'quotes': [],
                       'valid_quotes': kept[0]['valid_quotes'] if kept else []}])
    import datetime
    video_title = f"What's new in {src['name']} - {datetime.date.today():%B %Y}"
    report = {'ai': a.ai, 'pages_loaded': sorted(usable), 'page_errors': {u: e for u, e in texts.items() if u.endswith('#error')},
              'segments_kept': len(kept), 'updates_listed': len(updates), 'updates_chosen': len(chosen), 'segments_dropped': dropped,
              'words_kept': sum(len(s['narration'].split()) for s in kept)}
    (a.out / 'grounding_report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
    if len(kept) < 6:   # hook + >= 4 verified updates + closing
        raise SystemExit('grounding gate: fewer than 4 verified segments — no video (see grounding_report.json)')
    out = {'ai': a.ai, 'title': video_title, 'language': 'en', 'segments': kept}
    (a.out / 'plan.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    (a.out / 'narration_texts.json').write_text(json.dumps([s['narration'] for s in kept], ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'segments_dropped'} | {'dropped': len(dropped)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
