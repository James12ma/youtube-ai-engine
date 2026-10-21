/* LogicScript Studio runtime.
   A video = resolved plan (from Python): format, style pack, shots (each a scene function + params + timed cues),
   captions (word timings), headlines. render(t) draws frame t deterministically.

   Scene contract (built-in scenes in scenes.js and AI-written scenes share it):
     function scene(S) { ...build SVG under S.root...; return function update(t) { ... } }
   S.root   : <g> in a 1000x1000 drawing box (or the full frame when shot.layout=='full', see S.W/S.H)
   S.W,S.H  : drawing box size      S.A : drawing helpers (art.js)      S.theme : style pack colours
   S.p      : shot params           S.dur : shot length (s)
   S.at(name, fallback) : local time (s) of a named cue, i.e. when the narration says that phrase
   S.cues   : [{name, at, args}] all cues of this shot, sorted
*/
(function(){
const A=window.ART, SC=window.SCENES;
const ST={plan:null,shots:[],w:1080,h:1920,errors:[]};
window.__errors=ST.errors;
window.addEventListener('error',e=>ST.errors.push(String(e.message||e)));

function layoutFor(fmt){
  // drawing box, headline box and caption line per format
  if(fmt==='horizontal')return {w:1920,h:1080,art:{x:460,y:150,w:1000,h:760},head:{top:40,size:58,src:20},cap:{bottom:70,size:44,maxw:1300},brand:{x:40,y:1032},prog:{x:40,y:1060,w:1840}};
  if(fmt==='square')return {w:1080,h:1080,art:{x:140,y:250,w:800,h:640},head:{top:50,size:60,src:18},cap:{bottom:60,size:42,maxw:900},brand:{x:40,y:1040},prog:{x:40,y:1066,w:1000}};
  return {w:1080,h:1920,art:{x:40,y:500,w:1000,h:1000},head:{top:200,size:96,src:22},cap:{bottom:265,size:52,maxw:860},brand:{x:0,y:1752},prog:{x:90,y:1860,w:900}};
}

function applyStyle(style){
  const r=document.documentElement.style;const pal=style.palette||{};
  for(const k in pal)r.setProperty('--'+k,pal[k]);
  const bg=document.getElementById('bg');
  const kind=(style.background||'grid');
  if(kind==='paper'){bg.style.backgroundImage='radial-gradient(#00000010 1.5px,transparent 1.5px)';bg.style.backgroundSize='34px 34px'}
  else if(kind==='plain'){bg.style.backgroundImage='none'}
  else if(kind==='glow'){bg.style.backgroundImage='radial-gradient(ellipse at 50% 30%, var(--bg2) 0%, transparent 65%)';bg.style.backgroundSize='100% 100%'}
  if(style.font)document.getElementById('stage').style.fontFamily=style.font;
}

function buildShot(shot,i,L){
  const host=document.createElement('div');host.className='shot';host.dataset.i=i;
  const full=shot.layout==='full';
  const box=full?{x:0,y:0,w:L.w,h:L.h}:L.art;
  const art=document.createElement('div');art.className='art';
  Object.assign(art.style,{left:box.x+'px',top:box.y+'px',width:box.w+'px',height:box.h+'px'});
  const W=full?L.w:1000,H=full?L.h:1000;
  const svg=A.svg(W,H);art.appendChild(svg);host.appendChild(art);
  const root=A.g(svg);
  const cues=(shot.cues||[]).map(c=>({name:c.name,at:c.at-shot.start,args:c.args||{}})).sort((a,b)=>a.at-b.at);
  const S={root,svg,W,H,A,theme:ST.plan.style.palette||{},p:shot.params||{},dur:shot.end-shot.start,cues,
    at:(name,fb)=>{const c=cues.find(c=>c.name===name);return c?c.at:(fb===undefined?1e9:fb)},
    args:name=>{const c=cues.find(c=>c.name===name);return c?c.args:{}},
    format:ST.plan.format};
  let update=()=>{};
  try{
    let fn=null;
    if(shot.code){fn=new Function('S','"use strict";\n'+shot.code+'\nreturn scene(S);');update=fn(S)}
    else if(SC[shot.scene]){update=SC[shot.scene](S)}
    else throw new Error('unknown scene '+shot.scene);
    if(typeof update!=='function')throw new Error('scene did not return an update(t) function');
  }catch(e){ST.errors.push(`shot ${shot.id} (${shot.scene}) build: ${e.message}`);update=()=>{}}
  return {shot,host,art,update,box};
}

function camera(sh,tl){
  const cam=(sh.shot.camera||'push');const d=Math.max(.5,sh.shot.end-sh.shot.start);const p=A.eInOut(A.clamp(tl/d));
  if(cam==='none')return 'none';
  if(cam==='pull')return `scale(${A.lerp(1.08,1,p)})`;
  if(cam==='pan')return `translateX(${A.lerp(30,-30,p)}px) scale(1.04)`;
  if(cam==='drift')return `translateY(${A.lerp(18,-18,p)}px)`;
  return `scale(${A.lerp(1,1.06,p)})`;   // push
}

function setHeadline(sh,tl){
  const el=document.getElementById('headline');const h=sh&&sh.shot.headline;const L=ST.L;
  if(!h||ST.plan.style.headline===false){el.innerHTML='';el.dataset.k='';return}
  const key=sh.shot.id+'|'+JSON.stringify(h);
  if(el.dataset.k!==key){
    el.dataset.k=key;el.style.top=L.head.top+'px';el.innerHTML='';
    if(h.pills&&h.pills.length){const pr=document.createElement('div');pr.className='pills';
      h.pills.slice(0,2).forEach((t,j)=>{const p=document.createElement('span');p.className='pill '+(j?'b':'a');p.textContent=t;pr.appendChild(p)});el.appendChild(pr)}
    (h.lines||[]).slice(0,3).forEach((ln,j)=>{const d=document.createElement('div');d.className='line'+(j===h.accent?' acc':'');d.textContent=ln;
      const n=Math.max(...(h.lines||['x']).map(s=>s.length));d.style.fontSize=Math.min(L.head.size,Math.round(L.head.size*11/Math.max(8,n)))+'px';el.appendChild(d)});
    if(h.source){const s=document.createElement('div');s.className='src';s.style.fontSize=L.head.src+'px';s.textContent=h.source;el.appendChild(s)}
  }
  const p=A.eOut(A.clamp(tl/.35));el.style.opacity=p;el.style.transform=`translateY(${(1-p)*20}px)`;
}

function setCaption(t){
  const el=document.getElementById('caption');const L=ST.L;const style=ST.plan.style.captions||'box';
  if(style==='none'){el.innerHTML='';return}
  const c=(ST.plan.captions||[]).find(c=>t>=c.start&&t<c.end);
  if(!c){el.innerHTML='';el.dataset.k='';return}
  const key=c.start+'';
  if(el.dataset.k!==key){el.dataset.k=key;el.style.bottom=L.cap.bottom+'px';el.innerHTML='';
    const b=document.createElement('div');b.className='box';b.style.fontSize=L.cap.size+'px';b.style.maxWidth=L.cap.maxw+'px';
    b.style.padding=Math.round(L.cap.size*.38)+'px '+Math.round(L.cap.size*.7)+'px';
    c.words.forEach((w,j)=>{const s=document.createElement('span');s.textContent=(j?' ':'')+w.text;if(w.key)s.className='k';s.dataset.st=w.start;b.appendChild(s)});
    el.appendChild(b)}
  if(style==='karaoke'){el.querySelectorAll('span').forEach(s=>{s.style.opacity=t>=+s.dataset.st?1:.35})}
}

window.STUDIO={
  load(plan){
    ST.plan=plan;const L=layoutFor(plan.format);ST.L=L;ST.w=L.w;ST.h=L.h;
    const stage=document.getElementById('stage');stage.style.width=L.w+'px';stage.style.height=L.h+'px';
    applyStyle(plan.style||{});
    const brand=document.getElementById('brand');brand.textContent=plan.brand||'';
    Object.assign(brand.style,{left:L.brand.x+'px',top:L.brand.y+'px',width:(plan.format==='vertical'?L.w:400)+'px',textAlign:plan.format==='vertical'?'center':'left',fontSize:(plan.format==='vertical'?30:22)+'px'});
    const pr=document.getElementById('progress');Object.assign(pr.style,{left:L.prog.x+'px',top:L.prog.y+'px',width:L.prog.w+'px'});
    if(plan.style.progress===false)pr.style.display='none';
    const host=document.getElementById('shots');host.innerHTML='';
    ST.shots=plan.shots.map((s,i)=>buildShot(s,i,L));ST.shots.forEach(s=>host.appendChild(s.host));
    return {w:L.w,h:L.h,errors:ST.errors.slice()};
  },
  render(t){
    const shots=ST.shots;const TR=(ST.plan.style.transition_s??.32);
    let cur=-1;for(let i=0;i<shots.length;i++)if(t>=shots[i].shot.start)cur=i;
    shots.forEach((sh,i)=>{
      const tl=t-sh.shot.start;const visible=i===cur||(i===cur-1&&t<shots[cur].shot.start+TR);
      if(!visible){sh.host.style.display='none';return}
      sh.host.style.display='block';
      try{sh.update(Math.max(0,tl))}catch(e){if(ST.errors.length<50)ST.errors.push(`shot ${sh.shot.id} (${sh.shot.scene}) t=${tl.toFixed(2)}: ${e.message}`)}
      if(i===cur){const p=A.eOut(A.clamp((t-sh.shot.start)/TR));const kind=sh.shot.transition||ST.plan.style.transition||'push';
        sh.host.style.opacity=p;sh.host.style.zIndex=2;
        const enter=kind==='slide'?`translateX(${(1-p)*120}px)`:kind==='fade'?'':`scale(${A.lerp(1.06,1,p)})`;
        sh.art.style.transform=camera(sh,tl).replace('none','')+' '+enter;
        if(sh.shot.layout==='full')sh.art.style.transform=enter||'none';}
      else{sh.host.style.zIndex=1;sh.host.style.opacity=1}
    });
    setHeadline(cur>=0?shots[cur]:null,cur>=0?t-shots[cur].shot.start:0);
    setCaption(t);
    const pb=document.querySelector('#progress div');pb.style.width=(100*A.clamp(t/ST.plan.duration))+'%';
    return ST.errors.length;
  },
  errors:()=>ST.errors.slice(),
  /* fraction of a shot's drawing box covered by its drawing (QA: is anything drawn?) */
  area(i){const sh=ST.shots[i];if(!sh)return 0;try{const b=sh.host.querySelector('svg > g').getBBox();
    const W=sh.shot.layout==='full'?ST.w:1000,H=sh.shot.layout==='full'?ST.h:1000;return (b.width*b.height)/(W*H)}catch(e){return 0}},
  /* bounds check for QA: fraction of a shot's drawing that falls outside its box */
  overflow(i){const sh=ST.shots[i];if(!sh)return 0;try{const b=sh.host.querySelector('svg > g').getBBox();
    const W=sh.shot.layout==='full'?ST.w:1000,H=sh.shot.layout==='full'?ST.h:1000;
    const ox=Math.max(0,-b.x)+Math.max(0,b.x+b.width-W),oy=Math.max(0,-b.y)+Math.max(0,b.y+b.height-H);
    return Math.max(ox/W,oy/H)}catch(e){return 0}},
};
})();
