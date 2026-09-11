import { parentPort, workerData as d } from 'node:worker_threads';
import { instantiate, setup, observe } from './runtime.mjs';

try {
  const state = instantiate(d.kernel, d.emitted, d.memory, d.metadata, (tcr, frame) => {
    const words = new Int32Array(d.memory.buffer);
    if (tcr !== d.plan.tcr.start) throw Error('park used the wrong TCR');
    Atomics.store(words, (tcr + 72) / 4, 1);
    parentPort.postMessage({ kind: 'parked', tcr, frame });
    while (!Atomics.load(words, (tcr + 76) / 4)) {
      if (Atomics.wait(words, (tcr + 76) / 4, 0, 5000) === 'timed-out') throw Error('C fixture rendezvous timeout');
    }
  });
  setup(state, d.memory, d.plan, d.metadata);
  // Deliberate injection after validated setup, confined to a quarantined run.
  if (d.mutantStackTop !== undefined) state.kernel.exports.__stack_pointer.value = d.mutantStackTop;
  state.kernel.exports.hold_stack(d.token);
  parentPort.postMessage({ kind: 'done', observation: observe(d.memory, d.plan), stackPointer: state.kernel.exports.__stack_pointer.value });
} catch (error) {
  parentPort.postMessage({ kind: 'error', error: error.stack });
}
