import {createHash} from 'node:crypto';
import {manifest as providerManifest} from '../namespace/fixtures.mjs';

export const largeFile = Uint8Array.from({length:9000},(_,i)=>(i*37+11)&255);
export function manifest() {
  const result=providerManifest();
  result.entries.push({path:'/ccl/large.bin',kind:'file',bytes:largeFile,
    sha256:createHash('sha256').update(largeFile).digest('hex')});
  return result;
}
