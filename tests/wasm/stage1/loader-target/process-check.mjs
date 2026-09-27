import assert from 'node:assert/strict';
import {processService, ProcessExit, ProcessReady, UnhandledCondition} from '../../../../runtime/wasm32/process-service.mjs';

const memory = new WebAssembly.Memory({initial: 1});
const words = new Uint32Array(memory.buffer), args = 64, vector = 128;
let clock = 100, waits = 0;
const output = [];
const request = processService({memory, now: () => clock,
  startup: {imageName: '/ccl/boot.image', cclRoot: '/ccl/', arguments: ['--no-init', 'λ😀']},
  output: (channel, text) => { output.push([channel, text]); },
  configuration: {pageSize: 65536, clockTicks: 1000, cpuCount: 1, stackSize: -1,
    defaults: [1048576, 1048576, 524288]},
  wait: ms => { clock += Math.min(ms, 20); waits++; }});
const call = (...values) => { words.set(values, args / 4); return request(args); };
words.set([2 * 256 + 250, 0, 0], vector / 4); // D1 simple-vector, two tagged slots.
clock += 1234.5;
assert.equal(call(0, vector + 6, 77825), 77825);
assert.deepEqual([...words.slice(vector / 4 + 1, vector / 4 + 3)], [4, 938000]);
assert.equal(call(4, 0, 100000), 77825);
assert.equal(waits, 2); // An early wakeup must not finish a 25 ms wait.
assert.equal(call(8, 0, 77825), 4000);
assert.equal(call(8, 12, 77825), -4);
assert.equal(call(24, 77825, 77825), 8);
assert.equal(call(20, 12, 77825), 8);
words.set([2 * 256 + 191, 0, 0], vector / 4);
assert.equal(call(20, 12, vector + 6), vector + 6);
assert.deepEqual([...words.slice(vector / 4 + 1, vector / 4 + 3)], [955, 128512]);
assert.equal(call(28, 4, vector + 6), vector + 6);
assert.equal(call(28, 8, vector + 6), vector + 6);
assert.deepEqual(output, [[1, 'λ😀'], [2, 'λ😀']]);
assert.throws(() => call(28, 12, vector + 6), /OUTPUT_CHANNEL/);
words[vector / 4 + 2] = 0xd800;
assert.throws(() => call(28, 4, vector + 6), /OUTPUT_SCALAR/);
assert.equal(output.length, 2);
words.set([2 * 256 + 250, 0, 0], vector / 4);
assert.throws(() => call(28, 4, vector + 6), /OUTPUT_STRING/);
for (const [values, reason] of [
  [[36, 0, 0], 'OPERATION'], [[8, 16, 0], 'CONFIG_KEY'],
  [[4, -4, 0], 'WAIT_RANGE'], [[4, 0, 4000004], 'WAIT_RANGE'],
  [[0, vector + 5, 0], 'TIME_VECTOR'], [[2, 0, 0], 'FIXNUM'],
  [[20, 16, 77825], 'STARTUP_KEY'], [[20, 12, vector + 6], 'STARTUP_BUFFER']
]) {
  const prior = [...words.slice(vector / 4, vector / 4 + 3)];
  assert.throws(() => call(...values), new RegExp(reason));
  assert.deepEqual([...words.slice(vector / 4, vector / 4 + 3)], prior);
}
clock = 99;
assert.throws(() => call(0, vector + 6, 77825), /MONOTONIC_CLOCK/);
assert.throws(() => call(12, 28, 77825), error => error instanceof ProcessExit && error.status === 7);
assert.throws(() => call(16, 134, 77825), error => error instanceof UnhandledCondition && error.condition === 134);
assert.throws(() => call(32, 77825, 77825), error => error instanceof ProcessReady);
console.log('PASS: monotonic time, early wakeup, configuration, startup strings, Unicode stdout/stderr, exit, READY, twelve refusals');
