SHELL := /bin/bash

ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
NODE_BIN ?= node
PORT ?= 5173

IDB_CTL := $(ROOT_DIR)/scripts/wasm/idb-smoke-server-control.sh

.PHONY: persist-sandbox persist-host-doctor persist-host-lmdb persist-host-browser persist-host-all
.PHONY: persist-idb-up persist-idb-down persist-idb-restart persist-idb-status persist-idb-url persist-idb-logs

persist-sandbox:
	@cd "$(ROOT_DIR)" && $(NODE_BIN) --test doc/wasm/js/persist-service.test.mjs

persist-host-doctor:
	@$(NODE_BIN) -e "import('lmdb').then(()=>console.log('lmdb: available')).catch((err)=>{console.error('lmdb: unavailable:', err?.message || err); process.exit(1);})"

persist-host-lmdb: persist-host-doctor
	@cd "$(ROOT_DIR)" && $(NODE_BIN) doc/wasm/js/lmdb-smoke.mjs
	@cd "$(ROOT_DIR)" && CCL_ENABLE_LMDB_TESTS=1 $(NODE_BIN) --test doc/wasm/js/persist-service.test.mjs

persist-host-browser:
	@cd "$(ROOT_DIR)" && WEB_UI_ENABLE_BROWSER_TESTS=1 npm --prefix web-ui run test:browser

persist-host-all: persist-host-lmdb
	@echo "Host-only persistence checks completed."
	@echo "For browser IndexedDB smoke:"
	@echo "  make -f scripts/wasm/persist-host.mk persist-idb-up"
	@echo "  open $$(make -s -f scripts/wasm/persist-host.mk persist-idb-url)"
	@echo "  make -f scripts/wasm/persist-host.mk persist-idb-down"

persist-idb-up:
	@PORT="$(PORT)" NODE_BIN="$(NODE_BIN)" "$(IDB_CTL)" start

persist-idb-down:
	@"$(IDB_CTL)" stop

persist-idb-restart:
	@PORT="$(PORT)" NODE_BIN="$(NODE_BIN)" "$(IDB_CTL)" restart

persist-idb-status:
	@"$(IDB_CTL)" status

persist-idb-url:
	@PORT="$(PORT)" "$(IDB_CTL)" url

persist-idb-logs:
	@"$(IDB_CTL)" logs
