import {test} from 'node:test';
import assert from 'node:assert/strict';
import {filmRequest} from '../src/premium_control.mjs';
import {dispatchJob} from '../src/index.js';
test('cinema plain script and genre stay private and exact',()=>{
 const text='The applicant prepares one application and sends it to the recruiter.';
 const r=filmRequest('finance en '+text);assert.equal(r.script,text);assert.equal(r.genre,'finance');assert.equal(r.visual_mode,'cinematic');
 assert.ok(filmRequest('',true).script.includes('candidate finds'));
});
test('review branch applies only to the isolated cinematic kind',async()=>{
 const original=globalThis.fetch,calls=[];
 globalThis.fetch=async(url,args)=>{calls.push(JSON.parse(args.body));return new Response(null,{status:204});};
 try{
  const env={GITHUB_TOKEN:'FAKE',CINEMA_REVIEW_REF:'feat/semantic-film-director-20261020'};
  await dispatchJob(env,{id:'1234abcd',kind:'cinematic_video',arg:'{"file_id":"private","source_sha256":"hash"}'});
  await dispatchJob(env,{id:'1234abce',kind:'premium_video',arg:'{"file_id":"private"}'});
  assert.equal(calls[0].ref,env.CINEMA_REVIEW_REF);assert.equal(calls[1].ref,'main');
  assert.deepEqual(Object.keys(calls[0].inputs).sort(),['job_id','payload']);
 }finally{globalThis.fetch=original;}
});
