/*
 * WASM32 kernel_request smoke exports.
 *
 * These exports exist to validate the kernel_request ABI wiring early, without
 * bringing up start_lisp.
 */

#ifdef WASM32

#include "wasm-host.h"

#include <stddef.h>
#include <stdint.h>

__attribute__((used, visibility("default"), export_name("wasm_kernel_caps_abi_version")))
uint32_t
wasm_kernel_caps_abi_version(void)
{
  uint32_t abi = 0;
  int32_t r = wasm_kernel_caps(&abi, NULL, NULL);
  if (r < 0) {
    return 0;
  }
  return abi;
}

__attribute__((used, visibility("default"), export_name("wasm_kernel_request_smoke_write")))
int32_t
wasm_kernel_request_smoke_write(uint32_t sid_or_fd)
{
  static const char msg[] = "kernel_request smoke write\n";
  return wasm_kernel_stream_write(sid_or_fd, msg, (uint32_t)(sizeof(msg) - 1));
}

#endif /* WASM32 */
