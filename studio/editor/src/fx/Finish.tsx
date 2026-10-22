import React from 'react';
import {AbsoluteFill, random, useCurrentFrame} from 'remotion';
import {EASE_IN, EASE_OUT, tween} from '../motion';

/** Entry effect for a shot; runs over its first `frames` frames (local time). */
export const TransitionIn: React.FC<{kind: string; frames: number; children: React.ReactNode}> = ({kind, frames, children}) => {
  const f = useCurrentFrame();
  const n = Math.max(1, frames);
  const t = tween(f, [0, n], [0, 1], EASE_OUT);
  let style: React.CSSProperties = {};
  if (kind === 'whip_blur') {
    style = {transform: `translateX(${(1 - t) * 38}%) scaleX(${1 + (1 - t) * 0.25})`, filter: `blur(${(1 - t) * 26}px)`};
  } else if (kind === 'zoom_through') {
    style = {transform: `scale(${1 + (1 - t) * 0.45})`, filter: `blur(${(1 - t) * 20}px)`, opacity: tween(f, [0, 3], [0.2, 1])};
  } else if (kind === 'blur') {
    style = {filter: `blur(${(1 - t) * 30}px)`, opacity: tween(f, [0, n * 0.6], [0, 1])};
  } else if (kind === 'slide_up') {
    style = {transform: `translateY(${(1 - t) * 100}%)`};
  }
  const dip = kind === 'dip_white' || kind === 'dip_black';
  return (
    <AbsoluteFill style={style}>
      {children}
      {dip ? (
        <AbsoluteFill style={{backgroundColor: kind === 'dip_white' ? '#f6f5f1' : '#000', opacity: tween(f, [0, n], [1, 0], EASE_OUT)}} />
      ) : null}
    </AbsoluteFill>
  );
};

/** The outgoing half of a dip: the shot before a dip fades into the dip colour. */
export const TransitionOutDip: React.FC<{kind: string; frames: number; duration: number}> = ({kind, frames, duration}) => {
  const f = useCurrentFrame();
  const n = Math.max(1, frames);
  return (
    <AbsoluteFill
      style={{backgroundColor: kind === 'dip_white' ? '#f6f5f1' : '#000', opacity: tween(f, [duration - n, duration], [0, 1], EASE_IN)}}
    />
  );
};

/** Film grain + soft vignette over everything (kills banding, unifies the two worlds). */
export const FilmFinish: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <>
      <AbsoluteFill style={{background: 'radial-gradient(ellipse 90% 75% at 50% 48%, rgba(0,0,0,0) 58%, rgba(0,0,0,0.18) 100%)'}} />
      <svg width="100%" height="100%" style={{position: 'absolute', inset: 0, opacity: 0.06, mixBlendMode: 'overlay'}}>
        <filter id="grain">
          <feTurbulence type="fractalNoise" baseFrequency={0.85} numOctaves={2} seed={Math.floor(random(`g${f % 24}`) * 1000)} stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter="url(#grain)" />
      </svg>
    </>
  );
};
