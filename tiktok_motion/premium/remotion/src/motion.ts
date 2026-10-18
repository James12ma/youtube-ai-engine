import {Easing, interpolate} from 'remotion';

// One easing vocabulary for the whole piece so every move feels related.
export const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1); // expo-like settle
export const EASE_IN = Easing.bezier(0.7, 0, 0.84, 0);
export const EASE_IN_OUT = Easing.bezier(0.65, 0, 0.35, 1);

export const clampOpts = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

export const tween = (
  frame: number,
  [a, b]: [number, number],
  [from, to]: [number, number],
  easing = EASE_OUT,
) => interpolate(frame, [a, b], [from, to], {...clampOpts, easing});

/** 0 → 1 while entering, 1 → 0 while exiting (exit window ends at `exitEnd`). */
export const presence = (frame: number, start: number, exitEnd: number, inDur = 10, outDur = 10) =>
  Math.min(tween(frame, [start, start + inDur], [0, 1]), tween(frame, [exitEnd - outDur, exitEnd], [1, 0], EASE_IN));
