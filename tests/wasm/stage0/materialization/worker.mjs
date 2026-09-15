// Full-profile Worker: instantiates the shared runtime and the shared
// materialized template over the supervisor's shared memory, then calls the
// template entry; the runtime blocks in memory.atomic.wait32 until notified.
import { parentPort, workerData } from 'node:worker_threads';
const { memory, runtime, template, argument, calls } = workerData;
try {
  const rt = new WebAssembly.Instance(new WebAssembly.Module(runtime), { env: { memory } });
  const t = new WebAssembly.Instance(new WebAssembly.Module(template), { env: { memory }, runtime: { request: rt.exports.request } });
  const results = [];
  for (let i = 0; i < calls; i++) results.push(Array.from(t.exports.entry(argument)));
  parentPort.postMessage({ status: 'OK', results, size: t.exports.size() });
} catch (e) { parentPort.postMessage({ status: 'ERROR', error: e.constructor.name, message: e.message }); }
