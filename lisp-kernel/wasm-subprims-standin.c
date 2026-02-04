/*
 * WASM subprims stand-ins (C)
 *
 * These are placeholders so the JS host can install a complete subprims table.
 * Real implementations can later override table entries with handwritten WASM.
 */

#ifdef WASM32
#include "lisp.h"
#include "lisp-exceptions.h"
#include "wasm-subprims-map.h"

#define DECL_SUBPRIM(name) \
  __attribute__((used, weak, visibility("default"), export_name(#name))) void name(void)
#define SUBPRIM_STUB(name) \
  DECL_SUBPRIM(name) { Bug(NULL, "WASM subprim not implemented: %s", #name); }

FOR_EACH_WASM_SUBPRIM(SUBPRIM_STUB)

#undef SUBPRIM_STUB
#undef DECL_SUBPRIM

#endif
