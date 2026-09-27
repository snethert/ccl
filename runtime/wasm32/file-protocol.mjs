// D5-style single outstanding request. Only the Lisp Worker writes its TCR.
// Descriptor is stable, outside the moving heap; payload contains bytes only.
export const REQUEST = 1900544, SIZE = 8192, PAYLOAD = 64, CAPACITY = SIZE-PAYLOAD;
export const PENDING = 0, COMPLETE = 1;
export const ERRNO = Object.freeze({NOT_FOUND:2, BAD_HANDLE:9, HANDLE:9, RANGE:22, HANDLE_KIND:9,
  NOT_DIRECTORY:20, IS_DIRECTORY:21, READ_ONLY:30, HANDLE_LIMIT:24,
  HANDLE_EXHAUSTED:24, PATH:22, OFFSET:22, COUNT:22, ORIGIN:22});
export function views(memory) {
  return {words:new Int32Array(memory.buffer,REQUEST,16),
    pair:new BigUint64Array(memory.buffer,REQUEST+8,1),
    payload:new Uint8Array(memory.buffer,REQUEST+PAYLOAD,CAPACITY)};
}
export function pair(generation, wake) {return (BigInt(generation)<<32n)|BigInt(wake);}
