// The caller owns this single Worker's pool interval and stops Lisp execution
// for the whole operation. No other Worker receives this SharedArrayBuffer.
import assert from 'node:assert/strict';
import {capture,restore} from './snapshot.mjs';
function stage(memory,base,size){
 assert(memory instanceof WebAssembly.Memory);assert(Number.isInteger(base)&&base>=8);
 assert(Number.isInteger(size)&&size>=0&&size<=16*1024*1024&&base+size<=memory.buffer.byteLength);
 return new WebAssembly.Memory({initial:Math.ceil((base+size)/65536)});
}
export function captureOwned(memory,manifest){
 const copy=stage(memory,manifest.base,manifest.length);
 new Uint8Array(copy.buffer,manifest.base,manifest.length).set(new Uint8Array(memory.buffer,manifest.base,manifest.length));
 return capture(copy,manifest);
}
export function restoreOwned(bytes,digest,memory,base,size,symbols){
 const copy=stage(memory,base,size);
 const result=restore(bytes,digest,copy,base,size,symbols);
 // Validation and relocation complete before the only publication write.
 new Uint8Array(memory.buffer,base,result.byteLength).set(new Uint8Array(copy.buffer,base,result.byteLength));
 return result;
}
