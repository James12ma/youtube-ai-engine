// End-to-end tests of the real Worker in workerd (Miniflare) with a real local D1.
// Telegram and GitHub are replaced by a fake outbound service; nothing leaves the runner.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { Miniflare } from 'miniflare';

const TOKEN = '123456:TEST-TOKEN-never-printed';
const OWNER = '777';
let mf, db, worker;
const calls = [];
const github = { mode: 'up', runs: [] };

async function secretFor(token) {
  const data = new TextEncoder().encode('alan7-webhook:' + token);
  const h = await crypto.subtle.digest('SHA-256', data);
  return [...new Uint8Array(h)].map((b) => b.toString(16).padStart(2, '0')).join('').slice(0, 48);
}

before(async () => {
  mf = new Miniflare({
    modules: true,
    scriptPath: new URL('../src/index.js', import.meta.url).pathname,
    compatibilityDate: '2025-09-01',
    d1Databases: ['DB'],
    bindings: { TELEGRAM_BOT_TOKEN: TOKEN, OWNER_ID: OWNER, GITHUB_TOKEN: 'ghs_fake' },
    outboundService: async (req) => {
      const url = new URL(req.url);
      const body = req.method === 'POST' ? await req.text() : '';
      calls.push({ host: url.host, path: url.pathname, method: req.method, body });
      if (url.host === 'api.telegram.org') return Response.json({ ok: true, result: true });
      if (url.host === 'api.github.com') {
        if (github.mode === 'down') return new Response('unavailable', { status: 503 });
        if (url.pathname.endsWith('/dispatches')) return new Response(null, { status: 204 });
        if (url.pathname.endsWith('/runs')) return Response.json({ workflow_runs: github.runs });
        if (url.pathname.endsWith('/cancel')) return new Response(null, { status: 202 });
      }
      return new Response('unexpected', { status: 599 });
    },
  });
  db = await mf.getD1Database('DB');
  const sql = readFileSync(new URL('../migrations/0001_init.sql', import.meta.url), 'utf8');
  for (const stmt of sql.split(';').map((s) => s.replace(/--.*$/gm, '').trim()).filter(Boolean)) {
    await db.prepare(stmt).run();
  }
  worker = await mf.getWorker();
});

after(async () => { await mf.dispose(); });

async function say(text, { from = OWNER, chatType = 'private', secret } = {}) {
  const res = await mf.dispatchFetch('https://alan7.example.workers.dev/telegram', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-telegram-bot-api-secret-token': secret ?? await secretFor(TOKEN) },
    body: JSON.stringify({ update_id: 1, message: { message_id: 1, text, from: { id: Number(from) }, chat: { id: Number(from), type: chatType } } }),
  });
  const raw = await res.text();
  let json = null;
  try { json = JSON.parse(raw); } catch {}
  return { status: res.status, raw, json };
}

const jobs = async () => (await db.prepare('SELECT * FROM jobs ORDER BY created_at').all()).results;

test('rejects requests without the webhook secret', async () => {
  const r = await say('/start', { secret: 'wrong' });
  assert.equal(r.status, 403);
});

test('ignores anyone who is not the owner (and group chats)', async () => {
  const a = await say('/start', { from: '999' });
  const b = await say('/start', { chatType: 'group' });
  assert.equal(a.raw, 'ok');
  assert.equal(b.raw, 'ok');
});

test('/start and /help answer from the Worker itself', async () => {
  const r = await say('/start');
  assert.equal(r.json.method, 'sendMessage');
  assert.match(r.json.text, /\/create test/);
  assert.ok(!r.raw.includes(TOKEN));
});

test('/create test dispatches to GitHub and the cron reports completion', async () => {
  github.mode = 'up';
  const r = await say('/create test');
  assert.match(r.json.text, /voye bay GitHub Actions/);
  const [job] = await jobs();
  assert.equal(job.state, 'running');
  const dispatch = calls.find((c) => c.path.endsWith('/dispatches'));
  assert.ok(dispatch && JSON.parse(dispatch.body).inputs.job_id === job.id);
  github.runs = [{ id: 42, display_title: `alan7 ${job.id}`, status: 'completed', conclusion: 'success', html_url: 'x' }];
  await worker.scheduled({ cron: '*/5 * * * *' });
  const after = (await jobs()).find((j) => j.id === job.id);
  assert.equal(after.state, 'done');
  const note = calls.filter((c) => c.host === 'api.telegram.org' && c.path.endsWith('/sendMessage')).pop();
  assert.match(note.body, /fini/);
});

test('GitHub down: job stays queued, bot still answers, cron retries, then recovers', async () => {
  github.mode = 'down';
  const r = await say('/create test');
  assert.equal(r.status, 200);
  assert.match(r.json.text, /GitHub pa disponib/);
  let job = (await jobs()).pop();
  assert.equal(job.state, 'queued');
  // /status and /queue still work while GitHub is down
  assert.match((await say('/status')).json.text, /ap reponn/);
  assert.match((await say('/queue')).json.text, new RegExp(job.id));
  // retry while still down -> attempts grow, still queued
  await db.prepare('UPDATE jobs SET next_try_at = 0 WHERE id = ?1').bind(job.id).run();
  await worker.scheduled({ cron: '*/5 * * * *' });
  job = (await jobs()).find((j) => j.id === job.id);
  assert.equal(job.state, 'queued');
  assert.equal(job.attempts, 2);
  // GitHub back -> dispatched on the next tick
  github.mode = 'up';
  await db.prepare('UPDATE jobs SET next_try_at = 0 WHERE id = ?1').bind(job.id).run();
  await worker.scheduled({ cron: '*/5 * * * *' });
  job = (await jobs()).find((j) => j.id === job.id);
  assert.equal(job.state, 'running');
});

test('/cancel and /create lena (no GPU launched)', async () => {
  const r = await say('/create lena');
  assert.match(r.json.text, /tann apwobasyon/);
  const lena = (await jobs()).find((j) => j.kind === 'lena');
  assert.equal(lena.state, 'awaiting_approval');
  const c = await say(`/cancel ${lena.id}`);
  assert.match(c.json.text, /anile/);
  assert.equal((await jobs()).find((j) => j.id === lena.id).state, 'cancelled');
  assert.match((await say('/create video')).json.text, /pa konnen/);
});

test('/setup registers the webhook with the derived secret, never echoing the token', async () => {
  const res = await mf.dispatchFetch('https://alan7.example.workers.dev/setup');
  const text = await res.text();
  assert.equal(res.status, 200);
  assert.ok(!text.includes(TOKEN));
  const call = calls.filter((c) => c.path.endsWith('/setWebhook')).pop();
  const body = JSON.parse(call.body);
  assert.equal(body.url, 'https://alan7.example.workers.dev/telegram');
  assert.equal(body.secret_token, await secretFor(TOKEN));
});

test('no reply or stored row ever contains the bot token', async () => {
  const ev = (await db.prepare('SELECT detail FROM events').all()).results.map((r) => r.detail).join(' ');
  const meta = (await db.prepare('SELECT value FROM meta').all()).results.map((r) => r.value).join(' ');
  assert.ok(!ev.includes(TOKEN) && !meta.includes(TOKEN) && !ev.includes('ghs_fake'));
});
