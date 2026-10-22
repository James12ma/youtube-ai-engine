import {Composition, staticFile} from 'remotion';
import {Film} from './Film';
import {RenderPlan} from './types';

const EMPTY: RenderPlan = {
  id: 'empty', title: '', width: 1080, height: 1920, fps: 30, durationInFrames: 30, style: 'editorial_two_world',
  voice: null, music: {asset: null, gain_db: -20, duck_db: -8}, words: [], shots: [], preview_timing: true,
  missing_assets: [],
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Film"
    component={Film}
    defaultProps={{plan: EMPTY, planFile: 'plan.json'}}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={30}
    calculateMetadata={async ({props}) => {
      // The plan is written by studio/timeline.py into public/; props can also carry it inline.
      const plan: RenderPlan =
        props.plan && props.plan.shots.length ? props.plan : await (await fetch(staticFile(props.planFile))).json();
      return {
        durationInFrames: plan.durationInFrames,
        fps: plan.fps,
        width: plan.width,
        height: plan.height,
        props: {...props, plan},
      };
    }}
  />
);
