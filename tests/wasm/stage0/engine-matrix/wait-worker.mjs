// Full-profile waiter: blocks inside Wasm memory.atomic.wait32 on shared memory
// until the supervisor writes the mailbox and notifies. Runs as a Node Worker
// or a browser module Worker; both hosts use the same protocol words.
function run(data) {
  const { memory, bytes, words } = data;
  const x = new WebAssembly.Instance(new WebAssembly.Module(bytes), { env: { memory }, host: { fail() { throw new Error('unused'); } } }).exports;
  const result = {};
  x.store(words.flag, 1);
  result.code = x.wait(words.wait, 0, -1n);
  result.mailbox = x.load(words.mailbox);
  result.timed_out_code = x.wait(words.timed, 0, 1000000n);
  result.not_equal_code = x.wait(words.notEqual, 99, -1n);
  result.rmw_before = x.rmw_add(words.counter, 5);
  result.rmw_after = x.load(words.counter);
  return result;
}
const isNode = typeof process !== 'undefined' && !!(process.versions && process.versions.node);
if (isNode) {
  const { parentPort, workerData } = await import('node:worker_threads');
  try { parentPort.postMessage({ status: 'OK', ...run(workerData) }); }
  catch (e) { parentPort.postMessage({ status: 'ERROR', error: e.constructor.name, message: e.message }); }
} else {
  self.onmessage = e => {
    try { self.postMessage({ status: 'OK', ...run(e.data) }); }
    catch (err) { self.postMessage({ status: 'ERROR', error: err.constructor.name, message: err.message }); }
  };
}
