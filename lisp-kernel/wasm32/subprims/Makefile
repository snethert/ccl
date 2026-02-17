# CCL WASM32 Subprims Build
#
# Builds the subprims side-module (subprims.wasm).
# Inherits toolchain configuration from config.mk / environment variables.
# Source env.sh before running: source scripts/wasm/env.sh && make -C lisp-kernel/wasm32/subprims

# Repository root (three levels up from lisp-kernel/wasm32/subprims/)
REPO_ROOT := $(shell cd ../../.. && pwd)

# Include build configuration (shared with kernel Makefile)
-include ../config.mk

# Toolchain (from environment / config.mk)
CC := $(CCL_WASM_CC)
WASM_LD := $(CCL_WASM_LD)
WASM_TARGET := $(CCL_WASM_TARGET)

# Build directories
SUBPRIMS_DIR := $(CCL_WASM_SUBPRIMS_DIR)
SUBPRIMS_WASM := $(SUBPRIMS_DIR)/subprims.wasm

VC_REVISION := "$(shell git describe --dirty 2>/dev/null || echo unknown)"

VPATH = ../../
RM = /bin/rm

CDEFINES = -DWASM32 -D_REENTRANT -DVC_REVISION=$(VC_REVISION)
CDEBUG = $(CCL_WASM_DEBUG)
COPT = $(CCL_WASM_OPT)
WFORMAT = -Wno-format
PLATFORM_H = platform-wasm32.h

.DEFAULT_GOAL := all

.c.o:
	$(CC) --target=$(WASM_TARGET) -include ../../$(PLATFORM_H) -c $< $(CDEFINES) $(CDEBUG) $(COPT) $(WFORMAT) -o $@

COBJ = wasm-subprims-provider.o

cclean:
	$(RM) -f $(COBJ) $(SUBPRIMS_WASM)

clean: cclean

.PHONY: all subprims clean cclean

all: subprims

subprims: $(COBJ)
	@echo "Building subprims module..."
	@mkdir -p $(SUBPRIMS_DIR)
	$(WASM_LD) --no-entry --import-memory --import-table -z stack-size=1048576 \
	  -o $(SUBPRIMS_WASM) $(COBJ)
	@echo "Subprims built: $(SUBPRIMS_WASM)"
