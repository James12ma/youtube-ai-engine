import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildSEOPackage, formatSEOPackage, seoPackCommand, handleCommand } from '../src/index.js';

const ID = 'A1b2C3d4E5F';

test('Alan7 documentary produces 5 distinct Spanish review titles, hook and safe metadata', () => {
  const videos = [{id: ID, snippet: {title: 'Acrobacias de ballenas jorobadas'},
                   statistics: {viewCount:'90000'}}];
  const p = buildSEOPackage('ballenas jorobadas', 'es', 'documentary', videos);
  assert.equal(p.titles.length, 5);
  assert.equal(new Set(p.titles).size, 5);
  assert.ok(p.titles.every(x => x.length <= 100));
  assert.equal(p.status, 'NEEDS_OWNER_REVIEW');
  assert.equal(p.published, false);
  assert.equal(p.appliedToRelease, false);
  assert.match(p.hook, /fuentes verificadas/);
  assert.match(p.description, /\[añadir escenas y hechos comprobados/);
  assert.ok(p.keywords.some(t => t.includes('ballenas jorobadas')));
  assert.ok(p.hashtags.some(t => t === '#BallenasJorobadas'));
  assert.deepEqual(p.angles[0], {term: 'acrobacias', count: 1});
  assert.match(formatSEOPackage(p), /5 tit pwopoze/);
});

test('LogicScript tutorial gets accurate unapproved English metadata', () => {
  const p = buildSEOPackage('Excel expense tracker', 'en', 'tutorial', []);
  assert.equal(p.titles.length, 5);
  assert.match(p.titles[0], /step-by-step/);
  assert.match(p.hook, /on screen/);
  assert.match(p.description, /reviewed screen demonstration/);
  assert.ok(p.hashtags.includes('#HowTo'));
  assert.equal(p.generator, 'deterministic_templates_no_llm');
});

test('safe Telegram escaping and no competitor-brand keyword copying', () => {
  const p = buildSEOPackage('ballenas jorobadas', 'es', 'documentary', [
    {id:ID, snippet:{title:'<script>acrobacias</script> de ballenas jorobadas',
       tags:['National Geographic','other company']}, statistics:{viewCount:'30'}},
  ]);
  const text = formatSEOPackage(p);
  assert.doesNotMatch(text, /<script>/);
  assert.doesNotMatch(text, /National Geographic/);
  assert.match(text, /&lt;script&gt;/);
});

test('on-demand /seopack uses two official public API GETs, no publishing', async () => {
  const orig=globalThis.fetch;
  const calls=[];
  globalThis.fetch=async (url,opts) => {
    const u=new URL(url);
    calls.push({u,method:opts.method,redirect:opts.redirect});
    if(u.pathname.endsWith('/search')){
      return Response.json({items:[{id:{videoId:ID}}]});
    }
    if(u.pathname.endsWith('/videos')){
      return Response.json({items:[{id:ID,snippet:{
        title:'Acrobacias de ballenas jorobadas',tags:['ballenas'],channelId:'UC'+'x'.repeat(22)
      },statistics:{viewCount:'8772'}}]});
    }
    throw Error('Unexpected endpoint');
  };
  try {
    const result=await handleCommand({YOUTUBE_API_KEY:'DO_NOT_ECHO'},'/seopack es doc ballenas jorobadas');
    assert.match(result, /SEO EDITORIAL PACKAGE/);
    assert.match(result, /views: 8772/);
    assert.match(result, /5 tit pwopoze/);
    assert.equal(calls.length,2);
    assert.equal(calls[0].u.searchParams.get('part'),'snippet');
    assert.ok(calls.every(c=>c.method==='GET'&&c.redirect==='manual'));
    assert.doesNotMatch(result,/DO_NOT_ECHO/);
  } finally {globalThis.fetch=orig;}
});

test('without API key no outbound request or invented competitor evidence',async ()=>{
  const old=globalThis.fetch;
  let calls=0;
  globalThis.fetch=async ()=>{calls++;throw Error('NO');};
  try{
    const result=await seoPackCommand({},'en tutorial Excel');
    assert.match(result,/YOUTUBE_API_KEY/);
    assert.equal(calls,0);
  } finally {globalThis.fetch=old;}
});

test('Google errors do not turn into fabricated SEO output',async()=>{
  const old=globalThis.fetch;
  globalThis.fetch=async()=>Response.json({error:{details:[{reason:'quotaExceeded'}]}},{status:403});
  try {
    const result=await seoPackCommand({YOUTUBE_API_KEY:'NO_ECHO'},'es jaguar');
    assert.match(result,/quotaExceeded/);
    assert.doesNotMatch(result,/SEO EDITORIAL PACKAGE|NO_ECHO/);
  } finally {globalThis.fetch=old;}
});
