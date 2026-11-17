export type CWord = {text: string; startMs: number; endMs: number; line?: number; emphasis?: boolean};
export type CPage = {startMs: number; endMs: number; words: CWord[]};
/** `front`: draw this giant word in front of the speaker (numbers), not behind. */
export type CBig = {text: string; startMs: number; endMs: number; front?: boolean};
export type CaptionsFile = {
  version: number;
  video: {width: number; height: number; fps: number; durationMs: number};
  style: string;
  pages: CPage[];
  big?: CBig[];
  /** Music styles: tempo, every beat and every bar start in ms (from scripts/beats.py). Absent when the audio has no clear pulse. */
  beats?: {bpm: number; times: number[]; downbeats: number[]};
};
export type FontSpec = {family: string; file: string; weight: number};
export type Layer = 'all' | 'behind' | 'front' | 'mask';

/** A style preset (styles/<name>.json). Sizes are % of frame height. Style-specific keys live in `anim` and friends. */
export type Style = {
  name: string;
  font: FontSpec;
  emphasisFont?: FontSpec;
  /** How an emphasised word looks in this style: colours, font, scale. Keys are private to each style. */
  emphasis?: Record<string, any>;
  noteFont?: FontSpec;
  case: 'upper' | 'sentence' | 'lower';
  size: number;
  wideScale?: number;
  lineHeight?: number;
  letterSpacing?: number;
  color: string;
  activeColor?: string;
  dimColor?: string | null;
  shadow?: {x: number; y: number; blur: number; color: string} | null;
  container?: Record<string, any> | null;
  backdropBlur?: number;
  position: {x?: number; y: number; marginX: number};
  page: {maxLines?: number; minFrames?: number};
  anim: Record<string, any> & {type: string};
  behind?: {
    enabled: boolean;
    bigY?: number;
    frontY?: number;
    frontWidth?: number;
    bigWidth?: number;
    bigMaxSize?: number;
    bigOpacity?: number;
    bigFont?: FontSpec;
    bigColor?: string;
  };
};

/** Frame geometry: pixel size, fps, and whether the video is landscape. */
export type Frame = {W: number; H: number; fps: number; wide: boolean};
export type Box = {x: number; y: number; w: number; h: number};
