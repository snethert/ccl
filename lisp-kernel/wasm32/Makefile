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
CC = clang
# Set to wasm32-wasi if targeting WASI.
CDEFINES = -DWASM32 -D_REENTRANT -DVC_REVISION=$(VC_REVISION)
CDEBUG = -g
COPT = -O2
# Once in a while, -Wformat says something useful.  The odds are against that,
# however.
WFORMAT = -Wno-format
PLATFORM_H = platform-wasm32.h

.c.o:
	$(CC) --target=$(WASM_TARGET) -include ../$(PLATFORM_H) -c $< $(CDEFINES) $(CDEBUG) $(COPT) $(WFORMAT) -o $@

# COBJ  = pmcl-kernel.o gc-common.o arm-gc.o bits.o  arm-exceptions.o \
# 	image.o thread_manager.o lisp-debug.o memory.o unix-calls.o

# DEBUGOBJ = lispdcmd.o plprint.o plsym.o albt.o arm_print.o
# KERNELOBJ= $(COBJ) arm-asmutils.o  imports.o

# CHEADERS = area.h bits.h arm-constants.h lisp-errors.h gc.h lisp.h \
# 	lisp-exceptions.h lisp_globals.h macros.h memprotect.h image.h \
# 	threads.h arm-exceptions.h $(PLATFORM_H)

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
# $(COBJ): $(CHEADERS)
# $(DEBUGOBJ): $(CHEADERS) lispdcmd.h


cclean:
	$(RM) -f $(KERNELOBJ) $(DEBUGOBJ) ../../wasmcl

clean:	cclean
	$(RM) -f $(SPOBJ)

# strip:	../../armcl
# 	strip -g ../../armcl
