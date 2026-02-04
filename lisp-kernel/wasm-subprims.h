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

#ifndef __wasm_subprims_h__
#define __wasm_subprims_h__

#include "lisp.h"

/* Subprims are represented as fixnum indices into a WASM function table. */
static inline uint32_t
wasm_subprim_index_from_fixnum(LispObj sp_index_fixnum)
{
  return (uint32_t)unbox_fixnum(sp_index_fixnum);
}

/* Dispatcher: extracts index and performs call_indirect in the WASM backend. */
void wasm_call_subprim_fixnum(LispObj sp_index_fixnum);

#endif
