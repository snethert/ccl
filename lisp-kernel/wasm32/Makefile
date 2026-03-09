#
# Copyright 2010 Clozure Associates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ============================================================================
# CCL WASM32 Kernel Build
# ============================================================================

# Repository root (two levels up from lisp-kernel/wasm32/)
REPO_ROOT := $(shell cd ../.. && pwd)

# Include build configuration
-include config.mk

# ============================================================================
# Toolchain Setup
# ============================================================================

# Use environment variables with fallbacks from config.mk
CC := $(CCL_WASM_CC)
WASM_LD := $(CCL_WASM_LD)
WASM_TARGET := $(CCL_WASM_TARGET)

# Build directories
BUILD_DIR := $(CCL_WASM_BUILD_DIR)
KERNEL_DIR := $(CCL_WASM_KERNEL_DIR)

# Output file
KERNEL_WASM := $(KERNEL_DIR)/wasmcl.wasm

# ============================================================================
# Compiler and Linker Flags
# ============================================================================

VC_REVISION := "$(shell git describe --dirty 2>/dev/null || echo unknown)"

VPATH = ../
RM = /bin/rm

WASM_ALLOW_MEMORY_GROWTH := $(CCL_WASM_ALLOW_MEMORY_GROWTH)

CDEFINES = -DWASM32 -DWASM_ALLOW_MEMORY_GROWTH=$(WASM_ALLOW_MEMORY_GROWTH) -D_REENTRANT -DVC_REVISION=$(VC_REVISION)
CDEBUG = $(CCL_WASM_DEBUG)
COPT = $(CCL_WASM_OPT)
WFORMAT = -Wno-format
PLATFORM_H = platform-wasm32.h

# User-provided additional flags
CFLAGS_EXTRA := $(CCL_WASM_CFLAGS)
LDFLAGS_EXTRA := $(CCL_WASM_LDFLAGS)

# ============================================================================
# Source Files
# ============================================================================

COBJ = pmcl-kernel.o gc-common.o wasm-gc.o wasm-cstack.o wasm-exceptions.o \
       wasm-host.o wasm-time.o wasm-kernel-imports.o wasm-kernel-request-smoke.o \
       wasm-step-demo.o wasm-ccl-step.o wasm-subprims.o wasm-subprims-standin.o \
       wasm-subprims-smoke.o wasm-no-wasi-libc.o wasm-kernel-stubs.o \
       bits.o image.o thread_manager.o lisp-debug.o memory.o unix-calls.o

DEBUGOBJ =
KERNELOBJ = $(COBJ)

CHEADERS = area.h bits.h arm-constants.h lisp-errors.h gc.h lisp.h \
           lisp-exceptions.h lisp_globals.h macros.h memprotect.h image.h \
           threads.h constants.h wasm-host.h $(PLATFORM_H)

# ============================================================================
# Build Rules
# ============================================================================

.DEFAULT_GOAL := all

# Compilation rule
# -I$(BUILD_DIR): find generated abi-validate.h in the build directory
.c.o:
	$(CC) --target=$(WASM_TARGET) -include ../$(PLATFORM_H) -I$(BUILD_DIR) -c $< \
	  $(CDEFINES) $(CDEBUG) $(COPT) $(WFORMAT) $(CFLAGS_EXTRA) -o $@

# ABI contract header (auto-generated; run generator if missing)
ABI_VALIDATE_H := $(BUILD_DIR)/abi-validate.h

$(ABI_VALIDATE_H):
	@echo "Generating ABI contract artifacts..."
	python3 $(REPO_ROOT)/scripts/wasm/generate_abi_contract.py --build-dir $(BUILD_DIR)

# Dependencies
$(COBJ): $(CHEADERS) $(ABI_VALIDATE_H)

# Build targets
.PHONY: all wasmcl clean cclean

all: wasmcl

wasmcl: $(KERNELOBJ)
	@echo "Building WASM kernel..."
	@mkdir -p $(KERNEL_DIR)
	# --table-base=256: reserve indices 0-255 for the subprims table
	# (installed by JS installSubprimsTable).  Without this, wasm-ld
	# assigns C function-pointer indices starting at 1, which overlap
	# the subprim range and get silently overwritten at runtime.
	$(WASM_LD) --no-entry --import-memory --import-table --table-base=256 -z stack-size=1048576 \
	  --export=wasm_ccl_start \
	  --export=wasm_ccl_start_lisp \
	  --export=wasm_set_current_tcr --export=wasm_get_current_tcr \
	  --export=wasm_request_interrupt_tcr \
	  --export=wasm_get_interrupt_pending_tcr \
	  --export=wasm_get_tcr_toplevel_function --export=wasm_set_tcr_toplevel_function \
	  --export=wasm_set_cstack_bounds --export=wasm_set_cstack_pointer --export=wasm_get_cstack_pointer \
	  --export=wasm_memory_grow_and_relocate \
	  --export=wasm_call_subprim_fixnum \
	  --export=wasm_boot_entry --export=wasm_run_toplevel \
	  --export=wasm_test_entry --export=wasm_test_funcall --export=wasm_test_const_funcall \
	  --export=wasm_test_entry_funcall --export=wasm_test_entry_funcall2 \
	  --export=wasm_const_entry --export=wasm_set_const_value --export=wasm_return_constant \
	  --export=wasm_get_arg_z --export=wasm_get_arg_y \
	  --export=wasm_set_arg_z --export=wasm_set_arg_y --export=wasm_set_arg_x \
	  --export=wasm_set_nargs --export=wasm_set_nfn --export=wasm_set_imm0 --export=wasm_get_nfn \
	  --export=wasm_return_arg_z --export=wasm_return_arg_y \
	  --export=wasm_return_values2 --export=wasm_return_values3 --export=wasm_return_values4 \
	  --export=wasm_get_mv --export=wasm_get_mv_indexed --export=wasm_restore_vsp \
	  --export=wasm_vpush --export=wasm_vpop \
	  --export=wasm_spill_push --export=wasm_spill_pop \
	  --export=wasm_funcall0 --export=wasm_funcall1 --export=wasm_funcall2 \
	  --export=wasm_funcall3 --export=wasm_funcall4 --export=wasm_funcall5 --export=wasm_funcall6 \
	  --export=wasm_funcall7 --export=wasm_funcall8 --export=wasm_funcall9 --export=wasm_funcall10 \
	  --export=wasm_funcall0_mv --export=wasm_funcall1_mv --export=wasm_funcall2_mv \
	  --export=wasm_funcall3_mv --export=wasm_funcall4_mv --export=wasm_funcall5_mv --export=wasm_funcall6_mv \
	  --export=wasm_funcall7_mv --export=wasm_funcall8_mv --export=wasm_funcall9_mv --export=wasm_funcall10_mv \
	  --export=wasm_pending_throw_p \
	  --export=wasm_pending_throw_raw \
	  --export=wasm_return_fixnum_add --export=wasm_return_fixnum_sub \
	  --export=wasm_return_fixnum_mul --export=wasm_return_fixnum_ash \
	  --export=wasm_return_fixnum_logand --export=wasm_return_fixnum_logior \
	  --export=wasm_return_fixnum_logxor --export=wasm_return_fixnum_lognot \
	  --export=wasm_return_fixnum_neg \
	  --export=wasm_test_entry_funcall1_raw --export=wasm_test_entry_funcall0_raw \
	  --export=wasm_reset_root_image_runtime_state --export=wasm_repair_udf_binding --export=wasm_repair_udf_bindings_scan \
	  --export=wasm_set_entry_call_abi --export=wasm_get_entry_call_abi --export=wasm_clear_entry_call_abi \
	  --export=wasm_kernel_ui_poll --export=wasm_kernel_ui_render --export=wasm_kernel_ui_measure_text \
	  --export=wasm_ffi_test_add \
	  --export=wasm_save_image_direct \
	  --export=wasm_box_signed_64 \
	  --export=wasm_alloc_cons_bridge \
	  --export=wasm_get_lisp_nil --export=wasm_get_compiled_module_registry \
	  --export=wasm_boot_get_phase --export=wasm_boot_set_phase \
	  --export=wasm_ccl_load_image --export=wasm_ccl_step --export=wasm_restore_lisp_pointers \
	  --export=wasm_clear_pending_throw \
	  --export=wasm_const_pool_install --export=wasm_const_pool_alias --export=wasm_entry_fn_cache_clear --export=wasm_const_pool_purge_all --export=wasm_const_pool_ref --export=wasm_const_pool_diag_fail_get \
	  --export=wasm_lisp_word_ref --export=wasm_lisp_word_set \
	  --export=wasm_fasload_path \
	  --export=wasm_get_nargs \
	  --export=wasm_kernel_runtime_command_poll --export=wasm_kernel_runtime_event \
	  --export=wasm_probe_foreign_call1 \
	  --export=wasm_run_script_with_output \
	  --export=wasm_set_entry_gc_root_policy_mode --export=wasm_set_subprims_ready \
	  --export=wasm_set_toplfunc_entry --export=wasm_set_symbol_function_entry \
	  --export=wasm_check_symbol_fbound \
	  --export=wasm_grow_lisp_heap \
	  --export=wasm_heap_profile \
	  --export=wasm_vsp_ref \
	  --export=_SPfix_overflow --export=_SPmakes32 \
	  --export=lisp_open --export=lisp_read --export=lisp_write --export=lisp_close \
	  --export=lisp_lseek --export=lisp_fstat --export=lisp_ftruncate --export=lisp_fchmod \
	  --export=wasm_debug_dump_state --export=wasm_debug_tcr_offset --export=wasm_reset_debug_counters \
	  --export=wasm_diag_get_last_cpr_entry --export=wasm_diag_get_last_cpr_slot \
	  --export=wasm_validate_builtin_entries \
	  --export=lisp_bug --export=malloc --export=free \
	  $(LDFLAGS_EXTRA) \
	  -o $(KERNEL_WASM) $(KERNELOBJ)
	@echo "Kernel built: $(KERNEL_WASM)"
	@# Keep scripts/wasm/lib copy in sync (load-image.mjs loads from there)
	@cp $(KERNEL_WASM) $(REPO_ROOT)/scripts/wasm/lib/wasmcl.wasm
	@echo "Kernel synced: $(REPO_ROOT)/scripts/wasm/lib/wasmcl.wasm"

# Clean targets
cclean:
	$(RM) -f $(KERNELOBJ) $(DEBUGOBJ) $(KERNEL_WASM)

clean: cclean

# ============================================================================
# Help
# ============================================================================

.PHONY: help
help:
	@echo "CCL WASM32 Kernel Build"
	@echo ""
	@echo "Targets:"
	@echo "  all (default)  - Build the WASM kernel"
	@echo "  clean          - Remove build artifacts"
	@echo "  help           - Show this help"
	@echo ""
	@echo "Configuration (via environment variables):"
	@echo "  CCL_WASM_CC               - C compiler (current: $(CC))"
	@echo "  CCL_WASM_LD               - WASM linker (current: $(WASM_LD))"
	@echo "  CCL_WASM_TARGET           - Target triple (current: $(WASM_TARGET))"
	@echo "  CCL_WASM_BUILD_DIR        - Build directory (current: $(BUILD_DIR))"
	@echo "  CCL_WASM_CFLAGS           - Additional compiler flags"
	@echo "  CCL_WASM_LDFLAGS          - Additional linker flags"
	@echo "  CCL_WASM_OPT              - Optimization level (current: $(COPT))"
	@echo "  CCL_WASM_DEBUG            - Debug flags (current: $(CDEBUG))"
	@echo ""
	@echo "Output:"
	@echo "  $(KERNEL_WASM)"
	@echo ""
	@echo "See config.mk for defaults and doc/wasm/build.md for documentation."
