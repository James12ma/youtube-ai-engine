/* Built-in scene library. Every scene follows the same contract as AI-written scenes:
   scene(S) builds SVG under S.root (1000x1000) and returns update(t). Cues are named moments in
   the narration (S.at(name)). Cue names each scene understands are listed in studio/catalog.py. */
(function(){
const A=window.ART;const SC={};
const T=S=>Object.assign({bg:'#0b1021',ink:'#fff',accent:'#f7bf75',accent2:'#7bf1d0',danger:'#ff5a5f',ok:'#22c55e',muted:'#9fb3c8',paper:'#f8fafc',paperInk:'#0f172a',line:'#cbd5e1'},S.theme);
const pop=(t,at)=>A.back(A.prog(t,at,.4));
const cuesNamed=(S,prefix)=>S.cues.filter(c=>c.name===prefix||c.name.startsWith(prefix));

/* pointer used by UI scenes */
function cursor(parent){const g=A.g(parent);const ring=A.el('circle',{r:10,fill:'none',stroke:'#7bf1d0','stroke-width':5,opacity:0},g);
  A.el('path',{d:'M0 0 L0 46 L12 35 L21 56 L30 52 L21 32 L37 32 Z',fill:'#fff',stroke:'#0f172a','stroke-width':3},g);
  return {g,set(x,y,click){A.tf(g,x,y);if(click>0){A.set(ring,{r:10+click*32,opacity:(1-click)*.9})}else A.op(ring,0)}}}
/* path of a pointer through timed targets: [{at,x,y,click:bool}] */
function cursorAt(t,stops,home){let x=home[0],y=home[1],click=0;
  for(let i=0;i<stops.length;i++){const s=stops[i];const prev=i?stops[i-1]:{x:home[0],y:home[1],at:s.at-.8};
    const travel=Math.min(.6,Math.max(.2,s.at-prev.at-.1));const p=A.eInOut(A.prog(t,s.at-travel,travel));
    if(t>=s.at-travel){x=A.lerp(prev.x,s.x,p);y=A.lerp(prev.y,s.y,p)}
    if(s.click&&t>=s.at&&t<s.at+.45)click=A.prog(t,s.at,.45)}
  return [x,y,click]}

/* ---------- character: people in a setting doing things ----------
   params: setting (office|home|city|none), cast:[{look:a|b|c|d, x, pose, scale, seated}]
   cues: pose:<i>:<pose>  say:<i> (args.text)  emote:<i>:<smile|surprise|neutral>  prop:<i> (args.icon)  walk:<i> (args.to, args.dur) */
SC.character=S=>{const th=T(S);if(S.p.setting&&S.p.setting!=='none')A.setting(S.root,S.p.setting);
  const cast=(S.p.cast||[{look:'a'}]).map((c,i)=>{const n=S.p.cast?S.p.cast.length:1;const g=A.g(S.root);
    A.shadow(g,0,0,95,18);const pe=A.person(g,c.look||'abcd'[i%4],{seated:c.seated,seed:i+1});
    const prop=A.g(g,{opacity:0});return {c,g,pe,prop,x:c.x??(n==1?500:200+i*600/Math.max(1,n-1)),propIcon:null}});
  return t=>{cast.forEach((k,i)=>{
    const poses=S.cues.filter(c=>c.name.startsWith(`pose:${i}:`)&&c.at<=t);
    const pose=poses.length?poses[poses.length-1].name.split(':')[2]:(k.c.pose||'stand');
    const prev=poses.length>1?poses[poses.length-2].name.split(':')[2]:(k.c.pose||'stand');
    const at=poses.length?poses[poses.length-1].at:-10;
    const says=S.cues.filter(c=>c.name===`say:${i}`&&c.at<=t);const say=says.length?says[says.length-1]:null;
    const emo=S.cues.filter(c=>c.name.startsWith(`emote:${i}:`)&&c.at<=t);
    let x=k.x;S.cues.filter(c=>c.name===`walk:${i}`&&c.at<=t).forEach(c=>{const p=A.eInOut(A.prog(t,c.at,c.args.dur||1.2));x=A.lerp(x,c.args.to??x,p)});
    A.tf(k.g,x,930,k.c.scale||1);
    k.pe.update(t,{pose,prev:poses.length>1?prev:(k.c.pose||'stand'),at,bubble:say&&say.args.text,bubbleAt:say?say.at:0,emote:emo.length?emo[emo.length-1].name.split(':')[2]:'smile'});
    const pc=S.cues.filter(c=>c.name===`prop:${i}`&&c.at<=t).pop();
    if(pc){if(k.propIcon!==pc.args.icon){k.prop.innerHTML='';A.icon(k.prop,pc.args.icon||'doc',0,0,120);k.propIcon=pc.args.icon}
      const p=pop(t,pc.at);A.tf(k.prop,130,-520-Math.sin(t*3)*8,Math.max(.01,p));A.op(k.prop,1)}else A.op(k.prop,0);
  })}};

/* ---------- phone_app: a phone in hand, an app being used ----------
   params: app, fields:[{label,value}], button, success, look
   cues: open  type:<i> (args.dur)  tap  success  notify (args.text) */
SC.phone_app=S=>{const th=T(S);const f=S.p.fields||[{label:'Name',value:'Alex Rivera'}];
  const g=A.g(S.root);const skin=({a:'#c68a5b',b:'#f1c7a1',c:'#8d5524',d:'#e0ac69'})[S.p.look||'a'];
  A.shadow(g,500,960,260,26,.3);
  const ph=A.g(g);A.el('rect',{x:300,y:60,width:400,height:820,rx:56,fill:'#0f172a'},ph);A.el('rect',{x:318,y:78,width:364,height:784,rx:42,fill:'#f8fafc'},ph);
  A.el('rect',{x:440,y:92,width:120,height:26,rx:13,fill:'#0f172a'},ph);
  const scr=A.g(ph);A.el('rect',{x:318,y:130,width:364,height:90,fill:th.accent2},scr);A.text(scr,500,178,S.p.app||'Apply',{fill:'#0f172a','font-size':38,'font-weight':800});
  const rows=f.map((fd,i)=>{const y=270+i*120;const gg=A.g(scr);A.text(gg,345,y,fd.label,{fill:'#64748b','font-size':24,'text-anchor':'start'});
    const box=A.el('rect',{x:340,y:y+18,width:320,height:62,rx:12,fill:'#fff',stroke:'#cbd5e1','stroke-width':3},gg);
    const val=A.text(gg,358,y+50,'',{fill:'#0f172a','font-size':28,'text-anchor':'start','font-weight':700});const caret=A.el('rect',{x:0,y:y+32,width:3,height:34,fill:th.accent2},gg);return {fd,box,val,caret,y}});
  const by=270+f.length*120+20;const btn=A.g(scr);const bR=A.el('rect',{x:340,y:by,width:320,height:78,rx:39,fill:'#2563eb'},btn);A.text(btn,500,by+40,S.p.button||'Send',{'font-size':32,'font-weight':800});
  const ok=A.g(ph,{opacity:0});A.el('rect',{x:318,y:78,width:364,height:784,rx:42,fill:'#f8fafc'},ok);A.icon(ok,'check',500,390,200);A.text(ok,500,560,S.p.success||'Sent!',{fill:'#0f172a','font-size':42,'font-weight':800});
  const okSub=A.text(ok,500,612,S.p.success_detail||'',{fill:'#64748b','font-size':26});
  const note=A.g(g,{opacity:0});A.el('rect',{x:330,y:0,width:340,height:110,rx:24,fill:'#fff'},note);A.icon(note,'bell',380,55,60);const nt=A.text(note,420,55,'',{fill:'#0f172a','font-size':26,'text-anchor':'start','font-weight':700});
  const hand=A.g(g);A.el('path',{d:'M640 980 Q700 760 690 700 Q720 690 735 720 Q760 820 760 980 Z',fill:skin},hand);
  const thumb=A.g(g);A.el('ellipse',{cx:0,cy:0,rx:34,ry:46,fill:skin,stroke:'#0002','stroke-width':3},thumb);const tap=A.el('circle',{r:20,fill:'none',stroke:th.accent2,'stroke-width':6,opacity:0},g);
  return t=>{const enter=A.eOut(A.prog(t,S.at('open',0),.5));A.tf(ph,0,(1-enter)*120);A.op(ph,enter);
    let tx=760,ty=900;const stops=[];
    rows.forEach((r,i)=>{const at=S.at(`type:${i}`);const dur=S.args(`type:${i}`).dur||1.0;const p=A.prog(t,at,dur);
      const n=Math.round(p*r.fd.value.length);r.val.textContent=r.fd.value.slice(0,n);
      const active=t>=at&&t<at+dur+.3;A.set(r.box,{stroke:active?'#2563eb':'#cbd5e1'});
      const w=r.val.getComputedTextLength?r.val.getComputedTextLength():0;A.set(r.caret,{x:360+w,opacity:active&&Math.floor(t*3)%2==0?1:0});
      if(at<1e8)stops.push({at,x:600,y:r.y+50})});
    const tapAt=S.at('tap');if(tapAt<1e8)stops.push({at:tapAt,x:500,y:by+40});
    stops.sort((a,b)=>a.at-b.at);for(const s of stops){if(t>=s.at-.4){const p=A.eInOut(A.prog(t,s.at-.4,.4));tx=A.lerp(tx,s.x,p);ty=A.lerp(ty,s.y+40,p)}}
    A.tf(thumb,tx,ty+30);const press=A.pulse(t,tapAt,.35);A.tf(btn,500*(1-(1-press*.06)),(by+40)*(press*.06),1-press*.06);
    A.set(bR,{fill:t>=tapAt?'#16a34a':'#2563eb'});
    if(t>=tapAt&&t<tapAt+.45)A.set(tap,{cx:500,cy:by+40,r:20+A.prog(t,tapAt,.45)*60,opacity:1-A.prog(t,tapAt,.45)});else A.op(tap,0);
    const sAt=S.at('success');const sp=A.eOut(A.prog(t,sAt,.4));A.op(ok,sp);okSub.textContent=S.p.success_detail||'';
    const nAt=S.at('notify');if(t>=nAt){nt.textContent=S.args('notify').text||'New message';const p=A.back(A.prog(t,nAt,.45));A.tf(note,0,A.lerp(-120,110,p));A.op(note,1)}else A.op(note,0);
    A.op(thumb,t<(sAt<1e8?sAt:1e9)?1:0);A.op(hand,1)}};

/* ---------- transfer: something travels between places ----------
   params: nodes:[{icon,label}] (2-4), item:{icon,label}
   cues: send:<a>-<b> (args.dur)  arrive:<i>  light:<i> */
SC.transfer=S=>{const th=T(S);const nodes=S.p.nodes||[{icon:'phone',label:'You'},{icon:'building',label:'Company'}];const n=nodes.length;
  const pos=nodes.map((_,i)=>[n==1?500:170+i*660/(n-1),500+(i%2?-90:90)*(n>2?1:0)]);
  const paths=[];for(let i=0;i<n-1;i++){const [x1,y1]=pos[i],[x2,y2]=pos[i+1];const mx=(x1+x2)/2,my=Math.min(y1,y2)-200;
    const d=`M${x1} ${y1} Q${mx} ${my} ${x2} ${y2}`;A.el('path',{d,fill:'none',stroke:th.muted,'stroke-width':6,'stroke-dasharray':'4 18','stroke-linecap':'round',opacity:.6},S.root);
    paths.push(A.el('path',{d,fill:'none',stroke:'none'},S.root))}
  const ns=nodes.map((nd,i)=>{const g=A.g(S.root);const ring=A.el('circle',{cx:0,cy:0,r:110,fill:'none',stroke:th.accent2,'stroke-width':8,opacity:0},g);
    A.el('circle',{cx:0,cy:0,r:105,fill:'#1c2546'},g);A.icon(g,nd.icon||'doc',0,-6,130);A.text(g,0,160,nd.label||'',{'font-size':38,'font-weight':800,fill:th.ink});return {g,ring}});
  const item=A.g(S.root,{transform:`translate(${pos[0][0]} ${pos[0][1]})`});A.icon(item,(S.p.item&&S.p.item.icon)||'envelope',0,0,130);const itl=A.text(item,0,92,(S.p.item&&S.p.item.label)||'',{'font-size':30,fill:th.accent,'font-weight':800});
  return t=>{ns.forEach((k,i)=>{const p=pop(t,S.at(`light:${i}`,i*.15));A.tf(k.g,pos[i][0],pos[i][1],Math.max(.01,Math.min(1,p||1)));
      const ar=S.at(`arrive:${i}`);const q=A.prog(t,ar,.8);A.set(k.ring,{r:110+q*45,opacity:t>=ar&&q<1?(1-q):0})});
    let shown=false;cuesNamed(S,'send:').forEach(c=>{const [a,b]=c.name.slice(5).split('-').map(Number);const dur=c.args.dur||1.2;
      if(t>=c.at&&a<n-1+1&&b<n){const p=A.eInOut(A.prog(t,c.at,dur));const seg=Math.min(a,b);const path=paths[seg];if(!path)return;
        const L=path.getTotalLength();const pt=path.getPointAtLength((a<b?p:1-p)*L);A.tf(item,pt.x,pt.y,1+Math.sin(p*Math.PI)*.15);shown=true}});
    A.op(item,shown?1:0);if(!shown)A.tf(item,pos[0][0],pos[0][1])}};

/* ---------- inbox: someone receives and reviews items on a computer ----------
   params: look, title, items:[{from,subject}], detail:{title, lines:[]}, buttons:[..]
   cues: incoming:<i>  open:<i>  read  click:<j>  stamp (args.text) */
SC.inbox=S=>{const th=T(S);const items=S.p.items||[{from:'Alex Rivera',subject:'Application'}];
  A.setting(S.root,'office',{x:0,y:0,w:1000,h:450,r:40});const desk=A.g(S.root);
  const pe=A.person(desk,S.p.look||'b',{seated:true,seed:3});A.tf(pe.root,500,500,.56);
  A.el('rect',{x:150,y:372,width:700,height:34,rx:10,fill:'#5b3a29'},desk);A.el('path',{d:'M405 372 L420 290 H580 L595 372 Z',fill:'#cbd5e1'},desk);A.el('circle',{cx:500,cy:332,r:11,fill:'#94a3b8'},desk);
  const glow=A.el('ellipse',{cx:500,cy:250,rx:160,ry:60,fill:th.accent2,opacity:0},desk);
  const win=A.g(S.root);A.el('rect',{x:60,y:470,width:880,height:500,rx:24,fill:'#f8fafc'},win);A.el('rect',{x:60,y:470,width:880,height:64,rx:24,fill:'#e2e8f0'},win);
  ['#ef4444','#f59e0b','#22c55e'].forEach((c,i)=>A.el('circle',{cx:100+i*30,cy:502,r:9,fill:c},win));A.text(win,500,503,S.p.title||'Inbox',{fill:'#334155','font-size':28});
  const list=items.map((it,i)=>{const g=A.g(win);const bg=A.el('rect',{x:80,y:0,width:360,height:96,rx:14,fill:'#fff',stroke:'#e2e8f0','stroke-width':3},g);
    A.icon(g,'person',125,48,56);A.text(g,165,32,it.from||'',{fill:'#0f172a','font-size':24,'text-anchor':'start','font-weight':800});A.text(g,165,66,it.subject||'',{fill:'#64748b','font-size':21,'text-anchor':'start'});
    const badge=A.g(g);A.el('rect',{x:370,y:12,width:58,height:28,rx:14,fill:th.danger},badge);A.text(badge,399,27,'NEW',{'font-size':16,'font-weight':800});return {g,bg,badge}});
  const det=A.g(win,{opacity:0});const D=S.p.detail||{title:items[0].subject,lines:['Experience','Skills','Availability']};
  A.el('rect',{x:460,y:552,width:460,height:400,rx:16,fill:'#fff',stroke:'#e2e8f0','stroke-width':3},det);A.text(det,690,592,D.title||'',{fill:'#0f172a','font-size':28,'font-weight':800});
  const lines=(D.lines||[]).slice(0,5).map((ln,i)=>{const hl=A.el('rect',{x:478,y:622+i*52,width:424,height:42,rx:8,fill:th.accent,opacity:0},det);A.text(det,494,644+i*52,ln,{fill:'#334155','font-size':23,'text-anchor':'start'});return hl});
  const btns=(S.p.buttons||['Shortlist']).slice(0,2).map((b,j)=>{const g=A.g(det);const r=A.el('rect',{x:478+j*220,y:880,width:200,height:56,rx:28,fill:j?'#e2e8f0':'#2563eb'},g);A.text(g,578+j*220,909,b,{'font-size':24,'font-weight':800,fill:j?'#334155':'#fff'});return {r,x:578+j*220,y:908}});
  const stamp=A.g(win,{opacity:0,transform:'translate(690 760) rotate(-8)'});A.el('rect',{x:-150,y:-44,width:300,height:88,rx:12,fill:'none',stroke:th.ok,'stroke-width':8},stamp);const stt=A.text(stamp,0,2,'',{fill:th.ok,'font-size':40,'font-weight':800});
  const cur=cursor(S.root);
  return t=>{let slot=0;list.forEach((k,i)=>{const at=S.at(`incoming:${i}`,i==0?0:1e9);const p=A.eOut(A.prog(t,at,.45));
      if(t<at){A.op(k.g,0);return}A.op(k.g,p);k.g.setAttribute('transform',`translate(${(1-p)*-60} ${552+slot*108})`);slot++;
      A.op(k.badge,t<S.at(`open:${i}`)?1:0);const sel=t>=S.at(`open:${i}`);A.set(k.bg,{stroke:sel?'#2563eb':'#e2e8f0'})});
    const oi=list.findIndex((_,i)=>t>=S.at(`open:${i}`));const oAt=oi>=0?S.at(`open:${oi}`):1e9;
    A.op(det,A.eOut(A.prog(t,oAt+.15,.35)));
    const rAt=S.at('read');lines.forEach((hl,i)=>{const p=A.prog(t,rAt+i*.45,.45);A.op(hl,t>=rAt?(p<1?.55*Math.sin(p*Math.PI)+.15:.15):0)});
    const stops=[];if(oAt<1e8)stops.push({at:oAt,x:260,y:552+48,click:true});
    btns.forEach((b,j)=>{const c=S.at(`click:${j}`);if(c<1e8){stops.push({at:c,x:b.x,y:b.y,click:true});A.set(b.r,{fill:t>=c?th.ok:(j?'#e2e8f0':'#2563eb')})}});
    const [x,y,cl]=cursorAt(t,stops.sort((a,b)=>a.at-b.at),[880,940]);cur.set(x,y,cl);
    const sa=S.at('stamp');if(t>=sa){stt.textContent=S.args('stamp').text||'APPROVED';A.op(stamp,1);stamp.setAttribute('transform',`translate(690 760) rotate(-8) scale(${A.lerp(1.6,1,A.eOut(A.prog(t,sa,.3)))})`)}else A.op(stamp,0);
    const pose=t>=rAt&&t<rAt+2.2?'read':(oAt<1e8&&t>=oAt-.5?'type':'stand');pe.update(t,{pose,prev:'stand',at:0,emote:t>=sa?'smile':'neutral'});
    const ia=Math.min(...list.map((_,i)=>S.at(`incoming:${i}`,1e9)).filter(x=>x>0.05),1e9);A.op(glow,t>=ia?.25*A.pulse(t,ia,1.0):0)}};

/* ---------- ui: a software window operated with a mouse ----------
   params: title, elements:[{id,type:heading|text|input|button|toggle|item, label, value}]
   cues: click:<id>  type:<id> (args.text, args.dur)  toggle:<id>  highlight:<id> */
SC.ui=S=>{const th=T(S);const els=S.p.elements||[];const win=A.g(S.root);
  A.el('rect',{x:40,y:80,width:920,height:840,rx:26,fill:'#f8fafc'},win);A.el('rect',{x:40,y:80,width:920,height:70,rx:26,fill:'#e2e8f0'},win);
  ['#ef4444','#f59e0b','#22c55e'].forEach((c,i)=>A.el('circle',{cx:84+i*32,cy:115,r:10,fill:c},win));A.text(win,500,116,S.p.title||'App',{fill:'#334155','font-size':30});
  let y=200;const map={};
  els.forEach(e=>{const g=A.g(win);const k={e,g,y};
    if(e.type==='heading'){A.text(g,90,y+10,e.label,{fill:'#0f172a','font-size':44,'font-weight':800,'text-anchor':'start'});y+=80}
    else if(e.type==='text'){A.text(g,90,y,e.label,{fill:'#475569','font-size':28,'text-anchor':'start'});y+=60}
    else if(e.type==='input'){A.text(g,90,y,e.label,{fill:'#64748b','font-size':24,'text-anchor':'start'});k.box=A.el('rect',{x:90,y:y+20,width:820,height:70,rx:14,fill:'#fff',stroke:'#cbd5e1','stroke-width':3},g);
      k.val=A.text(g,112,y+56,e.value||'',{fill:'#0f172a','font-size':30,'text-anchor':'start','font-weight':700});k.cx=500;k.cy=y+55;y+=125}
    else if(e.type==='toggle'){A.text(g,90,y+20,e.label,{fill:'#0f172a','font-size':30,'text-anchor':'start'});k.track=A.el('rect',{x:800,y:y-6,width:110,height:54,rx:27,fill:'#cbd5e1'},g);k.knob=A.el('circle',{cx:827,cy:y+21,r:22,fill:'#fff'},g);k.cx=855;k.cy=y+21;y+=90}
    else if(e.type==='item'){k.bg=A.el('rect',{x:90,y:y-10,width:820,height:80,rx:14,fill:'#fff',stroke:'#e2e8f0','stroke-width':3},g);A.text(g,120,y+30,e.label,{fill:'#0f172a','font-size':28,'text-anchor':'start','font-weight':700});
      if(e.value)A.text(g,880,y+30,e.value,{fill:'#64748b','font-size':26,'text-anchor':'end'});k.cx=500;k.cy=y+30;y+=96}
    else {k.btn=A.el('rect',{x:90,y:y,width:820,height:84,rx:42,fill:'#2563eb'},g);A.text(g,500,y+43,e.label,{'font-size':32,'font-weight':800});k.cx=500;k.cy=y+42;y+=120}
    map[e.id]=k});
  const cur=cursor(S.root);
  return t=>{const stops=[];
    els.forEach(e=>{const k=map[e.id];['click','type','toggle'].forEach(v=>{const at=S.at(`${v}:${e.id}`);if(at<1e8&&k.cx)stops.push({at,x:k.cx,y:k.cy,click:v!=='type'})});
      const ta=S.at(`type:${e.id}`);if(k.val&&ta<1e8){const a=S.args(`type:${e.id}`);const txt=a.text??e.value??'';const p=A.prog(t,ta,a.dur||1.2);k.val.textContent=t>=ta?txt.slice(0,Math.round(p*txt.length)):(e.value&&a.text?e.value:'');A.set(k.box,{stroke:t>=ta&&p<1?'#2563eb':'#cbd5e1'})}
      const og=S.at(`toggle:${e.id}`);if(k.track){const on=t>=og;const p=A.eOut(A.prog(t,og,.25));A.set(k.track,{fill:on?th.ok:'#cbd5e1'});A.set(k.knob,{cx:on?A.lerp(827,883,p):827})}
      const ca=S.at(`click:${e.id}`);if(k.btn)A.set(k.btn,{fill:t>=ca?th.ok:'#2563eb'});if(k.bg)A.set(k.bg,{stroke:t>=ca?'#2563eb':'#e2e8f0'});
      const ha=S.at(`highlight:${e.id}`);A.op(k.g,1);if(t>=ha&&t<ha+1.2)k.g.setAttribute('transform',`translate(0 0) scale(1)`)});
    const [x,y,c]=cursorAt(t,stops.sort((a,b)=>a.at-b.at),[900,900]);cur.set(x,y,c)}};

/* ---------- table: rows with a status column (spreadsheets, lists, logs) ----------
   params: columns:[..], rows:[[..]], status:[..] (OK|ERROR|CHECK|''), title
   cues: row:<i>  status:<i> (args.value)  highlight:<i>  callout (args.text, args.row) */
SC.table=S=>{const th=T(S);const cols=S.p.columns||['Item','Amount','Status'];const rows=S.p.rows||[];const st=S.p.status||[];
  const card=A.g(S.root);const top=120,rh=104,x0=40,x1=960;const n=rows.length;
  A.el('rect',{x:x0,y:top,width:x1-x0,height:110+n*rh,rx:28,fill:th.paper},card);
  const cw=(x1-x0-60)/cols.length;cols.forEach((c,j)=>A.text(card,x0+30+j*cw,top+55,c,{fill:'#475569','font-size':40,'text-anchor':'start','font-weight':700}));
  const R=rows.map((r,i)=>{const g=A.g(card);const y=top+110+i*rh;const bg=A.el('rect',{x:x0,y,width:x1-x0,height:rh,fill:'#fde2e1',opacity:0},g);const bar=A.el('rect',{x:x0,y,width:12,height:rh,fill:th.danger,opacity:0},g);
    A.el('line',{x1:x0,x2:x1,y1:y,y2:y,stroke:'#cbd5e1','stroke-width':3},g);
    const tx=r.map((v,j)=>A.text(g,x0+30+j*cw,y+rh/2,String(v),{fill:'#0f172a','font-size':44,'text-anchor':'start','font-weight':500}));
    const chip=A.g(g);const cr=A.el('rect',{x:0,y:-28,width:120,height:56,rx:12},chip);const ct=A.text(chip,60,1,'',{'font-size':32,'font-weight':800});
    chip.setAttribute('transform',`translate(${x0+30+(cols.length-1)*cw} ${y+rh/2})`);return {g,bg,bar,tx,chip,cr,ct,y}});
  const call=A.g(S.root,{opacity:0});const cb=A.el('rect',{x:-300,y:0,width:600,height:84,rx:18,fill:th.accent},call);A.el('path',{d:'M-30 0 L30 0 L0 -44 Z',fill:th.accent},call);const ctx=A.text(call,0,43,'',{fill:'#0b1021','font-size':34,'font-weight':800});
  const colors={OK:['#dcfce7','#15803d'],ERROR:['#b91c1c','#fff'],CHECK:['#fef3c7','#b45309']};
  return t=>{R.forEach((k,i)=>{const at=S.at(`row:${i}`,0);const p=A.eOut(A.prog(t,at,.35));A.op(k.g,t>=at?p:0);k.g.setAttribute('transform',`translate(${(1-p)*40} 0)`);
      const sc=S.cues.filter(c=>c.name===`status:${i}`&&c.at<=t).pop();const v=sc?sc.args.value:(st[i]||'');
      if(v){const [bg,fg]=colors[v]||colors.CHECK;A.set(k.cr,{fill:bg,width:v.length*24+40});A.set(k.ct,{fill:fg,x:(v.length*24+40)/2});k.ct.textContent=v;A.op(k.chip,1);
        const sp=sc?A.back(A.prog(t,sc.at,.35)):1;k.chip.setAttribute('transform',`translate(${x0+30+(cols.length-1)*cw} ${k.y+rh/2}) scale(${Math.max(.01,sp)})`)}else A.op(k.chip,0);
      const err=v==='ERROR';A.op(k.bg,err?1:0);A.op(k.bar,err?1:0);k.tx.forEach((e,j)=>A.set(e,{fill:err&&j==1?'#b91c1c':'#0f172a'}));
      const hl=S.at(`highlight:${i}`);if(t>=hl)A.op(k.bg,Math.max(err?1:0,.5+.3*Math.sin((t-hl)*6)))});
    const ca=S.at('callout');if(t>=ca){const a=S.args('callout');ctx.textContent=a.text||'';const w=Math.max(300,(a.text||'').length*19+60);A.set(cb,{x:-w/2,width:w});
      const r=R[a.row??n-1];const y=(r?r.y+rh:top+110+n*rh)+50;call.setAttribute('transform',`translate(${a.x??500} ${y}) scale(${Math.max(.01,A.back(A.prog(t,ca,.4)))})`);A.op(call,1)}else A.op(call,0)}};

/* ---------- bars: animated bar chart (only real, sourced numbers) ----------
   params: labels, values, unit, max   cues: grow (args.dur)  highlight:<i> */
SC.bars=S=>{const th=T(S);const L=S.p.labels||[];const V=S.p.values||[];const mx=S.p.max||Math.max(...V,1);const n=V.length;
  const bw=Math.min(150,760/Math.max(1,n)-30);const bars=V.map((v,i)=>{const x=120+i*(800/n)+((800/n)-bw)/2;const g=A.g(S.root);
    const r=A.el('rect',{x,y:860,width:bw,height:0,rx:10,fill:th.accent2},g);const vt=A.text(g,x+bw/2,0,'',{'font-size':38,'font-weight':800,fill:th.ink});
    A.text(g,x+bw/2,910,L[i]||'',{'font-size':30,fill:th.muted});return {r,vt,v,x}});
  A.el('line',{x1:90,x2:930,y1:860,y2:860,stroke:th.muted,'stroke-width':4},S.root);
  return t=>{const g0=S.at('grow',.2);const dur=S.args('grow').dur||1.4;bars.forEach((b,i)=>{const p=A.eOut(A.prog(t,g0+i*.12,dur));const h=b.v/mx*640*p;
    A.set(b.r,{y:860-h,height:h});b.vt.setAttribute('y',830-h);b.vt.textContent=p>0?(Math.round(b.v*p*10)/10)+(S.p.unit||''):'';
    const hl=S.at(`highlight:${i}`);A.set(b.r,{fill:t>=hl?th.accent:th.accent2})})}};

/* ---------- number: a big counting figure ----------  params: value, prefix, suffix, label, decimals  cues: count (args.dur) */
SC.number=S=>{const th=T(S);const v=+S.p.value||0;const d=S.p.decimals||0;
  const big=A.text(S.root,500,470,'',{'font-size':240,'font-weight':800,fill:th.accent});const lab=A.text(S.root,500,640,S.p.label||'',{'font-size':46,fill:th.ink,'font-weight':700});
  return t=>{const p=A.eOut(A.prog(t,S.at('count',.1),S.args('count').dur||1.4));big.textContent=(S.p.prefix||'')+(v*p).toFixed(d).replace(/\B(?=(\d{3})+(?!\d))/g,',')+(S.p.suffix||'');
    A.op(lab,A.prog(t,S.at('count',.1)+.3,.4))}};

/* ---------- steps: ordered checklist / process ----------  params: items  cues: step:<i> */
SC.steps=S=>{const th=T(S);const it=S.p.items||[];const n=it.length;const gap=Math.min(170,820/Math.max(1,n));
  const R=it.map((s,i)=>{const g=A.g(S.root);const y=120+i*gap;A.el('rect',{x:60,y,width:880,height:gap-30,rx:24,fill:'#1c2546'},g);
    const c=A.el('circle',{cx:140,cy:y+(gap-30)/2,r:42,fill:'#334155'},g);const num=A.text(g,140,y+(gap-30)/2,String(i+1),{'font-size':40,'font-weight':800});
    const ck=A.g(g,{opacity:0});A.icon(ck,'check',140,y+(gap-30)/2,92);A.text(g,215,y+(gap-30)/2,s,{'font-size':Math.min(46,1300/Math.max(18,s.length)),'text-anchor':'start','font-weight':700,fill:th.ink});return {g,ck,num}});
  return t=>{R.forEach((k,i)=>{const at=S.at(`step:${i}`,i*.4);const p=A.eOut(A.prog(t,at,.35));A.op(k.g,t>=at?p:.25);k.g.setAttribute('transform',`translate(${(1-p)*30} 0)`);
    const done=S.at(`done:${i}`);A.op(k.ck,t>=done?1:0);A.op(k.num,t>=done?0:1)})}};

/* ---------- icons: a row/grid of concepts that pop in ----------  params: items:[{icon,label}]  cues: pop:<i>  focus:<i> */
SC.icons=S=>{const th=T(S);const it=S.p.items||[];const n=it.length;const cols=n<=3?n:2;const rows=Math.ceil(n/cols);
  const R=it.map((x,i)=>{const g=A.g(S.root);const cx=cols==1?500:180+(i%cols)*(640/(cols-1));const cy=rows==1?470:220+Math.floor(i/cols)*(600/Math.max(1,rows-1));
    const ring=A.el('circle',{cx:0,cy:0,r:120,fill:'#1c2546',stroke:th.accent2,'stroke-width':0},g);A.icon(g,x.icon||'star',0,-8,150);A.text(g,0,175,x.label||'',{'font-size':38,'font-weight':800,fill:th.ink});return {g,ring,cx,cy}});
  return t=>{R.forEach((k,i)=>{const p=pop(t,S.at(`pop:${i}`,i*.3));const f=S.at(`focus:${i}`);const fo=t>=f?1:0;
    k.g.setAttribute('transform',`translate(${k.cx} ${k.cy+Math.sin(t*2+i)*6}) scale(${Math.max(.01,p)*(1+fo*.08)})`);A.set(k.ring,{'stroke-width':fo*10})})}};

/* ---------- compare: two sides (before/after, wrong/right) ----------  params: left:{title,icon,lines,tone}, right:{...}  cues: left right verdict (args.text) */
SC.compare=S=>{const th=T(S);const side=(d,x,cue)=>{const g=A.g(S.root);const tone=d.tone==='bad'?th.danger:th.ok;
    A.el('rect',{x:x,y:100,width:440,height:760,rx:30,fill:'#1c2546',stroke:tone,'stroke-width':6},g);A.icon(g,d.icon||(d.tone==='bad'?'cross':'check'),x+220,260,170);
    A.text(g,x+220,420,d.title||'',{'font-size':46,'font-weight':800,fill:tone});(d.lines||[]).slice(0,4).forEach((l,i)=>A.text(g,x+220,510+i*70,l,{'font-size':32,fill:th.ink}));return {g,cue}};
  const L=side(S.p.left||{title:'Before',tone:'bad'},40,'left'),R=side(S.p.right||{title:'After',tone:'good'},520,'right');
  const v=A.g(S.root,{opacity:0});A.el('rect',{x:200,y:900,width:600,height:90,rx:45,fill:th.accent},v);const vt=A.text(v,500,946,'',{fill:'#0b1021','font-size':38,'font-weight':800});
  return t=>{[L,R].forEach((k,i)=>{const p=A.eOut(A.prog(t,S.at(k.cue,i*.5),.4));A.op(k.g,p);k.g.setAttribute('transform',`translate(0 ${(1-p)*50})`)});
    const va=S.at('verdict');if(t>=va){vt.textContent=S.args('verdict').text||'';A.op(v,A.prog(t,va,.3))}else A.op(v,0)}};

/* ---------- question: end card asking the viewer ----------  params: question, options:[..]  cues: options */
SC.question=S=>{const th=T(S);const q=S.p.question||'What would you do?';const words=q.split(' ');const lines=[];let cur='';words.forEach(w=>{if((cur+' '+w).trim().length>16){lines.push(cur.trim());cur=w}else cur+=' '+w});lines.push(cur.trim());
  lines.forEach((l,i)=>A.text(S.root,500,280+i*110,l.toUpperCase(),{'font-size':92,'font-weight':800,fill:i==lines.length-1?th.accent:th.ink}));
  const opts=(S.p.options||['YES','NO']).slice(0,2).map((o,i)=>{const g=A.g(S.root);A.el('rect',{x:-180,y:-55,width:360,height:110,rx:30,fill:i?th.danger:th.ok},g);A.text(g,0,2,o,{'font-size':54,'font-weight':800});return g});
  return t=>{opts.forEach((g,i)=>{const p=pop(t,S.at('options',.6)+i*.15);g.setAttribute('transform',`translate(${290+i*420} ${760+Math.sin(t*3+i)*6}) scale(${Math.max(.01,p)})`)})}};

/* ---------- title: big statement ----------  params: kicker, text, accent_words:[..], icon */
SC.title=S=>{const th=T(S);const words=(S.p.text||'').split(' ');const acc=new Set((S.p.accent_words||[]).map(w=>w.toLowerCase()));
  const lines=[];let cur=[];words.forEach(w=>{if(cur.join(' ').length+w.length>13&&cur.length){lines.push(cur);cur=[w]}else cur.push(w)});if(cur.length)lines.push(cur);
  const g=A.g(S.root);if(S.p.icon)A.icon(g,S.p.icon,500,180,190);
  const L=lines.map((ln,i)=>{const t=A.el('text',{x:500,y:430+i*130,'font-family':'InterTight','font-weight':800,'font-size':120,'text-anchor':'middle'},g);
    ln.forEach((w,j)=>{const s=A.el('tspan',{fill:acc.has(w.toLowerCase().replace(/[^a-z0-9']/g,''))?th.accent:th.ink},t);s.textContent=(j?' ':'')+w.toUpperCase()});return t});
  if(S.p.kicker)A.text(g,500,330,S.p.kicker,{'font-size':36,fill:th.accent2,'font-weight':700});
  return t=>{L.forEach((e,i)=>{const p=A.eOut(A.prog(t,.08+i*.12,.45));A.op(e,p);e.setAttribute('transform',`translate(0 ${(1-p)*40})`)})}};

window.SCENES=SC;
})();
