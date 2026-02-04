/*
 * WASM32 kernel_request smoke exports.
 *
 * These exports exist to validate the kernel_request ABI wiring early, without
 * bringing up start_lisp.
 */

#ifdef WASM32

#include "wasm-host.h"

#include <errno.h>
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

__attribute__((used, visibility("default"), export_name("wasm_kernel_request_smoke_time_now_ms")))
uint64_t
wasm_kernel_request_smoke_time_now_ms(void)
{
  uint64_t ms = 0;
  int32_t r = wasm_kernel_time_now(&ms);
  if (r < 0) {
    return 0;
  }
  return ms;
}

__attribute__((used, visibility("default"), export_name("wasm_kernel_request_smoke_begin_stdin_read")))
uint32_t
wasm_kernel_request_smoke_begin_stdin_read(uint32_t max_bytes)
{
  struct payload {
    uint32_t sid_or_fd;
    uint32_t max_bytes;
  } p;

  uint32_t request_id = 0;

  p.sid_or_fd = 0;
  p.max_bytes = max_bytes;

  int32_t r = wasm_kernel_request_begin(KERNEL_OP_STREAM_READ, &p, (uint32_t)sizeof(p), &request_id);
  if (r < 0) {
    return 0;
  }
  return request_id;
}

__attribute__((used, visibility("default"), export_name("wasm_kernel_request_smoke_poll")))
uint32_t
wasm_kernel_request_smoke_poll(uint32_t request_id)
{
  return wasm_kernel_request_status(request_id);
}

__attribute__((used, visibility("default"), export_name("wasm_kernel_request_smoke_result")))
int32_t
wasm_kernel_request_smoke_result(uint32_t request_id)
{
  return wasm_kernel_request_get_result(request_id);
}

__attribute__((used, visibility("default"), export_name("wasm_kernel_request_smoke_copy_response")))
int32_t
wasm_kernel_request_smoke_copy_response(uint32_t request_id, uint32_t dst_ptr, uint32_t dst_cap)
{
  uint32_t n = 0;
  int32_t r = wasm_kernel_request_copy_response(request_id, (void *)(uintptr_t)dst_ptr, dst_cap, &n);
  if (r < 0) {
    return r;
  }
  return (int32_t)n;
}

__attribute__((used, visibility("default"), export_name("wasm_kernel_request_smoke_drop")))
void
wasm_kernel_request_smoke_drop(uint32_t request_id)
{
  wasm_kernel_request_drop(request_id);
}

__attribute__((used, visibility("default"), export_name("wasm_kernel_request_smoke_pipe_roundtrip")))
int32_t
wasm_kernel_request_smoke_pipe_roundtrip(void)
{
  static const uint8_t msg[] = {0x00, 0x01, 0x02, 0x7f, 0x80, 0xff};
  uint8_t buf[16];
  uint32_t nread = 0;

  uint32_t sid = 0;
  int32_t r = wasm_kernel_stream_open(KERNEL_STREAM_KIND_PIPE, NULL, 0, &sid);
  if (r < 0) {
    return r;
  }

  r = wasm_kernel_stream_write(sid, msg, (uint32_t)sizeof(msg));
  if (r != (int32_t)sizeof(msg)) {
    (void)wasm_kernel_stream_close(sid);
    return (r < 0) ? r : -1;
  }

  r = wasm_kernel_stream_read(sid, buf, (uint32_t)sizeof(buf), &nread);
  if (r != (int32_t)sizeof(msg) || nread != (uint32_t)sizeof(msg)) {
    (void)wasm_kernel_stream_close(sid);
    return (r < 0) ? r : -1;
  }
  for (size_t i = 0; i < sizeof(msg); i++) {
    if (buf[i] != msg[i]) {
      (void)wasm_kernel_stream_close(sid);
      return -1;
    }
  }

  r = wasm_kernel_stream_close(sid);
  if (r < 0) {
    return r;
  }

  r = wasm_kernel_stream_read(sid, buf, (uint32_t)sizeof(buf), &nread);
  if (r != -EBADF) {
    return (r < 0) ? r : -1;
  }
  return 0;
}

#endif /* WASM32 */
