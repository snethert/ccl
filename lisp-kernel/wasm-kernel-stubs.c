/*
 * WASM32 kernel stubs
 *
 * These definitions exist to let the WASM kernel link as a freestanding module
 * during early bring-up (no image loader, no OS, no WASI).
 */

#ifdef WASM32

#include "lisp.h"
#include "lisp-exceptions.h"

#include <stdint.h>
#include <sys/types.h>

/* Used by lisp-debug.c for banner/prompt printing. */
pid_t main_thread_pid = 0;

/* pmcl-kernel.c stores the address of these in lisp globals. On other
 * platforms they're code labels; for now they're placeholders.
 */
LispObj ret1valn = 0;
LispObj nvalret = 0;
LispObj popj = 0;
extern LispObj lisp_nil;

static uint32_t wasm_subprims_ready = 0;

__attribute__((used, visibility("default"), export_name("wasm_set_subprims_ready")))
void
wasm_set_subprims_ready(uint32_t ready)
{
  wasm_subprims_ready = ready ? 1u : 0u;
}

__attribute__((used, visibility("default"), export_name("wasm_get_subprims_ready")))
uint32_t
wasm_get_subprims_ready(void)
{
  return wasm_subprims_ready;
}

LispObj
start_lisp(TCR *tcr, LispObj arg)
{
  (void)arg;
  if (tcr != NULL) {
    tcr->valence = TCR_STATE_LISP;
  }

  /* Bring-up behavior:
   * The full Lisp toplevel loop isn't wired for WASM yet. Return to the host
   * without trapping so the embedding can drive execution via wasm_ccl_step.
   */
  {
    if (!wasm_subprims_ready) {
      static const char msg[] =
        "WASM start_lisp: subprims not ready; returning to host\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    } else {
      static const char msg[] =
        "WASM start_lisp: toplevel loop not wired; returning to host\n";
      wasm_host_log(msg, (unsigned)(sizeof(msg) - 1));
    }
  }

  if (tcr != NULL) {
    tcr->valence = TCR_STATE_FOREIGN;
  }

  return lisp_nil;
}

__attribute__((used, visibility("default"), export_name("wasm_get_lisp_nil")))
LispObj
wasm_get_lisp_nil(void)
{
  extern LispObj lisp_nil;
  return lisp_nil;
}

#endif /* WASM32 */
