import fs from 'node:fs';
import path from 'node:path';

// Homebrew splits clang and LLD into separate formulae. Never select the linker
// from an unrelated PATH entry or another project's environment by accident.
const prefix = fs.existsSync('/opt/homebrew/opt/llvm/bin/clang') ? '/opt/homebrew' : '/usr/local';
export const clang = process.env.CCL_WASM_CLANG || path.join(prefix, 'opt/llvm/bin/clang');
export const ld = process.env.CCL_WASM_LD || path.join(prefix, 'opt/lld/bin/wasm-ld');
export const wat = process.env.CCL_WASM_WAT2WASM || path.join(prefix, 'bin/wat2wasm');
export const llvmVersion = '21.1.8';
export function checkLLVM(compiler, linker) {
  for (const [name, version] of [['clang', compiler], ['wasm-ld', linker]]) {
    if (!new RegExp(`\\b${llvmVersion.replaceAll('.', '\\.')}\\b`).test(version))
      throw Error(`${name} must be LLVM ${llvmVersion}; selected version: ${version}`);
  }
}
