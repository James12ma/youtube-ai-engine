/* LogicScript Studio: drawing helpers, icons, characters and settings.
   Everything is deterministic: appearance depends only on parameters and time t (seconds). */
(function(){
const NS='http://www.w3.org/2000/svg';
const A={};

/* ---------- math / easing ---------- */
A.clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
A.lerp=(a,b,p)=>a+(b-a)*p;
A.prog=(t,t0,dur)=>A.clamp((t-t0)/Math.max(dur,1e-6));
A.eOut=p=>1-Math.pow(1-p,3);
A.eInOut=p=>p<.5?4*p*p*p:1-Math.pow(-2*p+2,3)/2;
A.back=p=>{const c1=1.70158,c3=c1+1;return 1+c3*Math.pow(p-1,3)+c1*Math.pow(p-1,2)};
A.pulse=(t,t0,dur=.5)=>{const p=A.prog(t,t0,dur);return p<=0||p>=1?0:Math.sin(p*Math.PI)};
A.rand=seed=>{let s=seed>>>0||1;return()=>((s=Math.imul(s^s>>>15,1|s)+0x6d2b79f5>>>0)%10000)/10000};

/* ---------- svg dom ---------- */
A.el=(tag,attrs={},parent=null)=>{const e=document.createElementNS(NS,tag);
  for(const k in attrs){if(attrs[k]!==undefined&&attrs[k]!==null)e.setAttribute(k,attrs[k])}
  if(parent)parent.appendChild(e);return e};
A.svg=(w,h)=>A.el('svg',{viewBox:`0 0 ${w} ${h}`,width:w,height:h,preserveAspectRatio:'xMidYMid meet'});
A.g=(parent,attrs={})=>A.el('g',attrs,parent);
A.text=(parent,x,y,str,attrs={})=>{const t=A.el('text',Object.assign({x,y,'font-family':'InterTight','font-weight':700,'font-size':32,fill:'#fff','text-anchor':'middle','dominant-baseline':'middle'},attrs),parent);t.textContent=str;return t};
A.set=(e,attrs)=>{for(const k in attrs)e.setAttribute(k,attrs[k])};
A.tf=(e,x,y,s=1,r=0)=>e.setAttribute('transform',`translate(${x} ${y}) rotate(${r}) scale(${s})`);
A.op=(e,o)=>e.setAttribute('opacity',A.clamp(o).toFixed(3));
A.shadow=(parent,cx,cy,rx,ry,o=.25)=>A.el('ellipse',{cx,cy,rx,ry,fill:'#000',opacity:o},parent);

/* ---------- icons (drawn in a 100x100 box, centered at 50,50) ---------- */
const ICON={
 phone:g=>{A.el('rect',{x:30,y:10,width:40,height:80,rx:8,fill:'#e2e8f0'},g);A.el('rect',{x:34,y:18,width:32,height:58,rx:3,fill:'#1e293b'},g);A.el('circle',{cx:50,cy:83,r:3,fill:'#94a3b8'},g)},
 laptop:g=>{A.el('rect',{x:18,y:22,width:64,height:42,rx:4,fill:'#e2e8f0'},g);A.el('rect',{x:23,y:27,width:54,height:32,fill:'#1e293b'},g);A.el('path',{d:'M10 68 H90 L84 76 H16 Z',fill:'#cbd5e1'},g)},
 cloud:g=>{A.el('path',{d:'M28 70 Q12 70 12 56 Q12 42 28 42 Q30 24 50 24 Q68 24 72 40 Q90 40 90 56 Q90 70 74 70 Z',fill:'#e2e8f0'},g)},
 building:g=>{A.el('rect',{x:24,y:16,width:52,height:74,rx:3,fill:'#e2e8f0'},g);for(let r=0;r<4;r++)for(let c=0;c<3;c++)A.el('rect',{x:31+c*14,y:24+r*14,width:9,height:9,fill:'#1e293b'},g);A.el('rect',{x:43,y:76,width:14,height:14,fill:'#1e293b'},g)},
 server:g=>{for(let i=0;i<3;i++){A.el('rect',{x:20,y:16+i*24,width:60,height:20,rx:4,fill:'#e2e8f0'},g);A.el('circle',{cx:30,cy:26+i*24,r:3,fill:'#22c55e'},g)}},
 envelope:g=>{A.el('rect',{x:14,y:26,width:72,height:48,rx:6,fill:'#ffffff'},g);A.el('path',{d:'M16 30 L50 54 L84 30',fill:'none',stroke:'#94a3b8','stroke-width':4},g)},
 doc:g=>{A.el('path',{d:'M26 10 H62 L76 24 V90 H26 Z',fill:'#ffffff'},g);A.el('path',{d:'M62 10 V24 H76',fill:'#cbd5e1'},g);for(let i=0;i<4;i++)A.el('rect',{x:34,y:36+i*12,width:i==3?22:34,height:5,rx:2,fill:'#94a3b8'},g)},
 check:g=>{A.el('circle',{cx:50,cy:50,r:40,fill:'#22c55e'},g);A.el('path',{d:'M32 51 L45 64 L69 38',fill:'none',stroke:'#fff','stroke-width':9,'stroke-linecap':'round','stroke-linejoin':'round'},g)},
 cross:g=>{A.el('circle',{cx:50,cy:50,r:40,fill:'#ef4444'},g);A.el('path',{d:'M35 35 L65 65 M65 35 L35 65',stroke:'#fff','stroke-width':9,'stroke-linecap':'round'},g)},
 bell:g=>{A.el('path',{d:'M50 14 Q72 14 72 42 V62 L80 72 H20 L28 62 V42 Q28 14 50 14 Z',fill:'#f7bf75'},g);A.el('circle',{cx:50,cy:80,r:7,fill:'#f7bf75'},g)},
 money:g=>{A.el('rect',{x:12,y:28,width:76,height:44,rx:6,fill:'#22c55e'},g);A.el('circle',{cx:50,cy:50,r:12,fill:'#bbf7d0'},g);A.text(g,50,51,'$',{fill:'#166534','font-size':18,'font-weight':800})},
 lock:g=>{A.el('path',{d:'M34 44 V32 Q34 16 50 16 Q66 16 66 32 V44',fill:'none',stroke:'#e2e8f0','stroke-width':8},g);A.el('rect',{x:24,y:42,width:52,height:42,rx:6,fill:'#e2e8f0'},g);A.el('circle',{cx:50,cy:62,r:6,fill:'#1e293b'},g)},
 chart:g=>{[30,50,70].forEach((h,i)=>A.el('rect',{x:20+i*22,y:84-h,width:16,height:h,rx:3,fill:['#7bf1d0','#f7bf75','#60a5fa'][i]},g))},
 search:g=>{A.el('circle',{cx:44,cy:44,r:22,fill:'none',stroke:'#e2e8f0','stroke-width':8},g);A.el('path',{d:'M60 60 L80 80',stroke:'#e2e8f0','stroke-width':10,'stroke-linecap':'round'},g)},
 person:g=>{A.el('circle',{cx:50,cy:34,r:16,fill:'#e2e8f0'},g);A.el('path',{d:'M22 86 Q22 56 50 56 Q78 56 78 86 Z',fill:'#e2e8f0'},g)},
 star:g=>{A.el('path',{d:'M50 12 L61 38 L89 40 L67 58 L74 86 L50 71 L26 86 L33 58 L11 40 L39 38 Z',fill:'#f7bf75'},g)},
 clock:g=>{A.el('circle',{cx:50,cy:50,r:36,fill:'#e2e8f0'},g);A.el('path',{d:'M50 50 V28 M50 50 L64 58',stroke:'#1e293b','stroke-width':6,'stroke-linecap':'round'},g)},
 spreadsheet:g=>{A.el('rect',{x:14,y:16,width:72,height:68,rx:6,fill:'#ffffff'},g);A.el('rect',{x:14,y:16,width:72,height:14,rx:6,fill:'#22c55e'},g);for(let r=0;r<4;r++)A.el('line',{x1:14,x2:86,y1:44+r*10,y2:44+r*10,stroke:'#cbd5e1','stroke-width':2},g);A.el('line',{x1:40,x2:40,y1:30,y2:84,stroke:'#cbd5e1','stroke-width':2},g)},
 robot:g=>{A.el('rect',{x:22,y:30,width:56,height:46,rx:12,fill:'#e2e8f0'},g);A.el('circle',{cx:38,cy:52,r:6,fill:'#1e293b'},g);A.el('circle',{cx:62,cy:52,r:6,fill:'#1e293b'},g);A.el('path',{d:'M50 30 V18',stroke:'#e2e8f0','stroke-width':5},g);A.el('circle',{cx:50,cy:15,r:5,fill:'#7bf1d0'},g)},
 globe:g=>{A.el('circle',{cx:50,cy:50,r:36,fill:'#60a5fa'},g);A.el('path',{d:'M14 50 H86 M50 14 Q30 50 50 86 M50 14 Q70 50 50 86',fill:'none',stroke:'#dbeafe','stroke-width':4},g)},
};
A.ICONS=Object.keys(ICON);
A.icon=(parent,name,cx,cy,size)=>{const outer=A.g(parent);const g=A.g(outer,{transform:`translate(${cx-size/2} ${cy-size/2}) scale(${size/100})`});
  (ICON[name]||ICON.doc)(g);return outer};

/* ---------- characters ----------
   Flat vector person, origin = feet centre, ~430 units tall. Pose angles in degrees. */
const LOOKS={
 a:{skin:'#c68a5b',hair:'#1f1410',shirt:'#3b82f6',pants:'#1e293b',hairStyle:'short'},
 b:{skin:'#f1c7a1',hair:'#7c2d12',shirt:'#f97316',pants:'#334155',hairStyle:'long'},
 c:{skin:'#8d5524',hair:'#0f0f0f',shirt:'#10b981',pants:'#1f2937',hairStyle:'bun'},
 d:{skin:'#e0ac69',hair:'#3f3f46',shirt:'#a855f7',pants:'#111827',hairStyle:'short'},
};
const POSES={
 stand:{ls:8,le:6,rs:-8,re:-6,head:0},
 wave:{ls:8,le:6,rs:-150,re:-30,head:-4},
 phone:{ls:8,le:6,rs:22,re:128,head:12},
 point:{ls:8,le:6,rs:-95,re:0,head:-3},
 think:{ls:8,le:6,rs:18,re:150,head:-8},
 type:{ls:-28,le:-62,rs:28,re:62,head:8},
 cheer:{ls:150,le:20,rs:-150,re:-20,head:-6},
 read:{ls:-22,le:-80,rs:22,re:80,head:10},
};
A.POSES=Object.keys(POSES);
A.LOOKS=Object.keys(LOOKS);
function limb(parent,color,len1,len2,w){const upper=A.g(parent);A.el('rect',{x:-w/2,y:0,width:w,height:len1,rx:w/2,fill:color},upper);
  const lower=A.g(upper,{transform:`translate(0 ${len1-6})`});A.el('rect',{x:-w/2+2,y:0,width:w-4,height:len2,rx:(w-4)/2,fill:color},lower);
  const hand=A.el('circle',{cx:0,cy:len2,r:w/2+2},lower);return {upper,lower,hand}}
A.person=(parent,lookKey='a',opts={})=>{
  const L=Object.assign({},LOOKS[lookKey]||LOOKS.a,opts.look||{});
  const root=A.g(parent);const body=A.g(root);
  if(!opts.seated){A.el('rect',{x:-44,y:-200,width:36,height:200,rx:16,fill:L.pants},body);A.el('rect',{x:8,y:-200,width:36,height:200,rx:16,fill:L.pants},body);
    A.el('rect',{x:-50,y:-14,width:46,height:16,rx:8,fill:'#0f172a'},body);A.el('rect',{x:4,y:-14,width:46,height:16,rx:8,fill:'#0f172a'},body);}
  const torso=A.g(body,{transform:'translate(0 -200)'});
  const armL=A.g(torso,{transform:'translate(-58 -170)'});const armR=A.g(torso,{transform:'translate(58 -170)'});
  A.el('rect',{x:-66,y:-190,width:132,height:196,rx:44,fill:L.shirt},torso);
  const al=limb(armL,L.shirt,96,92,30);al.hand.setAttribute('fill',L.skin);
  const ar=limb(armR,L.shirt,96,92,30);ar.hand.setAttribute('fill',L.skin);
  // phone prop in right hand
  const prop=A.g(ar.lower,{transform:'translate(0 92)',opacity:0});A.el('rect',{x:-18,y:-36,width:36,height:62,rx:7,fill:'#0f172a'},prop);A.el('rect',{x:-14,y:-30,width:28,height:46,rx:3,fill:'#7bf1d0',opacity:.8},prop);
  torso.appendChild(armL);torso.appendChild(armR); // arms drawn above torso
  A.el('rect',{x:-16,y:-214,width:32,height:30,fill:L.skin},torso);
  const head=A.g(torso,{transform:'translate(0 -250)'});
  if(L.hairStyle==='long')A.el('path',{d:'M-58 0 Q-62 -66 0 -68 Q62 -66 58 0 L58 70 Q30 80 0 74 Q-30 80 -58 70 Z',fill:L.hair},head);
  A.el('circle',{cx:0,cy:0,r:56,fill:L.skin},head);
  if(L.hairStyle==='short')A.el('path',{d:'M-56 -6 Q-58 -62 0 -62 Q58 -62 56 -6 Q40 -34 0 -34 Q-40 -34 -56 -6 Z',fill:L.hair},head);
  if(L.hairStyle==='long')A.el('path',{d:'M-56 -4 Q-56 -60 0 -60 Q56 -60 56 -4 Q30 -30 -10 -36 Q-40 -30 -56 -4 Z',fill:L.hair},head);
  if(L.hairStyle==='bun'){A.el('circle',{cx:0,cy:-66,r:24,fill:L.hair},head);A.el('path',{d:'M-56 -6 Q-56 -60 0 -60 Q56 -60 56 -6 Q36 -30 0 -32 Q-36 -30 -56 -6 Z',fill:L.hair},head);}
  const eyes=A.g(head);const eL=A.el('ellipse',{cx:-20,cy:4,rx:6,ry:7,fill:'#111827'},eyes);const eR=A.el('ellipse',{cx:20,cy:4,rx:6,ry:7,fill:'#111827'},eyes);
  const mouth=A.el('path',{d:'M-16 26 Q0 38 16 26',fill:'none',stroke:'#7f1d1d','stroke-width':5,'stroke-linecap':'round'},head);
  const bubble=A.g(root,{transform:'translate(70 -560)',opacity:0});A.el('rect',{x:0,y:-60,width:300,height:90,rx:24,fill:'#fff'},bubble);
  A.el('path',{d:'M30 26 L10 60 L60 28 Z',fill:'#fff'},bubble);const btxt=A.text(bubble,150,-15,'',{fill:'#0f172a','font-size':34,'font-weight':800});
  const seed=opts.seed||1;
  /* s = {pose, prev, at, bubble, bubbleAt, emote} computed by the scene from its actions (pure function of t) */
  function update(t,s){
    const p=A.eInOut(A.prog(t,s.at,.45));const P0=POSES[s.prev]||POSES.stand,P1=POSES[s.pose]||POSES.stand;
    const ang=k=>A.lerp(P0[k],P1[k],p);
    let rs=ang('rs'),re=ang('re'),ls=ang('ls'),le=ang('le');
    if(s.pose==='type'){rs+=Math.sin(t*14)*4;ls+=Math.sin(t*14+1.7)*4}
    if(s.pose==='wave'){re+=Math.sin(t*9)*22}
    if(s.pose==='phone'){re+=Math.sin(t*6)*2}
    armL.setAttribute('transform',`translate(-58 -170) rotate(${ls})`);al.lower.setAttribute('transform',`translate(0 90) rotate(${le})`);
    armR.setAttribute('transform',`translate(58 -170) rotate(${rs})`);ar.lower.setAttribute('transform',`translate(0 90) rotate(${re})`);
    A.op(prop,s.pose==='phone'?p:(s.prev==='phone'?1-p:0));
    const breathe=1+Math.sin(t*2.2+seed)*.012;torso.setAttribute('transform',`translate(0 -200) scale(1 ${breathe})`);
    head.setAttribute('transform',`translate(0 -250) rotate(${ang('head')+Math.sin(t*1.3+seed)*1.5})`);
    const blink=((t+seed*.7)%3.7)<.12?.15:1;eL.setAttribute('ry',7*blink);eR.setAttribute('ry',7*blink);
    const look=s.pose==='phone'||s.pose==='read'||s.pose==='type'?6:0;eyes.setAttribute('transform',`translate(0 ${look})`);
    mouth.setAttribute('d',s.emote==='surprise'?'M-8 28 Q0 40 8 28 Q0 18 -8 28':s.emote==='neutral'?'M-14 30 L14 30':'M-16 26 Q0 38 16 26');
    if(s.bubble){btxt.textContent=s.bubble;const w=Math.max(220,Math.min(560,s.bubble.length*19+60));
      bubble.querySelector('rect').setAttribute('width',w);btxt.setAttribute('x',w/2);
      const bp=A.back(A.prog(t,s.bubbleAt,.35));bubble.setAttribute('transform',`translate(70 -560) scale(${Math.max(.01,bp)})`);A.op(bubble,1)}
    else A.op(bubble,0);
  }
  return {root,update};
};

/* ---------- settings (backdrops), drawn in a 1000x1000 box ---------- */
A.setting=(parent,kind,box)=>{const B=box||{x:0,y:0,w:1000,h:1000,r:44};const outer=A.g(parent);
  const id='clip'+(A._clip=(A._clip||0)+1);const cp=A.el('clipPath',{id},outer);A.el('rect',{x:B.x,y:B.y,width:B.w,height:B.h,rx:B.r??44},cp);
  const g=A.g(outer,{'clip-path':`url(#${id})`});
  if(kind==='office'){A.el('rect',{x:0,y:0,width:1000,height:700,fill:'#16213f'},g);A.el('rect',{x:0,y:700,width:1000,height:300,fill:'#0f1730'},g);
    A.el('rect',{x:640,y:110,width:250,height:180,rx:10,fill:'#1e2b52'},g);A.el('rect',{x:660,y:130,width:210,height:140,fill:'#2b3b6b'},g);
    A.el('circle',{cx:170,cy:180,r:62,fill:'#1e2b52'},g);A.el('path',{d:'M170 180 V140 M170 180 L198 196',stroke:'#7bf1d0','stroke-width':8,'stroke-linecap':'round'},g);
    A.el('rect',{x:60,y:420,width:120,height:280,rx:8,fill:'#1e2b52'},g);for(let i=0;i<3;i++)A.el('rect',{x:74,y:440+i*86,width:92,height:60,rx:4,fill:'#2b3b6b'},g);}
  else if(kind==='home'){A.el('rect',{x:0,y:0,width:1000,height:720,fill:'#1d2340'},g);A.el('rect',{x:0,y:720,width:1000,height:280,fill:'#141a33'},g);
    A.el('rect',{x:600,y:110,width:300,height:300,rx:8,fill:'#2c3d70'},g);A.el('rect',{x:616,y:126,width:268,height:268,fill:'#3d5a9e'},g);A.el('path',{d:'M750 126 V394 M616 260 H884',stroke:'#2c3d70','stroke-width':10},g);
    A.el('circle',{cx:820,cy:190,r:30,fill:'#f7bf75',opacity:.9},g);
    A.el('rect',{x:80,y:600,width:90,height:120,rx:10,fill:'#7c3a1d'},g);A.el('path',{d:'M125 600 Q70 520 100 470 Q130 520 125 600 Q150 500 190 480 Q170 560 125 600',fill:'#22c55e'},g);}
  else if(kind==='city'){A.el('rect',{x:0,y:0,width:1000,height:1000,fill:'#1a2347'},g);
    const r=A.rand(7);for(let i=0;i<9;i++){const w=80+r()*60,h=220+r()*360,x=i*115-20;A.el('rect',{x,y:760-h,width:w,height:h,fill:i%2?'#22305e':'#2a3a70'},g);
      for(let yy=780-h;yy<730;yy+=44)for(let xx=x+14;xx<x+w-20;xx+=30)if(r()>.35)A.el('rect',{x:xx,y:yy,width:14,height:20,fill:'#f7bf75',opacity:.55},g);}
    A.el('rect',{x:0,y:760,width:1000,height:240,fill:'#111833'},g);}
  return outer};

window.ART=A;
})();
