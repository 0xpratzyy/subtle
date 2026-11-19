#!/usr/bin/env node
// Renders many transparent stills with ONE bundle (render.mjs bundles for every call).
// node template/stills.mjs jobs.json    jobs: [{captions: path, style: path, layer: "all|behind|front", frame: 123, png: path}]
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const fontsDir = path.resolve(here, '..', 'fonts');
const jobs = JSON.parse(fs.readFileSync(path.resolve(process.cwd(), process.argv[2]), 'utf8'));
const {bundle} = await import('@remotion/bundler');
const {renderStill, selectComposition} = await import('@remotion/renderer');
const bundleDir = fs.mkdtempSync(path.join(os.tmpdir(), 'subtle-bundle-'));
const cleanup = () => { try { fs.rmSync(bundleDir, {recursive: true, force: true}); } catch {} };
process.on('exit', cleanup);
for (const sig of ['SIGINT', 'SIGTERM']) process.on(sig, () => { cleanup(); process.exit(1); });
const serveUrl = await bundle({entryPoint: path.join(here, 'src', 'index.ts'), publicDir: fontsDir, outDir: bundleDir, enableCaching: false});
const cache = new Map();
const read = (p) => cache.get(p) ?? (cache.set(p, JSON.parse(fs.readFileSync(path.resolve(process.cwd(), p), 'utf8'))), cache.get(p));
let n = 0;
for (const j of jobs) {
  const inputProps = {captions: read(j.captions), style: read(j.style), layer: j.layer ?? 'all'};
  const composition = await selectComposition({serveUrl, id: 'Captions', inputProps, logLevel: 'error'});
  const out = path.resolve(process.cwd(), j.png);
  fs.mkdirSync(path.dirname(out), {recursive: true});
  await renderStill({composition, serveUrl, inputProps, frame: Number(j.frame), imageFormat: 'png', output: out, logLevel: 'error'});
  n++;
}
console.log(JSON.stringify({stills: n}));
