import React from 'react';
import {random, useCurrentFrame} from 'remotion';
import {EASE_IN_OUT, EASE_OUT, tween} from '../motion';

/** Out-of-focus grey discs drifting in the foreground (parallax against the 3D plate). */
export const Bokeh: React.FC<{start: number}> = ({start}) => {
  const frame = useCurrentFrame();
  // Keep discs on the frame edges so they never sit on the hero object or the headline.
  const discs = Array.from({length: 9}, (_, i) => ({
    x: random(`bx${i}`) < 0.5 ? 20 + random(`bxl${i}`) * 170 : 890 + random(`bxr${i}`) * 170,
    y: 640 + random(`by${i}`) * 1200,
    r: 26 + random(`br${i}`) * 70,
    blur: 3 + random(`bb${i}`) * 9,
    depth: 0.4 + random(`bd${i}`) * 1.2,
    delay: random(`bt${i}`) * 40,
  }));
  return (
    <>
      {discs.map((d, i) => {
        const t = tween(frame, [start + d.delay, start + d.delay + 24], [0, 1], EASE_OUT);
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: d.x - d.r + (frame - start) * -0.35 * d.depth,
              top: d.y - d.r + (frame - start) * -0.6 * d.depth,
              width: d.r * 2 * (0.6 + 0.4 * t),
              height: d.r * 2 * (0.6 + 0.4 * t),
              borderRadius: '50%',
              background: 'radial-gradient(circle at 40% 35%, #d9d9db, #bdbdc0)',
              filter: `blur(${d.blur}px)`,
              opacity: 0.55 * t,
            }}
          />
        );
      })}
    </>
  );
};

/** Hand-drawn style hairline arcs that sweep across the frame (editorial accent). */
export const SketchArcs: React.FC<{start: number; end: number}> = ({start, end}) => {
  const frame = useCurrentFrame();
  const draw = tween(frame, [start, start + 34], [0, 1], EASE_IN_OUT);
  const fade = tween(frame, [end - 14, end], [1, 0]);
  const paths = [
    'M -60 760 C 260 840, 520 1180, 1140 1260',
    'M -40 1640 C 300 1500, 700 980, 1160 860',
  ];
  return (
    <svg width={1080} height={1920} style={{position: 'absolute', inset: 0, opacity: fade}}>
      {paths.map((d, i) => (
        <path
          key={i}
          d={d}
          fill="none"
          stroke="#111"
          strokeWidth={2.4}
          strokeLinecap="round"
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={1 - tween(frame, [start + i * 6, start + i * 6 + 34], [0, 1], EASE_IN_OUT) * (draw > 0 ? 1 : 0)}
        />
      ))}
    </svg>
  );
};

/** Underline swoosh with arrow head drawn under a headline. */
export const Swoosh: React.FC<{start: number; end: number; y: number}> = ({start, end, y}) => {
  const frame = useCurrentFrame();
  const t = tween(frame, [start, start + 22], [0, 1], EASE_IN_OUT);
  const head = tween(frame, [start + 18, start + 26], [0, 1]);
  const fade = tween(frame, [end - 10, end], [1, 0]);
  return (
    <svg width={1080} height={200} style={{position: 'absolute', left: 0, top: y, opacity: fade}}>
      <path
        d="M 250 40 C 380 120, 640 128, 830 56"
        fill="none"
        stroke="#111"
        strokeWidth={4}
        strokeLinecap="round"
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={1 - t}
      />
      <path d="M 806 44 L 834 54 L 816 80" fill="none" stroke="#111" strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" opacity={head} />
    </svg>
  );
};

/** Animated film grain + soft vignette: kills banding on the white paper and adds a filmic finish. */
export const FilmFinish: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(ellipse 85% 70% at 50% 48%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.16) 100%)',
        }}
      />
      <svg width={1080} height={1920} style={{position: 'absolute', inset: 0, opacity: 0.07, mixBlendMode: 'multiply'}}>
        <filter id="grain">
          <feTurbulence type="fractalNoise" baseFrequency={0.9} numOctaves={2} seed={frame % 24} stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter="url(#grain)" />
      </svg>
    </>
  );
};
