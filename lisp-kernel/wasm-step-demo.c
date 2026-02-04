/*
 * WASM32 Stage-2 stepping demo (explicit yield/resume boundary).
 *
 * This is not the full Lisp scheduler; it's a minimal state machine that:
 *   1) issues a STREAM_READ request (stdin),
 *   2) returns BLOCKED while the request is PENDING,
 *   3) copies the response when DONE and writes it to stdout,
 *   4) returns DONE.
 *
 * It exists to validate the "explicit stepping" model described in
 * doc/wasm/yield-resume.md without relying on stack-suspension toolchains.
 */

#ifdef WASM32

#include "wasm-host.h"

#include <stdint.h>

enum {
  WASM_STEP_RUNNING = 0,
  WASM_STEP_BLOCKED = 1,
  WASM_STEP_DONE = 2,
};

static uint32_t demo_request_id = 0;
static uint8_t demo_buf[256];
static uint32_t demo_len = 0;
static uint32_t demo_done = 0;

__attribute__((used, visibility("default"), export_name("wasm_step_demo_reset")))
void
wasm_step_demo_reset(void)
{
  if (demo_request_id != 0) {
    wasm_kernel_request_drop(demo_request_id);
  }
  demo_request_id = 0;
  demo_len = 0;
  demo_done = 0;
}

__attribute__((used, visibility("default"), export_name("wasm_step_demo_step")))
int32_t
wasm_step_demo_step(void)
{
  if (demo_done) {
    return WASM_STEP_DONE;
  }

  if (demo_request_id == 0) {
    struct payload {
      uint32_t sid_or_fd;
      uint32_t max_bytes;
    } p;
    p.sid_or_fd = 0;
    p.max_bytes = (uint32_t)sizeof(demo_buf);

    int32_t r = wasm_kernel_request_begin(KERNEL_OP_STREAM_READ, &p, (uint32_t)sizeof(p), &demo_request_id);
    if (r < 0) {
      return r;
    }
  }

  uint32_t st = wasm_kernel_request_status(demo_request_id);
  if (st == KERNEL_STATUS_PENDING) {
    return WASM_STEP_BLOCKED;
  }

  int32_t result = wasm_kernel_request_get_result(demo_request_id);
  if (st == KERNEL_STATUS_ERROR) {
    wasm_kernel_request_drop(demo_request_id);
    demo_request_id = 0;
    return (result != 0) ? result : -1;
  }

  if (result < 0) {
    wasm_kernel_request_drop(demo_request_id);
    demo_request_id = 0;
    return result;
  }

  demo_len = 0;
  int32_t cr = wasm_kernel_request_copy_response(demo_request_id, demo_buf, (uint32_t)sizeof(demo_buf), &demo_len);
  wasm_kernel_request_drop(demo_request_id);
  demo_request_id = 0;
  if (cr < 0) {
    return cr;
  }

  /* For bring-up, STREAM_WRITE is synchronous in the reference microkernel. */
  if (demo_len != 0) {
    (void)wasm_kernel_stream_write(1, demo_buf, demo_len);
  }

  demo_done = 1;
  return WASM_STEP_DONE;
}

#endif /* WASM32 */

