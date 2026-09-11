import { parentPort, workerData } from 'node:worker_threads';

try {
  const instance = new WebAssembly.Instance(new WebAssembly.Module(workerData.bytes), { env: { memory: workerData.memory } });
  instance.exports.init();
  instance.exports.privateSetup(workerData.privateOffset, workerData.token);
  const words = new Int32Array(workerData.memory.buffer);
  parentPort.postMessage({ sentinel: words[4], privateValue: words[workerData.privateOffset / 4], initialized: words[0] });
} catch (error) {
  parentPort.postMessage({ error: error.stack });
}
