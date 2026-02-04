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
#include <stdint.h>
#include "lisp.h"
#include "lisp-exceptions.h"
#include "wasm-subprims.h"
#include "wasm-subprims-map.h"

typedef void (*subprim_fn)(void);

static void
wasm_call_subprim_index(uint32_t index)
{
  if (index >= WASM_SUBPRIMS_COUNT) {
    Bug(NULL, "WASM subprim index out of range");
  }
  /* In WASM, a function pointer call becomes a `call_indirect` through the
   * module's function table. We represent subprims as raw table indices, so
   * we can dispatch by casting the index to a function pointer.
   *
   * Toolchain note: for a shared multi-module table, link the modules with an
   * imported table (e.g. wasm-ld `--import-table`) and have the JS host provide
   * and populate it with subprim implementations.
   */
  ((subprim_fn)(uintptr_t)index)();
}

__attribute__((used, visibility("default"), export_name("wasm_call_subprim_fixnum")))
void
wasm_call_subprim_fixnum(LispObj sp_index_fixnum)
{
  uint32_t index = wasm_subprim_index_from_fixnum(sp_index_fixnum);
  wasm_call_subprim_index(index);
}

/* Subprim implementations are installed into the WASM table by the host.
 * The kernel provides:
 *  - the `sptab` fixnum-index table (copied into each TCR)
 *  - a dispatcher that performs a `call_indirect` via the table index.
 */

static LispObj wasm_sptab_storage[WASM_SUBPRIMS_COUNT];
LispObj *sptab = wasm_sptab_storage;
LispObj *sptab_end = wasm_sptab_storage + WASM_SUBPRIMS_COUNT;
static int wasm_sptab_initialized = 0;

void
wasm_init_sptab(void)
{
  int i;

  if (wasm_sptab_initialized) {
    return;
  }
  for (i = 0; i < WASM_SUBPRIMS_COUNT; i++) {
    wasm_sptab_storage[i] = box_fixnum(i);
  }
  wasm_sptab_initialized = 1;
}
#endif
