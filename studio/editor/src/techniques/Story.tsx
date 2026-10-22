import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, staticFile, useCurrentFrame} from 'remotion';
import {EASE_IN_OUT, tween} from '../motion';
import {Camera, ShotProps} from '../types';

const GRADES: Record<string, {filter: string; overlay: string; blend: React.CSSProperties['mixBlendMode']}> = {
  none: {filter: 'none', overlay: 'transparent', blend: 'normal'},
  night: {filter: 'contrast(1.12) saturate(0.82) brightness(0.92)', overlay: 'rgba(16,40,78,0.30)', blend: 'multiply'},
  morning: {filter: 'contrast(1.04) saturate(1.05) brightness(1.04)', overlay: 'rgba(255,196,128,0.16)', blend: 'soft-light'},
  warm: {filter: 'contrast(1.06) saturate(1.08)', overlay: 'rgba(255,150,60,0.14)', blend: 'soft-light'},
  mono: {filter: 'grayscale(1) contrast(1.15)', overlay: 'transparent', blend: 'normal'},
  teal_orange: {filter: 'contrast(1.1) saturate(1.1)', overlay: 'linear-gradient(160deg, rgba(0,90,110,0.22), rgba(255,120,40,0.16))', blend: 'overlay'},
};

/** Continuous camera move over the whole shot (the reference's slow push / drift on stills). */
export const cameraTransform = (cam: Camera, f: number, duration: number) => {
  const t = tween(f, [0, duration], [0, 1], EASE_IN_OUT);
  const k = cam.intensity;
  const [fx, fy] = cam.focus;
  const origin = `${fx * 100}% ${fy * 100}%`;
  const base = 1.04 + k; // headroom so pans never reveal edges
  switch (cam.move) {
    case 'push_in': return {transform: `scale(${1.02 + k * t})`, transformOrigin: origin};
    case 'pull_out': return {transform: `scale(${1.02 + k * (1 - t)})`, transformOrigin: origin};
    case 'pan_left': return {transform: `scale(${base}) translateX(${(0.5 - t) * k * 100}%)`, transformOrigin: origin};
    case 'pan_right': return {transform: `scale(${base}) translateX(${(t - 0.5) * k * 100}%)`, transformOrigin: origin};
    case 'tilt_up': return {transform: `scale(${base}) translateY(${(0.5 - t) * -k * 100}%)`, transformOrigin: origin};
    case 'tilt_down': return {transform: `scale(${base}) translateY(${(t - 0.5) * -k * 100}%)`, transformOrigin: origin};
    case 'drift': return {transform: `scale(${base}) translate(${Math.sin(t * 2.2) * k * 30}%, ${Math.cos(t * 1.7) * k * 20}%)`, transformOrigin: origin};
    default: return {transform: 'scale(1.02)', transformOrigin: origin};
  }
};

export const Pending: React.FC<{name: string}> = ({name}) => (
  <AbsoluteFill style={{background: 'repeating-linear-gradient(135deg,#1a1b20 0 40px,#202128 40px 80px)', alignItems: 'center', justifyContent: 'center'}}>
    <div style={{fontFamily: 'InterTight', fontWeight: 700, fontSize: 34, color: '#ff6b6b', textAlign: 'center', lineHeight: 1.4}}>
      ASSET PENDING<br /><span style={{color: '#ccc', fontWeight: 500}}>{name.replace('missing:', '')}</span>
    </div>
  </AbsoluteFill>
);

const Graded: React.FC<{grade: string; vignette: number; sweep: boolean; children: React.ReactNode}> = ({grade, vignette, sweep, children}) => {
  const f = useCurrentFrame();
  const g = GRADES[grade] ?? GRADES.none;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{filter: g.filter}}>{children}</AbsoluteFill>
      <AbsoluteFill style={{background: g.overlay, mixBlendMode: g.blend}} />
      {sweep ? (
        <AbsoluteFill style={{background: `linear-gradient(115deg, rgba(255,240,210,0) ${f * 1.4 - 40}%, rgba(255,240,210,0.22) ${f * 1.4 - 20}%, rgba(255,240,210,0) ${f * 1.4}%)`, mixBlendMode: 'screen'}} />
      ) : null}
      <AbsoluteFill style={{background: `radial-gradient(ellipse 80% 70% at 50% 45%, rgba(0,0,0,0) 45%, rgba(0,0,0,${vignette}) 100%)`}} />
    </AbsoluteFill>
  );
};

export const Still25D: React.FC<ShotProps> = ({shot, duration}) => {
  const f = useCurrentFrame();
  const p = shot.params;
  if (String(p.image).startsWith('missing:')) return <Pending name={p.image} />;
  return (
    <Graded grade={p.grade ?? 'none'} vignette={p.vignette ?? 0.35} sweep={!!p.light_sweep}>
      <Img src={staticFile(p.image)} style={{width: '100%', height: '100%', objectFit: 'cover', ...cameraTransform(shot.camera, f, duration)}} />
    </Graded>
  );
};

export const Clip: React.FC<ShotProps> = ({shot, duration}) => {
  const f = useCurrentFrame();
  const p = shot.params;
  if (String(p.video).startsWith('missing:')) return <Pending name={p.video} />;
  return (
    <Graded grade={p.grade ?? 'none'} vignette={0.35} sweep={false}>
      <OffthreadVideo
        src={staticFile(p.video)}
        startFrom={Math.round((p.start_s ?? 0) * 30)}
        playbackRate={p.speed ?? 1}
        muted
        style={{width: '100%', height: '100%', objectFit: 'cover', ...cameraTransform({...shot.camera, intensity: shot.camera.intensity * 0.5}, f, duration)}}
      />
    </Graded>
  );
};
