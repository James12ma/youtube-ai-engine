import {Composition} from 'remotion';
import {PremiumPrototype} from './PremiumPrototype';
import {OwnerPremium,OwnerPlan} from './OwnerPremium';
import {GeoCinematic,GeoPlan} from './GeoCinematic';
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
  <Composition id="GeoCinematic" component={GeoCinematic} durationInFrames={360} fps={30} width={1280} height={720}
    defaultProps={{plan:{geo_clip:'job/god_eye_director.mp4',audio:'job/speech_0.wav',durationInFrames:360,geo_attribution:'Natural Earth; original illustrative route'} as GeoPlan}}
    calculateMetadata={({props})=>({durationInFrames:props.plan.durationInFrames})}/>
  <Composition id="OwnerPremium" component={OwnerPremium} durationInFrames={300} fps={30} width={1080} height={1920}
    defaultProps={{plan:{title:"",scenes:[],durationInFrames:300,fps:30,width:1080,height:1920} as OwnerPlan}}
    calculateMetadata={({props})=>({durationInFrames:props.plan.durationInFrames})}/>
  </>
);
