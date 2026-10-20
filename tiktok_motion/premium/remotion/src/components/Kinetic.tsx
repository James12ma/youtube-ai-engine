import React from 'react';
import {useCurrentFrame} from 'remotion';
import {EASE_IN, EASE_OUT, tween} from '../motion';

export const INK = '#0b0b0c';
export const MUTE = '#a3a3a6';

export type Word = {text: string; tone?: 'ink' | 'mute'};

const exitStyle = (frame: number, exitEnd: number): React.CSSProperties => {
  const t = tween(frame, [exitEnd - 10, exitEnd], [0, 1], EASE_IN);
  return {
    opacity: 1 - t,
    filter: `blur(${t * 18}px)`,
    transform: `translateY(${-46 * t}px) scale(${1 - 0.04 * t})`,
  };
};

/** Small bold sans line: words land one by one out of a soft blur. */
export const SmallLine: React.FC<{words: Word[]; start: number; exitEnd: number; stagger?: number; size?: number}> = ({
  words,
  start,
  exitEnd,
  stagger = 4,
  size = 56,
}) => {
  const frame = useCurrentFrame();
  return (
    <div style={{display: 'flex', justifyContent: 'center', gap: size * 0.26, ...exitStyle(frame, exitEnd)}}>
      {words.map((w, i) => {
        const s = start + i * stagger;
        const t = tween(frame, [s, s + 11], [0, 1], EASE_OUT);
        return (
          <span
            key={i}
            style={{
              fontFamily: 'InterTight',
              fontWeight: 800,
              fontSize: size,
              letterSpacing: '-0.05em',
              color: w.tone === 'mute' ? MUTE : INK,
              opacity: t,
              filter: `blur(${(1 - t) * 12}px)`,
              transform: `translateY(${(1 - t) * 30}px)`,
              display: 'inline-block',
              textShadow: w.tone === 'mute' ? 'none' : '0 6px 14px rgba(0,0,0,0.10)',
            }}
          >
            {w.text}
          </span>
        );
      })}
    </div>
  );
};

/** Condensed italic serif headline: letters cascade in, whole word settles from a slight overscale. */
export const BigWord: React.FC<{text: string; start: number; exitEnd: number; size?: number; condense?: number}> = ({
  text,
  start,
  exitEnd,
  size = 150,
  condense = 0.8,
}) => {
  const frame = useCurrentFrame();
  const settle = tween(frame, [start, start + 34], [1.12, 1], EASE_OUT);
  const track = tween(frame, [start, start + 40], [0.04, -0.035], EASE_OUT);
  const letters = [...text];
  return (
    <div style={{display: 'flex', justifyContent: 'center', ...exitStyle(frame, exitEnd)}}>
      <div
        style={{
          transform: `scale(${settle * condense}, ${settle})`,
          whiteSpace: 'pre',
          fontFamily: 'PlayfairItalic',
          fontStyle: 'italic',
          fontWeight: 900,
          fontSize: size,
          lineHeight: 0.92,
          letterSpacing: `${track}em`,
          color: INK,
          textShadow: '0 22px 30px rgba(0,0,0,0.20), 0 4px 6px rgba(0,0,0,0.12)',
        }}
      >
        {letters.map((ch, i) => {
          const s = start + i * 1.6;
          const t = tween(frame, [s, s + 9], [0, 1], EASE_OUT);
          return (
            <span
              key={i}
              style={{
                display: 'inline-block',
                opacity: t,
                filter: `blur(${(1 - t) * 10}px)`,
                transform: `translateY(${(1 - t) * 0.42 * size}px) scaleY(${1 + (1 - t) * 0.35})`,
                transformOrigin: '50% 100%',
              }}
            >
              {ch}
            </span>
          );
        })}
      </div>
    </div>
  );
};
