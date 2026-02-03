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
#include "platform-wasm32.h"

void
restore_soft_stack_limit(unsigned stkreg)
{
  TCR *tcr = get_tcr(false);
  area *a;

  (void)stkreg;
  if (tcr == NULL) {
    return;
  }
  a = tcr->cs_area;
  if (a == NULL) {
    return;
  }
  tcr->cs_limit = (LispObj)ptr_to_lispobj(a->softlimit);
}
#endif
