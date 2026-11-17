import React, {useEffect, useMemo, useState} from 'react';
import {AbsoluteFill, cancelRender, continueRender, delayRender, useCurrentFrame, useVideoConfig} from 'remotion';
import {CaptionsFile, Layer, Plate, Style, f30, frameInfo, layoutPage, loadFonts, pageTimings, wordStates} from './engine';
import {REGISTRY} from './styles';

export const Captions: React.FC<{captions: CaptionsFile; style: Style; layer: Layer}> = ({captions, style: st, layer}) => {
  const frame = useCurrentFrame();
  const {width, height, fps} = useVideoConfig();
  const [handle] = useState(() => delayRender('subtle: loading fonts', {timeoutInMilliseconds: 60000}));
  const [ready, setReady] = useState(false);
  useEffect(() => {
    loadFonts(st)
      .then(() => {
        setReady(true);
        continueRender(handle);
      })
      .catch((err) => cancelRender(err));
  }, []);

  const f = useMemo(() => frameInfo(width, height, fps), [width, height, fps]);
  const def = REGISTRY[st.anim?.type] ?? REGISTRY[st.name];
  if (!def && ready) throw new Error(`no style registered for "${st.anim?.type ?? st.name}"`);
  const timings = useMemo(() => pageTimings(captions.pages, fps, def?.minShow ? f30(def.minShow, fps) : 0, !!captions.beats), [captions, fps, def]);
  const wantPage = layer === 'all' || layer === 'front' || (layer === 'mask' && !!def?.hasMask);
  const layouts = useMemo(() => {
    if (!ready || !def || !wantPage) return [];
    const o = def.layout?.(st, f) ?? {};
    return captions.pages.map((p) => layoutPage(p, st, f, {...o, specs: def.spec?.(p, st)}));
  }, [ready, captions, st, f, wantPage, def]);
  if (!ready || !def) return null;

  const mask = layer === 'mask';
  let page: React.ReactNode = null;
  if (wantPage) {
    const idx = timings.findIndex((t) => frame >= t.s && frame < t.e);
    if (idx >= 0) {
      const t = timings[idx];
      const P = def.Page;
      page = (
        <P
          st={st}
          f={f}
          page={captions.pages[idx]}
          pageIndex={idx}
          L={layouts[idx]}
          t={t}
          frame={frame}
          since={frame - t.s}
          left={t.e - frame}
          ws={wordStates(t, frame)}
          mode={mask ? 'mask' : 'visible'}
          captions={captions}
        />
      );
    }
  }
  const BigC = def.Big;
  // Giant words: the `behind` layer carries the ones that go behind the speaker, the `front` layer the ones marked
  // `front` (numbers, which must stay fully readable); `all` draws both.
  const bigAll = captions.big ?? [];
  const bigList = layer === 'all' ? bigAll : layer === 'behind' ? bigAll.filter((b) => !b.front) : layer === 'front' ? bigAll.filter((b) => b.front) : [];
  const big = bigList.length && BigC && st.behind?.enabled ? <BigC st={st} f={f} big={bigList} frame={frame} /> : null;
  return (
    <AbsoluteFill style={{background: mask ? '#000' : 'transparent'}}>
      <Plate f={f} mask={mask}>
        {big}
        {page}
      </Plate>
    </AbsoluteFill>
  );
};
