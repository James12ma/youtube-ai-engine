import {Composition} from 'remotion';
import {PremiumPrototype} from './PremiumPrototype';
import {OwnerPremium,OwnerPlan} from './OwnerPremium';
import {TL} from './timeline';

export const RemotionRoot: React.FC = () => (
  <>
  <Composition
    id="PremiumPrototype"
    component={PremiumPrototype}
    durationInFrames={TL.frames}
    fps={TL.fps}
    width={TL.width}
    height={TL.height}
    defaultProps={{platesDir: 'plates', withAudio: true}}
  />
  <Composition id="OwnerPremium" component={OwnerPremium} durationInFrames={300} fps={30} width={1080} height={1920}
    defaultProps={{plan:{title:"",scenes:[],durationInFrames:300,fps:30,width:1080,height:1920} as OwnerPlan}}
    calculateMetadata={({props})=>({durationInFrames:props.plan.durationInFrames})}/>
  </>
);
