/*
 * WASM32 host ABI (kernel_request) helpers.
 *
 * These wrappers provide a synchronous "Stage 1" path for calling into the JS
 * microkernel while the full yield/resume model is still being designed.
 *
 * See: doc/wasm/kernel-request-abi.md
 */

#ifdef WASM32

#include "wasm-host.h"

#include <errno.h>
#include <string.h>

int32_t
wasm_kernel_request_copy(uint32_t opcode,
                         const void *payload,
                         uint32_t payload_len,
                         void *out_buf,
                         uint32_t out_cap,
                         uint32_t *out_len)
{
  uint32_t request_id;
  uint32_t status;
  int32_t result;
  uint32_t need;

  if (out_len) {
    *out_len = 0;
  }

  request_id = kernel_request(opcode, payload, payload_len);
  if (request_id == 0) {
    return -EINVAL;
  }

  status = kernel_poll(request_id);
  if (status == KERNEL_STATUS_PENDING) {
    /* Stage 2 will need an explicit yield/resume mechanism. For now, treat
     * pending as would-block and drop the request.
     */
    kernel_drop_request(request_id);
    return -EWOULDBLOCK;
  }

  result = kernel_result(request_id);

  /* ABI-level errors still provide an errno-style result; surface it. */
  if (status == KERNEL_STATUS_ERROR) {
    kernel_drop_request(request_id);
    return result ? result : -EINVAL;
  }

  /* Copy response payload if requested. */
  if (out_buf && out_cap) {
    need = kernel_response_size(request_id);
    if (need > out_cap) {
      kernel_drop_request(request_id);
      return -E2BIG;
    }
    if (need) {
      uint32_t copied = kernel_copy_response(request_id, out_buf, out_cap);
      if (copied != need) {
        kernel_drop_request(request_id);
        return -EINVAL;
      }
      if (out_len) {
        *out_len = copied;
      }
    }
  } else if (out_len) {
    *out_len = kernel_response_size(request_id);
  }

  kernel_drop_request(request_id);
  return result;
}

int32_t
wasm_kernel_caps(uint32_t *out_abi_version,
                 uint32_t *out_capability_bits,
                 uint32_t *out_max_response_bytes)
{
  struct caps {
    uint32_t abi_version;
    uint32_t capability_bits;
    uint32_t max_response_bytes;
    uint32_t reserved;
  } c;
  uint32_t n = 0;
  int32_t r = wasm_kernel_request_copy(KERNEL_OP_CAPS, NULL, 0, &c, (uint32_t)sizeof(c), &n);
  if (r < 0) {
    return r;
  }
  if (n != sizeof(c)) {
    return -EINVAL;
  }
  if (out_abi_version) {
    *out_abi_version = c.abi_version;
  }
  if (out_capability_bits) {
    *out_capability_bits = c.capability_bits;
  }
  if (out_max_response_bytes) {
    *out_max_response_bytes = c.max_response_bytes;
  }
  return 0;
}

int32_t
wasm_kernel_stream_write(uint32_t sid_or_fd, const void *bytes, uint32_t len)
{
  struct payload {
    uint32_t sid_or_fd;
    uint32_t flags;
    uint32_t data_ptr;
    uint32_t data_len;
  } p;

  p.sid_or_fd = sid_or_fd;
  p.flags = 0;
  p.data_ptr = (uint32_t)(uintptr_t)bytes;
  p.data_len = len;

  int32_t r = wasm_kernel_request_copy(KERNEL_OP_STREAM_WRITE, &p, (uint32_t)sizeof(p), NULL, 0, NULL);
  return r;
}

int32_t
wasm_kernel_stream_read(uint32_t sid_or_fd, void *buf, uint32_t cap, uint32_t *out_nread)
{
  struct payload {
    uint32_t sid_or_fd;
    uint32_t max_bytes;
  } p;
  uint32_t n = 0;

  if (out_nread) {
    *out_nread = 0;
  }

  p.sid_or_fd = sid_or_fd;
  p.max_bytes = cap;

  int32_t r = wasm_kernel_request_copy(KERNEL_OP_STREAM_READ, &p, (uint32_t)sizeof(p), buf, cap, &n);
  if (r < 0) {
    return r;
  }
  if ((uint32_t)r != n) {
    return -EINVAL;
  }
  if (out_nread) {
    *out_nread = n;
  }
  return r;
}

int32_t
wasm_kernel_time_now(uint64_t *out_unix_ms)
{
  uint64_t ms = 0;
  uint32_t n = 0;
  int32_t r = wasm_kernel_request_copy(KERNEL_OP_TIME_NOW, NULL, 0, &ms, (uint32_t)sizeof(ms), &n);
  if (r < 0) {
    return r;
  }
  if (n != sizeof(ms)) {
    return -EINVAL;
  }
  if (out_unix_ms) {
    /* WASM is little-endian; microkernel returns little-endian u64. */
    *out_unix_ms = ms;
  }
  return 0;
}

#endif /* WASM32 */

