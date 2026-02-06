/*
 * Stage-2 stepping baseline (explicit yield/resume boundary).
 *
 * This implements the minimal exported API sketched in:
 *   doc/wasm/yield-resume.md
 *
 * The step function now drives the Lisp toplevel loop and returns to the host
 * when the toplevel yields or exits.
 */

#ifdef WASM32

#include <errno.h>
#include <stdint.h>

enum {
  WASM_CCL_STEP_RUNNING = 0,
  WASM_CCL_STEP_BLOCKED = 1,
  WASM_CCL_STEP_EXITED = 2,
  WASM_CCL_STEP_TRAPPED = 3,
};

enum {
  WASM_TOPLEVEL_EXIT = 0,
  WASM_TOPLEVEL_PENDING_THROW = 1,
  WASM_TOPLEVEL_YIELD = 2
};

static uint32_t ccl_blocked_request_id = 0;
static uint32_t ccl_toplevel_done = 0;
static uint32_t ccl_toplevel_trapped = 0;
static int32_t ccl_exit_code = 0;
static int32_t ccl_last_error = 0;

extern int wasm_run_toplevel(void);

__attribute__((used, visibility("default"), export_name("wasm_ccl_init")))
int32_t
wasm_ccl_init(void)
{
  ccl_blocked_request_id = 0;
  ccl_toplevel_done = 0;
  ccl_toplevel_trapped = 0;
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

  if (ccl_toplevel_trapped) {
    return WASM_CCL_STEP_TRAPPED;
  }
  if (ccl_toplevel_done) {
    return WASM_CCL_STEP_EXITED;
  }

  ccl_blocked_request_id = 0;
  ccl_last_error = 0;
  {
    TCR *tcr = wasm_get_current_tcr();
    if (tcr != NULL && tcr->interrupt_pending > 0) {
      tcr->interrupt_pending = 0;
      ccl_last_error = -EINTR;
      ccl_toplevel_trapped = 1;
      return WASM_CCL_STEP_TRAPPED;
    }
  }

  int rc = wasm_run_toplevel();
  if (rc == WASM_TOPLEVEL_EXIT) {
    ccl_exit_code = 0;
    ccl_toplevel_done = 1;
    return WASM_CCL_STEP_EXITED;
  }
  if (rc == WASM_TOPLEVEL_YIELD) {
    return WASM_CCL_STEP_BLOCKED;
  }
  if (rc == WASM_TOPLEVEL_PENDING_THROW) {
    ccl_last_error = -EFAULT;
    ccl_toplevel_trapped = 1;
    return WASM_CCL_STEP_TRAPPED;
  }
  if (rc < 0) {
    ccl_last_error = rc;
    ccl_toplevel_trapped = 1;
    return WASM_CCL_STEP_TRAPPED;
  }

  return WASM_CCL_STEP_RUNNING;
}

#endif /* WASM32 */
