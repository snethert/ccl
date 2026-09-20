// Host-independent bytes. Snapshots always copy, including ArrayBuffer inputs.
const encoder = new TextEncoder();
export const utf8 = text => encoder.encode(text);
export function byteView(value) {
  if (ArrayBuffer.isView(value)) return new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
  if (value instanceof ArrayBuffer || (typeof SharedArrayBuffer !== 'undefined' && value instanceof SharedArrayBuffer)) return new Uint8Array(value);
  throw new TypeError('Expected a byte buffer or view');
}
export const snapshotBytes = value => new Uint8Array(byteView(value));
export const hex = value => Array.from(byteView(value), b => b.toString(16).padStart(2, '0')).join('');
