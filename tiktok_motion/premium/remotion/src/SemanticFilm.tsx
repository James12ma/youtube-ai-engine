/** Original procedural vector film. Persistent assets; native-word-timed actions. */
import React from 'react';
import {AbsoluteFill,Audio,Sequence,staticFile,useCurrentFrame,interpolate} from 'remotion';
import type {OwnerPlan} from './OwnerPremium';
const clamp=(x:number)=>Math.max(0,Math.min(1,x));
const smooth=(x:number)=>{const t=clamp(x);return t*t*(3-2*t);};
const mix=(a:number,b:number,t:number)=>a+(b-a)*t;
const W=1080,H=1550;
const C={ink:'#203b4b',teal:'#52d8be',gold:'#edb966',paper:'#f4eddf',blue:'#365c8e'};
const Defs=()=> <defs>
 <linearGradient id="wall" x2="0" y2="1"><stop stopColor="#e7eee8"/><stop offset="1" stopColor="#c7d6ce"/></linearGradient>
 <linearGradient id="night" x2="0" y2="1"><stop stopColor="#111f39"/><stop offset="1" stopColor="#254a5a"/></linearGradient>
 <linearGradient id="wood"><stop stopColor="#d7a479"/><stop offset="1" stopColor="#ae7654"/></linearGradient>
 <linearGradient id="case"><stop stopColor="#5c7585"/><stop offset=".15" stopColor="#263c4f"/><stop offset="1" stopColor="#142834"/></linearGradient>
 <linearGradient id="glass" x2=".8" y2="1"><stop stopColor="#ffffff"/><stop offset="1" stopColor="#e7eff1"/></linearGradient>
 <radialGradient id="lamp"><stop stopColor="#fff2bc" stopOpacity=".45"/><stop offset="1" stopColor="#fff2bc" stopOpacity="0"/></radialGradient>
 <filter id="shadow" x="-60%" y="-60%" width="220%" height="240%"><feGaussianBlur stdDeviation="12"/></filter>
 <pattern id="officeWindows" width="46" height="65" patternUnits="userSpaceOnUse"><rect x="8" y="10" width="24" height="40" rx="3" fill="#b5e6db" opacity=".6"/></pattern>
 </defs>;
const Text:React.FC<{x:number;y:number;size?:number;fill?:string;children:React.ReactNode;anchor?:'middle'|'start'|'end';weight?:number}>=({x,y,size=22,fill=C.ink,children,anchor='start',weight=600})=><text x={x} y={y} fontSize={size} fill={fill} textAnchor={anchor} fontWeight={weight} fontFamily="InterTight,Arial,sans-serif">{children}</text>;
const Check:React.FC<{x:number;y:number;on?:boolean;size?:number}>=({x,y,on=true,size=1})=><g transform={`translate(${x},${y}) scale(${size})`} opacity={on?1:.2}><circle r="13" fill={C.teal}/><path d="M-6 0 L-1 5 L7 -5" fill="none" stroke="#153d38" strokeWidth="3" strokeLinecap="round"/></g>;
const Plant:React.FC<{x:number;y:number;s?:number;f:number}>=({x,y,s=1,f})=><g transform={`translate(${x},${y}) scale(${s})`}>
 <path d="M-36 0 L-25 66 Q0 82 25 66 L36 0" fill="#bd7e61"/><ellipse rx="36" ry="12" fill="#e9b692"/>
 <g transform={`rotate(${Math.sin(f/60)*1.8})`}><path d="M0 0 Q-3 -80 8 -145" stroke="#436c58" strokeWidth="7" fill="none"/>
 {[-1,1].map((v,i)=><g key={v}><path d={`M0 -65 Q${v*105} -145 ${v*100} -45 Q${v*45} -18 0 -65`} fill={i?'#6d9d73':'#4c7c61'}/><path d={`M4 -120 Q${v*66} -205 ${v*66} -105 Q${v*30} -82 4 -120`} fill={i?'#91b28a':'#527d64'}/></g>)}</g></g>;
const Person:React.FC<{x:number;y:number;id:'candidate'|'recruiter';f:number;world:any;reach?:number;close?:boolean}>=({x,y,id,f,world,reach=0})=>{
 const a=world[id],breath=Math.sin(f/33)*2,blink=f%145>139;
 return <g transform={`translate(${x},${y+breath})`}>
 <ellipse cy="345" rx="160" ry="27" fill="#203b4b" opacity=".1"/>
 <path d="M-100 82 Q-145 100 -145 264 L140 264 Q140 110 92 82 L45 65 L-45 65Z" fill={a.shirt}/>
 <path d="M-12 103 L0 250 L25 103 L0 128Z" fill="#fff" opacity=".6"/><path d="M-48 67 L-12 103 L-46 141 L-87 82 M48 67 L25 103 L56 143 L95 82" fill="none" stroke="#162c3d" opacity=".3" strokeWidth="4"/>
 <rect x="-31" y="26" width="62" height="65" rx="18" fill={a.skin}/>
 <path d="M-72 -125 Q0 -185 72 -112 L70 -28 Q55 52 0 55 Q-56 43 -73 -29Z" fill={a.skin}/>
 <ellipse cx="-74" cy="-45" rx="14" ry="23" fill={a.skin}/><ellipse cx="74" cy="-45" rx="14" ry="23" fill={a.skin}/>
 <path d="M-76 -62 Q-98 -159 -38 -169 Q12 -190 59 -154 Q94 -145 79 -57 L58 -102 Q12 -94 -22 -139 L-57 -89Z" fill={a.hair}/>
 <path d="M-49 -69 Q-31 -78 -15 -68 M18 -68 Q37 -77 51 -64" fill="none" stroke={a.hair} strokeWidth="6" strokeLinecap="round"/>
 {[-31,35].map(v=><g key={v}><ellipse cx={v} cy="-48" rx="11" ry={blink?1:8} fill="#fff"/><ellipse cx={v+4} cy="-48" rx="4.5" ry={blink?1:5.5} fill="#20303a"/></g>)}
 <path d="M7 -42 L13 -8 L2 -6" stroke="#8d5a44" strokeWidth="3" fill="none" strokeLinecap="round"/>
 <path d={`M-20 18 Q0 ${24+Math.sin(f/30)*2} 22 13`} stroke="#784c43" strokeWidth="4" fill="none" strokeLinecap="round"/>
 <path d="M-108 116 Q-152 165 -112 210 L-35 214" fill="none" stroke={a.skin} strokeWidth="31" strokeLinecap="round"/>
 <path d={`M105 121 Q${155+reach*80} ${163-reach*15} ${137+reach*180} ${204-reach*5}`} fill="none" stroke={a.skin} strokeWidth="31" strokeLinecap="round"/>
 <path d={`M${137+reach*180} ${204-reach*5} l22 -7`} stroke={a.skin} strokeWidth="16" strokeLinecap="round"/>
 </g>;
};
const Phone:React.FC<{x:number;y:number;f:number;state:string;tap?:number;scale?:number;id?:string}>=({x,y,f,state,tap=0,scale=1,id='APP-042'})=>{
 const received=['received','review','invited','invitation_received'].includes(state),sent=state==='sent';
 return <g transform={`translate(${x},${y}) scale(${scale})`}>
 <ellipse cx="70" cy="285" rx="81" ry="17" fill="#183447" opacity=".18" filter="url(#shadow)"/>
 <rect width="140" height="270" rx="23" fill="url(#case)" stroke="#9eb6bb" strokeWidth="2"/>
 <rect x="7" y="8" width="126" height="253" rx="18" fill="url(#glass)"/>
 <rect x="47" y="13" width="46" height="9" rx="5" fill="#1b303e"/><circle cx="104" cy="27" r="2" fill="#5a8c7e"/>
 <Text x={17} y={46} size={8} fill="#647c85">EXAMPLE STUDIO · DEMO</Text>
 <Text x={17} y={67} size={13} weight={800}>{state==='invitation_received'?'Interview invitation':received?'New application':'Job application'}</Text>
 <Text x={17} y={83} size={9} fill="#65818b">{id} · FICTIONAL</Text>
 <rect x="16" y="96" width="108" height="68" rx="9" fill={received?'#d8ece8':'#e7edf0'}/>
 {state==='review'?<><Text x={25} y={112} size={9}>Application reviewed</Text><Text x={25} y={128} size={8}>Skills · project examples</Text><Check x={105} y={148} size={.45}/></>:<><path d="M28 109 H91 M28 120 H106 M28 131 H85 M28 142 H98" stroke="#9eb6bd" strokeWidth="3" strokeLinecap="round"/><Text x={26} y={157} size={7}>{received?'Tap to open application':'CV and project examples'}</Text></>}
 <rect x="16" y="179" width="108" height="36" rx="10" fill={state==='draft'?'#2e7977':C.teal}/>
 <Text x={70} y={201} size={12} anchor="middle" fill="#153d38" weight={850}>{({draft:'Send application',sending:'Sending…',sent:'Sent ✓',received:'Notification',review:'Invite to interview',invited:'Invitation sent ✓',invitation_received:'Open invitation'} as Record<string,string>)[state]||'Application'}</Text>
 <Text x={70} y={237} size={8} anchor="middle" fill="#6c8189">{sent?'Sent from applicant device':received?'Recruiter device':'Illustrative interface'}</Text>
 <rect x="49" y="249" width="42" height="3" rx="2" fill="#9cafb3"/>
 {tap>0&&tap<1&&<circle cx="95" cy="196" r={8+tap*34} fill="none" stroke={C.gold} strokeWidth={3*(1-tap)} opacity={1-tap}/>}
 {state==='sending'&&<circle cx="119" cy="67" r="4" fill={C.gold} opacity={.5+.5*Math.sin(f/3)}/>}
 </g>;
};
const Laptop:React.FC<{x:number;y:number;f:number;review?:boolean;progress:number}>=({x,y,f,review=false,progress})=><g transform={`translate(${x},${y})`}>
 <path d="M0 0 H260 Q274 0 274 14 V182 H-14 V14 Q-14 0 0 0" fill="#334c5b"/>
 <rect x="0" y="12" width="260" height="157" rx="4" fill="#f8faf7"/>
 <rect x="0" y="12" width="260" height="22" fill="#dbe8e7"/><circle cx="12" cy="23" r="3" fill="#ce8b6c"/><circle cx="23" cy="23" r="3" fill="#d7b368"/><circle cx="34" cy="23" r="3" fill="#82b79e"/>
 <Text x={18} y={56} size={12} weight={850}>EXAMPLE STUDIO</Text><Text x={18} y={76} size={10}>{review?'APP-042 · FICTIONAL CV':'Open role · fictional listing'}</Text>
 {[0,1,2].map(i=><g key={i} opacity={progress>i/4?1:.15}><rect x="20" y={91+i*22} width={130+i*16} height="5" rx="2" fill="#a4bab9"/><Check x={226} y={93+i*22} size={.4}/></g>)}
 <path d="M-14 182 H274 L305 210 H-45Z" fill="#8198a2"/><path d="M-20 190 H280 M-5 197 H264" stroke="#5d7480" strokeWidth="3"/><rect x="103" y="199" width="50" height="7" rx="3" fill="#b1c1c5"/>
 </g>;
const Room:React.FC<{office:boolean;f:number;world:any;phase:string;tap:number;reach:number}>=({office,f,world,phase,tap,reach})=><g>
 <rect x="-1500" y="-1500" width="4000" height="4300" fill="url(#wall)"/>
 <path d="M0 1250 H1080 V1700 H0Z" fill={office?'#bdcecc':'#d2b99d'}/>
 <path d="M0 1250 L1080 1250 M150 1250 L50 1600 M430 1250 L390 1600 M710 1250 L760 1600 M960 1250 L1120 1600" stroke="#a6ada2" strokeWidth="3" opacity=".4"/>
 <g transform="translate(80,290)"><rect width="420" height="390" rx="5" fill="#779fa8"/><rect x="15" y="15" width="390" height="360" fill="#d8e9e5"/>
 {[0,1,2,3,4].map(i=><g key={i} transform={`translate(${i*83-20},${155-i%3*40})`}><rect width="75" height={220+i%3*40} fill={office?'#93b6b8':'#b9ceca'}/><path d="M15 20 V175 M38 20 V175 M60 20 V175" stroke="#d6e3de" strokeWidth="8" strokeDasharray="16 15"/></g>)}
 <path d="M210 0 V390 M0 190 H420" stroke="#f5f2e8" strokeWidth="13"/><path d="M-10 -15 H440" stroke="#627d82" strokeWidth="10"/>
 <path d="M5 390 L390 390 L690 890 L160 890Z" fill="#ffffdc" opacity=".2"/></g>
 <g transform="translate(750,330)"><rect width="205" height="200" fill="#e9e3d6" stroke="#9eafa6" strokeWidth="8"/><path d="M20 150 L65 78 L108 123 L155 48 L189 150" fill="none" stroke={office?'#80a8ae':'#8ba68a'} strokeWidth="18"/><Text x={100} y={180} size={13} anchor="middle">{office?'EXAMPLE STUDIO':'MAKE SOMETHING'}</Text></g>
 <ellipse cx="530" cy="1190" rx="400" ry="65" fill="#203b4b" opacity=".1" filter="url(#shadow)"/>
 <path d="M190 830 H540 Q590 830 590 900 V1200 H145 V890 Q145 830 190 830" fill="#5d7379"/>
 <Person x={350} y={760} id={office?'recruiter':'candidate'} f={f} world={world} reach={reach}/>
 <path d="M115 1040 L905 1040 L1020 1168 H50Z" fill="url(#wood)"/><path d="M50 1168 H1020 V1198 H50Z" fill="#956747"/>
 <path d="M120 1198 V1450 M918 1198 V1450" stroke="#5f7479" strokeWidth="25"/>
 <Laptop x={465} y={854} f={f} review={office} progress={office?(phase==='review'||phase==='invited'?1:0):clamp(f/110)}/>
 <g transform="translate(222,1020)"><ellipse cy="28" rx="40" ry="14" fill="#896e58" opacity=".3"/><path d="M-27 -28 H27 V20 Q0 45 -27 20Z" fill="#edf0e3"/><path d="M27 -19 Q62 -24 49 9 Q43 21 28 11" fill="none" stroke="#edf0e3" strokeWidth="10"/><path d={`M-8 -40 Q${Math.sin(f/20)*15} -62 -3 -82 M10 -40 Q${Math.sin(f/22)*10+15} -66 14 -81`} fill="none" stroke="#fff" strokeWidth="3" opacity=".45"/></g>
 <g transform="translate(868,1023)"><path d="M0 0 L-15 -310 L-90 -358" stroke="#536f72" strokeWidth="10" fill="none"/><path d="M-125 -360 L-61 -360 L-40 -300 H-145Z" fill="#e2b570"/><ellipse cx="-90" cy="-150" rx="150" ry="240" fill="url(#lamp)"/></g>
 <Phone x={720} y={850-(office?0:reach*16)} f={f} state={phase} tap={tap}/>
 {reach>.1&&<g><path d={`M664 ${1112-reach*16} Q696 ${1135-reach*16} 742 ${1120-reach*16}`} fill="none" stroke={world[office?'recruiter':'candidate'].skin} strokeWidth="20" strokeLinecap="round"/>
 <path d={`M890 1090 Q879 1030 ${815+Math.sin(tap*Math.PI)*-3} ${1046-Math.sin(tap*Math.PI)*9}`} fill="none" stroke={world[office?'recruiter':'candidate'].skin} strokeWidth="18" strokeLinecap="round"/></g>}
 <Plant x={965} y={1240} s={.8} f={f}/><Plant x={95} y={1130} s={.38} f={f}/>
 </g>;
const OfficeBuilding:React.FC<{x:number;y:number;f:number;lit:boolean}>=({x,y,f,lit})=><g transform={`translate(${x},${y})`}>
 <path d="M-90 -290 L35 -360 L160 -280 L160 80 L-90 80Z" fill="#314f66"/>
 <path d="M35 -360 L160 -280 V80 H35Z" fill="#233f54"/><path d="M-90 -290 L35 -360 V80 H-90Z" fill="url(#officeWindows)"/>
 <path d="M35 -280 H160 V80 H35Z" fill="url(#officeWindows)"/>
 <rect x="53" y="-114" width="72" height="62" rx="5" fill={lit?C.gold:'#9bbdbb'} opacity={lit?1:.5}/>
 {lit&&<circle cx="89" cy="-83" r={60+Math.sin(f/7)*5} fill="none" stroke={C.gold} strokeWidth="4" opacity=".6"/>}
 <Text x={28} y={130} size={27} fill="#dcf0ee" anchor="middle">Example Studio</Text><Text x={28} y={165} size={18} fill="#92b2c1" anchor="middle">Same company · fictional office</Text>
 </g>;
function Stage({shot,global,plan}:{shot:any;global:number;plan:OwnerPlan}){
 const world=plan.director.world,shots=plan.director.shots;
 const send=shots.find((s:any)=>s.action==='compose_send'),receive=shots.find((s:any)=>s.action==='receive'),review=shots.find((s:any)=>s.action==='review'),invite=shots.find((s:any)=>s.action==='invite');
 const sendAt=send.action_frame,recAt=receive.action_frame,revAt=review.action_frame,inviteAt=invite.action_frame;
 const phase=global<sendAt?'draft':global<sendAt+17?'sending':global<receive.from?'sent':global<revAt?'received':global<inviteAt?'review':'invited';
 const tap=clamp((global-(shot.action==='compose_send'?sendAt:shot.action==='review'?revAt:inviteAt)+6)/24);
 const progress=smooth((global-shot.from)/Math.max(1,shot.to-shot.from-8));
 const camera=shot.camera.from.map((v:number,i:number)=>mix(v,shot.camera.to[i],progress));
 const reach=clamp((global-send.from)/27);
 let visual:React.ReactNode;
 if(['establish','compose_send'].includes(shot.action))visual=<Room office={false} f={global} world={world} phase={phase} tap={tap} reach={reach}/>;
 else if(shot.action==='transmit'){
   const travel=smooth((global-shot.action_frame)/Math.max(1,shot.to-shot.action_frame-12));
   const x=mix(200,860,travel),y=1030-Math.sin(travel*Math.PI)*340;
   visual=<g><rect x="-1500" y="-1500" width="4000" height="4300" fill="url(#night)"/>
    {Array.from({length:18},(_,i)=><path key={i} d={`M0 ${i*90} H1080 M${i*90} 0 V1550`} stroke="#67b7b3" opacity=".07"/>)}
    <path d="M0 1290 L280 1160 L630 1280 L1080 1110 V1600 H0Z" fill="#163c4b"/>
    <OfficeBuilding x={865} y={1110} f={global} lit={travel>.95}/>
    <Phone x={120} y={900} f={global} state="sent"/>
    <path d="M200 1030 Q530 350 860 1030" fill="none" stroke={C.teal} strokeWidth="6" strokeDasharray="11 14" opacity=".6"/>
    <path d="M200 1030 Q530 350 860 1030" fill="none" stroke="#effff7" strokeWidth="9" pathLength="1" strokeDasharray="1" strokeDashoffset={1-travel} opacity=".8"/>
    <g transform={`translate(${x},${y})`}><circle r="59" fill="#52d8be" opacity=".1"/><rect x="-45" y="-28" width="90" height="56" rx="8" fill={C.gold}/><path d="M-40 -23 L0 3 L40 -23" fill="none" stroke="#7b603a" strokeWidth="4"/><Text x={0} y={52} size={20} fill="#fff" anchor="middle">APP-042</Text></g>
    <Text x={540} y={430} size={35} fill="#e5f8f3" anchor="middle">One application. Two connected devices.</Text>
    <Text x={540} y={1320} size={22} fill="#a9c9cc" anchor="middle">ILLUSTRATIVE ROUTE · NOT A REAL NETWORK TRACE</Text>
    </g>;
 }else if(shot.action==='invite'){
    const reply=smooth((global-inviteAt)/42);
    visual=<g><rect x="-1500" y="-1500" width="4000" height="4300" fill="#dce8e2"/><path d="M540 0 V1550" stroke="#b5c9c5" strokeWidth="4"/>
    <g transform="translate(28,170) scale(.58)"><Room office={false} f={global} world={world} phase={reply>.85?'invitation_received':'sent'} tap={0} reach={1}/></g>
    <g transform="translate(550,170) scale(.58)"><Room office f={global} world={world} phase="invited" tap={tap} reach={1}/></g>
    <path d="M810 1080 C810 1310 270 1310 270 1080" fill="none" stroke="#468b83" strokeWidth="6" strokeDasharray="9 12"/>
    <g transform={`translate(${mix(810,270,reply)},${1080+Math.sin(reply*Math.PI)*165})`}><rect x="-46" y="-31" width="92" height="62" rx="12" fill={C.teal}/><Text x={0} y={7} size={20} anchor="middle">INVITE</Text></g>
    <Text x={270} y={1030} size={31} anchor="middle">Applicant</Text><Text x={810} y={1030} size={31} anchor="middle">Recruiter</Text>
    <Text x={540} y={1390} size={32} anchor="middle">APP-042 · Interview invitation</Text>
    </g>;
 }else visual=<Room office f={global} world={world} phase={global<recAt?'sent':phase} tap={tap} reach={clamp((global-revAt+15)/30)}/>;
 return <svg width={W} height={H} viewBox={camera.join(' ')} style={{position:'absolute',inset:0}}><Defs/>{visual}</svg>;
}
export const SemanticFilm:React.FC<{plan:OwnerPlan}>=({plan})=>{
 const frame=useCurrentFrame(),shots=plan.director.shots;
 const index=shots.findIndex((s:any)=>frame>=s.from&&frame<s.to),shot=shots[Math.max(0,index)];
 const blend=clamp((frame-shot.from)/8);let offset=0;
 const audio=plan.scenes.map((s,i)=>{const start=offset;offset+=s.durationFrames;return <Sequence key={i} from={start} durationInFrames={s.durationFrames}><Audio src={staticFile(s.audio)}/></Sequence>;});
 let from=0;let caption='';for(const s of plan.scenes){if(frame>=from&&frame<from+s.durationFrames){caption=s.captions.find(c=>(frame-from)/30>=c.start&&(frame-from)/30<c.end)?.text||'';break;}from+=s.durationFrames;}
 const titles:Record<string,string>={establish:'THE OPPORTUNITY',compose_send:'ONE DELIBERATE ACTION',transmit:'FOLLOW THE APPLICATION',receive:'THE OTHER END',review:'RECEIVED → REVIEWED',invite:'THE HUMAN RESPONSE'};
 return <AbsoluteFill style={{background:'#dce8e2',fontFamily:'InterTight',overflow:'hidden'}}>
  <div style={{position:'absolute',top:115,width:1080,height:1550}}>
   {index>0&&blend<1&&<Stage shot={shots[index-1]} global={shot.from-1} plan={plan}/>}
   <div style={{position:'absolute',inset:0,opacity:index>0?blend:1}}><Stage shot={shot} global={frame} plan={plan}/></div>
  </div>
  <div style={{position:'absolute',inset:0,background:'radial-gradient(ellipse at center,transparent 45%,#102d3d1c 100%)',pointerEvents:'none'}}/>
  <div style={{position:'absolute',left:58,right:58,top:53,display:'flex',justifyContent:'space-between',fontSize:22,letterSpacing:2,color:C.ink,fontWeight:800}}><span>LOGICSCRIPT / FIELD NOTES</span><span>0{index+1} / 06</span></div>
  <div style={{position:'absolute',top:115,left:58,fontSize:23,color:shot.action==='transmit'?'#b7d9dc':C.ink,fontWeight:700,letterSpacing:3}}>{titles[shot.action]}</div>
  <div style={{position:'absolute',bottom:290,left:58,right:58,fontSize:19,color:shot.action==='transmit'?'#b7d9dc':'#536e75',letterSpacing:1.2}}>FICTIONAL UI · ORIGINAL ANIMATED SIMULATION</div>
  {caption&&<div style={{position:'absolute',left:58,right:58,bottom:145,color:'#173b49',background:'#f8faf1ef',borderRadius:15,padding:'23px 30px',fontSize:43,fontWeight:800,lineHeight:1.18,boxShadow:'0 8px 25px #173b4912'}}>{caption}</div>}
  <div style={{position:'absolute',bottom:72,left:58,right:58,height:3,background:'#1e43552a'}}><div style={{height:3,width:`${frame/plan.durationInFrames*100}%`,background:'#347e79'}}/></div>
  {audio}{plan.director.soundtrack&&<Audio src={staticFile(plan.director.soundtrack)}/>}
 </AbsoluteFill>;
};
