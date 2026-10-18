// Alan7 Telegram control bot — Cloudflare Worker (webhook) + D1 (jobs/queue).
//
// Design rules
// - Replies come from the Worker itself, so the bot answers even when GitHub
//   Actions, Kaggle or any GPU is down. Heavy work is only *dispatched*.
// - Only the owner (OWNER_ID, private chat) is served; everyone else is ignored.
// - Secrets (TELEGRAM_BOT_TOKEN, OWNER_ID, GITHUB_TOKEN) live in Cloudflare
//   Secrets. They are never logged or echoed. The webhook secret is derived
//   from the bot token, so there is no extra secret to manage.
// - Jobs whose dispatch fails stay queued and are retried by the cron with
//   backoff. Nothing is published anywhere.

import { parseVideoRequest, routeVideoRequest } from './video_director.js';

const TG = 'https://api.telegram.org';
const GH = 'https://api.github.com';
const REPO = 'James12ma/youtube-ai-engine';
const JOB_WORKFLOW = 'alan7-job.yml';
const VIDEO_WORKFLOW = 'alan7-video.yml';
const MAX_ATTEMPTS = 12;

// Job kinds the bot can run today. Anything else is refused with an honest message.
const KINDS = {
  test: { label: 'Tès sistèm (GitHub Actions, san GPU)', dispatch: true },
  lena: { label: 'Plan IA LENA 3 s (Kaggle GPU gratis, ~1 è)', dispatch: true, workflow: 'alan7-daily.yml' },
};

const HELP = [
  '<b>Alan7 — kòmand</b>',
  '/status — eta bot la, GitHub ak file atant lan',
  '/create test — lanse yon tès sistèm (san GPU)',
  '/create lena [0-4] — jenere yon plan IA LENA 3 s sou Kaggle (~1 è); videyo a rive isit la',
  '/video sijè | lang=en | duration=60 | style=motion | mode=preview — mande yon nouvo videyo',
  '/topics — wè sa motè a ka pwodwi kounye a',
  '🎬 Voye yon klip videyo (MP4, &lt; 20 MB) ak yon tèks an panyòl kòm caption: m ap retounen l ak narasyon, soutit ak etikèt IA.',
  '/queue — 10 dènye travay yo',
  '/cancel &lt;id&gt; — anile yon travay',
  '/help — lis sa a',
  '',
  'Bot la pa pibliye anyen sou YouTube.',
].join('\n');

// ---------------------------------------------------------------- helpers

export async function webhookSecret(token) {
  const data = new TextEncoder().encode('alan7-webhook:' + token);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return [...new Uint8Array(hash)].map((b) => b.toString(16).padStart(2, '0')).join('').slice(0, 48);
}

function esc(s) {
  return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function newId() {
  const b = crypto.getRandomValues(new Uint8Array(4));
  return [...b].map((x) => x.toString(16).padStart(2, '0')).join('');
}

const now = () => Math.floor(Date.now() / 1000);

async function tg(env, method, payload) {
  try {
    const r = await fetch(`${TG}/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return { ok: r.ok, status: r.status, body: await r.json().catch(() => ({})) };
  } catch (e) {
    return { ok: false, status: 0, body: { description: 'network: ' + (e && e.name) } };
  }
}

const send = (env, chatId, text) =>
  tg(env, 'sendMessage', { chat_id: chatId, text, parse_mode: 'HTML', disable_web_page_preview: true });

async function setMeta(env, key, value) {
  await env.DB.prepare('INSERT INTO meta(key, value, updated_at) VALUES (?1, ?2, ?3) ' +
    'ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at')
    .bind(key, String(value), now()).run();
}

async function getMeta(env, key) {
  const row = await env.DB.prepare('SELECT value, updated_at FROM meta WHERE key = ?1').bind(key).first();
  return row || null;
}

async function logEvent(env, jobId, event, detail) {
  await env.DB.prepare('INSERT INTO events(job_id, event, detail, at) VALUES (?1, ?2, ?3, ?4)')
    .bind(jobId, event, String(detail ?? '').slice(0, 500), now()).run();
}

// ---------------------------------------------------------------- GitHub

function ghHeaders(env) {
  return {
    authorization: `Bearer ${env.GITHUB_TOKEN}`,
    accept: 'application/vnd.github+json',
    'x-github-api-version': '2022-11-28',
    'user-agent': 'alan7-bot',
  };
}

// Returns {ok, status, detail}. Never throws; never includes the token.
export async function dispatchJob(env, job) {
  if (!env.GITHUB_TOKEN) return { ok: false, status: 0, detail: 'GITHUB_TOKEN pa konfigire' };
  try {
    const wf = workflowFor(job.kind);
    let inputs;
    if (job.kind === 'video') {
      // Even if D1 data is changed, never send an unsupported topic to the runner.
      if (env.VIDEO_RUNNER_ENABLED !== '1') return { ok: false, status: 0, detail: 'video runner disabled (zero-cost approval pending)' };
      let requested;
      try { requested = routeVideoRequest(parseVideoRequest(JSON.parse(job.arg).request)); }
      catch { return { ok: false, status: 0, detail: 'invalid video request' }; }
      if (!requested.supported_now) return { ok: false, status: 0, detail: 'unsupported video request' };
      inputs = { job_id: job.id, topic_id: requested.topic_id, mode: requested.mode,
        language: requested.language, style: requested.style };
    } else {
      inputs = wf === JOB_WORKFLOW ? { job_id: job.id, kind: job.kind, arg: job.arg || '' }
        : { job_id: job.id, shot: /^[0-4]$/.test((job.arg || '').trim()) ? job.arg.trim() : '' };
    }
    const r = await fetch(`${GH}/repos/${REPO}/actions/workflows/${wf}/dispatches`, {
      method: 'POST',
      headers: { ...ghHeaders(env), 'content-type': 'application/json' },
      body: JSON.stringify({ ref: 'main', inputs }),
    });
    if (r.status === 204 || r.status === 200) return { ok: true, status: r.status, detail: 'dispatched' };
    return { ok: false, status: r.status, detail: `GitHub HTTP ${r.status}` };
  } catch (e) {
    return { ok: false, status: 0, detail: 'GitHub network error' };
  }
}

const workflowFor = (kind) => kind === 'video' ? VIDEO_WORKFLOW : (KINDS[kind] && KINDS[kind].workflow) || JOB_WORKFLOW;

// Find the run started for a job (run-name "alan7 <job_id>") and return its state.
export async function findRun(env, job) {
  if (!env.GITHUB_TOKEN) return null;
  try {
    const r = await fetch(`${GH}/repos/${REPO}/actions/workflows/${workflowFor(job.kind)}/runs?event=workflow_dispatch&per_page=30`,
      { headers: ghHeaders(env) });
    if (!r.ok) return { error: `GitHub HTTP ${r.status}` };
    const data = await r.json();
    const run = (data.workflow_runs || []).find((w) => (w.display_title || w.name || '') === `alan7 ${job.id}`);
    if (!run) return { missing: true };
    return { id: run.id, status: run.status, conclusion: run.conclusion, url: run.html_url };
  } catch (e) {
    return { error: 'GitHub network error' };
  }
}

async function cancelRun(env, runId) {
  if (!env.GITHUB_TOKEN || !runId) return false;
  try {
    const r = await fetch(`${GH}/repos/${REPO}/actions/runs/${runId}/cancel`, { method: 'POST', headers: ghHeaders(env) });
    return r.status === 202;
  } catch (e) {
    return false;
  }
}

// ---------------------------------------------------------------- commands

async function cmdStatus(env) {
  const counts = await env.DB.prepare('SELECT state, COUNT(*) AS n FROM jobs GROUP BY state').all();
  const c = Object.fromEntries((counts.results || []).map((r) => [r.state, r.n]));
  const gh = await getMeta(env, 'github_last');
  const cron = await getMeta(env, 'cron_last');
  const fmt = (m) => (m ? `${esc(m.value)} (${new Date(m.updated_at * 1000).toISOString().slice(0, 16).replace('T', ' ')} UTC)` : 'poko');
  return [
    '<b>Alan7 — estati</b>',
    'Bot: ✅ ap reponn (Cloudflare Worker)',
    `GitHub: ${env.GITHUB_TOKEN ? fmt(gh) : '⚠️ GITHUB_TOKEN pa konfigire — travay yo rete nan file atant'}`,
    `Dènye verifikasyon otomatik (cron): ${fmt(cron)}`,
    `File atant: ${c.queued || 0} · ap travay: ${c.running || 0} · tann apwobasyon: ${c.awaiting_approval || 0}`,
    `Fini: ${c.done || 0} · echwe: ${c.failed || 0} · anile: ${c.cancelled || 0}`,
    'GPU: Kaggle T4 gratis (~1 è pou chak plan 3 s)',
  ].join('\n');
}

async function cmdCreate(env, arg) {
  const [kindRaw, ...rest] = (arg || '').trim().split(/\s+/);
  const kind = (kindRaw || '').toLowerCase();
  if (!KINDS[kind]) {
    return `Mwen pa konnen "<code>${esc(kindRaw || '')}</code>". Sa ki disponib: ${Object.keys(KINDS).map((k) => `<code>${k}</code>`).join(', ')}.`;
  }
  const id = newId();
  const spec = KINDS[kind];
  const state = spec.dispatch ? 'queued' : spec.state;
  await env.DB.prepare('INSERT INTO jobs(id, kind, arg, state, attempts, created_at, updated_at) VALUES (?1, ?2, ?3, ?4, 0, ?5, ?5)')
    .bind(id, kind, rest.join(' ').slice(0, 200), state, now()).run();
  await logEvent(env, id, 'created', kind);
  if (!spec.dispatch) {
    return `🗂 Travay <code>${id}</code> anrejistre: ${esc(spec.label)}.\nEta: tann apwobasyon. Pa gen okenn GPU ki lanse.`;
  }
  const job = { id, kind, arg: rest.join(' ') };
  const d = await dispatchJob(env, job);
  await setMeta(env, 'github_last', d.ok ? 'OK' : d.detail);
  if (d.ok) {
    await env.DB.prepare("UPDATE jobs SET state = 'running', attempts = 1, updated_at = ?2 WHERE id = ?1").bind(id, now()).run();
    await logEvent(env, id, 'dispatched', 'ok');
    return `🚀 Travay <code>${id}</code> voye bay GitHub Actions (${esc(spec.label)}).\nM ap ekri w lè li fini.`;
  }
  await env.DB.prepare('UPDATE jobs SET attempts = 1, last_error = ?2, next_try_at = ?3, updated_at = ?3 WHERE id = ?1')
    .bind(id, d.detail, now() + 300).run();
  await logEvent(env, id, 'dispatch_failed', d.detail);
  return `🕒 Travay <code>${id}</code> anrejistre, men GitHub pa disponib kounye a (${esc(d.detail)}).\n` +
    'Li rete nan file atant; m ap eseye ankò otomatikman chak 5 minit.';
}

async function cmdVideo(env, arg) {
  let request;
  try { request = routeVideoRequest(parseVideoRequest(arg)); }
  catch (error) { return '⚠️ ' + esc(error.message); }
  const id = newId();
  const active = request.supported_now && env.VIDEO_RUNNER_ENABLED === '1' && Boolean(env.GITHUB_TOKEN);
  const state = active ? 'queued' : 'awaiting_approval';
  const storedArg = JSON.stringify({ request: arg.trim(), route: request });
  await env.DB.prepare('INSERT INTO jobs(id, kind, arg, state, attempts, created_at, updated_at) VALUES (?1, ?2, ?3, ?4, 0, ?5, ?5)')
    .bind(id, 'video', storedArg.slice(0, 1800), state, now()).run();
  await logEvent(env, id, 'video_requested', request.status);
  if (!request.supported_now) {
    return '🗂 Demann <code>' + id + '</code> anrejistre. Sijè: <b>' + esc(request.topic) + '</b>.\n'
      + 'Motè sijere: ' + esc(request.suggested_engine) + '.\n'
      + '⚠️ Poko gen motè valide pou konbinezon sa a. AI Director Gemini poko konekte. '
      + 'Pa gen okenn videyo ki lanse, ni okenn lajan ki depanse.';
  }
  if (!active) {
    return '🗂 Demann <code>' + id + '</code> anrejistre. Motè a sipòte sijè sa a.\n'
      + '⏸ Rannman otomatik an poz: GitHub Actions / zero-cost runner poko otorize oswa konekte. '
      + 'Pa gen okenn videyo ki lanse. Konsève id travay la.';
  }
  const d = await dispatchJob(env, { id, kind: 'video', arg: storedArg });
  await setMeta(env, 'github_last', d.ok ? 'OK' : d.detail);
  if (d.ok) {
    await env.DB.prepare("UPDATE jobs SET state = 'running', attempts = 1, updated_at = ?2 WHERE id = ?1").bind(id, now()).run();
    await logEvent(env, id, 'dispatched', 'video');
    return '🎬 Travay <code>' + id + '</code> voye bay motè GitHub. '
      + (request.mode === 'preview' ? 'Preview 4 segonn.' : 'Videyo 60 segonn.')
      + ' Mp4 prive sèlman; pa gen piblikasyon.';
  }
  await env.DB.prepare('UPDATE jobs SET state = ?2, attempts = 1, last_error = ?3, next_try_at = ?4, updated_at = ?5 WHERE id = ?1')
    .bind(id, 'queued', d.detail, now() + 300, now()).run();
  await logEvent(env, id, 'dispatch_failed', d.detail);
  return '🕒 Demann <code>' + id + '</code> anrejistre, men GitHub pa disponib (' + esc(d.detail)
    + '). Li rete nan file atant; m ap reeseye san depans lè runner gratis la aktive.';
}

async function cmdQueue(env) {
  const rows = await env.DB.prepare('SELECT id, kind, state, attempts, created_at FROM jobs ORDER BY created_at DESC LIMIT 10').all();
  const list = rows.results || [];
  if (!list.length) return 'File atant lan vid.';
  const icon = { queued: '🕒', running: '⚙️', done: '✅', failed: '❌', cancelled: '🚫', awaiting_approval: '⏸' };
  return ['<b>10 dènye travay</b>', ...list.map((j) =>
    `${icon[j.state] || '•'} <code>${j.id}</code> ${esc(j.kind)} — ${esc(j.state)}` + (j.attempts > 1 ? ` (eseye ${j.attempts} fwa)` : ''))].join('\n');
}

async function cmdCancel(env, arg) {
  const id = (arg || '').trim().toLowerCase();
  if (!/^[0-9a-f]{8}$/.test(id)) return 'Ekri: /cancel &lt;id&gt; (8 karaktè, wè /queue).';
  const job = await env.DB.prepare('SELECT * FROM jobs WHERE id = ?1').bind(id).first();
  if (!job) return `Pa gen travay <code>${esc(id)}</code>.`;
  if (['done', 'failed', 'cancelled'].includes(job.state)) return `Travay <code>${id}</code> deja ${esc(job.state)}.`;
  let note = '';
  if (job.state === 'running') {
    const ok = await cancelRun(env, job.run_id);
    note = ok ? ' Mwen mande GitHub kanpe l.' : ' (GitHub pa t konfime anilasyon an; m ap verifye ankò.)';
  }
  await env.DB.prepare("UPDATE jobs SET state = 'cancelled', updated_at = ?2 WHERE id = ?1").bind(id, now()).run();
  await logEvent(env, id, 'cancelled', note);
  return `🚫 Travay <code>${id}</code> anile.${note}`;
}

export async function handleCommand(env, text) {
  const m = /^\/(\w+)(?:@\w+)?\s*([\s\S]*)$/.exec((text || '').trim());
  if (!m) return HELP;
  const [, cmd, arg] = m;
  switch (cmd.toLowerCase()) {
    case 'start':
      return '👋 Byenveni nan bot kontwòl Alan7.\n\n' + HELP;
    case 'help':
      return HELP;
    case 'status':
      return cmdStatus(env);
    case 'create':
      return cmdCreate(env, arg);
    case 'queue':
      return cmdQueue(env);
    case 'topics':
      return '🎬 Kounye a, motè valide: <code>job-interviews</code> (en, 60s, motion; preview/full). '
        + 'Ou kapab soumèt lòt sijè pou planifikasyon, men yo pap rann san yon motè teste. '
        + 'Gemini AI Director poko konekte.';
    case 'video':
      return cmdVideo(env, arg);
    case 'cancel':
      return cmdCancel(env, arg);
    default:
      return 'Kòmand sa a pa egziste. ' + HELP;
  }
}

// A video sent to the bot becomes a "clip" job: GitHub renders it with Spanish narration (the caption),
// subtitles and the AI label, then sends the finished MP4 back to the owner privately.
export async function handleClip(env, msg) {
  const v = msg.video || (msg.document && /^video\//.test(msg.document.mime_type || '') ? msg.document : null);
  if (!v) return null;
  if ((v.file_size || 0) > 20 * 1024 * 1024) return '⚠️ Klip la depase 20 MB (limit Telegram pou bot yo). Voye yon vèsyon pi piti.';
  const caption = (msg.caption || '').trim();
  if (caption.split(/\s+/).filter(Boolean).length < 3) {
    return '✍️ Voye klip la ankò ak yon <b>caption</b> an panyòl (narasyon an), pa egzanp: <i>Una madre jaguar guía a sus crías por la selva.</i>';
  }
  const id = newId();
  const arg = JSON.stringify({ file_id: v.file_id, caption: caption.slice(0, 600), duration: v.duration || null });
  await env.DB.prepare("INSERT INTO jobs(id, kind, arg, state, attempts, created_at, updated_at) VALUES (?1, 'clip', ?2, 'queued', 0, ?3, ?3)")
    .bind(id, arg, now()).run();
  await logEvent(env, id, 'created', 'clip');
  const d = await dispatchJob(env, { id, kind: 'clip', arg });
  await setMeta(env, 'github_last', d.ok ? 'OK' : d.detail);
  if (d.ok) {
    await env.DB.prepare("UPDATE jobs SET state = 'running', attempts = 1, updated_at = ?2 WHERE id = ?1").bind(id, now()).run();
    return `🎬 Klip resevwa (travay <code>${id}</code>). M ap ajoute narasyon, soutit ak etikèt IA; MP4 la ap rive isit la nan ~15–25 minit.`;
  }
  await env.DB.prepare('UPDATE jobs SET attempts = 1, last_error = ?2, next_try_at = ?3, updated_at = ?3 WHERE id = ?1').bind(id, d.detail, now() + 300).run();
  return `🕒 Klip anrejistre (<code>${id}</code>), men GitHub pa disponib (${esc(d.detail)}). M ap eseye ankò otomatikman.`;
}

// ---------------------------------------------------------------- cron

export async function tick(env) {
  const t = now();
  const notes = [];
  // 1) retry queued dispatches (GitHub was unavailable)
  const queued = await env.DB.prepare("SELECT * FROM jobs WHERE state = 'queued' AND (next_try_at IS NULL OR next_try_at <= ?1) LIMIT 5").bind(t).all();
  for (const job of queued.results || []) {
    if (job.attempts >= MAX_ATTEMPTS) {
      await env.DB.prepare("UPDATE jobs SET state = 'failed', updated_at = ?2 WHERE id = ?1").bind(job.id, t).run();
      notes.push(`❌ Travay <code>${job.id}</code> pa t ka voye apre ${job.attempts} eseye (${esc(job.last_error)}).`);
      continue;
    }
    const d = await dispatchJob(env, job);
    await setMeta(env, 'github_last', d.ok ? 'OK' : d.detail);
    if (d.ok) {
      await env.DB.prepare("UPDATE jobs SET state = 'running', attempts = attempts + 1, updated_at = ?2 WHERE id = ?1").bind(job.id, t).run();
      notes.push(`🚀 GitHub disponib ankò: travay <code>${job.id}</code> voye.`);
    } else {
      const backoff = Math.min(3600, 300 * 2 ** Math.min(job.attempts, 4));
      await env.DB.prepare('UPDATE jobs SET attempts = attempts + 1, last_error = ?2, next_try_at = ?3, updated_at = ?4 WHERE id = ?1')
        .bind(job.id, d.detail, t + backoff, t).run();
    }
  }
  // 2) follow running jobs
  const running = await env.DB.prepare("SELECT * FROM jobs WHERE state = 'running' LIMIT 10").all();
  for (const job of running.results || []) {
    const run = await findRun(env, job);
    if (!run || run.error || run.missing) {
      if (run && run.error) await setMeta(env, 'github_last', run.error);
      if (run && run.missing && t - job.updated_at > 1800) {
        await env.DB.prepare("UPDATE jobs SET state = 'failed', last_error = 'run not found', updated_at = ?2 WHERE id = ?1").bind(job.id, t).run();
        notes.push(`❌ Travay <code>${job.id}</code>: GitHub pa janm kòmanse l.`);
      }
      continue;
    }
    await setMeta(env, 'github_last', 'OK');
    if (!job.run_id) await env.DB.prepare('UPDATE jobs SET run_id = ?2 WHERE id = ?1').bind(job.id, run.id).run();
    if (run.status === 'completed') {
      const ok = run.conclusion === 'success';
      await env.DB.prepare('UPDATE jobs SET state = ?2, last_error = ?3, updated_at = ?4 WHERE id = ?1')
        .bind(job.id, ok ? 'done' : 'failed', ok ? null : run.conclusion, t).run();
      notes.push(`${ok ? '✅' : '❌'} Travay <code>${job.id}</code> (${esc(job.kind)}) ${ok ? 'fini' : 'echwe: ' + esc(run.conclusion)}.`);
    }
  }
  await setMeta(env, 'cron_last', 'OK');
  if (notes.length && env.OWNER_ID) await send(env, env.OWNER_ID, notes.join('\n'));
  return notes;
}

// ---------------------------------------------------------------- HTTP

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === 'GET' && url.pathname === '/health') {
      return Response.json({ ok: true, at: new Date().toISOString() });
    }
    if (request.method === 'GET' && url.pathname === '/setup') {
      // Points the bot's webhook at this Worker. Idempotent; reveals nothing secret.
      if (!env.TELEGRAM_BOT_TOKEN) return new Response('TELEGRAM_BOT_TOKEN pa konfigire', { status: 500 });
      const r = await tg(env, 'setWebhook', {
        url: `${url.origin}/telegram`,
        secret_token: await webhookSecret(env.TELEGRAM_BOT_TOKEN),
        allowed_updates: ['message'],
        drop_pending_updates: false,
      });
      return new Response(r.ok ? 'Webhook konfigire ✅' : `Erè Telegram (${r.status})`, { status: r.ok ? 200 : 502 });
    }
    if (request.method === 'POST' && url.pathname === '/telegram') {
      const expected = await webhookSecret(env.TELEGRAM_BOT_TOKEN || '');
      if (request.headers.get('x-telegram-bot-api-secret-token') !== expected) {
        return new Response('forbidden', { status: 403 });
      }
      const update = await request.json().catch(() => null);
      const msg = update && update.message;
      if (!msg || !(msg.text || msg.video || msg.document)) return new Response('ok');
      const owner = String(env.OWNER_ID || '');
      if (!owner || String(msg.from && msg.from.id) !== owner || msg.chat.type !== 'private') {
        return new Response('ok'); // silently ignore everyone but the owner
      }
      await setMeta(env, 'webhook_last', 'OK');
      let reply;
      try {
        reply = msg.text ? await handleCommand(env, msg.text)
          : (await handleClip(env, msg)) || 'Mwen aksepte sèlman kòmand oswa klip videyo.';
      } catch (e) {
        reply = '⚠️ Erè entèn — mesaj ou a resevwa, men mwen pa t ka trete l. Eseye ankò.';
      }
      // Reply inside the webhook response: no extra outbound call needed.
      return Response.json({ method: 'sendMessage', chat_id: msg.chat.id, text: reply, parse_mode: 'HTML',
        disable_web_page_preview: true });
    }
    return new Response('not found', { status: 404 });
  },

  async scheduled(event, env, ctx) {
    ctx.waitUntil(tick(env));
  },
};
