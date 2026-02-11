VC_REVISION := "$(shell git describe --dirty 2>/dev/null || echo unknown)"

VPATH = ../../
RM = /bin/rm
WASM_TARGET ?= wasm32-unknown-unknown
WASM_LD ?= wasm-ld-18
CC ?= clang
CDEFINES = -DWASM32 -D_REENTRANT -DVC_REVISION=$(VC_REVISION)
CDEBUG = -g
COPT = -O2
WFORMAT = -Wno-format
PLATFORM_H = platform-wasm32.h

.DEFAULT_GOAL := all

.c.o:
	$(CC) --target=$(WASM_TARGET) -include ../../$(PLATFORM_H) -c $< $(CDEFINES) $(CDEBUG) $(COPT) $(WFORMAT) -o $@

COBJ = wasm-subprims-provider.o

cclean:
	$(RM) -f $(COBJ) ../../../doc/wasm/js/subprims.wasm

clean: cclean

.PHONY: all subprims

all: subprims

subprims: $(COBJ)
	mkdir -p ../../../doc/wasm/js
	$(WASM_LD) --no-entry --import-memory --import-table \
	  -o ../../../doc/wasm/js/subprims.wasm $(COBJ)
