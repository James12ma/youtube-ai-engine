/** Grounded storyboard shots. Vector scenes only: no fabricated footage or human likeness. */
import React from 'react';
import {useCurrentFrame,interpolate,OffthreadVideo,staticFile} from 'remotion';

export type StoryVisual = {
  kind:string; headline:string; items:string[];
  actors?:string[]; setting?:string; action?:string; camera?:string;
  flow?:{from?:string;to?:string}; data?:{label:string;value:number}[];
  excerpt?:string; source_label?:string; geo_clip?:string; geo_attribution?:string;
};
export const isStoryKind=(kind:string)=>['character','device','signal_flow','document','data','map','hero','god_eye'].includes(kind);
const shotPalette:Record<string,[string,string,string]>={
  character:['#102440','#ebf3fd','#69c8f8'], device:['#161b37','#f5f4ff','#a9a0ff'],
  signal_flow:['#051e2c','#edfcff','#55e0e5'], document:['#29221e','#fff8ed','#ffd16a'],
  data:['#102a2a','#edfff9','#71e5bf'], map:['#151e39','#f0f5ff','#9cb4ff'],
  hero:['#241431','#fff4fe','#f2a8d8'], god_eye:['#101f36','#e6f6ff','#7fc5ff']
};
const appear=(f:number,start=0)=>interpolate(f,[start,start+20],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
const titleCase=(s:string)=>s.length>60?s.slice(0,59)+'…':s;
const Phone:React.FC<{name:string;f:number;accent:string;small?:boolean}>=({name,f,accent,small})=>{
  const scale=small ? 0.77 : 1;
  return <div style={{width:300,height:530,transform:'scale('+scale+')',borderRadius:54,background:'linear-gradient(145deg,#6c778f,#111a2c 18%,#02070f 80%,#657185)',padding:13,boxSizing:'border-box',boxShadow:'23px 42px 75px #0008, inset 0 0 0 2px #ffffff55'}}>
    <div style={{height:'100%',background:'#fcfdff',borderRadius:42,color:'#172338',overflow:'hidden',padding:22,boxSizing:'border-box'}}>
      <div style={{width:90,height:18,borderRadius:30,background:'#0c1322',margin:'-8px auto 48px'}}/>
      <div style={{fontSize:19,fontWeight:700,opacity:.55,marginBottom:16}}>COMMUNICATION</div>
      <div style={{fontSize:31,fontWeight:900,lineHeight:1.1,minHeight:85}}>{titleCase(name)}</div>
      <div style={{background:'#e9f3fd',borderRadius:20,padding:16,fontSize:19,marginTop:20}}>Illustration <span style={{color:'#16866b'}}>✓</span></div>
      <div style={{height:90,marginTop:30,display:'flex',alignItems:'center',justifyContent:'center'}}>
        <div style={{width:56,height:56,borderRadius:'50%',background:accent,boxShadow:'0 0 '+(12+Math.sin(f/8)*9)+'px '+accent}}/>
      </div>
      <div style={{fontSize:17,color:'#64748b',textAlign:'center'}}>Illustrative interface</div>
    </div>
  </div>;
};
const Person:React.FC<{name:string;f:number;accent:string;right?:boolean}>=({name,f,accent,right})=><div style={{width:300,textAlign:'center',transform:'translateY('+Math.sin(f/20+(right?1:0))*8+'px)'}}>
  <div style={{height:300,position:'relative',filter:'drop-shadow(14px 24px 25px #0006)'}}>
    <div style={{position:'absolute',width:140,height:155,top:5,left:80,borderRadius:'45% 45% 43% 43%',background:'#c68f70'}}/>
    <div style={{position:'absolute',width:156,height:73,top:0,left:73,borderRadius:'65% 55% 20% 20%',background:'#22263c'}}/>
    <div style={{position:'absolute',width:260,height:173,bottom:0,left:20,borderRadius:'95px 95px 20px 20px',background:accent}}/>
    <div style={{position:'absolute',width:22,height:8,left:122,top:98,borderRadius:9,background:'#422e31'}}/>
    <div style={{position:'absolute',width:22,height:8,left:177,top:98,borderRadius:9,background:'#422e31'}}/>
  </div>
  <div style={{fontSize:27,fontWeight:800,color:'#fff',marginTop:20}}>{titleCase(name)}</div>
</div>;
const DeviceScene:React.FC<{scene:StoryVisual;f:number;accent:string}>=({scene,f,accent})=><div style={{height:690,position:'relative',display:'flex',justifyContent:'center',alignItems:'center'}}>
  <div style={{transform:'translateY('+(1-appear(f,3))*100+'px) rotateY('+Math.sin(f/60)*9+'deg)'}}><Phone name={scene.items[0]||scene.action||'DEVICE'} f={f} accent={accent}/></div>
  <div style={{position:'absolute',right:20,top:110,fontSize:26,background:'#fff',color:'#0c2340',padding:'18px 25px',borderRadius:22,boxShadow:'0 20px 40px #0006',opacity:appear(f,24)}}>{scene.items[1]||'Visual example'} ✓</div>
</div>;
const CharacterScene:React.FC<{scene:StoryVisual;f:number;accent:string}>=({scene,f,accent})=><div style={{height:690,display:'flex',justifyContent:'space-around',alignItems:'center',position:'relative'}}>
  <Person name={scene.actors?.[0]||'Role'} f={f} accent={accent}/>
  {scene.actors?.[1]&&<Person name={scene.actors[1]} f={f} accent="#778bc8" right/>}
  <div style={{position:'absolute',top:10,right:12,background:'#fff',color:'#17304a',padding:'22px 26px',borderRadius:20,fontSize:24,fontWeight:800,transform:'scale('+appear(f,12)+')'}}>{scene.items[0]||'CONVERSATION'}</div>
  <div style={{position:'absolute',bottom:28,left:70,right:70,height:27,borderRadius:'50%',background:'#0005',filter:'blur(12px)'}}/>
</div>;
const SignalScene:React.FC<{scene:StoryVisual;f:number;accent:string}>=({scene,f,accent})=>{
  const t=(f%135)/135;const x=110+650*t,y=280-160*4*t*(1-t);
  return <div style={{height:680,position:'relative'}}>
    <div style={{position:'absolute',top:80,left:0,right:0,display:'flex',justifyContent:'space-between'}}>
      {[scene.flow?.from||'',scene.flow?.to||''].map((name,i)=><div key={i} style={{width:300,textAlign:'center'}}>
        <div style={{width:170,height:260,border:'11px solid #a4c0ce',borderRadius:27,margin:'auto',background:'#0b1529',boxShadow:'15px 20px 50px #0008',display:'flex',alignItems:'center',justifyContent:'center',fontSize:60}}> {i?'▣':'☎'} </div>
        <div style={{marginTop:27,fontSize:27,fontWeight:800}}>{titleCase(name)}</div>
      </div>)}
    </div>
    <svg viewBox="0 0 870 550" style={{position:'absolute',top:30,left:8,width:'100%',height:510,overflow:'visible'}}>
      <path d="M110 280 Q435 -40 760 280" stroke={accent} strokeWidth={7} strokeDasharray="14 15" fill="none" opacity=".7"/>
      <circle cx={x} cy={y} r={19} fill="#fff" stroke={accent} strokeWidth={9}/>
      <circle cx={x} cy={y} r={37} fill="none" stroke={accent} strokeWidth={3} opacity=".5"/>
    </svg>
    <div style={{position:'absolute',bottom:45,left:60,right:60,textAlign:'center',fontSize:25,letterSpacing:3,fontWeight:800}}>DIRECTIONAL SIGNAL FLOW</div>
  </div>;
};
const DocumentScene:React.FC<{scene:StoryVisual;f:number;accent:string}>=({scene,f,accent})=><div style={{height:690,display:'flex',alignItems:'center',justifyContent:'center'}}>
  <div style={{width:665,minHeight:500,background:'#fffdf8',color:'#26272b',padding:'46px 48px',boxSizing:'border-box',boxShadow:'30px 35px 65px #0006',borderRadius:8,transform:'rotate('+(2-Math.min(2,appear(f)*2))+'deg) translateY('+(1-appear(f))*80+'px)'}}>
    <div style={{fontSize:18,fontWeight:800,color:'#84796d',letterSpacing:5}}>DOCUMENT / EXCERPT</div>
    <div style={{height:8,width:220,background:accent,marginTop:30,marginBottom:35}}/>
    <div style={{fontSize:38,fontWeight:850,lineHeight:1.3,background:'linear-gradient(transparent 48%, '+accent+'aa 48%)'}}>{scene.excerpt}</div>
    <div style={{borderTop:'2px solid #e5e2dc',marginTop:48,paddingTop:20,fontSize:21,color:'#777'}}>{scene.source_label||'Owner-supplied excerpt — source unverified'}</div>
  </div>
</div>;
const DataScene:React.FC<{scene:StoryVisual;f:number;accent:string}>=({scene,f,accent})=>{
  const values=scene.data||[];const high=Math.max(1,...values.map(p=>p.value));
  return <div style={{height:690,display:'flex',alignItems:'end',justifyContent:'space-evenly',gap:12,padding:'40px 24px 90px',boxSizing:'border-box',borderBottom:'3px solid #fff5'}}>
    {values.map((p,i)=><div key={i} style={{width:100,textAlign:'center'}}>
      <div style={{fontSize:25,fontWeight:800,marginBottom:10}}>{p.value.toLocaleString('en-US',{maximumFractionDigits:2})}</div>
      <div style={{height:440*p.value/high*appear(f,i*7),minHeight:p.value?3:0,background:'linear-gradient(180deg,'+accent+',#357b9c)',borderRadius:'15px 15px 2px 2px',boxShadow:'7px 10px 30px #0005'}}/>
      <div style={{fontSize:18,marginTop:18,overflowWrap:'anywhere',fontWeight:700}}>{p.label}</div>
    </div>)}
  </div>;
};
const MapScene:React.FC<{scene:StoryVisual;f:number;accent:string}>=({scene,f,accent})=><div style={{height:690,display:'grid',placeItems:'center',position:'relative'}}>
  <svg viewBox="0 0 650 650" width="650" height="650" role="img" aria-label="Conceptual network globe, not a geographic map" style={{transform:'rotate('+(Math.sin(f/40)*5)+'deg)'}}>
    <circle cx="325" cy="325" r="250" fill="#0b3d53" stroke={accent} strokeWidth="8"/>
    {[-160,-80,0,80,160].map((v,i)=><ellipse key={i} cx="325" cy="325" rx={250-Math.abs(v)*.7} ry="250" fill="none" stroke="#8deaf399" strokeWidth="3"/>)}
    {[-170,-85,0,85,170].map((v,i)=><ellipse key={i} cx="325" cy="325" rx="250" ry={Math.sqrt(250*250-v*v)} fill="none" stroke="#8deaf366" strokeWidth="3"/>)}
    <circle cx={220+Math.sin(f/14)*9} cy="290" r={15+Math.sin(f/6)*4} fill="#fff"/>
    <circle cx="440" cy="392" r="16" fill={accent}/>
    <path d="M220 290 Q345 160 440 392" fill="none" stroke="#fff" strokeWidth="7" strokeDasharray="12 12"/>
  </svg>
  <div style={{position:'absolute',bottom:35,fontSize:24,color:'#fff'}}>Conceptual visualization · not a geographic locator</div>
</div>;
/** Reviewed silent scene clip prepared from the upstream God's Eye View/Cesium app.
 *  Local-only; never embeds iframe or loads live map tiles at render time.
 *  Real-world imagery usage is reviewed by the video owner before publishing.
 */
const GodEyeScene:React.FC<{scene:StoryVisual}>=({scene})=>{
  const clip=scene.geo_clip||'';
  if(!/^job\\/god_eye_[a-zA-Z0-9_-]{1,64}\\.mp4$/.test(clip)){
    throw new Error('Unreviewed God Eye clip path');
  }
  return <div style={{position:'relative',height:690,overflow:'hidden',borderRadius:28,background:'#0a1524'}}>
    <OffthreadVideo src={staticFile(clip)} muted volume={0}
      style={{position:'absolute',width:'100%',height:'100%',objectFit:'cover'}}/>
    <div style={{position:'absolute',left:20,right:20,bottom:16,padding:'10px 14px',fontSize:19,
      color:'#f4fbff',background:'#07111dcc',borderRadius:12}}>
      {scene.geo_attribution||'Source attribution required · not for publication'}
    </div>
  </div>;
};
const HeroScene:React.FC<{scene:StoryVisual;f:number;accent:string}>=({scene,f,accent})=><div style={{height:680,display:'grid',placeItems:'center',position:'relative'}}>
  {[0,1,2].map(i=><div key={i} style={{position:'absolute',width:500+i*100,height:500+i*100,borderRadius:'50%',border:'4px solid '+accent,opacity:.28,transform:'scale('+(appear(f,i*8)*(.8+i*.2))+') rotate('+f/8+'deg)'}}/>)}
  <div style={{fontFamily:'InterTight',fontSize:100,fontWeight:900,textAlign:'center',lineHeight:.95,letterSpacing:-4,padding:'0 55px',transform:'scale('+(0.8+appear(f,4)*.2)+')'}}>{titleCase(scene.items[0]||scene.headline)}</div>
</div>;
export const CinematicScene:React.FC<{scene:StoryVisual}>=({scene})=>{
  const f=useCurrentFrame(),[bg,ink,accent]=shotPalette[scene.kind]||shotPalette.hero;
  const pan=scene.camera==='pan_left'?-f*.5:scene.camera==='pan_right'?f*.5:0;
  const zoom=scene.camera==='static'?1:1+Math.min(f,200)*.00035;
  const angle=scene.camera==='orbit'?Math.sin(f/42)*5:0;
  const visual=scene.kind==='character'?<CharacterScene scene={scene} f={f} accent={accent}/>:
    scene.kind==='device'?<DeviceScene scene={scene} f={f} accent={accent}/>:
    scene.kind==='signal_flow'?<SignalScene scene={scene} f={f} accent={accent}/>:
    scene.kind==='document'?<DocumentScene scene={scene} f={f} accent={accent}/>:
    scene.kind==='data'?<DataScene scene={scene} f={f} accent={accent}/>:
    scene.kind==='map'?<MapScene scene={scene} f={f} accent={accent}/>:
    scene.kind==='god_eye'?<GodEyeScene scene={scene}/>:
    <HeroScene scene={scene} f={f} accent={accent}/>;
  return <div style={{position:'absolute',inset:0,color:ink,background:'radial-gradient(ellipse at 25% 30%,'+bg+' 0%,#080d18 100%)',overflow:'hidden'}}>
    <div style={{position:'absolute',top:110,left:72,right:72,fontFamily:'InterTight',fontSize:25,letterSpacing:4,opacity:.65}}>{(scene.setting||'PREMIUM VISUAL STORY').toUpperCase()}</div>
    <div style={{position:'absolute',top:240,left:72,right:72,fontFamily:'InterTight',fontSize:70,fontWeight:900,lineHeight:1.05,letterSpacing:-2,opacity:appear(f)}}>{titleCase(scene.headline)}</div>
    <div style={{position:'absolute',top:520,left:60,right:60,transform:'translateX('+pan+'px) rotateY('+angle+'deg) scale('+zoom+')',transformOrigin:'center'}}>{visual}</div>
    {scene.action&&<div style={{position:'absolute',top:1300,left:72,right:72,borderLeft:'7px solid '+accent,padding:'15px 22px',background:'#0004',borderRadius:8,fontSize:32,fontWeight:700,lineHeight:1.25,opacity:appear(f,24)}}>{scene.action}</div>}
    
  </div>;
};
