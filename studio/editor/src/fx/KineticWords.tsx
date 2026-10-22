import React from 'react';
import {useCurrentFrame} from 'remotion';
import {EASE_IN, EASE_OUT, INK, MUTE, tween} from '../motion';
import {ShotProps, WordF} from '../types';

type Run = {big: boolean; words: WordF[]};

/** Split the shot's words into alternating small/big runs, preserving order (reference grammar). */
const runs = (words: WordF[], emphasis: Set<number>): Run[] => {
  const out: Run[] = [];
  for (const w of words) {
    const big = emphasis.has(w.i);
    if (out.length && out[out.length - 1].big === big) out[out.length - 1].words.push(w);
    else out.push({big, words: [w]});
  }
  return out;
};

const Word: React.FC<{w: WordF; at: number; big: boolean; mute: boolean; dark: boolean; size: number}> = ({w, at, big, mute, dark, size}) => {
  const f = useCurrentFrame();
  const t = tween(f, [at, at + 9], [0, 1], EASE_OUT);
  const ink = dark ? '#fff' : INK;
  const muted = dark ? 'rgba(255,255,255,0.62)' : MUTE;
  return (
    <span
      style={{
        display: 'inline-block',
        fontFamily: big ? 'PlayfairItalic' : 'InterTight',
        fontStyle: big ? 'italic' : 'normal',
        fontWeight: big ? 900 : 800,
        fontSize: size,
        letterSpacing: big ? '-0.03em' : '-0.045em',
        textTransform: big ? 'uppercase' : 'none',
        color: mute ? muted : ink,
        opacity: t,
        filter: `blur(${(1 - t) * (big ? 12 : 9)}px)`,
        transform: `translateY(${(1 - t) * (big ? 0.35 : 0.4) * size}px) scaleY(${big ? 1 + (1 - t) * 0.25 : 1})`,
        transformOrigin: '50% 100%',
        textShadow: dark
          ? '0 4px 18px rgba(0,0,0,0.65), 0 1px 3px rgba(0,0,0,0.6)'
          : big ? '0 18px 26px rgba(0,0,0,0.18), 0 3px 5px rgba(0,0,0,0.12)' : '0 5px 12px rgba(0,0,0,0.08)',
        marginRight: big ? size * 0.3 : size * 0.24,
      }}
    >
      {w.text}
    </span>
  );
};

export const KineticWords: React.FC<ShotProps> = ({shot, local, duration}) => {
  const f = useCurrentFrame();
  const {text} = shot;
  if (text.mode === 'none') return null;
  let words = text.words;
  if (text.show_words) words = words.filter((w) => w.i >= text.show_words![0] && w.i <= text.show_words![1]);
  const emphasis = new Set(text.emphasis);
  const mute = new Set(text.mute);
  const dark = shot.world === 'story' || shot.params.background === 'asset' || shot.params.background === 'dark';
  const out = tween(f, [duration - 7, duration], [0, 1], EASE_IN);
  const exit: React.CSSProperties = {opacity: 1 - out, filter: `blur(${out * 14}px)`, transform: `translateY(${-30 * out}px)`};
  const pos: React.CSSProperties =
    text.position === 'top' ? {top: 200} : text.position === 'bottom' ? {bottom: 330} : {top: 0, bottom: 0, justifyContent: 'center'};

  if (text.mode === 'center_word') {
    // Only the most recent run is on screen: one idea at a time, replaced on each spoken word group.
    const said = words.filter((w) => local(w.from) <= f);
    if (!said.length) return null;
    const last = said[said.length - 1];
    const isBig = emphasis.has(last.i);
    const group = isBig ? said.filter((w) => emphasis.has(w.i) && last.i - w.i < 3) : [last];
    return (
      <div style={{position: 'absolute', left: 60, right: 60, display: 'flex', flexDirection: 'column', alignItems: 'center', ...pos, ...exit}}>
        <div style={{display: 'flex', flexWrap: 'nowrap', justifyContent: 'center', whiteSpace: 'nowrap', transform: isBig ? 'scaleX(0.82)' : undefined}}>
          {group.map((w) => (
            <Word key={w.i} w={w} at={local(w.from)} big={isBig} mute={mute.has(w.i)} dark={dark} size={isBig ? Math.min(170, 1150 / (0.66 * Math.max(4, group.map((x) => x.text).join(' ').length))) : 96} />
          ))}
        </div>
      </div>
    );
  }

  const stack = text.mode === 'stack';
  const headline = text.mode === 'headline';
  const rs = runs(words, emphasis);
  const crowd = rs.length > 2 ? 0.8 : 1; // keep the text block out of the subject's space
  // Big runs never wrap: size them from their length (Playfair caps ~0.62em wide before the 0.82 condense).
  const bigSize = (r: Run) => Math.min(headline ? 168 : 150, 1150 / (0.66 * Math.max(4, r.words.map((w) => w.text).join(' ').length))) * crowd;
  return (
    <div style={{position: 'absolute', left: 56, right: 56, display: 'flex', flexDirection: 'column', alignItems: 'center', ...pos, ...exit}}>
      {rs.map((r, k) => (
        <div
          key={k}
          style={{
            display: 'flex', flexWrap: r.big ? 'nowrap' : 'wrap', justifyContent: 'center', flexDirection: stack ? 'column' : 'row', whiteSpace: 'nowrap',
            alignItems: 'center', lineHeight: r.big ? 0.92 : 1.05, marginTop: k ? (r.big ? -4 : 6) : 0,
            transform: r.big ? 'scaleX(0.82)' : undefined,
          }}
        >
          {r.words.map((w) => (
            <Word key={w.i} w={w} at={local(w.from)} big={r.big} mute={mute.has(w.i)} dark={dark}
              size={r.big ? bigSize(r) : (headline ? 66 : 58) * crowd} />
          ))}
        </div>
      ))}
    </div>
  );
};
