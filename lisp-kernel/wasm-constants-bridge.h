#ifndef CCL_WASM_CONSTANTS_BRIDGE_H
#define CCL_WASM_CONSTANTS_BRIDGE_H

#include "arm-constants.h"

#ifdef WASM32
/* wasm-host.h defines kernel opcodes validated by the ABI contract. */
#include "wasm-host.h"
#include <stddef.h>
/* Cross-language ABI contract validation (auto-generated). */
#include "../build/wasm32/abi-validate.h"
#endif

#endif
