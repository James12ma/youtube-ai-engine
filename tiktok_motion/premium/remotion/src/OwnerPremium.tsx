import React,{useEffect,useState} from 'react';
import {AbsoluteFill,Audio,Sequence,staticFile,useCurrentFrame,interpolate,delayRender,continueRender,cancelRender} from 'remotion';
import {BigWord,SmallLine} from './components/Kinetic';
import {FilmFinish,SketchArcs} from './components/Finish';
import {SemanticFilm} from './SemanticFilm';
import {CinematicScene,isStoryKind,StoryVisual} from './CinematicScene';

type Scene=StoryVisual & {narration:string;audio:string;durationFrames:number;captions:{start:number;end:number;text:string}[]};
export type OwnerPlan={title:string;scenes:Scene[];durationInFrames:number;fps:number;width:number;height:number;director?:any};
const useOwnerFonts=()=>{const [h]=useState(()=>delayRender('premium fonts'));useEffect(()=>{Promise.all([
 ['InterTight','inter-tight-latin-800-normal.woff2','800','normal'],['PlayfairItalic','playfair-display-latin-900-italic.woff2','900','italic']
].map(([family,file,weight,style])=>new FontFace(family,`url(${staticFile('fonts/'+file)})`,{weight,style}).load().then(f=>document.fonts.add(f)))).then(()=>continueRender(h)).catch(cancelRender);},[h]);};
const ease=(f:number)=>interpolate(f,[0,22],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
const Glossy:React.FC<{scene:Scene}>=({scene})=>{const f=useCurrentFrame();const labels=scene.items.length?scene.items:scene.headline.split(/\s+/).slice(0,4);const process=['process','timeline'].includes(scene.kind);
return <div style={{position:'absolute',top:680,left:80,right:80,height:650,perspective:1100}}>
 <div style={{position:'absolute',inset:'60px 80px',borderRadius:'50%',background:'radial-gradient(ellipse,#222 0%,#555 20%,#0000 68%)',filter:'blur(45px)',transform:'rotateX(68deg) translateY(140px)',opacity:.28}}/>
 {labels.map((label,i)=>{const enter=ease(f-i*7);const angle=(i/labels.length)*Math.PI*2;const grid=labels.length>4;const x=grid?(i%3-1)*300:process?(i-(labels.length-1)/2)*230:Math.sin(angle)*250;const y=grid?(Math.floor(i/3)-.5)*250:process?(i%2)*75:Math.cos(angle)*185;
 return <div key={i} style={{position:'absolute',left:'50%',top:'42%',width:process?200:250,minHeight:150,padding:'30px 20px',boxSizing:'border-box',color:'#fff',background:'linear-gradient(140deg,#68686e 0%,#151518 30%,#000 70%,#3c3c42 100%)',border:'2px solid #fff8',borderRadius:scene.kind==='chart'?'50%':34,boxShadow:'15px 40px 45px #0003,inset 0 2px 5px #fff7',transform:`translate(calc(-50% + ${x}px),calc(-50% + ${y+Math.sin(f/28+i)*12+(1-enter)*90}px)) rotateY(${Math.sin(f/55+i)*13}deg) rotateX(${8+Math.cos(f/63)*5}deg) scale(${.5+.5*enter})`,opacity:enter,display:'flex',alignItems:'center',justifyContent:'center',textAlign:'center',overflowWrap:'anywhere',fontFamily:'InterTight',fontWeight:800,fontSize:Math.max(26,Math.min(36,260/Math.max(6,label.length)*1.4))}}>{label}</div>;})}
 {scene.kind==='ui'&&<div style={{position:'absolute',bottom:0,left:160,right:160,background:'#111',color:'#fff',borderRadius:22,padding:28,fontFamily:'InterTight',fontSize:30,transform:`translateY(${(1-ease(f-20))*100}px)`,boxShadow:'0 20px 35px #0003'}}>Example interface · owner review</div>}
</div>;};
const Shot:React.FC<{scene:Scene;index:number;total:number}>=({scene,index,total})=>{const f=useCurrentFrame();const cue=scene.captions.find(c=>f/30>=c.start&&f/30<c.end);const words=scene.headline.split(/\s+/);const lead=words.slice(0,Math.max(1,words.length-2));const big=words.slice(-Math.min(2,words.length)).join(' ');
return <AbsoluteFill style={{background:'#f3f1ec',overflow:'hidden'}}>
 {isStoryKind(scene.kind)?<CinematicScene scene={scene}/>:<React.Fragment>
 <div style={{position:'absolute',inset:0,backgroundImage:'linear-gradient(#1111 1px,transparent 1px),linear-gradient(90deg,#1111 1px,transparent 1px)',backgroundSize:'100px 100px',opacity:.3,transform:`translateY(${f%100}px)`}}/>
 <div style={{position:'absolute',top:110,left:70,right:70,display:'flex',justifyContent:'space-between',fontFamily:'InterTight',fontSize:24,color:'#777'}}><span>LOGICSCRIPT</span><span>{String(index+1).padStart(2,'0')} / {String(total).padStart(2,'0')}</span></div>
 <div style={{position:'absolute',top:270,width:'100%',padding:'0 50px',boxSizing:'border-box'}}><SmallLine words={lead.map(text=>({text}))} start={0} exitEnd={scene.durationFrames+30} size={Math.min(48,780/Math.max(10,lead.join(' ').length)*1.9)}/><div style={{marginTop:35}}><BigWord text={big} start={8} exitEnd={scene.durationFrames+30} size={Math.min(145,1000/Math.max(8,big.length)*1.5)}/></div></div>
 <SketchArcs start={22} end={scene.durationFrames+20}/><Glossy scene={scene}/>
 </React.Fragment>}
 {cue&&<div style={{position:'absolute',left:70,right:70,bottom:220,fontFamily:'InterTight',fontSize:48,lineHeight:1.2,fontWeight:800,color:'#111',textAlign:'center',padding:'22px 24px',borderRadius:20,background:'#faf9f5eb',boxShadow:'0 8px 25px #0001'}}>{cue.text}</div>}
 <div style={{position:'absolute',bottom:115,left:70,right:70,height:4,background:'#0002'}}><div style={{height:4,width:`${f/scene.durationFrames*100}%`,background:'#111'}}/></div>
 <Audio src={staticFile(scene.audio)}/><FilmFinish/>
 </AbsoluteFill>;};
export const OwnerPremium:React.FC<{plan:OwnerPlan}>=({plan})=>{useOwnerFonts();if(plan.director?.version)return <SemanticFilm plan={plan}/>;let start=0;return <AbsoluteFill>{plan.scenes.map((scene,i)=>{const from=start;start+=scene.durationFrames;return <Sequence key={i} from={from} durationInFrames={scene.durationFrames}><Shot scene={scene} index={i} total={plan.scenes.length}/></Sequence>;})}</AbsoluteFill>;};

