import React from 'react';
import {AbsoluteFill, random, useCurrentFrame} from 'remotion';
import {EASE_IN_OUT, EASE_OUT, INK, PAPER, pop, tween} from '../motion';
import {ShotProps} from '../types';

// The city lies on a plane tilted away from camera; we project points ourselves so labels and the
// travelling packet stay upright (billboards) while the streets recede in perspective.
const W = 1400, H = 1700;           // plane size in px
const CX = 540, CY = 1180;          // where the plane centre sits on screen
const TILT = (52 * Math.PI) / 180;  // rotateX
const PERSP = 1500;

const project = (x: number, y: number, zoom: number) => {
  const dx = (x - W / 2) * zoom, dy = (y - H / 2) * zoom;
  const yr = dy * Math.cos(TILT);
  const z = dy * Math.sin(TILT); // CSS rotateX: points above centre move away from the viewer
  const s = PERSP / (PERSP - z);
  return {x: CX + dx * s, y: CY + yr * s, s};
};

const S = {x: 470, y: 1300};   // sender (phone) on the plane
const R = {x: 1000, y: 420};   // receiver (company)
const C = {x: 330, y: 620};    // path control point (swings around the river)
const bez = (t: number) => ({
  x: (1 - t) ** 2 * S.x + 2 * (1 - t) * t * C.x + t * t * R.x,
  y: (1 - t) ** 2 * S.y + 2 * (1 - t) * t * C.y + t * t * R.y,
});

const Pin: React.FC<{x: number; y: number; label: string; icon: 'phone' | 'building'; glow: number; appear: number}> = ({x, y, label, icon, glow, appear}) => (
  <div style={{position: 'absolute', left: x, top: y, transform: `translate(-50%, -100%) scale(${appear})`, transformOrigin: '50% 100%', display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
    <div style={{padding: '10px 18px', borderRadius: 999, background: '#fff', fontFamily: 'InterTight', fontWeight: 800, fontSize: 30, color: INK,
      boxShadow: '0 10px 24px rgba(0,0,0,0.14)', whiteSpace: 'nowrap', marginBottom: 14}}>{label}</div>
    <div style={{width: 112, height: 112, borderRadius: 30, background: INK, display: 'flex', alignItems: 'center', justifyContent: 'center',
      boxShadow: `0 18px 34px rgba(0,0,0,0.3), 0 0 0 ${glow * 18}px rgba(15,157,118,${0.35 * glow})`}}>
      {icon === 'phone' ? (
        <div style={{width: 40, height: 66, borderRadius: 10, border: '5px solid #9fe3c8', background: '#24423a'}} />
      ) : (
        <svg width={70} height={70} viewBox="0 0 24 24"><path d="M3 21V9l6-3v15M9 21V3l12 5v13M12 8h2M12 11h2M12 14h2M16 9h2M16 12h2M16 15h2" stroke="#9fe3c8" strokeWidth={1.6} fill="none" /></svg>
      )}
    </div>
    <div style={{width: 6, height: 26, background: INK, borderRadius: 3}} />
  </div>
);

export const DataTransfer: React.FC<ShotProps> = ({shot, local, duration}) => {
  const f = useCurrentFrame();
  const p = shot.params;
  const depart = local(p.depart_frame ?? 0);
  const arrive = local(p.arrive_frame ?? duration - 10);
  const zoom = 0.92 + tween(f, [0, duration], [0, 0.1], EASE_IN_OUT);
  const t = tween(f, [depart, arrive], [0, 1], EASE_IN_OUT);
  const appear = tween(f, [0, 14], [0, 1], EASE_OUT);

  // Streets: a deterministic irregular grid plus blocks with soft shadows.
  const blocks = Array.from({length: 46}, (_, i) => ({
    x: 60 + (i % 7) * 190 + random(`bx${i}`) * 40, y: 60 + Math.floor(i / 7) * 240 + random(`by${i}`) * 50,
    w: 110 + random(`bw${i}`) * 60, h: 140 + random(`bh${i}`) * 70,
  }));
  const pathPts = Array.from({length: 61}, (_, k) => bez(k / 60));
  const drawn = Math.max(0, Math.min(1, t * 1.05));
  const proj = pathPts.map((q) => project(q.x, q.y, zoom));
  const visible = proj.slice(0, Math.max(1, Math.round(drawn * 60) + 1));
  const d = (pts: {x: number; y: number}[]) => pts.map((q, k) => `${k ? 'L' : 'M'}${q.x.toFixed(1)},${q.y.toFixed(1)}`).join(' ');
  const pk = project(bez(t).x, bez(t).y, zoom);
  const arrived = tween(f, [arrive, arrive + 10], [0, 1]);
  const packetOn = f >= depart - 6 && f < arrive + 8;
  const sp = project(S.x, S.y, zoom), rp = project(R.x, R.y, zoom);
  const lift = Math.sin(t * Math.PI) * 120; // the packet arcs above the city

  return (
    <AbsoluteFill style={{background: `linear-gradient(180deg, #f4f3ef 0%, ${PAPER} 35%, #e2e1dc 100%)`}}>
      {/* the plane, drawn in 3D with CSS so streets get true perspective */}
      <div style={{position: 'absolute', left: CX - W / 2, top: CY - H / 2, width: W, height: H, transformOrigin: '50% 50%',
        transform: `perspective(${PERSP}px) rotateX(52deg) scale(${zoom})`, opacity: appear}}>
        <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
          <path d="M -40 760 C 300 700, 520 980, 900 860 S 1300 700, 1460 820" stroke="#cfd8dc" strokeWidth={70} fill="none" />
          {Array.from({length: 9}, (_, k) => <line key={`h${k}`} x1={0} x2={W} y1={k * 210} y2={k * 210 + 20} stroke="#d9d8d2" strokeWidth={6} />)}
          {Array.from({length: 8}, (_, k) => <line key={`v${k}`} y1={0} y2={H} x1={k * 200} x2={k * 200 - 30} stroke="#d9d8d2" strokeWidth={6} />)}
          {blocks.map((b, k) => (
            <rect key={k} x={b.x} y={b.y} width={b.w} height={b.h} rx={10} fill={k % 5 ? '#e7e6e1' : '#dcdbd5'} />
          ))}
        </svg>
      </div>
      {/* screen-space overlays projected from the plane */}
      <svg width={1080} height={1920} style={{position: 'absolute', inset: 0}}>
        <path d={d(proj)} stroke="rgba(11,11,12,0.12)" strokeWidth={6} strokeDasharray="4 16" fill="none" strokeLinecap="round" />
        <path d={d(visible)} stroke="#0f9d76" strokeWidth={10} fill="none" strokeLinecap="round" />
        <path d={d(visible)} stroke="#9fe3c8" strokeWidth={26} fill="none" strokeLinecap="round" opacity={0.35} />
      </svg>
      <Pin x={sp.x} y={sp.y} label={p.sender_label} icon="phone" glow={tween(f, [depart - 4, depart + 8], [1, 0])} appear={pop(f, 2, 14, 1.4)} />
      <Pin x={rp.x} y={rp.y} label={p.receiver_label} icon="building" glow={arrived * (1 - tween(f, [arrive + 12, arrive + 40], [0, 1]))} appear={pop(f, 8, 14, 1.4)} />
      {packetOn ? (
        <div style={{position: 'absolute', left: pk.x, top: pk.y - lift - 60, transform: `translate(-50%, -50%) scale(${(0.8 + 0.3 * pk.s) * (1 - arrived * 0.7)}) rotate(${(1 - t) * -8}deg)`,
          opacity: 1 - arrived}}>
          <div style={{width: 210, height: 260, borderRadius: 18, background: '#fff', boxShadow: '0 30px 50px rgba(0,0,0,0.28)', padding: 20,
            fontFamily: 'InterTight', display: 'flex', flexDirection: 'column', gap: 12}}>
            <div style={{fontWeight: 800, fontSize: 24, color: '#0f9d76'}}>{p.packet_label}</div>
            {[90, 70, 84, 60].map((w, k) => <div key={k} style={{height: 12, width: `${w}%`, borderRadius: 6, background: k === 3 ? '#ffd60a' : '#e3e5e9'}} />)}
            <div style={{marginTop: 'auto', fontWeight: 700, fontSize: 18, color: '#6b6e78'}}>Maya Rivera</div>
          </div>
          {/* motion trail */}
          <div style={{position: 'absolute', left: -120, top: 100, width: 140, height: 60, background: 'linear-gradient(90deg, rgba(15,157,118,0), rgba(15,157,118,0.35))',
            filter: 'blur(14px)', opacity: Math.sin(t * Math.PI)}} />
        </div>
      ) : null}
      {arrived > 0 ? (
        <div style={{position: 'absolute', left: rp.x - 160 * arrived, top: rp.y - 70 - 160 * arrived, width: 320 * arrived, height: 320 * arrived, borderRadius: '50%',
          border: `6px solid rgba(15,157,118,${0.7 * (1 - arrived)})`}} />
      ) : null}
    </AbsoluteFill>
  );
};
