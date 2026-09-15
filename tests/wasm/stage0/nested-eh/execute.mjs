#!/usr/bin/env node
// Node/V8 execution of one nested-EH bundle: node execute.mjs BUNDLE OUT
// Each case instantiates the frames module over a fresh memory, lays out the
// fixture TCR, the two B arguments at VSP, calls entry(self, nargs) and
// records the returned pair or the escaping exception together with the TCR
// words, the caller-owned result region, the transit region and the event log.
import fs from 'node:fs';
import path from 'node:path';
const [bundle, out] = process.argv.slice(2);
if (!bundle || !out) throw Error('usage: node execute.mjs BUNDLE_DIRECTORY OUTPUT_DIRECTORY');
const abi = JSON.parse(fs.readFileSync(path.join(bundle, 'abi.json'), 'utf8'));
const bytes = new Uint8Array(fs.readFileSync(path.join(bundle, 'frames.wasm')));
const F = abi.tcr.fields, T = abi.tcr.address, W = abi.regions;
const cases = abi.cases;

function runCase(c) {
  const memory = new WebAssembly.Memory({ initial: 1, maximum: 1 });
  const words = new Int32Array(memory.buffer), tcr = T / 4;
  const instance = new WebAssembly.Instance(new WebAssembly.Module(bytes), { env: { memory } });
  const x = instance.exports;
  words[W.vsp_base / 4] = c.mode; words[W.vsp_base / 4 + 1] = c.argument;
  const initial = { vsp: W.vsp_base + 8, tsp: W.tsp_base, csp: W.csp_base, special: abi.initial_special, root_head: 0, handler_depth: 0,
    cleanup_count: 0, post_exit_effects: 0, mv_base: W.mv_base, mv_count: 0, transit_base: W.transit_base, transit_count: 0, handler_calls: 0, event_count: 0, max_handler_depth: 0, resumed: 0 };
  for (const [name, value] of Object.entries(initial)) words[tcr + F[name] / 4] = value;
  const record = { mode: c.mode, argument: c.argument };
  try { record.returned = Array.from(x.entry(abi.self, 2)); }
  catch (e) {
    const wasm = typeof WebAssembly.Exception === 'function' && e instanceof WebAssembly.Exception;
    const tag = wasm ? ['lisp', 'other', 'unhandled', 'condition'].find(name => e.is(x[name])) : null;
    record.thrown = { error: e.constructor.name, wasm_exception: wasm, tag: tag || null, arg: tag ? e.getArg(x[tag], 0) : null, message: wasm ? undefined : e.message };
  }
  record.state = Object.fromEntries(Object.keys(initial).map(name => [name, words[tcr + F[name] / 4]]));
  record.result_region = Array.from(words.slice(W.mv_base / 4, W.mv_base / 4 + 6));
  record.transit_region = Array.from(words.slice(W.transit_base / 4, W.transit_base / 4 + 6));
  record.events = Array.from(words.slice(W.events / 4, W.events / 4 + record.state.event_count));
  return record;
}
const record = { version: 1, engine: { node: process.version, v8: process.versions.v8 }, cases: {} };
for (const c of cases) record.cases[c.name] = runCase(c);
fs.mkdirSync(out, { recursive: true });
fs.writeFileSync(path.join(out, 'observed.json'), JSON.stringify(record, null, 2) + '\n');
console.log('observed ' + path.join(out, 'observed.json'));
