# RESET-DB-FILES startup effect

Auxiliary proposal, not integrated and no LL15 credit. This implements native startup
callback snapshot 13017, system ordinal 27:
`RESET-DB-FILES` in `lib/db-io.lisp`. It clears seven cached database handles in
every interface directory; it does not close files or rebuild the directory list.

The unchanged compiler generates four modules for ordinary, cleanup and dynamic
multiple-value calls through the unchanged owner-installed leaf adapter. The new
freestanding `db.c` implements the callback's storage effect on a pinned D1 DLL.
The native oracle runs the untouched registered callback against a private
`*target-ftd*`, checks the actual structure slot indices, and supplies the return
and post-state for empty through 128-directory lists. It never opens a database.

Owner admission requires one contiguous arena containing a four-word DLL header
and all twelve-word interface-directory structures, with distinct trusted type
descriptor identities. It validates every object and both directions of the
complete list before any write. Then it clears slots 5–11 without a call or poll
and publishes all four result words. Names, subdirectories, descriptors, links,
padding and surrounding guards stay unchanged. Malformed lists refuse without
changing the arena, result words or TCR. Repeated reset is idempotent.

The harness runs both list orders at 4 MiB and 2 GiB: 96 scenarios and 30
refusals. It poisons every publication word, independently derives expected
changed bytes, and checks all TCR words except the returned multiple-value count.
Four compiled faults cover a missed slot, a missed final directory, an omitted
publication word and a write on refusal. Compiler R6/R6a is reused by exact hash;
only these four modules and the native callback oracle are compiled afresh.

This is a pinned-storage startup effect, not a general moving structure scanner,
production FTD materializer or a joined startup schedule. The owner supplies the
DLL head and descriptor identities; their production installation and selection
from `*target-ftd*` remain open. The accepted collector does not scan this struct
kind. No concurrency, database I/O, browser or performance claim. Later joining
must preserve native registry order. The sixteen remaining callbacks after the
winners proposal become fifteen after this effect, not a complete startup claim.

Replay from the committed checkout (evidence repository is the sibling):

```
python3 tests/wasm/stage1/startup-db/packet.py verify \
  --evidence ../ccl-evidence \
  --packet ../ccl-evidence/2026-09-20-stage1-startup-db-r1 \
  --output /private/tmp/ccl-startup-db-review
```
