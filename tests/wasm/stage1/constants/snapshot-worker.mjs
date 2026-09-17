import {parentPort, workerData} from 'node:worker_threads';
import {readFileSync} from 'node:fs';
import {capture, restore} from './snapshot.mjs';
const {mode, fixture, snapshot, sha256, probe} = workerData;
const base = mode === 'capture' ? 0x1000 : 0x80000000;
const memory = new WebAssembly.Memory({initial:mode === 'capture' ? 2 : 32769});
const wasm = await WebAssembly.instantiate(readFileSync(probe), {env:{memory}});
const load = offset => wasm.instance.exports.load(base+offset) >>> 0;
if (mode === 'capture') {
  new Uint8Array(memory.buffer,base,fixture.image.length/2).set(Buffer.from(fixture.image,'hex'));
  // Prove capture reads live target bytes: change the cons CAR through Wasm.
  wasm.instance.exports.store(base+fixture.mutationOffset,36);
  const result = capture(memory,fixture.manifest);
  parentPort.postMessage({bytes:result.bytes.toString('hex'),sha256:result.sha256});
} else {
  const result = restore(Buffer.from(snapshot,'hex'),sha256,memory,base,65536,{'P::X':0x5006});
  const observations = {roots:result.roots, objects:result.objects, words:[]};
  for (let i=0;i<result.byteLength;i+=4) observations.words.push(load(i));
  parentPort.postMessage(observations);
}
