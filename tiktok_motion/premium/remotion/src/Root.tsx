import {Composition} from 'remotion';
import {PremiumPrototype} from './PremiumPrototype';
import {TL} from './timeline';

export const RemotionRoot: React.FC = () => (
  <Composition
    id="PremiumPrototype"
    component={PremiumPrototype}
    durationInFrames={TL.frames}
    fps={TL.fps}
    width={TL.width}
    height={TL.height}
    defaultProps={{platesDir: 'plates', withAudio: true}}
  />
);
