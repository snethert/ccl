#!/usr/bin/env node
// Execute one bootstrap case: node execute.mjs BUNDLE CONFIG OUT
// The bundle directory holds the loader, manifest and assembled modules; the
// config names the case, which manifest to use and which module file (or
// none) stands in for each closure module. The observation records the
// loader's result, its event ledger and the physical memory state.
import fs from 'node:fs';
import path from 'node:path';
import { gzipSync } from 'node:zlib';
import { pathToFileURL } from 'node:url';
const [bundle, configPath, out] = process.argv.slice(2);
if (!bundle || !configPath || !out) throw Error('usage: node execute.mjs BUNDLE CONFIG OUT');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
const { bootstrap } = await import(pathToFileURL(path.join(bundle, config.loader || 'loader.mjs')).href);
const manifest = JSON.parse(fs.readFileSync(path.join(bundle, config.manifest || 'closure.json'), 'utf8'));
const abi = JSON.parse(fs.readFileSync(path.join(bundle, 'abi.json'), 'utf8'));
const supplied = {};
for (const [name, file] of Object.entries(config.modules)) if (file) supplied[name] = new Uint8Array(fs.readFileSync(path.join(bundle, file)));
const memory = new WebAssembly.Memory({ initial: abi.memory.pages, maximum: abi.memory.pages });
const bytes = new Uint8Array(memory.buffer);
for (let i = 0; i < bytes.length; i++) bytes[i] = (i * 13 + 7) % 256;   // nonzero background exposes accidental clearing
const words = new Int32Array(memory.buffer);
for (const r of [abi.regions.completion_words, abi.regions.execution_counters]) for (let k = 0; k < r.count; k++) words[r.base / 4 + k] = 0;
for (const a of [abi.regions.mode_word, abi.regions.fatal_sink, abi.regions.slot_count, abi.regions.summary_word, abi.regions.ready.generation, abi.regions.ready.count, abi.regions.ready.checksum, abi.regions.event_log.count]) words[a / 4] = 0;
let result;
try { result = bootstrap(manifest, supplied, memory); }
catch (e) { result = { crash: { error: e.constructor.name, message: e.message } }; }
const R = abi.regions;
const physical = {
  completion_words: Array.from(words.slice(R.completion_words.base / 4, R.completion_words.base / 4 + R.completion_words.count)),
  execution_counters: Array.from(words.slice(R.execution_counters.base / 4, R.execution_counters.base / 4 + R.execution_counters.count)),
  mode: words[R.mode_word / 4], fatal_sink: words[R.fatal_sink / 4], slot_count: words[R.slot_count / 4], summary: words[R.summary_word / 4],
  ready: { generation: words[R.ready.generation / 4], count: words[R.ready.count / 4], checksum: words[R.ready.checksum / 4] },
  region_table: Array.from(words.slice(R.region_table.base / 4, R.region_table.base / 4 + 1 + 3 * R.region_table.entries)),
  event_log: Array.from(words.slice(R.event_log.base / 4, R.event_log.base / 4 + words[R.event_log.count / 4])),
  definitions: Object.fromEntries(Object.entries(R.definitions).map(([k, a]) => [k, Array.from(words.slice(a / 4, a / 4 + 5))])),
  canonical: { nil_cdr: words[R.canonical.nil_cons / 4], nil_car: words[R.canonical.nil_cons / 4 + 1], t_header: words[R.canonical.t_header / 4] },
};
fs.mkdirSync(out, { recursive: true });
fs.writeFileSync(path.join(out, 'memory.bin.gz'), gzipSync(Buffer.from(memory.buffer)));
fs.writeFileSync(path.join(out, 'observed.json'), JSON.stringify({ version: 1, case: config.case, node: process.version, result, physical }, null, 2) + '\n');
console.log('observed ' + path.join(out, 'observed.json'));
