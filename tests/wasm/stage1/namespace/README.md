# Read-only namespace provider, R1

Files cross-compiled / cross-loaded / target-loaded: 0 / 0 / 0 in this unit.
Accepted originals remain 575 / 535 non-NIL. This implements the host half of
NSL-1; it does not submit S1-NAMESPACE-a or claim generated-Lisp execution.

`namespace.mjs` admits a version-1 manifest with explicit root and directory
entries, file byte arrays and SHA-256 hashes, and owner-supplied absolute `cwd`
and `cclRoot`. It snapshots ordinary byte arrays and rejects shared input buffers.
It never imports a filesystem, opens a host path, resolves a symlink, normalizes
Unicode or decodes percent escapes. Hash-only entries must be resolved by the
owner before admission. Paths are physical namespace paths: Lisp logical-host
translation to `cclRoot` remains part of the caller bridge.

Each session owns monotonically allocated descriptors, positions and directory
cursors. Closing a descriptor never makes its number live again. Reads return
copies. PREAD does not change position; READ advances by the returned byte count;
EOF, including a position past EOF, returns an empty array. SEEK permits positions
past EOF. Directory iteration is sorted and returns `null` at end. There are no
write operations; non-read OPEN modes refuse. Limits bound entries, copied bytes,
active handles, lifetime handle IDs (positive target fixnums) and read sizes.

The private tree's paths are canonical at admission. Runtime resolution checks
each directory traversed, collapses `.`/`..`, clamps `..` at the virtual root and
requires a trailing slash to designate a directory. Two refusal differences
from CCL's Darwin path normalization are explicitly asserted: `a.bin/../ab.bin`
and `a.bin/` are refused here; native `%REALPATH` simplifies them. They get no
native comparison credit. This boundary needs review alongside the eventual
Lisp pathname bridge; it is not an assertion that the native behavior is wrong.

Validation: 57 matching native rows (CCL's actual OPEN, READ-SEQUENCE,
FILE-POSITION, FILE-LENGTH, CLOSE, DIRECTORY and %REALPATH), two explicit path
differences, 80 directed/state checks, and six rejected faults. Four hand-built
D5 transport cases reuse `stage0/integrated-runtime` unchanged: full/short/EOF
reads, collection while FOREIGN, interrupt wakeup, value/root/thread restoration
and stale completion rejection. These select request arguments on the owner;
they do **not** prove encoding or dispatch of a generated Lisp file request.
No new mailbox protocol or production TCR contract is introduced.

A separate native probe calls the existing INSTALL-STANDARD-FOREIGN-TYPES with a
fresh descriptor matching the registered 32-bit Wasm descriptor, while CDB-OPEN
would fail. Seven sizes match and no database is opened. This confirms the
initializer itself need not be replaced. Reading/initializing the foreign-types
file on the target (including its host descriptor definition) remains owed.

Next: compile and connect the real file callers. Today FD-READ/FD-OPEN-PATH/
FD-LSEEK/FD-CLOSE still reach INT-ERRNO-FFCALL and %KERNEL-IMPORT in `l0-io.lisp`.
PROBE-FILE/TRUENAME still reach %REALPATH/%UNIX-FILE-KIND. The generated bridge
must marshal bounded paths/bytes into stable owner storage, retain Lisp roots
across D5 suspension, and translate returned statuses into the native contracts.
The JSPI profile is deferred. LOAD and normal FASL publication are not claimed.

Reproduce from the packet's source commit, beside `ccl-evidence`:

```sh
python3 tests/wasm/stage1/namespace/packet.py verify \
  ../ccl-evidence/2026-09-24-namespace-provider-r1 \
  /private/tmp/ccl-work/codex/namespace-review
```

This runs native, provider, faults and D5 composition in about six seconds on the
author's machine, excluding toolchain hashing. No compiler/runtime/native Lisp
product source changes here; no R6 rebuild is needed. Retention does not execute
anything and removes the managed output after verifying retained records.
