import {staticFile} from 'remotion';
import type {FontSpec, Style} from './types';

const loaded = new Set<string>();

/** Every {family, file, weight} object anywhere in the style JSON is a font to load from fonts/. */
export function fontSpecs(style: unknown, out: FontSpec[] = []): FontSpec[] {
  if (style && typeof style === 'object') {
    const o = style as Record<string, any>;
    if (typeof o.file === 'string' && typeof o.family === 'string') out.push(o as FontSpec);
    else for (const v of Object.values(o)) fontSpecs(v, out);
  }
  return out;
}

/**
 * Bundled fonts that cannot draw every character a caption may carry (checked against each file's cmap for
 * 0-9 $ ₹ € £ % , . x). A word with a missing character is drawn, and measured, in the closest font that has it.
 */
const PLAYFAIR_ITALIC: FontSpec = {family: 'Playfair Display Medium Italic', file: 'PlayfairDisplay-MediumItalic.ttf', weight: 500};
export const GLYPH_GAPS: Record<string, {missing: string; fallback: FontSpec}> = {
  'CourierPrime-Bold.ttf': {missing: '₹', fallback: {family: 'Inter Bold', file: 'Inter-Bold.ttf', weight: 700}},
  'CourierPrime-Regular.ttf': {missing: '₹', fallback: {family: 'Inter Regular', file: 'Inter-Regular.ttf', weight: 400}},
  'InstrumentSerif-Italic.ttf': {missing: '₹', fallback: PLAYFAIR_ITALIC},
  'InstrumentSerif-Regular.ttf': {missing: '₹', fallback: PLAYFAIR_ITALIC},
  'ArchivoBlack-Regular.ttf': {missing: '₹', fallback: {family: 'Montserrat Black', file: 'Montserrat-Black.ttf', weight: 900}},
  'PinyonScript-Regular.ttf': {missing: '₹', fallback: PLAYFAIR_ITALIC},
  'AbrilFatface-Regular.ttf': {missing: '₹', fallback: {family: 'Playfair Display Black Italic', file: 'PlayfairDisplay-BlackItalic.ttf', weight: 900}},
  'Corben-Bold.ttf': {missing: '₹', fallback: {family: 'Playfair Display Black Italic', file: 'PlayfairDisplay-BlackItalic.ttf', weight: 900}},
  'GloriaHallelujah-Regular.ttf': {missing: '₹', fallback: {family: 'Caveat SemiBold', file: 'Caveat-SemiBold.ttf', weight: 600}},
  'LibreBaskerville-wght.ttf': {missing: '₹', fallback: PLAYFAIR_ITALIC},
  'ReenieBeanie-Regular.ttf': {missing: '₹', fallback: {family: 'Caveat SemiBold', file: 'Caveat-SemiBold.ttf', weight: 600}},
};

/**
 * Indian scripts and Urdu. No style's own font has these letters, so a word written in one of them is drawn, and
 * measured, in the matching Noto font at the style's weight (all are variable fonts; Nastaliq covers 400 to 700).
 * Words in Latin letters keep the style's font, so a Hinglish caption looks exactly like an English one.
 */
type ScriptFont = {name: string; test: RegExp; family: string; file: string; min: number; max: number};
const RTL_RE = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/;
export const SCRIPT_FONTS: ScriptFont[] = [
  {name: 'Devanagari', test: /[\u0900-\u097F]/, family: 'Noto Sans Devanagari', file: 'NotoSansDevanagari-wght.ttf', min: 100, max: 900},
  {name: 'Bengali', test: /[\u0980-\u09FF]/, family: 'Noto Sans Bengali', file: 'NotoSansBengali-wght.ttf', min: 100, max: 900},
  {name: 'Gurmukhi', test: /[\u0A00-\u0A7F]/, family: 'Noto Sans Gurmukhi', file: 'NotoSansGurmukhi-wght.ttf', min: 100, max: 900},
  {name: 'Gujarati', test: /[\u0A80-\u0AFF]/, family: 'Noto Sans Gujarati', file: 'NotoSansGujarati-wght.ttf', min: 100, max: 900},
  {name: 'Odia', test: /[\u0B00-\u0B7F]/, family: 'Noto Sans Oriya', file: 'NotoSansOriya-wght.ttf', min: 100, max: 900},
  {name: 'Tamil', test: /[\u0B80-\u0BFF]/, family: 'Noto Sans Tamil', file: 'NotoSansTamil-wght.ttf', min: 100, max: 900},
  {name: 'Telugu', test: /[\u0C00-\u0C7F]/, family: 'Noto Sans Telugu', file: 'NotoSansTelugu-wght.ttf', min: 100, max: 900},
  {name: 'Kannada', test: /[\u0C80-\u0CFF]/, family: 'Noto Sans Kannada', file: 'NotoSansKannada-wght.ttf', min: 100, max: 900},
  {name: 'Malayalam', test: /[\u0D00-\u0D7F]/, family: 'Noto Sans Malayalam', file: 'NotoSansMalayalam-wght.ttf', min: 100, max: 900},
  {name: 'Urdu', test: RTL_RE, family: 'Noto Nastaliq Urdu', file: 'NotoNastaliqUrdu-wght.ttf', min: 400, max: 700},
];

/** The script font for `text`, if it is written in an Indian script or Urdu. */
export const scriptFont = (text: string) => SCRIPT_FONTS.find((s) => s.test.test(text));

/** Written right to left (Urdu, Arabic script). */
export const isRtl = (text: string) => RTL_RE.test(text);

/**
 * The letters of a word for styles that animate one letter at a time. A word in an Indian script or Urdu stays whole:
 * its letters join and stack (conjuncts, vowel signs, Nastaliq), so splitting it would draw broken shapes.
 */
export const letters = (text: string): string[] => (scriptFont(text) ? [text] : [...text]);

/** `font`, or its fallback when `text` has a character the font lacks (an Indian script, Urdu, or a missing ₹). */
export function fontWithGlyphs(font: FontSpec, text: string): FontSpec {
  const sc = scriptFont(text);
  if (sc) return {family: sc.family, file: sc.file, weight: Math.min(sc.max, Math.max(sc.min, font.weight ?? 400))};
  const g = GLYPH_GAPS[font.file];
  return g && [...g.missing].some((ch) => text.includes(ch)) ? g.fallback : font;
}

/** Loads the style's fonts, plus the script fonts `text` (every caption word) needs. */
export async function loadFonts(style: Style, text = '') {
  const specs = fontSpecs(style);
  for (const f of [...specs]) if (GLYPH_GAPS[f.file]) specs.push(GLYPH_GAPS[f.file].fallback);
  for (const sc of SCRIPT_FONTS) if (sc.test.test(text)) specs.push({family: sc.family, file: sc.file, weight: sc.min});
  await Promise.all(
    specs.map(async (f) => {
      const key = `${f.family}|${f.file}`;
      if (loaded.has(key)) return;
      // A variable font (file name holds `wght`) is registered with its whole weight range, so the CSS weight picks the
      // instance; with a single weight the browser keeps the font's default (lightest) instance.
      const weight = /wght/.test(f.file) ? '100 900' : String(f.weight);
      const face = new FontFace(f.family, `url(${staticFile(f.file)})`, {weight});
      await face.load();
      document.fonts.add(face);
      loaded.add(key);
    }),
  );
  await document.fonts.ready;
}
