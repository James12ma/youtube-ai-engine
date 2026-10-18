// Video request router for Alan7 Telegram.
// Intentionally deterministic: a future Gemini director may propose decisions,
// but the capabilities/safety gate here remains authoritative.
const MAX_TOPIC = 180;
const MAX_ARGUMENT = 480;
const LANGS = new Set(['en', 'fr', 'es', 'ht']);
const MODES = new Set(['preview', 'full']);
const STYLES = new Set(['motion', 'premium', 'documentary', 'tutorial', 'news']);

export function parseVideoRequest(raw) {
  if (typeof raw !== 'string' || !raw.trim()) {
    throw new Error('Ekri: /video 5 types of job interviews | lang=en | duration=60 | mode=preview');
  }
  if (raw.length > MAX_ARGUMENT || /[\u0000-\u001f\u007f]/.test(raw)) {
    throw new Error('Demann videyo a twò long oswa gen karaktè ki pa akseptab.');
  }
  const pieces = raw.split('|').map(s => s.trim());
  const topic = pieces.shift();
  if (!topic || topic.length > MAX_TOPIC) throw new Error('Sijè a dwe genyen 1 a 180 karaktè.');
  const request = { topic, language: 'en', duration: 60, style: 'motion', mode: 'preview' };
  const seen = new Set();
  for (const part of pieces) {
    const match = /^(lang|language|duration|style|mode)\s*=\s*([a-zA-Z0-9_-]+)$/i.exec(part);
    if (!match) throw new Error('Paramèt pa valid. Sèvi ak lang=en, duration=60, style=motion, mode=preview.');
    const key = match[1].toLowerCase();
    const field = key === 'lang' ? 'language' : key;
    if (seen.has(field)) throw new Error('Menm paramèt la parèt de fwa.');
    seen.add(field);
    const value = match[2].toLowerCase();
    if (field === 'duration') {
      const n = Number(value);
      if (!Number.isInteger(n) || n < 10 || n > 600) throw new Error('Dire a dwe ant 10 ak 600 segonn.');
      request.duration = n;
    } else {
      request[field] = value;
    }
  }
  if (!LANGS.has(request.language)) throw new Error('Lang ki sipòte pou demann: en, fr, es, ht.');
  if (!STYLES.has(request.style)) throw new Error('Stil ki akseptab: motion, premium, documentary, tutorial, news.');
  if (!MODES.has(request.mode)) throw new Error('Mòd yo: preview oswa full.');
  return request;
}

function topicClass(topic) {
  const value = topic.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  if (/\b(interview|entretien|entrevista)\b|job[\s-]*interviews?/.test(value)) return 'career';
  if (/\b(excel|spreadsheet|tutorial|logiciel|software|powerpoint)\b/.test(value)) return 'tutorial';
  if (/\b(france|actualite|news|politic|election|breaking)\b/.test(value)) return 'news';
  if (/\b(wildlife|whale|jaguar|nature|ocean|documentary)\b/.test(value)) return 'documentary';
  return 'other';
}

export function routeVideoRequest(request) {
  const category = topicClass(request.topic);
  const engine = category === 'tutorial' ? 'logicscript'
    : category === 'documentary' ? 'alan7'
    : category === 'news' ? 'motion'
    : category === 'career' ? 'motion'
    : 'unassigned';
  const normalized = request.topic.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  const known = [
    'job interviews', 'job interview', 'interview types', '5 types of job interviews',
    'types of job interviews', 'job interviews types'
  ].includes(normalized);
  const runnable = known && request.language === 'en' && request.duration === 60 && request.style === 'motion';
  return {
    ...request,
    category,
    suggested_engine: engine,
    supported_now: runnable,
    topic_id: runnable ? 'job-interviews' : null,
    status: runnable ? 'render_supported' : 'awaiting_director',
    // The deterministic router is NOT a Gemini model, and unsupported requests must not render.
    ai_director: 'not_connected',
    requires_owner_approval: true,
    auto_publish: false,
    reason: runnable ? 'One registered, prewritten career explainer'
      : 'Requested topic/style/language/duration does not have a validated render path yet',
  };
}
