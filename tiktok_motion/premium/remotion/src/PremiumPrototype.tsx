import React, {useEffect, useState} from 'react';
import {AbsoluteFill, Audio, Img, continueRender, delayRender, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {Dialog, Cursor} from './components/Dialog';
import {Bokeh, FilmFinish, SketchArcs, Swoosh} from './components/Finish';
import {BigWord, MUTE, SmallLine, Word} from './components/Kinetic';
import {clampOpts, tween} from './motion';
import {B, COPY} from './timeline';

export type PrototypeProps = {platesDir: string; withAudio: boolean};

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

const words = (list: string[], mute: number[]): Word[] =>
  list.map((text, i) => ({text, tone: mute.includes(i) ? 'mute' : 'ink'}));

const TEXT_TOP = 286;

export const PremiumPrototype: React.FC<PrototypeProps> = ({platesDir, withAudio}) => {
  useFonts();
  const frame = useCurrentFrame();
  // Tiny impact bump when the hero sphere lands, and a breath on the click.
  const land = B.hero_drop[0] + (B.hero_drop[1] - B.hero_drop[0]) * 0.62;
  const bump = interpolate(frame, [land, land + 2, land + 8], [0, 7, 0], clampOpts);
  const breath = interpolate(frame, [B.cursor_click, B.cursor_click + 3, B.cursor_click + 16], [1, 1.012, 1], clampOpts);
  const pad = String(frame).padStart(4, '0');

  return (
    <AbsoluteFill style={{backgroundColor: '#e9e9e7', overflow: 'hidden'}}>
      <AbsoluteFill style={{transform: `translateY(${bump}px) scale(${breath})`}}>
        <Img src={staticFile(`${platesDir}/plate_${pad}.png`)} style={{width: '100%', height: '100%'}} />
      </AbsoluteFill>

      <SketchArcs start={B.line2[0] + 2} end={B.line2[1]} />

      {/* Act 1 */}
      <div style={{position: 'absolute', top: TEXT_TOP, width: '100%'}}>
        <SmallLine words={words(COPY.line1_small, [2, 4])} start={B.line1[0]} exitEnd={B.dialog_in[0] - 2} />
        <div style={{marginTop: 6}}>
          <BigWord text={COPY.line1_big} start={B.line1_big[0]} exitEnd={B.dialog_in[0] - 2} />
        </div>
      </div>

      {/* Act 2: the edit */}
      <Dialog
        inStart={B.dialog_in[0]}
        click={B.cursor_click}
        outStart={B.dialog_out[0]}
        outEnd={B.dialog_out[1]}
        title={COPY.dialog_title}
        body={COPY.dialog_body}
      />
      <Cursor start={B.dialog_in[0] + 8} click={B.cursor_click} end={B.dialog_out[1] - 2} />

      <div style={{position: 'absolute', top: TEXT_TOP, width: '100%'}}>
        <SmallLine words={words(COPY.line2_small, [1])} start={B.line2[0]} exitEnd={B.line2[1]} />
        <div style={{marginTop: 6}}>
          <BigWord text={COPY.line2_big} start={B.line2[0] + 12} exitEnd={B.line2[1]} />
        </div>
      </div>
      <Swoosh start={B.line2[0] + 30} end={B.line2[1]} y={TEXT_TOP + 236} />

      {/* Act 3: the result */}
      <Bokeh start={B.line3[0] - 10} />
      <div style={{position: 'absolute', top: TEXT_TOP, width: '100%'}}>
        <SmallLine words={words(COPY.line3_small, [0])} start={B.line3[0]} exitEnd={99999} size={60} stagger={6} />
        <div style={{marginTop: 6}}>
          <BigWord text={COPY.line3_big} start={B.line3[0] + 12} exitEnd={99999} size={160} />
        </div>
      </div>

      <IndexLabel />
      <FilmFinish />
      {withAudio && <Audio src={staticFile('audio/score.wav')} />}
    </AbsoluteFill>
  );
};

/** Editorial chapter marker, top-left. */
const IndexLabel: React.FC = () => {
  const frame = useCurrentFrame();
  const chapter = frame < B.dialog_in[0] ? '01' : frame < B.line3[0] ? '02' : '03';
  const t = tween(frame, [4, 18], [0, 1]);
  return (
    <div
      style={{
        position: 'absolute',
        top: 120,
        left: 72,
        right: 72,
        display: 'flex',
        justifyContent: 'space-between',
        fontFamily: 'InterTight',
        fontWeight: 700,
        fontSize: 24,
        letterSpacing: '0.18em',
        color: MUTE,
        opacity: t,
        transform: `translateY(${(1 - t) * 12}px)`,
      }}
    >
      <span>N° {chapter} / 03</span>
      <span>FOCUS</span>
    </div>
  );
};
