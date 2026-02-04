/*
 * Stage-2 stepping baseline (explicit yield/resume boundary).
 *
 * This implements the minimal exported API sketched in:
 *   doc/wasm/yield-resume.md
 *
 * It is intentionally small and does NOT attempt to run the full Lisp runtime
 * yet. Instead, it demonstrates the contract the real runtime will follow:
 *
 *   - issue a kernel_request for a potentially-blocking operation
 *   - return to the host while the request is PENDING (BLOCKED)
 *   - resume later, consume the result, and continue (RUNNING)
 *
 * For now the "program" is a simple stdin->stdout echo loop:
 *   - read bytes from stream 0
 *   - write them to stream 1
 *   - repeat until EOF
 *
 * This keeps the ABI honest while the real scheduler/start_lisp integration is
 * developed.
 */

#ifdef WASM32

#include "wasm-host.h"

#include <errno.h>
#include <stdint.h>

enum {
  WASM_CCL_STEP_RUNNING = 0,
  WASM_CCL_STEP_BLOCKED = 1,
  WASM_CCL_STEP_EXITED = 2,
  WASM_CCL_STEP_TRAPPED = 3,
};

static uint32_t ccl_request_id = 0;
static uint32_t ccl_blocked_request_id = 0;
static int32_t ccl_exit_code = 0;
static int32_t ccl_last_error = 0;
static uint8_t ccl_buf[1024];

__attribute__((used, visibility("default"), export_name("wasm_ccl_init")))
int32_t
wasm_ccl_init(void)
{
  if (ccl_request_id != 0) {
    wasm_kernel_request_drop(ccl_request_id);
  }
  ccl_request_id = 0;
  ccl_blocked_request_id = 0;
  ccl_exit_code = 0;
  ccl_last_error = 0;
  return 0;
}

__attribute__((used, visibility("default"), export_name("wasm_ccl_blocked_request_id")))
uint32_t
wasm_ccl_blocked_request_id(void)
{
  return ccl_blocked_request_id;
}

__attribute__((used, visibility("default"), export_name("wasm_ccl_exit_code")))
int32_t
wasm_ccl_exit_code(void)
{
  return ccl_exit_code;
}

__attribute__((used, visibility("default"), export_name("wasm_ccl_last_error")))
int32_t
wasm_ccl_last_error(void)
{
  return ccl_last_error;
}

__attribute__((used, visibility("default"), export_name("wasm_ccl_step")))
int32_t
wasm_ccl_step(int32_t deadline_ms)
{
  (void)deadline_ms; /* reserved for future deadline-based stepping */

  /* Start a new stdin read request if none is in-flight. */
  if (ccl_request_id == 0) {
    struct payload {
      uint32_t sid_or_fd;
      uint32_t max_bytes;
    } p;
    p.sid_or_fd = 0;
    p.max_bytes = (uint32_t)sizeof(ccl_buf);

    int32_t r = wasm_kernel_request_begin(KERNEL_OP_STREAM_READ, &p, (uint32_t)sizeof(p), &ccl_request_id);
    if (r < 0) {
      ccl_last_error = r;
      return WASM_CCL_STEP_TRAPPED;
    }
  }

  uint32_t st = wasm_kernel_request_status(ccl_request_id);
  if (st == KERNEL_STATUS_PENDING) {
    ccl_blocked_request_id = ccl_request_id;
    return WASM_CCL_STEP_BLOCKED;
  }

  ccl_blocked_request_id = 0;

  int32_t result = wasm_kernel_request_get_result(ccl_request_id);
  if (st == KERNEL_STATUS_ERROR) {
    wasm_kernel_request_drop(ccl_request_id);
    ccl_request_id = 0;
    ccl_last_error = (result != 0) ? result : -EINVAL;
    return WASM_CCL_STEP_TRAPPED;
  }

  if (result < 0) {
    if (result == -EWOULDBLOCK) {
      /* Stage-1 style: treat would-block as a yield boundary. */
      wasm_kernel_request_drop(ccl_request_id);
      ccl_request_id = 0;
      return WASM_CCL_STEP_BLOCKED;
    }
    wasm_kernel_request_drop(ccl_request_id);
    ccl_request_id = 0;
    ccl_last_error = result;
    return WASM_CCL_STEP_TRAPPED;
  }

  uint32_t nread = 0;
  int32_t cr = wasm_kernel_request_copy_response(ccl_request_id, ccl_buf, (uint32_t)sizeof(ccl_buf), &nread);
  wasm_kernel_request_drop(ccl_request_id);
  ccl_request_id = 0;
  if (cr < 0) {
    ccl_last_error = cr;
    return WASM_CCL_STEP_TRAPPED;
  }

  if (result == 0) {
    /* EOF */
    ccl_exit_code = 0;
    return WASM_CCL_STEP_EXITED;
  }

  if ((uint32_t)result != nread) {
    ccl_last_error = -EINVAL;
    return WASM_CCL_STEP_TRAPPED;
  }

  /* For bring-up, STREAM_WRITE is synchronous in the reference microkernel. */
  if (nread != 0) {
    (void)wasm_kernel_stream_write(1, ccl_buf, nread);
  }

  return WASM_CCL_STEP_RUNNING;
}

#endif /* WASM32 */
