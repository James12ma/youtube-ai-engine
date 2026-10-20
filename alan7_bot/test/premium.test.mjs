import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {Miniflare} from 'miniflare';
import {premiumRequest} from '../src/premium_control.mjs';

test('script words and paragraphs survive intake; English voice is explicit',()=>{
 const raw='My exact wording must remain.\n\nHere is my second paragraph for the new video.';
 assert.equal(premiumRequest('en '+raw).script,raw);
 assert.equal(premiumRequest('en voice=am_michael '+raw).voice,'am_michael');
 assert.throws(()=>premiumRequest('Excel tips'),/script konplè/);
 assert.throws(()=>premiumRequest('es Esto es un guion largo para una prueba hoy.'),/anglè/);
});

test('authenticated owner webhook stores private reference, deduplicates and survives GitHub failure',async()=>{
 const calls=[];let githubUp=false;
 const token='123:TEST_ONLY';const owner='777';
 const mf=new Miniflare({modules:true,scriptPath:new URL('../src/index.js',import.meta.url).pathname,compatibilityDate:'2025-09-01',d1Databases:['DB'],bindings:{TELEGRAM_BOT_TOKEN:token,OWNER_ID:owner,GITHUB_TOKEN:'TEST_ONLY'},outboundService:async req=>{
  const u=new URL(req.url);const body=await req.text();calls.push({url:u.pathname,body});
  if(u.hostname==='api.telegram.org')return Response.json({ok:true,result:{document:{file_id:'TG_PRIVATE_SOURCE'}}});
  if(u.pathname.endsWith('/dispatches'))return new Response(null,{status:githubUp?204:503});
  return Response.json({workflow_runs:[]});
 }});
 try{
  const db=await mf.getD1Database('DB');
  for(const s of readFileSync(new URL('../migrations/0001_init.sql',import.meta.url),'utf8').split(';').map(s=>s.replace(/--.*$/gm,'').trim()).filter(Boolean))await db.prepare(s).run();
  const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode('alan7-webhook:'+token));
  const secret=[...new Uint8Array(bytes)].map(x=>x.toString(16).padStart(2,'0')).join('').slice(0,48);
  const request=from=>mf.dispatchFetch('https://bot.example/telegram',{method:'POST',headers:{'content-type':'application/json','x-telegram-bot-api-secret-token':secret},body:JSON.stringify({message:{message_id:42,text:'/script en PRIVATE OWNER WORDS must not appear in any public GitHub input.',from:{id:from},chat:{id:from,type:'private'}}})});
  await request(999);assert.equal(calls.length,0);
  const r=await request(777);assert.match((await r.json()).text,/anrejistre/);
  const row=await db.prepare("SELECT * FROM jobs WHERE kind='premium_video'").first();assert.equal(row.state,'queued');
  const wire=calls.find(c=>c.url.endsWith('/dispatches'));
  const payload=JSON.parse(wire.body).inputs.payload;
  assert.ok(!payload.includes('PRIVATE OWNER WORDS'));assert.ok(!wire.body.includes('script:'));
  assert.equal(JSON.parse(payload).file_id,'TG_PRIVATE_SOURCE');
  const count=calls.length;await request(777);assert.equal(calls.length,count);
  githubUp=true;await db.prepare('UPDATE jobs SET next_try_at=0').run();
  await (await mf.getWorker()).scheduled({cron:'*/5 * * * *'});
  assert.equal((await db.prepare('SELECT state FROM jobs WHERE id=?1').bind(row.id).first()).state,'running');
 }finally{await mf.dispose();}
});
