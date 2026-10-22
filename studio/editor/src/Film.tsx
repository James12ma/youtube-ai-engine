import React, {useEffect, useState} from 'react';
import {AbsoluteFill, Audio, Sequence, continueRender, delayRender, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {FilmFinish, TransitionIn, TransitionOutDip} from './fx/Finish';
import {KineticWords} from './fx/KineticWords';
import {Clip, Still25D} from './techniques/Story';
import {UIFlow} from './techniques/UIFlow';
import {DataTransfer} from './techniques/DataTransfer';
import {DotsSubtract, Object3D, Title} from './techniques/Explain';
import {PAPER, clamp} from './motion';
import {RenderPlan, ShotPlan, ShotProps} from './types';

const FONTS: [string, string, string, string][] = [
  ['InterTight', 'fonts/inter-tight-latin-500-normal.woff2', '500', 'normal'],
  ['InterTight', 'fonts/inter-tight-latin-700-normal.woff2', '700', 'normal'],
  ['InterTight', 'fonts/inter-tight-latin-800-normal.woff2', '800', 'normal'],
  ['PlayfairItalic', 'fonts/playfair-display-latin-900-italic.woff2', '900', 'italic'],
];

const useFonts = () => {
  const [handle] = useState(() => delayRender('fonts'));
  useEffect(() => {
    Promise.all(
      FONTS.map(([family, file, weight, style]) =>
        new FontFace(family, `url(${staticFile(file)})`, {weight, style}).load().then((f) => document.fonts.add(f)),
      ),
    ).then(() => continueRender(handle));
  }, [handle]);
};

const TECHNIQUES: Record<string, React.FC<ShotProps>> = {
  still_2_5d: Still25D,
  clip: Clip,
  ui_flow: UIFlow,
  data_transfer: DataTransfer,
  dots_subtract: DotsSubtract,
  object_3d: Object3D,
  title: Title,
};

const SFX_FILES: Record<string, string> = {
  tap: 'sfx/tap.wav', click: 'sfx/click.wav', whoosh: 'sfx/whoosh.wav', pop: 'sfx/pop.wav', ding: 'sfx/ding.wav',
  thud: 'sfx/thud.wav', ring: 'sfx/ring.wav', type: 'sfx/type.wav', swoosh_up: 'sfx/swoosh_up.wav',
};

const ShotLayer: React.FC<{shot: ShotPlan; next?: ShotPlan}> = ({shot, next}) => {
  const Tech = TECHNIQUES[shot.technique];
  const duration = shot.to - shot.from;
  const local = (abs: number) => abs - shot.from;
  return (
    <AbsoluteFill style={{backgroundColor: shot.world === 'story' ? '#050506' : PAPER, overflow: 'hidden'}}>
      <TransitionIn kind={shot.transition.kind} frames={shot.transition.frames}>
        {Tech ? <Tech shot={shot} local={local} duration={duration} /> : null}
        <KineticWords shot={shot} local={local} duration={duration} />
      </TransitionIn>
      {next && next.transition.kind.startsWith('dip') ? (
        <TransitionOutDip kind={next.transition.kind} frames={next.transition.frames} duration={duration} />
      ) : null}
    </AbsoluteFill>
  );
};

export const Film: React.FC<{plan: RenderPlan; planFile: string}> = ({plan}) => {
  useFonts();
  const frame = useCurrentFrame();
  // Music ducks under narration words.
  const speaking = plan.words.some((w) => frame >= w.from - 4 && frame <= w.to + 6);
  const musicDb = plan.music.gain_db + (speaking ? plan.music.duck_db : 0);
  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      {plan.shots.map((shot, k) => (
        <Sequence key={shot.id} from={shot.from} durationInFrames={shot.to - shot.from} name={`${shot.id} · ${shot.technique}`}>
          <ShotLayer shot={shot} next={plan.shots[k + 1]} />
        </Sequence>
      ))}
      <FilmFinish />
      {plan.voice ? <Audio src={staticFile(plan.voice)} /> : null}
      {plan.music.asset ? (
        <Audio
          src={staticFile(plan.music.asset)}
          volume={(f) => interpolate(f, [0, 20, plan.durationInFrames - 30, plan.durationInFrames], [0, 1, 1, 0], clamp) * Math.pow(10, musicDb / 20)}
        />
      ) : null}
      {plan.shots.flatMap((s) =>
        s.sfx.map((c, i) =>
          SFX_FILES[c.sound] ? (
            <Sequence key={`${s.id}-sfx-${i}`} from={Math.max(0, c.frame - 1)} durationInFrames={90}>
              <Audio src={staticFile(SFX_FILES[c.sound])} volume={c.gain} />
            </Sequence>
          ) : null,
        ),
      )}
      {plan.preview_timing ? <PreviewBadge missing={plan.missing_assets} /> : null}
    </AbsoluteFill>
  );
};

const PreviewBadge: React.FC<{missing: string[]}> = ({missing}) => (
  <div style={{position: 'absolute', left: 24, bottom: 24, padding: '8px 14px', borderRadius: 10, background: 'rgba(200,30,40,0.85)',
    color: '#fff', fontFamily: 'InterTight', fontWeight: 700, fontSize: 22}}>
    PREVIEW · estimated timing{missing.length ? ` · ${missing.length} assets pending` : ''}
  </div>
);
