// Mirror of studio/timeline.py build_plan() output. Python is the source of truth.
export type WordF = {i: number; text: string; from: number; to: number};

export type TextSpec = {
  mode: 'none' | 'words' | 'headline' | 'stack' | 'center_word';
  emphasis: number[];
  mute: number[];
  position: 'top' | 'center' | 'bottom';
  show_words: [number, number] | null;
  words: WordF[];
};

export type Camera = {move: string; intensity: number; focus: [number, number]};
export type TransitionSpec = {kind: string; frames: number; match_entity: string | null};
export type Beat = {action: string; actor: string | null; object: string | null; frame: number};
export type Sfx = {sound: string; frame: number; gain: number};

export type ShotPlan = {
  id: string;
  world: 'story' | 'explain' | 'screen' | 'map' | 'footage';
  technique: string;
  from: number;
  to: number;
  params: Record<string, any>;
  camera: Camera;
  transition: TransitionSpec;
  text: TextSpec;
  beats: Beat[];
  sfx: Sfx[];
};

export type RenderPlan = {
  id: string;
  title: string;
  width: number;
  height: number;
  fps: number;
  durationInFrames: number;
  style: string;
  voice: string | null;
  music: {asset: string | null; gain_db: number; duck_db: number};
  words: WordF[];
  shots: ShotPlan[];
  preview_timing: boolean;
  missing_assets: string[];
};

// Inside a shot, techniques receive absolute frames converted to shot-local frames.
export type ShotProps = {shot: ShotPlan; local: (absFrame: number) => number; duration: number};
