/** Pre-captured upstream Cesium pixels; narration remains in the existing renderer. */
import React from 'react';
import {AbsoluteFill,Audio,OffthreadVideo,staticFile,interpolate,useCurrentFrame} from 'remotion';
export type GeoPlan={geo_clip:string;audio:string;durationInFrames:number;geo_attribution:string};
export const GeoCinematic:React.FC<{plan:GeoPlan}>=({plan})=>{
 const f=useCurrentFrame();
 if(!/^job\/god_eye_[a-zA-Z0-9_-]{1,64}\.mp4$/.test(plan.geo_clip))throw Error('Unreviewed geographic clip');
 if(!plan.geo_attribution)throw Error('Geographic source attribution required');
 const opacity=interpolate(f,[0,12,plan.durationInFrames-12,plan.durationInFrames-1],[0,1,1,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
 return <AbsoluteFill style={{background:'#020812'}}><AbsoluteFill style={{opacity}}>
   <OffthreadVideo src={staticFile(plan.geo_clip)} muted style={{width:'100%',height:'100%',objectFit:'contain'}}/>
 </AbsoluteFill><Audio src={staticFile(plan.audio)}/></AbsoluteFill>;
};
