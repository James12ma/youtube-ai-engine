import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseDirectorDraftRequest, directorDraftCommand, handleCommand} from '../src/index.js';

const example='en tutorial Excel expense tracker | https://support.microsoft.com/en-us/excel | https://learn.microsoft.com/en-us/office/';

test('draft request validates exact owner-provided source URLs',()=>{
  const p=parseDirectorDraftRequest(example);
  assert.equal(p.language,'en');
  assert.equal(p.mode,'tutorial');
  assert.equal(p.topic,'Excel expense tracker');
  assert.equal(p.urls.length,2);
});
test('free-text SEO preflight never dispatches draft workflow',async()=>{
  const old=globalThis.fetch;
  let calls=[];
  globalThis.fetch=async (url)=> {
    calls.push(url);
    const u=new URL(url);
    if(u.pathname.endsWith('/search'))return Response.json({items:[]});
    throw Error('Unexpected');
  };
  try{
    const msg=await handleCommand({YOUTUBE_API_KEY:'KEY'},'/director en tutorial Excel expense tracker');
    assert.match(msg,/Pa gen rezilta/);
    assert.equal(calls.length,1);
    assert.ok(calls.every(u=>!u.includes('github')));
  }finally{globalThis.fetch=old;}
});
test('no arbitrary public/internal or duplicate sources',()=>{
  for(const bad of [
    'en tutorial Excel expense tracker | http://example.com/1 | https://example.org/2',
    'en tutorial Excel expense tracker | https://localhost/1 | https://example.org/2',
    'en tutorial Excel expense tracker | https://127.0.0.1/1 | https://example.org/2',
    'en tutorial Excel expense tracker | https://user:pw@example.org/1 | https://example.net/2',
    'en tutorial Excel expense tracker | https://example.org/1 | https://example.org/1',
  ]) assert.ok(parseDirectorDraftRequest(bad).error);
});
test('no GitHub token means no outbound request or job',async()=>{
  const orig=globalThis.fetch;
  globalThis.fetch=()=>{throw Error('Network must not be called');};
  try{
    const reply=await directorDraftCommand({},example);
    assert.match(reply,/GitHub pa konekte/);
  }finally{globalThis.fetch=orig;}
});
test('bad free-form request never creates a job or calls API',async()=>{
  const reply=await directorDraftCommand({GITHUB_TOKEN:'NOT_USED'},'en tutorial Excel');
  assert.match(reply,/Bezwen 2 URL/);
});
