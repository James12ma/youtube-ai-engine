import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {EASE_IN_OUT, EASE_OUT, INK, PAPER, clamp, pop, tween} from '../motion';
import {ShotProps} from '../types';
import {Pending} from './Story';

type Screen = Record<string, any>;
const FONT = 'InterTight';

/* ---------- small building blocks ---------- */

const Typed: React.FC<{text: string; start: number | undefined; cps?: number; caret?: boolean}> = ({text, start, cps = 2.4, caret = true}) => {
  const f = useCurrentFrame();
  if (start === undefined) return <>{text}</>;
  const n = Math.max(0, Math.min(text.length, Math.floor((f - start) * cps)));
  const typing = f >= start && n < text.length;
  return (
    <>
      {text.slice(0, n)}
      {caret && (typing || (f >= start && f - start < text.length / cps + 12)) && Math.floor(f / 8) % 2 === 0 ? (
        <span style={{display: 'inline-block', width: 3, height: '1em', background: '#2f6bff', marginLeft: 2, verticalAlign: '-0.12em'}} />
      ) : null}
    </>
  );
};

/** A fingertip that approaches, presses and lifts; ripple on contact. */
const Touch: React.FC<{x: number; y: number; at: number; cursor?: boolean}> = ({x, y, at, cursor}) => {
  const f = useCurrentFrame();
  if (f < at - 14 || f > at + 22) return null;
  const approach = tween(f, [at - 14, at - 1], [0, 1], EASE_OUT);
  const press = interpolate(f, [at - 1, at + 1, at + 6], [1, 0.82, 1], clamp);
  const ripple = tween(f, [at, at + 16], [0, 1]);
  const leave = tween(f, [at + 10, at + 22], [0, 1]);
  const ox = (1 - approach) * 140 + leave * 60;
  const oy = (1 - approach) * 220 + leave * 120;
  return (
    <>
      {f >= at ? (
        <div style={{position: 'absolute', left: x - 70 * ripple, top: y - 70 * ripple, width: 140 * ripple, height: 140 * ripple,
          borderRadius: '50%', border: `4px solid rgba(47,107,255,${0.55 * (1 - ripple)})`}} />
      ) : null}
      {cursor ? (
        <svg width={56} height={56} viewBox="0 0 24 24" style={{position: 'absolute', left: x + ox - 6, top: y + oy - 3, transform: `scale(${press})`,
          transformOrigin: '6px 3px', opacity: 1 - leave, filter: 'drop-shadow(0 6px 10px rgba(0,0,0,0.35))'}}>
          <path d="M5 2.5 L5 19.5 L9.4 15.4 L12.3 21.6 L15.1 20.3 L12.2 14.2 L18.2 14.2 Z" fill="#fff" stroke="#000" strokeWidth={1.3} strokeLinejoin="round" />
        </svg>
      ) : (
        <div style={{position: 'absolute', left: x + ox - 44, top: y + oy - 44, width: 88, height: 88, borderRadius: '50%',
          background: 'radial-gradient(circle at 45% 40%, rgba(255,255,255,0.75), rgba(220,220,225,0.45))',
          boxShadow: '0 10px 26px rgba(0,0,0,0.28), inset 0 0 0 2px rgba(255,255,255,0.6)',
          transform: `scale(${press})`, opacity: approach * (1 - leave)}} />
      )}
    </>
  );
};

const Button: React.FC<{label: string; accent: string; pressAt?: number; w?: number}> = ({label, accent, pressAt, w = 460}) => {
  const f = useCurrentFrame();
  const s = pressAt === undefined ? 1 : interpolate(f, [pressAt - 2, pressAt, pressAt + 6], [1, 0.93, 1], clamp);
  return (
    <div style={{width: w, height: 92, borderRadius: 26, background: accent, color: '#fff', fontFamily: FONT, fontWeight: 700, fontSize: 36,
      display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${s})`,
      boxShadow: `0 14px 30px ${accent}55, inset 0 1px 0 rgba(255,255,255,0.3)`}}>
      {label}
    </div>
  );
};

/* ---------- screens ---------- */

const Listing: React.FC<{s: Screen; accent: string; tapAt?: number}> = ({s, accent, tapAt}) => {
  const f = useCurrentFrame();
  const card = pop(f, (s.at_frame ?? 0) + 2, 16, 1.2);
  return (
    <div style={{padding: '40px 34px', fontFamily: FONT}}>
      <div style={{fontWeight: 800, fontSize: 52, letterSpacing: '-0.04em', color: INK}}>Jobs</div>
      <div style={{marginTop: 18, height: 70, borderRadius: 20, background: '#f0f1f4', display: 'flex', alignItems: 'center', padding: '0 24px', color: '#8a8d96', fontSize: 28}}>
        🔍&nbsp; design · remote
      </div>
      {[0, 1].map((k) => (
        <div key={k} style={{marginTop: 22, height: 120, borderRadius: 24, background: '#f6f7f9', opacity: 0.6}} />
      ))}
      <div style={{marginTop: 22, borderRadius: 28, background: '#fff', padding: 28, boxShadow: `0 22px 50px rgba(20,30,60,0.18), 0 0 0 3px ${accent}`,
        transform: `scale(${0.9 + 0.1 * card}) translateY(${(1 - card) * 40}px)`, opacity: Math.min(1, card * 1.4)}}>
        <div style={{display: 'flex', gap: 20, alignItems: 'center'}}>
          <div style={{width: 84, height: 84, borderRadius: 22, background: INK, color: '#fff', fontWeight: 800, fontSize: 40, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
            {String(s.company ?? 'C')[0]}
          </div>
          <div>
            <div style={{fontWeight: 800, fontSize: 38, color: INK, letterSpacing: '-0.03em'}}>{s.title}</div>
            <div style={{fontWeight: 500, fontSize: 26, color: '#6b6e78'}}>{s.company}</div>
          </div>
        </div>
        <div style={{marginTop: 16, fontSize: 24, color: '#6b6e78'}}>{s.meta}</div>
        <div style={{marginTop: 24}}><Button label={s.cta ?? 'Apply'} accent={accent} pressAt={tapAt} w={500} /></div>
      </div>
    </div>
  );
};

const Form: React.FC<{s: Screen; accent: string; tapAt?: number}> = ({s, accent, tapAt}) => {
  const f = useCurrentFrame();
  return (
    <div style={{padding: '40px 34px', fontFamily: FONT}}>
      <div style={{fontWeight: 800, fontSize: 44, letterSpacing: '-0.04em', color: INK}}>Apply</div>
      <div style={{fontSize: 24, color: '#6b6e78', marginTop: 4}}>Product Designer · Northwind Studio</div>
      {(s.fields ?? []).map((fld: Screen, k: number) => {
        const start: number | undefined = fld.at_frame;
        const active = start !== undefined && f >= start - 2 && f < start + fld.value.length / 2.4 + 14;
        const hl = fld.highlight && (start === undefined || f >= start);
        const appear = start === undefined ? 1 : tween(f, [start - 8, start], [0.35, 1]);
        return (
          <div key={k} style={{marginTop: 26, opacity: appear}}>
            <div style={{fontSize: 24, fontWeight: 700, color: hl ? accent : '#6b6e78', letterSpacing: '0.02em', textTransform: 'uppercase'}}>{fld.label}</div>
            <div style={{marginTop: 10, minHeight: 84, borderRadius: 20, padding: '20px 24px', fontSize: fld.highlight ? 34 : 32,
              fontWeight: fld.highlight ? 700 : 500, color: INK, lineHeight: 1.25,
              background: hl ? `${accent}12` : '#f3f4f7',
              boxShadow: active || hl ? `0 0 0 3px ${accent}, 0 12px 30px ${accent}30` : 'inset 0 0 0 2px #e4e6eb'}}>
              <Typed text={fld.value} start={start} />
            </div>
          </div>
        );
      })}
      <div style={{marginTop: 40, display: 'flex', justifyContent: 'center'}}>
        <Button label={s.cta ?? 'Submit'} accent={accent} pressAt={tapAt} w={520} />
      </div>
    </div>
  );
};

const Confirm: React.FC<{s: Screen}> = ({s}) => {
  const f = useCurrentFrame();
  const at = s.at_frame ?? 0;
  const c = pop(f, at, 16, 1.6);
  const draw = tween(f, [at + 4, at + 16], [0, 1], EASE_IN_OUT);
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', fontFamily: FONT, background: '#fff'}}>
      <div style={{width: 250, height: 250, borderRadius: '50%', background: '#12b76a', transform: `scale(${c})`,
        boxShadow: '0 30px 60px rgba(18,183,106,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <svg width={150} height={150} viewBox="0 0 24 24">
          <path d="M5 12.5 L10 17.5 L19.5 7" fill="none" stroke="#fff" strokeWidth={2.8} strokeLinecap="round" strokeLinejoin="round"
            pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} />
        </svg>
      </div>
      <div style={{marginTop: 46, fontSize: 84, fontWeight: 800, letterSpacing: '-0.05em', color: INK, opacity: tween(f, [at + 6, at + 14], [0, 1])}}>{s.title}</div>
      <div style={{marginTop: 8, fontSize: 32, color: '#6b6e78', opacity: tween(f, [at + 10, at + 18], [0, 1])}}>{s.body}</div>
    </AbsoluteFill>
  );
};

const Inbox: React.FC<{s: Screen; accent: string}> = ({s, accent}) => {
  const f = useCurrentFrame();
  const arrive = s.arrive_frame ?? s.at_frame ?? 0;
  const rows: Screen[] = s.rows ?? [];
  return (
    <div style={{display: 'flex', height: '100%', fontFamily: FONT}}>
      <div style={{width: 210, background: '#f3f4f6', padding: 22}}>
        <div style={{fontWeight: 800, fontSize: 24, color: INK}}>Northwind</div>
        {['Inbox', 'Interviews', 'Offers'].map((x, k) => (
          <div key={x} style={{marginTop: 18, fontSize: 19, fontWeight: k ? 500 : 700, color: k ? '#6b6e78' : accent}}>{x}</div>
        ))}
      </div>
      <div style={{flex: 1, padding: '22px 26px'}}>
        <div style={{fontWeight: 800, fontSize: 30, color: INK, letterSpacing: '-0.03em'}}>Applications</div>
        {rows.map((r, k) => {
          const isNew = r.new;
          const t = isNew ? pop(f, arrive, 14, 1.3) : 1;
          const shift = isNew ? 0 : tween(f, [arrive, arrive + 10], [-86, 0]);
          if (isNew && f < arrive) return null;
          const glow = isNew ? Math.max(0, 1 - Math.max(0, f - arrive - 20) / 40) : 0;
          return (
            <div key={k} style={{marginTop: 14, height: 72, borderRadius: 14, padding: '0 18px', display: 'flex', alignItems: 'center', gap: 16,
              background: isNew ? `${accent}14` : '#fafafa', boxShadow: isNew ? `0 0 0 ${2 + glow * 3}px ${accent}` : 'inset 0 0 0 1px #eceef1',
              transform: `translateY(${isNew ? (1 - t) * -60 : shift}px) scale(${isNew ? 0.96 + 0.04 * t : 1})`, opacity: isNew ? Math.min(1, t * 1.5) : 1}}>
              <div style={{width: 42, height: 42, borderRadius: '50%', background: isNew ? accent : '#d6d8dd', color: '#fff', fontWeight: 800, fontSize: 20,
                display: 'flex', alignItems: 'center', justifyContent: 'center'}}>{r.name[0]}</div>
              <div style={{flex: 1}}>
                <div style={{fontWeight: 700, fontSize: 21, color: INK}}>{r.name}</div>
                <div style={{fontSize: 16, color: '#6b6e78'}}>{r.role}</div>
              </div>
              <div style={{fontSize: 15, fontWeight: 700, padding: '6px 12px', borderRadius: 999, color: isNew ? '#fff' : '#6b6e78', background: isNew ? accent : '#eceef1'}}>{r.tag}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const Detail: React.FC<{s: Screen; accent: string}> = ({s, accent}) => {
  const f = useCurrentFrame();
  const at = s.at_frame ?? 0;
  const hl = s.highlight_frame;
  return (
    <div style={{padding: '26px 34px', fontFamily: FONT, transform: `translateY(${tween(f, [at, at + 12], [40, 0])}px)`, opacity: tween(f, [at, at + 8], [0, 1])}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 16}}>
        <div style={{width: 58, height: 58, borderRadius: '50%', background: accent, color: '#fff', fontWeight: 800, fontSize: 26, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>M</div>
        <div style={{fontWeight: 800, fontSize: 32, color: INK, letterSpacing: '-0.03em'}}>{s.title}</div>
      </div>
      {(s.fields ?? []).map((fld: Screen, k: number) => {
        const sweep = fld.highlight && hl !== undefined ? tween(f, [hl, hl + 18], [0, 100], EASE_IN_OUT) : 0;
        return (
          <div key={k} style={{marginTop: 22}}>
            <div style={{fontSize: 16, fontWeight: 700, color: '#6b6e78', textTransform: 'uppercase', letterSpacing: '0.04em'}}>{fld.label}</div>
            <div style={{marginTop: 6, fontSize: fld.highlight ? 30 : 24, fontWeight: fld.highlight ? 700 : 500, color: INK, display: 'inline',
              backgroundImage: `linear-gradient(90deg, rgba(255,214,10,0.65) ${sweep}%, transparent ${sweep}%)`, padding: '2px 4px'}}>
              {fld.value}
            </div>
          </div>
        );
      })}
    </div>
  );
};

const IncomingCall: React.FC<{s: Screen; accent: string}> = ({s, accent}) => {
  const f = useCurrentFrame();
  const at = s.at_frame ?? 0;
  const appear = tween(f, [at, at + 10], [0, 1]);
  const shake = f > at + 6 ? Math.sin(f * 1.9) * 6 * Math.max(0, Math.sin((f - at) * 0.22)) : 0;
  return (
    <AbsoluteFill style={{background: 'linear-gradient(180deg,#1d2a35,#0b1218)', alignItems: 'center', fontFamily: FONT, opacity: appear}}>
      <div style={{marginTop: 220, fontSize: 28, color: 'rgba(255,255,255,0.65)'}}>incoming call…</div>
      <div style={{marginTop: 18, fontSize: 52, fontWeight: 800, color: '#fff', letterSpacing: '-0.03em', textAlign: 'center', padding: '0 30px'}}>{s.caller}</div>
      <div style={{position: 'relative', marginTop: 90, width: 220, height: 220}}>
        {[0, 1, 2].map((k) => {
          const r = ((f - at + k * 12) % 36) / 36;
          return <div key={k} style={{position: 'absolute', inset: -r * 120, borderRadius: '50%', border: `3px solid ${accent}`, opacity: (1 - r) * appear}} />;
        })}
        <div style={{position: 'absolute', inset: 0, borderRadius: '50%', background: accent, display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 100, fontWeight: 800, color: '#fff', transform: `rotate(${shake}deg)`}}>D</div>
      </div>
      <div style={{position: 'absolute', bottom: 150, display: 'flex', gap: 170}}>
        <div style={{width: 120, height: 120, borderRadius: '50%', background: '#ef4444'}} />
        <div style={{width: 120, height: 120, borderRadius: '50%', background: '#22c55e', transform: `scale(${1 + 0.06 * Math.sin(f * 0.5)})`}} />
      </div>
    </AbsoluteFill>
  );
};

/* ---------- devices ---------- */

const Phone: React.FC<{children: React.ReactNode; tilt: number}> = ({children, tilt}) => (
  <div style={{width: 640, height: 1300, borderRadius: 86, background: '#0c0c0e', padding: 16, transform: `perspective(2200px) rotateX(${tilt * 0.6}deg) rotateY(${tilt}deg)`,
    boxShadow: '0 70px 120px rgba(0,0,0,0.38), 0 20px 40px rgba(0,0,0,0.25), inset 0 0 0 3px #2a2b30'}}>
    <div style={{position: 'relative', width: '100%', height: '100%', borderRadius: 70, overflow: 'hidden', background: '#fff'}}>
      <div style={{height: 64, display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 46px', fontFamily: FONT, fontWeight: 700, fontSize: 24, color: INK}}>
        <span>2:07</span><span style={{width: 150, height: 36, borderRadius: 20, background: '#0c0c0e'}} /><span>●●● ▮</span>
      </div>
      <div style={{position: 'absolute', top: 64, left: 0, right: 0, bottom: 0}}>{children}</div>
    </div>
  </div>
);

const Laptop: React.FC<{children: React.ReactNode; tilt: number}> = ({children, tilt}) => (
  <div style={{transform: `perspective(2600px) rotateX(${8 + tilt * 0.3}deg) rotateY(${tilt}deg)`}}>
    <div style={{width: 980, height: 640, borderRadius: 30, background: '#111216', padding: 18, boxShadow: '0 60px 110px rgba(0,0,0,0.35)'}}>
      <div style={{position: 'relative', width: '100%', height: '100%', borderRadius: 14, overflow: 'hidden', background: '#fff'}}>{children}</div>
    </div>
    <div style={{margin: '0 auto', width: 1080, marginLeft: -50, height: 34, borderRadius: '0 0 30px 30px', background: 'linear-gradient(#cfd1d6,#9a9ca3)'}} />
  </div>
);

/* ---------- technique ---------- */

export const UIFlow: React.FC<ShotProps> = ({shot, local, duration}) => {
  const f = useCurrentFrame();
  const p = shot.params;
  const accent: string = p.accent ?? '#2f6bff';
  const screens: Screen[] = (p.screens ?? []).map((s: Screen) => {
    const m: Screen = {...s};
    for (const k of ['at_frame', 'tap_cta_frame', 'arrive_frame', 'highlight_frame']) if (m[k] !== undefined) m[k] = local(m[k]);
    m.fields = (s.fields ?? []).map((fl: Screen) => (fl.at_frame !== undefined ? {...fl, at_frame: local(fl.at_frame)} : fl));
    return m;
  });
  const idx = Math.max(0, screens.reduce((acc, s, k) => ((s.at_frame ?? 0) <= f + 3 ? k : acc), 0));
  const cur = screens[idx];
  const prev = idx > 0 ? screens[idx - 1] : null;
  const swap = cur.at_frame !== undefined && idx > 0 ? tween(f, [cur.at_frame - 3, cur.at_frame + 7], [0, 1], EASE_OUT) : 1;
  const taps = shot.beats.filter((b) => /tap|press|click|submit/i.test(b.action)).map((b) => local(b.frame));
  const tapAt = cur.tap_cta_frame ?? taps[0];
  const enter = tween(f, [0, 16], [0, 1], EASE_OUT);
  const tilt = (1 - enter) * 14 + Math.sin(f / 40) * 2.2 - 3;
  const isPhone = p.device !== 'laptop';
  const render = (s: Screen, pressAt?: number) => {
    switch (s.kind) {
      case 'listing': return <Listing s={s} accent={accent} tapAt={pressAt} />;
      case 'form': return <Form s={s} accent={accent} tapAt={pressAt} />;
      case 'confirm': return <Confirm s={s} />;
      case 'inbox': return <Inbox s={s} accent={accent} />;
      case 'detail': return <Detail s={s} accent={accent} />;
      case 'incoming_call': return <IncomingCall s={s} accent={accent} />;
      default: return null;
    }
  };
  // Where the tappable button sits on screen, in frame coordinates (device is centered horizontally).
  const devTop = isPhone ? 520 : 760;
  // Device content is scaled 0.86 from the top edge: screen y -> frame y = devTop + (16 + 64 + y) * 0.86.
  const btn = isPhone ? {x: 540, y: devTop + (16 + 64 + (cur.kind === 'listing' ? 760 : 735)) * 0.86} : {x: 640, y: devTop + 220};
  // Laptop: push the camera into the row/field that carries the story (micro-detail readable on a phone).
  const focusY = cur.kind === 'inbox' ? 0.24 : cur.kind === 'detail' ? 0.42 : 0.5;
  const zoomAt = cur.kind === 'inbox' ? (cur.arrive_frame ?? 0) : cur.kind === 'detail' ? (cur.highlight_frame ?? cur.at_frame ?? 0) - 6 : 0;
  const camZoom = isPhone ? 1 : 1 + tween(f, [zoomAt, zoomAt + 26], [0, 0.2], EASE_IN_OUT);
  const bg = p.background === 'asset' && p.background_image;
  return (
    <AbsoluteFill style={{background: PAPER}}>
      {bg ? (
        String(p.background_image).startsWith('missing:') ? <Pending name={p.background_image} /> : (
          <AbsoluteFill>
            <Img src={staticFile(p.background_image)} style={{width: '100%', height: '100%', objectFit: 'cover', filter: 'blur(14px) brightness(0.55) saturate(0.85)',
              transform: `scale(${1.12 + f / duration * 0.04})`}} />
          </AbsoluteFill>
        )
      ) : (
        <AbsoluteFill style={{background: `radial-gradient(ellipse 70% 45% at 50% 62%, #ffffff 0%, ${PAPER} 70%)`}} />
      )}
      {!bg ? (
        <div style={{position: 'absolute', left: 240, right: 240, top: isPhone ? 1760 : 1560, height: 60, borderRadius: '50%',
          background: 'rgba(0,0,0,0.22)', filter: 'blur(26px)'}} />
      ) : null}
      <div style={{position: 'absolute', left: 0, right: 0, top: devTop, display: 'flex', justifyContent: 'center',
        transform: `translateY(${(1 - enter) * 160}px) scale(${(isPhone ? 0.86 : 1) * (0.94 + 0.06 * enter) * camZoom})`,
        transformOrigin: isPhone ? '50% 0%' : `46% ${focusY * 100}%`, opacity: enter}}>
        {isPhone ? (
          <Phone tilt={tilt}>
            {prev && swap < 1 ? <AbsoluteFill style={{transform: `translateX(${-swap * 30}%)`, opacity: 1 - swap}}>{render(prev)}</AbsoluteFill> : null}
            <AbsoluteFill style={{transform: `translateX(${(1 - swap) * 40}%)`, opacity: swap}}>{render(cur, tapAt)}</AbsoluteFill>
          </Phone>
        ) : (
          <Laptop tilt={tilt}>
            {render(cur, tapAt)}
          </Laptop>
        )}
      </div>
      {tapAt !== undefined && p.hand !== false ? <Touch x={btn.x} y={btn.y} at={tapAt} cursor={!isPhone} /> : null}
    </AbsoluteFill>
  );
};
