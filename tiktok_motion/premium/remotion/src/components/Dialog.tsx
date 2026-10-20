import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {EASE_IN, EASE_IN_OUT, EASE_OUT, clampOpts, tween} from '../motion';

// Card geometry is fixed so the cursor can target the button without DOM measuring.
const CARD = {w: 780, h: 392, cx: 540, cy: 1190, pad: 46, gap: 18, btnH: 96};
const BTN_W = (CARD.w - CARD.pad * 2 - CARD.gap) / 2;
const REMOVE = {
  x: CARD.cx - CARD.w / 2 + CARD.pad + BTN_W + CARD.gap + BTN_W / 2,
  y: CARD.cy + CARD.h / 2 - CARD.pad - CARD.btnH / 2,
};

type Props = {inStart: number; click: number; outStart: number; outEnd: number; title: string; body: string};

export const Dialog: React.FC<Props> = ({inStart, click, outStart, outEnd, title, body}) => {
  const frame = useCurrentFrame();
  if (frame < inStart || frame > outEnd) return null;
  const tin = tween(frame, [inStart, inStart + 18], [0, 1], EASE_OUT);
  const tout = tween(frame, [outStart, outEnd], [0, 1], EASE_IN);
  const press = interpolate(frame, [click - 2, click, click + 5], [1, 0.93, 1], clampOpts);
  const hover = tween(frame, [click - 12, click - 4], [0, 1]);
  const [quoted, ...rest] = title.split('“');
  return (
    <div
      style={{
        position: 'absolute',
        left: CARD.cx - CARD.w / 2,
        top: CARD.cy - CARD.h / 2,
        width: CARD.w,
        height: CARD.h,
        borderRadius: 40,
        background: 'linear-gradient(180deg, rgba(34,34,37,0.86), rgba(14,14,16,0.92))',
        backdropFilter: 'blur(26px) saturate(1.2)',
        boxShadow: '0 60px 120px rgba(0,0,0,0.35), 0 18px 40px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.12)',
        border: '1px solid rgba(255,255,255,0.08)',
        padding: CARD.pad,
        boxSizing: 'border-box',
        opacity: tin * (1 - tout),
        filter: `blur(${(1 - tin) * 14 + tout * 18}px)`,
        transform: `translateY(${(1 - tin) * 60 + tout * 50}px) scale(${0.9 + 0.1 * tin - 0.08 * tout})`,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div style={{fontFamily: 'InterTight', fontWeight: 700, fontSize: 46, color: '#fff', letterSpacing: '-0.035em'}}>
        {quoted}
        <span style={{fontFamily: 'PlayfairItalic', fontStyle: 'italic', fontWeight: 900, fontSize: 52}}>
          {'“' + rest.join('“')}
        </span>
      </div>
      <div
        style={{
          fontFamily: 'InterTight',
          fontWeight: 500,
          fontSize: 29,
          lineHeight: 1.3,
          color: 'rgba(255,255,255,0.58)',
          marginTop: 14,
          letterSpacing: '-0.01em',
        }}
      >
        {body}
      </div>
      <div style={{flex: 1}} />
      <div style={{display: 'flex', gap: CARD.gap}}>
        <Button label="Cancel" bg="rgba(255,255,255,0.10)" color="rgba(255,255,255,0.9)" />
        <Button
          label="Remove"
          bg={`linear-gradient(180deg, ${hover ? '#ff5a5f' : '#f0464c'}, #c9272d)`}
          color="#fff"
          scale={press}
          glow={hover}
        />
      </div>
    </div>
  );
};

const Button: React.FC<{label: string; bg: string; color: string; scale?: number; glow?: number}> = ({
  label,
  bg,
  color,
  scale = 1,
  glow = 0,
}) => (
  <div
    style={{
      width: BTN_W,
      height: CARD.btnH,
      borderRadius: 26,
      background: bg,
      color,
      fontFamily: 'InterTight',
      fontWeight: 700,
      fontSize: 34,
      letterSpacing: '-0.02em',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      transform: `scale(${scale})`,
      boxShadow: glow ? `0 0 ${40 * glow}px rgba(240,70,76,${0.45 * glow}), inset 0 1px 0 rgba(255,255,255,0.25)` : 'inset 0 1px 0 rgba(255,255,255,0.08)',
    }}
  >
    {label}
  </div>
);

/** macOS-style pointer that glides in on an arc, clicks Remove, then drifts away. */
export const Cursor: React.FC<{start: number; click: number; end: number}> = ({start, click, end}) => {
  const frame = useCurrentFrame();
  if (frame < start || frame > end) return null;
  const t = tween(frame, [start, click - 6], [0, 1], EASE_IN_OUT);
  const from = {x: 1010, y: 1760};
  const ctrl = {x: 980, y: 1330};
  const to = {x: REMOVE.x + 40, y: REMOVE.y + 6};
  const x = (1 - t) ** 2 * from.x + 2 * (1 - t) * t * ctrl.x + t * t * to.x;
  const y = (1 - t) ** 2 * from.y + 2 * (1 - t) * t * ctrl.y + t * t * to.y;
  const away = tween(frame, [click + 10, end], [0, 1], EASE_IN);
  const s = interpolate(frame, [click - 2, click, click + 5], [1, 0.82, 1], clampOpts);
  const ripple = tween(frame, [click, click + 16], [0, 1]);
  return (
    <>
      {frame >= click && (
        <div
          style={{
            position: 'absolute',
            left: to.x - 90 * ripple,
            top: to.y - 90 * ripple,
            width: 180 * ripple,
            height: 180 * ripple,
            borderRadius: '50%',
            border: `3px solid rgba(255,255,255,${0.7 * (1 - ripple)})`,
          }}
        />
      )}
      <svg
        width={64}
        height={64}
        viewBox="0 0 24 24"
        style={{
          position: 'absolute',
          left: x + away * 120,
          top: y + away * 160,
          transform: `scale(${s * 1.15})`,
          transformOrigin: '6px 3px',
          opacity: tween(frame, [start, start + 6], [0, 1]) * (1 - away),
          filter: 'drop-shadow(0 6px 10px rgba(0,0,0,0.35))',
        }}
      >
        <path d="M5 2.5 L5 19.5 L9.4 15.4 L12.3 21.6 L15.1 20.3 L12.2 14.2 L18.2 14.2 Z" fill="#fff" stroke="#000" strokeWidth={1.3} strokeLinejoin="round" />
      </svg>
    </>
  );
};
