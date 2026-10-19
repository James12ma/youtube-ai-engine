import { test } from 'node:test';
import assert from 'node:assert/strict';
import { directorPreflight, directorPreflightCommand, formatDirectorPreflight, handleCommand } from '../src/index.js';

const id = 'A1b2C3d4E5F';
const sample = [
  {id, snippet: {title: 'Excel Budget Template | Automate your budget in 15 minutes'},
    statistics:{viewCount:'3858198'}},
  {id:'Q9w8E7r6T5Y',snippet:{title:'Excel Personal Finance Tracker | Build & Automate Yours in Minutes'},
    statistics:{viewCount:'965537'}},
];

test('preflight notices build and automate rather than generic themes, but claims no script', () => {
  const p=directorPreflight('Excel expense tracker','en','tutorial',sample);
  assert.equal(p.status,'AWAITING_VERIFIED_SCRIPT_AND_VISUALS');
  assert.equal(p.observedThemes.find(t=>t.theme==='automate').count,2);
  assert.equal(p.observedThemes.find(t=>t.theme==='build').count,1);
  assert.equal(p.sourcesVerified,false);
  assert.equal(p.scriptGenerated,false);
  assert.equal(p.realScreenRecordingVerified,false);
  assert.equal(p.published,false);
  assert.doesNotMatch(JSON.stringify(p), /guaranteed views|monetization/);
  const text=formatDirectorPreflight(p);
  assert.match(text,/automate: 2 tit/);
  assert.match(text,/Script konplè poko jenere ni verifye/);
  assert.match(text,/channel.cli director-review/);
});

test('director routes from actual Telegram command and uses two official GETs', async () => {
  const previous=globalThis.fetch;
  const calls=[];
  globalThis.fetch=async (url,opts)=>{
    const u=new URL(url);calls.push({u,opts});
    if(u.pathname.endsWith('/search'))
      return Response.json({items:sample.map(x=>({id:{videoId:x.id}}))});
    if(u.pathname.endsWith('/videos'))
      return Response.json({items:sample});
    throw Error('unexpected source');
  };
  try {
    const text=await handleCommand({YOUTUBE_API_KEY:'SECRET_NEVER_ECHO'},
      '/director en tutorial Excel expense tracker');
    assert.match(text,/AI DIRECTOR — EDITORIAL PREFLIGHT/);
    assert.match(text,/automate: 2 tit/);
    assert.equal(calls.length,2);
    assert.equal(calls[0].u.searchParams.get('part'),'snippet');
    assert.ok(calls.every(c=>c.opts.redirect==='manual'));
    assert.doesNotMatch(text,/SECRET_NEVER_ECHO/);
  } finally {globalThis.fetch=previous;}
});

test('documentary preflight cannot invent footage facts',()=>{
  const p=directorPreflight('ballenas jorobadas','es','documentary',
    [{id,snippet:{title:'Acrobacias de las ballenas jorobadas'}}]);
  assert.equal(p.mode,'documentary');
  assert.equal(p.realFootageVerified,false);
  assert.equal(p.scriptGenerated,false);
  assert.match(formatDirectorPreflight(p),/fuentes/);
});

test('no key and Google errors produce no fake director output',async()=>{
  const old=globalThis.fetch;
  let calls=0;
  globalThis.fetch=async()=>{calls++;return Response.json({error:{errors:[{reason:'quotaExceeded'}]}},{status:403})};
  try {
    const noKey=await directorPreflightCommand({},'en tutorial Excel');
    assert.match(noKey,/YOUTUBE_API_KEY/);
    assert.equal(calls,0);
    const rejected=await directorPreflightCommand({YOUTUBE_API_KEY:'DO_NOT_SHOW'},'en tutorial Excel');
    assert.match(rejected,/quotaExceeded/);
    assert.doesNotMatch(rejected,/DO_NOT_SHOW|EDITORIAL PREFLIGHT/);
  }finally{globalThis.fetch=old;}
});

test('angle title is not a competitor headline and does not claim automatic workflow',()=>{
  const p=directorPreflight('Excel expense tracker','en','tutorial',sample);
  assert.ok(!p.titleDraft.includes('15 minutes'));
  assert.ok(!p.titleDraft.includes('Automate'));
  assert.ok(p.plan.some(x=>x.includes('Capture actual clicks')));
});
