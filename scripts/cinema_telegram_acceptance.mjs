// Runs the actual branch Worker + local workerd/D1, private Telegram and real branch dispatch.
// This never deploys or changes the production Worker. Public key adds encrypted review only.
import {createRequire} from 'node:module';
import {readFileSync,writeFileSync} from 'node:fs';
import assert from 'node:assert/strict';
import {webhookSecret} from '../alan7_bot/src/index.js';
const require=createRequire(new URL('../alan7_bot/package.json',import.meta.url));
const {Miniflare}=require('miniflare');
let mf;
try{
 const owner=Number(process.env.OWNER),id=Number(process.env.MESSAGE_ID||2026102020);
 const branch=process.env.CINEMA_REVIEW_REF;
 assert.match(branch,/^feat\/semantic-film-director-/);
 const observed={telegram:false,github:false,private_payload:false};
 mf=new Miniflare({modules:true,scriptPath:new URL('../alan7_bot/src/index.js',import.meta.url).pathname,
  compatibilityDate:'2025-09-01',d1Databases:['DB'],bindings:{TELEGRAM_BOT_TOKEN:process.env.TG,OWNER_ID:String(owner),GITHUB_TOKEN:process.env.GH,CINEMA_REVIEW_REF:branch},
  outboundService:async req=>{
   try{
    const url=new URL(req.url);let body=req.method==='GET'?undefined:await req.arrayBuffer();
    if(url.host==='api.github.com'&&url.pathname.endsWith('/dispatches')){
      const data=JSON.parse(new TextDecoder().decode(body));assert.equal(data.ref,branch);
      const payload=JSON.parse(data.inputs.payload);assert.ok(payload.file_id&&payload.source_sha256);assert.ok(!data.inputs.payload.includes('candidate finds'));
      if(process.env.DELIVERY_PUBKEY)data.inputs.delivery_pubkey=process.env.DELIVERY_PUBKEY;
      body=JSON.stringify(data);observed.private_payload=true;
    }
    const r=await fetch(req.url,{method:req.method,headers:req.headers,body});
    if(url.host==='api.telegram.org'&&url.pathname.endsWith('/sendDocument'))observed.telegram=r.status===200;
    if(url.host==='api.github.com'&&url.pathname.endsWith('/dispatches'))observed.github=r.status===204;
    return r;
   }catch{return new Response('Private acceptance transport failed',{status:502});}
  }});
 const db=await mf.getD1Database('DB');const sql=readFileSync(new URL('../alan7_bot/migrations/0001_init.sql',import.meta.url),'utf8');
 for(const stmt of sql.split(';').map(x=>x.replace(/--.*$/gm,'').trim()).filter(Boolean))await db.prepare(stmt).run();
 const headers={'content-type':'application/json','x-telegram-bot-api-secret-token':await webhookSecret(process.env.TG)};
 const say=(who=owner)=>mf.dispatchFetch('https://branch.test/telegram',{method:'POST',headers,body:JSON.stringify({update_id:id,message:{message_id:id,text:'/filmtest',from:{id:who},chat:{id:owner,type:'private'}}})});
 assert.equal((await mf.dispatchFetch('https://branch.test/telegram',{method:'POST',body:'{}'})).status,403);
 assert.equal(await(await say(owner+1)).text(),'ok');
 const first=await(await say()).json();assert.ok(first.text.includes('lanse'),'Film command was not dispatched');
 const duplicate=await(await say()).json();assert.ok(duplicate.text.includes('deja'),'Duplicate was not blocked');
 const row=await db.prepare("SELECT id,kind,state FROM jobs LIMIT 1").first();
 assert.equal(row.kind,'cinematic_video');assert.equal(row.state,'running');assert.ok(observed.telegram&&observed.github&&observed.private_payload);
 const report={...observed,job_id:row.id,dispatch_ref:branch,authenticated_worker:true,real_workerd_and_local_d1:true,duplicate_suppressed:true,non_owner_ignored:true,production_worker_modified:false};
 writeFileSync('cinema-telegram-evidence.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
}catch(e){console.error('Cinema acceptance failed: '+e.name);process.exitCode=1;}finally{if(mf)await mf.dispose();}
