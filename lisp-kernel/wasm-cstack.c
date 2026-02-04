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
#include "lisp-exceptions.h"
#include "threads.h"

static void
wasm_cstack_bounds_or_bust(TCR *tcr, BytePtr sp, natural need)
{
  BytePtr base = (BytePtr)tcr->wasm_cstack_base;
  natural size = tcr->wasm_cstack_size;
  BytePtr low;

  if ((base == NULL) || (size == 0)) {
    Bug(NULL, "WASM cstack bounds not initialized (call wasm_set_cstack_bounds first)");
  }
  low = base - size;
  if ((sp < low) || (sp > base) || ((natural)(sp - low) < need)) {
    Bug(NULL, "WASM cstack pointer out of bounds");
  }
}

natural
wasm_cstack_push_frame(TCR *tcr, LispObj savefn, pc savelr, LispObj savevsp)
{
  natural old_last = tcr->last_lisp_frame;
  BytePtr sp = (BytePtr)wasm_get_cstack_pointer();
  lisp_frame *frame;

  wasm_cstack_bounds_or_bust(tcr, sp, sizeof(lisp_frame));
  sp -= sizeof(lisp_frame);
  frame = (lisp_frame *)sp;
  frame->marker = lisp_frame_marker;
  frame->savevsp = savevsp;
  frame->savefn = savefn;
  frame->savelr = (LispObj)savelr;

  wasm_set_cstack_pointer(sp);
  tcr->last_lisp_frame = (natural)sp;

  return old_last;
}

void
wasm_cstack_pop_frame(TCR *tcr, natural old_last_lisp_frame)
{
  BytePtr sp = (BytePtr)wasm_get_cstack_pointer();
  lisp_frame *frame = (lisp_frame *)sp;

  if (frame->marker != lisp_frame_marker) {
    Bug(NULL, "WASM cstack pop: not at a lisp frame");
  }

  sp += sizeof(lisp_frame);
  wasm_cstack_bounds_or_bust(tcr, sp, 0);
  wasm_set_cstack_pointer(sp);
  tcr->last_lisp_frame = old_last_lisp_frame;
}

natural
wasm_enter_lisp_frame(TCR *tcr, LispObj savefn, pc savelr, LispObj savevsp)
{
  /* All wasm entry paths must use this wrapper to keep last_lisp_frame
   * consistent for debugger/backtrace and GC stack scanning.
   */
  return wasm_cstack_push_frame(tcr, savefn, savelr, savevsp);
}

void
wasm_exit_lisp_frame(TCR *tcr, natural old_last_lisp_frame)
{
  wasm_cstack_pop_frame(tcr, old_last_lisp_frame);
}

BytePtr
wasm_cstack_push_alloc_marker(TCR *tcr, LispObj next)
{
  BytePtr sp = (BytePtr)wasm_get_cstack_pointer();
  LispObj *p;

  (void)tcr;
  wasm_cstack_bounds_or_bust(tcr, sp, (2 * sizeof(LispObj)));
  sp -= (2 * sizeof(LispObj));
  p = (LispObj *)sp;
  p[0] = stack_alloc_marker;
  p[1] = next;
  wasm_set_cstack_pointer(sp);

  return sp + (2 * sizeof(LispObj));
}

void
wasm_cstack_pop_alloc_marker(TCR *tcr, BytePtr old_sp)
{
  (void)tcr;
  wasm_cstack_bounds_or_bust(tcr, old_sp, 0);
  wasm_set_cstack_pointer(old_sp);
}
#endif
