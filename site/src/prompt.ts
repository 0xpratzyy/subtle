import {INSTALL, REPO, type Preset} from './data';
import {buildOverride, isTweaked, mergedStyle, pageText, type Edits, type Tweaks} from './tweaks';
import type {CPage} from './engine';

export type PromptInput = {
  preset: Preset;
  tweaks?: Tweaks;
  highlights: boolean;
  behindOn: boolean;
  edits: Edits;
  pages: CPage[];
};

const fmt = (ms: number) => (ms / 1000).toFixed(1) + 's';

export function styleJson(preset: Preset, tweaks?: Tweaks): string {
  return JSON.stringify(mergedStyle(preset, buildOverride(preset, tweaks)), null, 2) + '\n';
}

export function buildPrompt(i: PromptInput): string {
  const {preset, tweaks} = i;
  const name = preset.name;
  const over = buildOverride(preset, tweaks);
  const tweaked = isTweaked(tweaks);
  const file = '~/video.mp4';
  const L: string[] = [];
  L.push(`Install the Subtle skill from ${REPO} (${INSTALL.claude}) and caption ${file} in the \`${name}\` style.`);
  const flags: string[] = [];
  if (!i.highlights) flags.push('turn highlights off with --emphasis off');
  if (preset.behind?.enabled && !i.behindOn) flags.push('draw the giant words in front of me with --behind off');
  if (tweaks?.y != null) flags.push('keep the caption exactly where the style file puts it with --placement off');
  if (flags.length) L.push('', 'Options: ' + flags.join('; ') + '.');
  if (tweaked) {
    const parts: string[] = [];
    if (tweaks?.accent) parts.push(`accent colour ${tweaks.accent}`);
    if (tweaks?.size != null && tweaks.size !== 100) parts.push(`text size ${tweaks.size}% of the preset`);
    if (tweaks?.y != null) parts.push(`vertical position ${tweaks.y}% of the frame height`);
    if (tweaks?.case) parts.push({upper: 'UPPERCASE', sentence: 'Sentence case', lower: 'lowercase'}[tweaks.case]);
    L.push('', `Tweaks: ${parts.join(', ')}.`, '', `Save the merged style as ~/${name}.custom.json (deep-merge this override over styles/${name}.json) and render with --style ~/${name}.custom.json:`, '```json', JSON.stringify(over, null, 2), '```');
  }
  const edited = Object.keys(i.edits).map(Number).sort((a, b) => a - b).filter((k) => i.pages[k]);
  if (edited.length) {
    L.push('', 'Fix the wording: after the grouping step, edit <name>.captions.json so these pages read as below (keep the timings, spread the words evenly over each page), then render with --captions:');
    for (const k of edited) L.push(`- at ${fmt(i.pages[k].startMs)}: "${i.edits[k].trim()}"  (was "${pageText(i.pages[k]).trim()}")`);
  }
  L.push('', 'Then open the preview image and check the captions before you hand it over.');
  return L.join('\n');
}
