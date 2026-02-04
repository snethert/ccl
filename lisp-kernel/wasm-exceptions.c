/*
 * Copyright 1994-2010 Clozure Associates
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifdef WASM32
#include "lisp.h"
#include "threads.h"

/* No OS page protection, but lots of the kernel expects 4KiB page arithmetic. */
int page_size = 4096;
int log2_page_size = 12;

void
adjust_exception_pc(ExceptionInformation *xp, int delta)
{
  if (xp == NULL) {
    return;
  }
  xpPC(xp) = xpPC(xp) + delta;
}

void
exception_init()
{
  /* No signals on WASM32. */
}

Boolean
lisp_frame_p(lisp_frame *spPtr)
{
  return (spPtr->marker == lisp_frame_marker);
}

void
restore_soft_stack_limit(unsigned stkreg)
{
  TCR *tcr = wasm_get_tcr(false);
  area *a;

  (void)stkreg;
  if (tcr == NULL) {
    return;
  }
  a = tcr->cs_area;
  if (a == NULL) {
    return;
  }
#if WASM_ALLOW_MEMORY_GROWTH
  if (((natural)tcr->cs_limit == CS_OVERFLOW_FORCE_LIMIT) ||
      ((BytePtr)ptr_from_lispobj(tcr->cs_limit) <= a->hardlimit)) {
    wasm_grow_cstack(WASM_DEFAULT_CSTACK_SIZE);
  }
#endif
  tcr->cs_limit = (LispObj)ptr_to_lispobj(a->softlimit);
}
#endif
