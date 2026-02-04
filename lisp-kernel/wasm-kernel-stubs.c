/*
 * WASM32 kernel stubs
 *
 * These definitions exist to let the WASM kernel link as a freestanding module
 * during early bring-up (no image loader, no OS, no WASI).
 */

#ifdef WASM32

#include "lisp.h"
#include "lisp-exceptions.h"

#include <sys/types.h>

/* Used by lisp-debug.c for banner/prompt printing. */
pid_t main_thread_pid = 0;

/* pmcl-kernel.c stores the address of these in lisp globals. On other
 * platforms they're code labels; for now they're placeholders.
 */
LispObj ret1valn = 0;
LispObj nvalret = 0;
LispObj popj = 0;

/* imports.s provides this on other platforms. */
LispObj import_ptrs_base = 0;

LispObj
start_lisp(TCR *tcr, LispObj arg)
{
  (void)tcr;
  (void)arg;
  __builtin_trap();
  __builtin_unreachable();
}

#endif /* WASM32 */
