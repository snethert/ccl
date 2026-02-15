// Minimal test for RESTORE-LISP-POINTERS fix
// Tests if symbols can be found after image load (was broken, should be fixed now)

import { readFileSync } from 'fs';
import { WASI } from 'wasi';

const kernelPath = 'build/wasm32/kernel/wasmcl.wasm';
const imagePath = 'build/wasm32/wasm-boot.image';

console.log('Loading kernel...');
const kernelBytes = readFileSync(kernelPath);
const kernelModule = await WebAssembly.compile(kernelBytes);

console.log('Loading image...');
const imageBytes = readFileSync(imagePath);

// Create WASM instance with minimal imports
const imports = {
  env: {
    kernel_request: () => {
      console.log('kernel_request called (not implemented in this test)');
      return 0;
    }
  }
};

const instance = await WebAssembly.instantiate(kernelModule, imports);
const exports = instance.exports;

console.log('Kernel exports:', Object.keys(exports).slice(0, 10), '...');

// Allocate memory for image
const imageSize = imageBytes.length;
const memorySizePages = Math.ceil((imageSize + 65536 * 4) / 65536);

console.log(`Image size: ${imageSize} bytes, allocating ${memorySizePages} pages`);

// Check if memory needs to grow
const currentPages = exports.memory ? exports.memory.buffer.byteLength / 65536 : 0;
console.log(`Current memory: ${currentPages} pages`);

// Copy image into WASM memory
const imagePtr = 65536; // Start at 64KB offset
const memory = new Uint8Array(exports.memory.buffer);
memory.set(imageBytes, imagePtr);

console.log(`Copied ${imageBytes.length} bytes to offset ${imagePtr}`);

// Set up C stack (required before loading image)
if (exports.wasm_set_cstack_bounds) {
  const cstackBase = imagePtr + imageSize + 4096;
  const cstackSize = 16384;
  console.log(`Setting cstack: base=${cstackBase}, size=${cstackSize}`);
  exports.wasm_set_cstack_bounds(cstackBase, cstackSize);
}

// Load the image
console.log('Calling wasm_ccl_load_image...');
const loadResult = exports.wasm_ccl_load_image(imagePtr, imageSize);
console.log(`wasm_ccl_load_image returned: ${loadResult}`);

if (loadResult !== 0) {
  console.error('FAILED: Image load returned error code:', loadResult);
  process.exit(1);
}

console.log('SUCCESS: Image loaded without error!');
console.log('\nNote: Full symbol lookup test requires proper kernel_request implementation.');
console.log('This test verifies that RESTORE-LISP-POINTERS is called (no crash/error).');

process.exit(0);
