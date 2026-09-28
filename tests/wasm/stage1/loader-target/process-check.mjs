import assert from 'node:assert/strict';
import fs from 'node:fs';
import {processService, ProcessExit, ProcessReady, UnhandledCondition} from '../../../../runtime/wasm32/process-service.mjs';
import {sha256} from '../../../../runtime/wasm32/sha256.mjs';

const memory = new WebAssembly.Memory({initial: 1});
const words = new Uint32Array(memory.buffer), args = 64, vector = 128;
let clock = 100, waits = 0;
const output = [];
const configuration = {pageSize: 65536, clockTicks: 1000, cpuCount: 1, stackSize: -1,
  defaults: [1048576, 1048576, 524288]};
const request = processService({memory, now: () => clock,
  wallTime: () => -1,
  calendar: seconds => { assert.equal(seconds, -1); return {minutesWest: 360, daylight: false}; },
  cpuTime: () => ({user: 1234567, system: 7654321}),
  startup: {imageName: '/ccl/boot.image', cclRoot: '/ccl/', arguments: ['--no-init', 'λ😀']},
  output: (channel, text) => { output.push([channel, text]); },
  configuration,
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
  [[64, 0, 0], 'OPERATION'], [[60, 0, 0], 'FOREIGN_CAPABILITY'], [[8, 16, 0], 'CONFIG_KEY'],
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
assert.equal(call(36, vector + 6, 77825), 77825);
assert.deepEqual([...words.slice(vector / 4 + 1, vector / 4 + 3)], [(-4) >>> 0, 86399 * 4]);
assert.equal(call(40, vector + 6, 77825), 77825);
assert.deepEqual([...words.slice(vector / 4 + 1, vector / 4 + 3)], [360 * 4, 0]);
words.set([4 * 256 + 250, 0, 0, 0, 0], vector / 4);
assert.equal(call(44, vector + 6, 77825), 77825);
assert.deepEqual([...words.slice(vector / 4 + 1, vector / 4 + 5)], [4, 234567 * 4, 28, 654321 * 4]);
for (const operation of [36, 40])
  assert.throws(() => call(operation, vector + 6, 77825), /CLOCK_VECTOR/);
words.set([2 * 256 + 250, 0, 86400 * 4], vector / 4);
assert.throws(() => call(40, vector + 6, 77825), /CALENDAR_SECONDS/);
const calendarControls = [
  [9, {wallTime: null}, 'WALL_CLOCK_CAPABILITY'],
  [9, {wallTime: () => NaN}, 'WALL_CLOCK'],
  [9, {wallTime: () => 86400000 * 536870912}, 'CLOCK_RANGE'],
  [9, {wallTime: () => -86400000 * 536870913}, 'CLOCK_RANGE'],
  [10, {}, 'CALENDAR_CAPABILITY'],
  [10, {calendar: () => null}, 'CALENDAR_RESULT'],
  [10, {calendar: () => ({minutesWest: 0.5, daylight: false})}, 'CALENDAR_RESULT'],
  [10, {calendar: () => ({minutesWest: 1441, daylight: false})}, 'CALENDAR_RESULT'],
  [10, {calendar: () => ({minutesWest: 0, daylight: 1})}, 'CALENDAR_RESULT'],
  [11, {}, 'CPU_CAPABILITY'],
  [11, {cpuTime: () => null}, 'CPU_RESULT'],
  [11, {cpuTime: () => ({user: 0.5, system: 0})}, 'CPU_RESULT'],
  [11, {cpuTime: () => ({user: -1, system: 0})}, 'CPU_RESULT'],
  [11, {cpuTime: () => ({user: 0, system: NaN})}, 'CPU_RESULT'],
  [11, {cpuTime: () => ({user: 536870912 * 1000000, system: 0})}, 'CLOCK_RANGE']
];
for (const [op, capabilities, reason] of calendarControls) {
  words.set([(op === 11 ? 4 : 2) * 256 + 250, 0, 0, 0, 0], vector / 4);
  words.set([op * 4, vector + 6, 77825], args / 4);
  const before = [...words];
  const service = processService({memory, configuration, now: () => 0, wait: () => {}, ...capabilities});
  assert.throws(() => service(args), new RegExp(reason));
  assert.deepEqual([...words], before, reason + ' preserves memory');
}
// Shared vector predicate: alignment, extent and header are independent.
// The lower bound follows from the admitted unsigned aligned pointer (6 is
// its minimum); the 2/4-slot length branches each get an extent refusal.
let shapeControls = 0;
for (const op of [9, 10, 11]) {
  for (const word of [vector + 5, memory.buffer.byteLength - 2, vector + 6]) {
    words[vector / 4] = 250;
    words.set([op * 4, word, 77825], args / 4);
    const before = [...words];
    assert.throws(() => request(args), /CLOCK_VECTOR/);
    assert.deepEqual([...words], before); shapeControls++;
  }
}
for (const [days, seconds, reason] of [[1, 0, 'FIXNUM'], [0, 1, 'FIXNUM'],
  [0, -4, 'CALENDAR_SECONDS'], [0, 86400 * 4, 'CALENDAR_SECONDS']]) {
  words.set([762, days, seconds], vector / 4);
  words.set([40, vector + 6, 77825], args / 4);
  const before = [...words];
  assert.throws(() => request(args), new RegExp(reason));
  assert.deepEqual([...words], before); shapeControls++;
}
const inhibitionCalls = [];
const inhibition = processService({memory, configuration, now: () => 0, wait: () => {},
  collectionInhibition: delta => { inhibitionCalls.push(delta); return delta === 1 ? 2 : 1; }});
for (const [op, expected] of [[12, 8], [13, 4]]) {
  words.set([op * 4, 77825, 77825], args / 4);
  assert.equal(inhibition(args), expected);
}
assert.deepEqual(inhibitionCalls, [1, -1]);
for (const depth of [-536870911, -2, -1, 0, 536870911]) {
  const service = processService({memory, configuration, now: () => 0, wait: () => {},
    collectionInhibition: () => depth});
  words.set([48, 77825, 77825], args / 4);
  assert.equal(service(args), depth * 4);
}
const checkedTag = new WebAssembly.Tag({parameters: ['i32']});
const checkedFailure = new WebAssembly.Exception(checkedTag, [11]);
const throwing = processService({memory, configuration, now: () => 0, wait: () => {},
  collectionInhibition: () => { throw checkedFailure; }});
assert.throws(() => throwing(args), error => error === checkedFailure);
let inhibitionRefusals = 0;
for (const [service, values, reason] of [
  [request, [48, 77825, 77825], 'COLLECTOR_CAPABILITY'],
  [inhibition, [48, 0, 77825], 'COLLECTOR_ARGUMENTS'],
  [inhibition, [52, 77825, 0], 'COLLECTOR_ARGUMENTS'],
  ...[NaN, 0.5, -536870912, 536870912].map(value => [processService({memory, configuration,
    now: () => 0, wait: () => {}, collectionInhibition: () => value}),
    [48, 77825, 77825], 'COLLECTOR_RESULT'])
]) {
  words.set(values, args / 4);
  const before = [...words], calls = [...inhibitionCalls];
  assert.throws(() => service(args), new RegExp(reason));
  assert.deepEqual([...words], before);
  assert.deepEqual(inhibitionCalls, calls);
  inhibitionRefusals++;
}
let validityRefusals = 0;
for (const valid of [true, false]) {
  const service = processService({memory, configuration, now: () => 0, wait: () => {},
    objectValidity: word => { assert.equal(word, 0xfffffffe); return valid; }});
  words.set([56, 0xfffffffe, 77825], args / 4);
  assert.equal(service(args), valid ? 77838 : 77825);
}
for (const [capabilities, last, reason] of [[{}, 77825, 'OBJECT_CAPABILITY'],
  [{objectValidity: () => { throw Error('should not call'); }}, 0, 'OBJECT_ARGUMENTS'],
  ...[0, 1, null, undefined].map(value => [{objectValidity: () => value}, 77825, 'OBJECT_RESULT'])]) {
  words.set([56, 77825, last], args / 4);
  const before = [...words];
  const service = processService({memory, configuration, now: () => 0, wait: () => {}, ...capabilities});
  assert.throws(() => service(args), new RegExp(reason)); assert.deepEqual([...words], before);
  validityRefusals++;
}
words.set([56, 77825, 77825], args / 4);
assert.throws(() => processService({memory, configuration, now: () => 0, wait: () => {},
  objectValidity: () => { throw checkedFailure; }})(args), error => error === checkedFailure);
words.set([60, 8, 77825], args / 4);
let foreignCalls = 0;
const foreignRequest = processService({memory, configuration, now: () => 0, wait: () => {},
  foreign: pointer => { assert.equal(pointer, args); foreignCalls++; return -12; }});
assert.equal(foreignRequest(args), -12); assert.equal(foreignCalls, 1);
assert.throws(() => processService({memory, configuration, now: () => 0, wait: () => {},
  foreign: () => { throw checkedFailure; }})(args), error => error === checkedFailure);
console.log(JSON.stringify({foreignCalls, status: 'PASS', services: ['process', 'output', 'wall-clock', 'CPU', 'timezone/DST', 'object-validity'],
  validityRefusals,
  originalRefusals: 13, inhibitionRefusals, inhibitionSignedResults: 5, checkedExceptionIdentity: true,
  calendarCpuRefusals: 3 + calendarControls.length + shapeControls,
  inputs: Object.fromEntries(['./process-check.mjs', '../../../../runtime/wasm32/process-service.mjs',
    '../../../../runtime/wasm32/config.mjs'].map(path => [path, sha256(fs.readFileSync(new URL(path, import.meta.url)))]))}));
