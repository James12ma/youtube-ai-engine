import {Easing, interpolate} from 'remotion';

export const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1);
export const EASE_IN = Easing.bezier(0.7, 0, 0.84, 0);
export const EASE_IN_OUT = Easing.bezier(0.65, 0, 0.35, 1);
export const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

export const tween = (f: number, [a, b]: [number, number], [from, to]: [number, number], easing = EASE_OUT) =>
  interpolate(f, [a, b], [from, to], {...clamp, easing});

/** Damped spring 0 -> 1 starting at `start` (no remotion spring config needed for simple pops). */
export const pop = (f: number, start: number, dur = 14, overshoot = 1.7) => {
  const t = Math.min(1, Math.max(0, (f - start) / dur));
  const s = overshoot;
  return t <= 0 ? 0 : 1 + (s + 1) * Math.pow(t - 1, 3) + s * Math.pow(t - 1, 2);
};

export const PAPER = '#ecebe7';
export const INK = '#0b0b0c';
export const MUTE = '#a3a3a6';
