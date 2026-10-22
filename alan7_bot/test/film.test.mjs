import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {Miniflare} from 'miniflare';
import {filmRequest} from '../src/premium_control.mjs';

const SCRIPT = 'At two a.m., Maya finally finds the job she wants. She fills in the application on her phone and presses Submit.';

test('film intake keeps exact words, language, voice and title; refuses fragments and Creole honestly', () => {
  const r = filmRequest(`es voice=ef_dora title=La línea honesta | ${SCRIPT}`);
  assert.equal(r.script, SCRIPT);
  assert.deepEqual([r.language, r.voice, r.title], ['es', 'ef_dora', 'La línea honesta']);
  assert.equal(filmRequest(SCRIPT).language, 'en');
  assert.throws(() => filmRequest('en Excel tips'), /script konplè/);
  assert.throws(() => filmRequest('ht ' + SCRIPT), /Kreyòl/);
});

test('/film stores the script privately, writes an order on the studio branch, retries and tracks the push run', async () => {
  const calls = [];
  let githubUp = false;
  const token = '123:TEST_ONLY', owner = '777';
  const mf = new Miniflare({
    modules: true, scriptPath: new URL('../src/index.js', import.meta.url).pathname, compatibilityDate: '2025-09-01',
    d1Databases: ['DB'], bindings: {TELEGRAM_BOT_TOKEN: token, OWNER_ID: owner, GITHUB_TOKEN: 'TEST_ONLY'},
    outboundService: async (req) => {
      const u = new URL(req.url); const body = await req.text(); calls.push({url: u.pathname, method: req.method, body, search: u.search});
      if (u.hostname === 'api.telegram.org') return Response.json({ok: true, result: {document: {file_id: 'TG_PRIVATE_SOURCE'}}});
      if (u.pathname.includes('/contents/studio/orders/')) return new Response('{}', {status: githubUp ? 201 : 503});
      if (u.pathname.endsWith('/studio-film.yml/runs')) {
        const id = calls.find((c) => c.url.includes('/contents/'))?.url.split('/').pop().replace('.json', '');
        return Response.json({workflow_runs: [{id: 9, display_title: `Film order ${id}`, status: 'completed', conclusion: 'success', html_url: 'x'}]});
      }
      return Response.json({workflow_runs: []});
    },
  });
  try {
    const db = await mf.getD1Database('DB');
    for (const s of readFileSync(new URL('../migrations/0001_init.sql', import.meta.url), 'utf8').split(';').map((s) => s.replace(/--.*$/gm, '').trim()).filter(Boolean)) await db.prepare(s).run();
    const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode('alan7-webhook:' + token));
    const secret = [...new Uint8Array(bytes)].map((x) => x.toString(16).padStart(2, '0')).join('').slice(0, 48);
    const send = (from) => mf.dispatchFetch('https://bot.example/telegram', {method: 'POST',
      headers: {'content-type': 'application/json', 'x-telegram-bot-api-secret-token': secret},
      body: JSON.stringify({message: {message_id: 7, text: `/film en title=The honest line | ${SCRIPT}`, from: {id: from}, chat: {id: from, type: 'private'}}})});
    await send(999); assert.equal(calls.length, 0, 'strangers are ignored');
    assert.match((await (await send(777)).json()).text, /anrejistre/);
    const row = await db.prepare("SELECT * FROM jobs WHERE kind='film'").first();
    assert.equal(row.state, 'queued');
    const n = calls.length; await send(777); assert.equal(calls.length, n, 'same message is not ordered twice');
    githubUp = true; await db.prepare('UPDATE jobs SET next_try_at=0').run();
    await (await mf.getWorker()).scheduled({cron: '*/5 * * * *'});
    const put = calls.filter((c) => c.method === 'PUT').pop();
    const order = JSON.parse(atob(JSON.parse(put.body).content));
    assert.equal(JSON.parse(put.body).branch, 'ccr-ff883983-8z1psm');
    assert.equal(order.telegram_file_id, 'TG_PRIVATE_SOURCE');
    assert.equal(order.title, 'The honest line');
    assert.ok(!put.body.includes('Maya') && !atob(JSON.parse(put.body).content).includes('Maya'), 'script text never reaches GitHub');
    // the same tick dispatches the order, then finds its push-triggered run (here already finished)
    assert.equal((await db.prepare('SELECT state FROM jobs WHERE id=?1').bind(row.id).first()).state, 'done');
    assert.ok(calls.some((c) => c.url.endsWith('/studio-film.yml/runs') && c.search.includes('event=push')));
  } finally {
    await mf.dispose();
  }
});
