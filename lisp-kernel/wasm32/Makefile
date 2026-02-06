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

VC_REVISION := "$(shell git describe --dirty 2>/dev/null || echo unknown)"

VPATH = ../
# VPATH = ../
RM = /bin/rm
# compile with clang for wasm32
WASM_TARGET ?= wasm32-unknown-unknown
WASM_ALLOW_MEMORY_GROWTH ?= 1
WASM_LD ?= wasm-ld-18
CC = clang
# Set to wasm32-wasi if targeting WASI.
CDEFINES = -DWASM32 -DWASM_ALLOW_MEMORY_GROWTH=$(WASM_ALLOW_MEMORY_GROWTH) -D_REENTRANT -DVC_REVISION=$(VC_REVISION)
CDEBUG = -g
COPT = -O2
# Once in a while, -Wformat says something useful.  The odds are against that,
# however.
WFORMAT = -Wno-format
PLATFORM_H = platform-wasm32.h

.DEFAULT_GOAL := all

.c.o:
	$(CC) --target=$(WASM_TARGET) -include ../$(PLATFORM_H) -c $< $(CDEFINES) $(CDEBUG) $(COPT) $(WFORMAT) -o $@

COBJ  = pmcl-kernel.o gc-common.o wasm-gc.o wasm-cstack.o wasm-exceptions.o wasm-host.o wasm-time.o wasm-kernel-imports.o wasm-kernel-request-smoke.o wasm-step-demo.o wasm-ccl-step.o wasm-subprims.o wasm-subprims-standin.o \
		wasm-subprims-smoke.o wasm-no-wasi-libc.o wasm-kernel-stubs.o \
		bits.o image.o thread_manager.o lisp-debug.o memory.o unix-calls.o

DEBUGOBJ =
KERNELOBJ= $(COBJ)

CHEADERS = area.h bits.h arm-constants.h lisp-errors.h gc.h lisp.h \
	lisp-exceptions.h lisp_globals.h macros.h memprotect.h image.h \
	threads.h constants.h wasm-host.h $(PLATFORM_H)

# Subprims linked into the kernel ?
# Yes:

# KSPOBJ = $(SPOBJ)
# all:	../../armcl


# No:

# KSPOBJ=
# all:	../../armcl ../../subprims.so

# OSLIBS = -ldl -lm -lpthread -lrt


# ../../armcl:	$(KSPOBJ) $(KERNELOBJ) $(DEBUGOBJ)
# 	$(CC)  $(CDEBUG)  -Wl,--export-dynamic $(HASH_STYLE) -o $@  $(KSPOBJ) $(KERNELOBJ) $(DEBUGOBJ) -Wl,--no-as-needed $(OSLIBS)


# $(SPOBJ): $(SPINC)
# $(ASMOBJ): $(SPINC)
$(COBJ): $(CHEADERS)


cclean:
	$(RM) -f $(KERNELOBJ) $(DEBUGOBJ) ../../doc/wasm/js/wasmcl.wasm

clean:	cclean
	$(RM) -f $(SPOBJ)

.PHONY: all wasmcl

all: wasmcl

wasmcl: $(KERNELOBJ)
	mkdir -p ../../doc/wasm/js
	$(WASM_LD) --no-entry --import-memory --import-table \
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
	  --export=wasm_set_arg_z --export=wasm_set_arg_y --export=wasm_set_nargs --export=wasm_get_nfn \
	  --export=wasm_return_arg_z --export=wasm_return_arg_y \
	  --export=wasm_return_values2 --export=wasm_return_values3 --export=wasm_return_values4 \
	  --export=wasm_get_mv --export=wasm_get_mv_indexed --export=wasm_restore_vsp \
	  --export=wasm_spill_push --export=wasm_spill_pop \
	  --export=wasm_funcall0 --export=wasm_funcall1 --export=wasm_funcall2 \
	  --export=wasm_funcall3 --export=wasm_funcall4 --export=wasm_funcall5 --export=wasm_funcall6 \
	  --export=wasm_funcall7 --export=wasm_funcall8 --export=wasm_funcall9 --export=wasm_funcall10 \
	  --export=wasm_funcall0_mv --export=wasm_funcall1_mv --export=wasm_funcall2_mv \
	  --export=wasm_funcall3_mv --export=wasm_funcall4_mv --export=wasm_funcall5_mv --export=wasm_funcall6_mv \
	  --export=wasm_funcall7_mv --export=wasm_funcall8_mv --export=wasm_funcall9_mv --export=wasm_funcall10_mv \
	  --export=wasm_get_lisp_nil \
	  --export=wasm_pending_throw_p \
	  --export=wasm_return_fixnum_add --export=wasm_return_fixnum_sub \
	  --export=wasm_return_fixnum_mul --export=wasm_return_fixnum_ash \
	  --export=wasm_return_fixnum_logand --export=wasm_return_fixnum_logior \
	  --export=wasm_return_fixnum_logxor --export=wasm_return_fixnum_lognot \
	  --export=wasm_return_fixnum_neg \
	  --export=wasm_test_entry_funcall1_raw \
	  --export=wasm_get_compiled_module_registry \
	  --export=wasm_kernel_ui_poll --export=wasm_kernel_ui_render --export=wasm_kernel_ui_measure_text \
	  --export=wasm_ffi_test_add \
	  --export=wasm_const_pool_install --export=wasm_const_pool_ref \
	  --export=wasm_box_signed_64 \
	  --export=_SPfix_overflow --export=_SPmakes32 \
	  -o ../../doc/wasm/js/wasmcl.wasm $(KERNELOBJ)

# strip:	../../armcl
# 	strip -g ../../armcl
