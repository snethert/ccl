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
  BytePtr sp = (BytePtr)wasm_get_cstack_pointer();
  lisp_frame *frame = (lisp_frame *)sp;

  /*
   * Some control-flow paths can unwind past the host-entered frame before
   * returning to C (e.g. non-local exits). If the frame marker is gone, treat
   * the frame as already unwound and just restore the previous last_lisp_frame.
   */
  if (frame->marker != lisp_frame_marker) {
    tcr->last_lisp_frame = old_last_lisp_frame;
    return;
  }
  wasm_cstack_pop_frame(tcr, old_last_lisp_frame);
}

enum {
  WASM_CSTACK_FRAME_SELFTEST_OK = 1u,
  WASM_CSTACK_FRAME_SELFTEST_NO_TCR = 10u,
  WASM_CSTACK_FRAME_SELFTEST_NO_SAVEVSP = 11u,
  WASM_CSTACK_FRAME_SELFTEST_OUTER_FRAME_MISSING = 12u,
  WASM_CSTACK_FRAME_SELFTEST_OUTER_FRAME_SAVEVSP = 13u,
  WASM_CSTACK_FRAME_SELFTEST_INNER_FRAME_MISSING = 14u,
  WASM_CSTACK_FRAME_SELFTEST_INNER_FRAME_SAVEVSP = 15u,
  WASM_CSTACK_FRAME_SELFTEST_UNWIND_SP = 16u,
  WASM_CSTACK_FRAME_SELFTEST_UNWIND_LAST = 17u,
  WASM_CSTACK_FRAME_SELFTEST_FINAL_SP = 18u,
  WASM_CSTACK_FRAME_SELFTEST_FINAL_LAST = 19u,
  WASM_CSTACK_FRAME_SELFTEST_FINAL_SAVEVSP = 20u
};

static void
wasm_restore_cstack_selftest_state(TCR *tcr,
                                   BytePtr original_sp,
                                   natural original_last_lisp_frame,
                                   LispObj *original_save_vsp)
{
  if (tcr == NULL) {
    return;
  }
  wasm_set_cstack_pointer(original_sp);
  tcr->last_lisp_frame = original_last_lisp_frame;
  tcr->save_vsp = original_save_vsp;
}

uint32_t
wasm_cstack_frame_coherence_selftest(void)
{
  TCR *tcr = wasm_get_tcr(false);
  BytePtr original_sp;
  natural original_last_lisp_frame;
  LispObj *original_save_vsp;
  LispObj frame_save_vsp;
  natural old_outer_last_lisp_frame;
  BytePtr outer_sp;
  lisp_frame *outer_frame;
  natural old_inner_last_lisp_frame;
  BytePtr inner_sp;
  lisp_frame *inner_frame;
  BytePtr unwound_sp;
  LispObj outer_marker;

  if (tcr == NULL) {
    return WASM_CSTACK_FRAME_SELFTEST_NO_TCR;
  }

  original_sp = (BytePtr)wasm_get_cstack_pointer();
  original_last_lisp_frame = tcr->last_lisp_frame;
  original_save_vsp = tcr->save_vsp;
  frame_save_vsp = (LispObj)original_save_vsp;
  if (frame_save_vsp == 0) {
    frame_save_vsp = tcr->wasm_gprs[vsp];
  }
  if (frame_save_vsp == 0) {
    return WASM_CSTACK_FRAME_SELFTEST_NO_SAVEVSP;
  }

  old_outer_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, frame_save_vsp);
  outer_sp = (BytePtr)wasm_get_cstack_pointer();
  outer_frame = (lisp_frame *)outer_sp;
  if ((outer_frame->marker != lisp_frame_marker) ||
      (tcr->last_lisp_frame != (natural)outer_sp)) {
    wasm_restore_cstack_selftest_state(tcr,
                                       original_sp,
                                       original_last_lisp_frame,
                                       original_save_vsp);
    return WASM_CSTACK_FRAME_SELFTEST_OUTER_FRAME_MISSING;
  }
  if (outer_frame->savevsp != frame_save_vsp) {
    wasm_restore_cstack_selftest_state(tcr,
                                       original_sp,
                                       original_last_lisp_frame,
                                       original_save_vsp);
    return WASM_CSTACK_FRAME_SELFTEST_OUTER_FRAME_SAVEVSP;
  }

  old_inner_last_lisp_frame = wasm_enter_lisp_frame(tcr, 0, 0, frame_save_vsp);
  inner_sp = (BytePtr)wasm_get_cstack_pointer();
  inner_frame = (lisp_frame *)inner_sp;
  if ((inner_frame->marker != lisp_frame_marker) ||
      (tcr->last_lisp_frame != (natural)inner_sp)) {
    wasm_restore_cstack_selftest_state(tcr,
                                       original_sp,
                                       original_last_lisp_frame,
                                       original_save_vsp);
    return WASM_CSTACK_FRAME_SELFTEST_INNER_FRAME_MISSING;
  }
  if (inner_frame->savevsp != frame_save_vsp) {
    wasm_restore_cstack_selftest_state(tcr,
                                       original_sp,
                                       original_last_lisp_frame,
                                       original_save_vsp);
    return WASM_CSTACK_FRAME_SELFTEST_INNER_FRAME_SAVEVSP;
  }

  unwound_sp = inner_sp + sizeof(lisp_frame);
  outer_marker = outer_frame->marker;
  outer_frame->marker = 0;
  wasm_set_cstack_pointer(unwound_sp);
  tcr->last_lisp_frame = old_inner_last_lisp_frame;
  wasm_exit_lisp_frame(tcr, old_inner_last_lisp_frame);
  outer_frame->marker = outer_marker;
  if ((BytePtr)wasm_get_cstack_pointer() != unwound_sp) {
    wasm_restore_cstack_selftest_state(tcr,
                                       original_sp,
                                       original_last_lisp_frame,
                                       original_save_vsp);
    return WASM_CSTACK_FRAME_SELFTEST_UNWIND_SP;
  }
  if (tcr->last_lisp_frame != old_inner_last_lisp_frame) {
    wasm_restore_cstack_selftest_state(tcr,
                                       original_sp,
                                       original_last_lisp_frame,
                                       original_save_vsp);
    return WASM_CSTACK_FRAME_SELFTEST_UNWIND_LAST;
  }

  wasm_exit_lisp_frame(tcr, old_outer_last_lisp_frame);
  if ((BytePtr)wasm_get_cstack_pointer() != original_sp) {
    wasm_restore_cstack_selftest_state(tcr,
                                       original_sp,
                                       original_last_lisp_frame,
                                       original_save_vsp);
    return WASM_CSTACK_FRAME_SELFTEST_FINAL_SP;
  }
  if (tcr->last_lisp_frame != original_last_lisp_frame) {
    wasm_restore_cstack_selftest_state(tcr,
                                       original_sp,
                                       original_last_lisp_frame,
                                       original_save_vsp);
    return WASM_CSTACK_FRAME_SELFTEST_FINAL_LAST;
  }
  if (tcr->save_vsp != original_save_vsp) {
    wasm_restore_cstack_selftest_state(tcr,
                                       original_sp,
                                       original_last_lisp_frame,
                                       original_save_vsp);
    return WASM_CSTACK_FRAME_SELFTEST_FINAL_SAVEVSP;
  }

  return WASM_CSTACK_FRAME_SELFTEST_OK;
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
