// Exact owner script intake; no model call and no public plaintext transport.
export function premiumRequest(raw, test=false) {
  if(test) return {language:'en',voice:'af_heart',profile:'premium',script:JSON.stringify({title:'Prepare for your next interview',language:'en',scenes:[
    {kind:'cards',on_screen:'PREPARE WITH PURPOSE',items:['Role','Company','Examples'],narration:'Before your next interview, prepare three things. Understand the role, learn what the company does, and choose examples that show how you solve problems. Strong preparation gives your answers a clear direction.'},
    {kind:'process',on_screen:'SHOW YOUR THINKING',items:['Situation','Action','Result'],narration:'When you describe an experience, explain the situation, the action you took, and the result. Keep the example specific. If you do not know an answer, say so and explain how you would find it.'},
    {kind:'timeline',on_screen:'PRACTICE THEN IMPROVE',items:['Record','Listen','Refine'],narration:'Record a short practice answer. Listen for unclear wording and unnecessary detail. Then try again. The goal is not to memorize a perfect speech. It is to communicate your experience in your own words.'}
    ,{kind:'cards',on_screen:'MAKE IT YOUR OWN',items:['Listen','Clarify','Connect'],narration:'During the conversation, listen carefully before you answer. Ask for clarification when a question is unclear. Use simple language, and connect your experience to the work the role requires. Preparation helps you stay focused while remaining yourself.'}
  ]})};
  let text=String(raw||'').trim();let voice='af_heart';
  const m=/^(?:en\s+)?(?:voice=(af_heart|am_michael)\s+)?([\s\S]+)$/.exec(text);
  if(!m) throw Error('Voye script konplè a: /script en <tèks>. Separe sèn yo ak yon liy vid.');
  if(m[1])voice=m[1];text=m[2];
  if(text.length<20||text.length>12000||text.split(/\s+/).length<8)throw Error('Voye yon script konplè an anglè, pa sèlman yon sijè.');
  if(/^(es|fr|ht)\s/.test(text))throw Error('Nouvo chemen vwa sa a sipòte anglè pou kounye a.');
  return {language:'en',voice,profile:'premium',script:text};
}
export async function privateScriptFile(env, request) {
  const bytes=new TextEncoder().encode(JSON.stringify(request));
  const data=new FormData();data.set('chat_id',env.OWNER_ID);
  data.set('caption','Script resevwa pou rendering prive — mo ou yo konsève.');
  data.set('document',new Blob([bytes],{type:'application/json'}),'owner-script.json');
  try{
    const r=await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendDocument`,{method:'POST',body:data});
    const b=await r.json();const file=b?.result?.document?.file_id;
    if(!r.ok||b.ok!==true||typeof file!=='string')throw Error('delivery');
    const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(request.script));
    return {file_id:file,source_sha256:[...new Uint8Array(hash)].map(x=>x.toString(16).padStart(2,'0')).join(''),profile:'premium',voice:request.voice};
  }catch{throw Error('Telegram pa t ka konsève script la. Pa gen rann ki lanse.');}
}

export function filmRequest(raw,test=false){
  let text=String(raw||'').trim(),genre='education';
  const profiles=['children','finance','news','education','technology','documentary'];
  const first=text.split(/\s+/)[0];if(profiles.includes(first)){genre=first;text=text.slice(first.length).trim();}
  if(test)text="en A candidate finds an open position and prepares an application before contacting the company. The candidate picks up a phone and sends the application to the company's recruiting team. The message travels from the candidate's phone to the recruiter at the company office. The recruiter reviews the application and contacts the candidate to schedule an interview.";
  return {...premiumRequest(text),visual_mode:'cinematic',genre};
}
