"""List the free models each provider offers right now (names only, no keys printed)."""
import json, os, httpx

def note(title, msg):
    esc = lambda t: t.replace('%', '%25').replace('\r', ' ').replace('\n', ' ')
    print(f'::notice title={title}::{esc(msg)[:3800]}')

def get(url, headers=None):
    try:
        r = httpx.get(url, headers=headers or {}, timeout=30)
        return r.status_code, (r.json() if r.headers.get('content-type', '').startswith('application/json') else {})
    except Exception as exc:
        return 0, {'error': str(exc)[:200]}

c, d = get('https://openrouter.ai/api/v1/models')
free = sorted((m['id'], m.get('context_length'), (m.get('top_provider') or {}).get('max_completion_tokens'))
              for m in d.get('data', []) if m['id'].endswith(':free'))
note('openrouter-free', f'HTTP {c}: ' + ' | '.join(f'{i} ctx={x} out={y}' for i, x, y in free))
k = os.environ.get('GEMINI_API_KEY', '')
c, d = get('https://generativelanguage.googleapis.com/v1beta/models', {'x-goog-api-key': k})
note('gemini-models', f'HTTP {c}: ' + ' '.join(m['name'] for m in d.get('models', []) if 'flash' in m['name']) + json.dumps(d.get('error', ''))[:300])
k = os.environ.get('GROQ_API_KEY', '')
c, d = get('https://api.groq.com/openai/v1/models', {'Authorization': f'Bearer {k}'})
note('groq-models', f'HTTP {c}: ' + ' '.join(sorted(m['id'] for m in d.get('data', []))) + json.dumps(d.get('error', ''))[:300])
