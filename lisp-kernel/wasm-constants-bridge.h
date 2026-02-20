#ifndef CCL_WASM_CONSTANTS_BRIDGE_H
#define CCL_WASM_CONSTANTS_BRIDGE_H

#include "arm-constants.h"

#ifdef WASM32
/* wasm-host.h defines kernel opcodes validated by the ABI contract. */
#include "wasm-host.h"
#include <stddef.h>
/* Cross-language ABI contract validation (auto-generated).
   Found via -I$(BUILD_DIR) in the Makefile. */
#include "abi-validate.h"
#endif

#endif
