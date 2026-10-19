import assert from 'node:assert/strict';
import { test } from 'node:test';
import { handleOwnerScript } from '../src/index.js';

function fakeEnv() {
  const writes = [];
  return {
    writes,
    DB: {
      prepare(sql) {
        return {
          bind(...args) {
            return { async run() { writes.push({sql,args}); return {success:true}; } };
          }
        };
      }
    }
  };
}

const script = [
  '[00:00–00:05] — HOOK',
  'Think ChatGPT is just for answering questions? You are missing out on its features!',
  '[00:05–00:15] — FEATURE 1',
  'ChatGPT can browse websites and research information and complete multi-step tasks.',
].join('\n\n');

test('timestamped pasted owner script stored unchanged and never dispatched', async () => {
  const env = fakeEnv();
  const reply = await handleOwnerScript(env, script);
  assert.match(reply, /2 sekans, 15 segonn/);
  assert.match(reply, /Pa gen videyo ki lanse/);
  const insertion=env.writes.find(x=>x.sql.includes('INSERT INTO jobs'));
  assert.ok(insertion);
  const body=JSON.parse(insertion.args[1]);
  assert.equal(body.script,script);
  assert.equal(body.auto_publish,false);
  assert.equal(body.owner_review_required,true);
  assert.equal(env.writes.some(x=>/running|dispatch/.test(x.sql)),false);
});

test('refuses noncontiguous owner script timestamps', async () => {
  const env = fakeEnv();
  const bad=script.replace('[00:05–00:15]', '[00:06–00:15]');
  assert.match(await handleOwnerScript(env,bad),/Tan sekans yo dwe kontinyèl/);
  assert.equal(env.writes.length,0);
});

test('refuses short and oversized scripts', async () => {
  const env = fakeEnv();
  assert.match(await handleOwnerScript(env,'hello'),/twò kout/);
  assert.match(await handleOwnerScript(env,'x'.repeat(3600)),/depase/);
  assert.equal(env.writes.length,0);
});
