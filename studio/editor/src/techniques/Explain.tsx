import React from 'react';
import {AbsoluteFill, Img, random, staticFile, useCurrentFrame} from 'remotion';
import {EASE_IN, EASE_IN_OUT, EASE_OUT, INK, PAPER, pop, tween} from '../motion';
import {ShotProps} from '../types';
import {Pending} from './Story';

const Paper: React.FC<{children?: React.ReactNode}> = ({children}) => (
  <AbsoluteFill style={{background: `radial-gradient(ellipse 80% 60% at 50% 55%, #f7f6f2 0%, ${PAPER} 75%)`}}>{children}</AbsoluteFill>
);

/** Type-only beat; an optional kicker (a quote) sits under the narration words with a drawn underline. */
export const Title: React.FC<ShotProps> = ({shot, duration}) => {
  const f = useCurrentFrame();
  const p = shot.params;
  const dark = p.background === 'dark';
  const k = tween(f, [6, 22], [0, 1], EASE_OUT);
  const line = tween(f, [16, 36], [0, 1], EASE_IN_OUT);
  const drift = tween(f, [0, duration], [0, 1]);
  return (
    <AbsoluteFill style={{background: dark ? '#0b0b0c' : undefined}}>
      {!dark ? <Paper /> : null}
      {p.kicker ? (
        <div style={{position: 'absolute', left: 80, right: 80, top: 980, textAlign: 'center', transform: `translateY(${(1 - k) * 40 - drift * 16}px) scale(${1 + drift * 0.03})`,
          opacity: k, filter: `blur(${(1 - k) * 10}px)`}}>
          <div style={{fontFamily: 'PlayfairItalic', fontStyle: 'italic', fontWeight: 900, fontSize: 92, lineHeight: 1.08, letterSpacing: '-0.02em',
            color: dark ? '#fff' : INK, textShadow: '0 18px 30px rgba(0,0,0,0.16)'}}>{p.kicker}</div>
          <svg width={760} height={60} viewBox="0 0 760 60" style={{marginTop: 18}}>
            <path d="M10 40 C 200 10, 520 58, 750 22" stroke="#ffd60a" strokeWidth={14} fill="none" strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - line} />
          </svg>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

/** Many around one; on the narrated word everything but `keep` leaves. */
export const DotsSubtract: React.FC<ShotProps> = ({shot, local}) => {
  const f = useCurrentFrame();
  const p = shot.params;
  const remove = local(p.remove_frame ?? 30);
  const dots = Array.from({length: p.count ?? 28}, (_, i) => {
    const a = random(`a${i}`) * Math.PI * 2;
    const r = 230 + random(`r${i}`) * 220;
    return {x: 540 + Math.cos(a) * r, y: 1150 + Math.sin(a) * r, s: 26 + random(`s${i}`) * 18, d: random(`d${i}`)};
  });
  return (
    <Paper>
      {dots.map((d, i) => {
        const inT = pop(f, 4 + d.d * 18, 12, 1.8);
        const outT = tween(f, [remove + d.d * 14, remove + d.d * 14 + 9], [0, 1], EASE_IN);
        const s = inT * (1 - outT);
        return <div key={i} style={{position: 'absolute', left: d.x - d.s / 2, top: d.y - d.s / 2, width: d.s, height: d.s, borderRadius: '50%',
          background: INK, transform: `scale(${s})`, boxShadow: '8px 12px 14px rgba(0,0,0,0.25)'}} />;
      })}
      <div style={{position: 'absolute', left: 540 - 120, top: 1150 - 120, width: 240, height: 240, borderRadius: '50%', background: INK,
        transform: `scale(${pop(f, 0, 16, 1.4)})`, boxShadow: '30px 40px 50px rgba(0,0,0,0.3)'}} />
    </Paper>
  );
};

export const Object3D: React.FC<ShotProps> = ({shot, duration}) => {
  const f = useCurrentFrame();
  const p = shot.params;
  if (String(p.asset).startsWith('missing:')) return <Pending name={p.asset} />;
  const float = Math.sin(f / 18) * 12;
  const t = tween(f, [0, duration], [0, 1]);
  return (
    <Paper>
      {p.shadow !== false ? (
        <div style={{position: 'absolute', left: 300, right: 300, top: 1480, height: 70, borderRadius: '50%', background: 'rgba(0,0,0,0.25)', filter: 'blur(30px)',
          transform: `scale(${1 - float / 200})`}} />
      ) : null}
      <Img src={staticFile(p.asset)} style={{position: 'absolute', left: 140, width: 800, top: 650 + float, transform: `scale(${pop(f, 0, 18, 1.3) * (1 + t * 0.05)})`}} />
      {p.caption ? <div style={{position: 'absolute', bottom: 260, left: 0, right: 0, textAlign: 'center', fontFamily: 'InterTight', fontWeight: 700, fontSize: 34, color: '#6b6e78'}}>{p.caption}</div> : null}
    </Paper>
  );
};
