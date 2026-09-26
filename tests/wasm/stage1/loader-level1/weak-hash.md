# Runtime weak hash tables

The 26 September request supersedes the Stage 1 strong-table substitute for
runtime-created native-shape tables. Audit 185 (`fd385a5f`) found no defect;
the user accepted this implementation without additional criterion credit.

The collector admits weak keys and weak values, traces the fourteen header
cells strongly (including the cache), then computes the ephemeron fixed point.
A key reachable only through its own value does not retain the pair. Reaping
writes the native deleted markers and adjusts count/deleted-count according to
`keys_frozen`. Moving live tracked keys sets `key_moved`; reaping alone does not
request a rehash. Each pass reads original source pairs, so it never feeds an
already forwarded destination pointer back to `forward`. Invalid references in
either member still refuse, even in a pair that would otherwise be reaped.
All writes before commit stay in destination/scratch storage.

The brief's flag mask needed one correction found by target execution:
`$nhash-track-keys-mask` is `-(ash 1 28)`, whose tagged wasm32 value is
`0xc0000000`. Admission therefore accepts the sign bit only together with
`track_keys`, checks the remaining flags against `0x780c6800`, and preserves
the actual signed word. The sign bit without tracking still refuses. Separate
directed rows exercise both cases; the original startup/collection refusal
and the diagnostic object (`flags = 0xc0004800`) are retained.

Restored runtime requests cover function names, documentation, binding-index
reverse lookup, slot IDs, defgeneric methods, EQL methods, setter names and
inverses, lambda lists, and EQL specializers. Existing unguarded weak requests
(including EQUAL weak-value combined methods) use the same collector path.
The Wasm function-vector name side table also uses weak keys. Generated
Hash access, removal, clearing, counting and iteration distinguish native vectors from the early owner/pair
representations and dispatch native vectors to the Lisp implementation. The
Wasm type-predicate table maps HASH-TABLE, GVECTOR, BIT-VECTOR and PATHNAME
to their existing predicates, so ordinary hash access and atomic vector updates do not require
the unfinished FIND-CLASS bootstrap. The loader installs the same pinned EQL
leaf already qualified by the compiler/runtime corpus; it adds no comparison
implementation.

Phase 1 disposition: the image builder's owner-created metadata tables keep
its existing strong representation. Converting those tables requires a separate
image-builder step using native-shape vectors and the audit-133 size census.
Target execution corrected the brief's assumption about the level-1 witness:
this prefix serializes `%lambda-lists%`, `%setf-function-names%` and the inverse
map with value 51 (unbound), not with an owner-created table. The restored
`%lambda-lists%` DEFVAR therefore creates a weak table at runtime. Its witness
now requires the weak bit; the original failed strong expectation and the
initial binding words are retained. No image-built table is converted here.
`hash.c`, the early `%wasm-make-hash-table` substitute, population subtag 90,
finalization/termination, multi-Worker GC and upstream kernel source remain
outside this change. Finalizeable vectors and weak bits on owner-created
vectors continue to refuse.

O-116: the witness's `FUNCALL`/`SYMBOL-FUNCTION` idiom deliberately tests the
installed public constructor and count function cells. Generated accessors can
use the Wasm representation dispatchers; the indirect calls also check their
public native destinations. Product `l0-def` and `l1-utils` initializers call
`MAKE-HASH-TABLE` directly, so constructor coverage includes both call paths.

The declared level-1 runner extensions compile `weak-witnesses.lisp` and the
original `hash-table-weak-p`, `maphash` and iterator definitions. Four modes compare EQ `:weak t`,
EQ `:weak :key`, EQ `:weak :value`, and EQUAL `:weak :value`, each with a retained
reference and a dropped reference. The target invokes the producer, collects
at an owner boundary, then invokes the observer. Native invokes the same
producer and observer with `(gc)` between them. The native/target forms check
weakness, lookup presence/value and table count.
An additional witness checks HASH-TABLE type tests on a table, fixnum, cons and
ordinary vector. Four operation witnesses check insertion, MAPHASH, count,
REMHASH and CLRHASH for all four weakness/test combinations. The full corpus also supplies signed/unsigned conversion
boundary inputs and updates the obsolete bignum-LDB refusal to native-checked
results; those numeric capabilities were already present in the checkout.

```sh
python3 tests/wasm/stage1/loader-level1/collector.py /private/tmp/ccl-work/codex/weak-hash-collector/run
python3 tests/wasm/stage1/loader-level1/run.py /private/tmp/ccl-work/codex/weak-hash-execution/run
python3 tests/wasm/stage1/loader-level1/qualify.py readers /private/tmp/ccl-work/codex/weak-hash-readers/run
python3 tests/wasm/stage1/loader-level1/qualify.py native /private/tmp/ccl-work/codex/weak-hash-native/run
python3 tests/wasm/stage1/loader-level1/qualify.py corpus /private/tmp/ccl-work/codex/weak-hash-corpus/run
```

Collector qualification passes 123 directed/inherited checks and kills all
17 mutations (ten inherited, seven weak-specific). Directed cases cover both
reap variants, both weak directions, both chain orders, self/mutual cycles,
a newly discovered weak vector, tracking, strong caches, unreachable vectors,
minimum/maximum capacity, markers, invalid references and late space failure.
The original collector's refusal and the initial fixture failures are retained.

Native R6/R6a passes 21,843 tests (75 upstream-disabled cases unchanged) and
restores all 164 FASLs. Of the registered
FASLs, 45 are byte-identical and 119 have the permitted source-location
changes with decoded-code comparison; the three existing compiler module-list
changes remain explicitly declared. The 13 shared-source reader comparisons
cover all 17 existing target profiles (221 comparisons). The final source
hashes bind those results, including the separate final `l0-def` reader run.

Relative to the checkout at task start, product Lisp changes are 54 added and
25 removed lines; collector C changes are 78 added and 17 removed lines.
Weak support takes no whole-file or acceptance credit. The current checkout,
which already contained separate level-1 work, compiles and cross-loads 36
whole files; the next compilation stop remains `l1-streams.lisp` at
`:BOOTSTRAP-TYPECHECK`. The brief's 29/24/0 baseline is not attributed to this
weak-table change.

The final four execution modes pass all 52 new native-matched comparisons
(13 observations per mode), including retained/dropped weak entries and table
operations. Each mode installs 1,478 modules, executes 93 of 97 initializers,
and checks 176 observations plus 141 controls. Plain/relocated modes perform
25 collections; collection/relocated-collection modes perform 298. Of the 176
observations, 169 derive their results from native execution (one fresh-RNG
row uses an explicitly adapted seed setup) and seven are explicit target
expectations: platform, metrics, metadata, and four seed-boundary/collection
rows. The immutable weak-pack summary counted only three explicit expectations;
this corrects that reporting error without changing any comparison or result.

The complete prefix still reports INCOMPLETE: the preexisting non-lock-free
hash GC-lock case, three malformed-FASL condition cases and the seed-condition
case remain pending. Four startup refusals remain (STRING= package export,
%TYPE-OF, and the two GC-statistics pointer registrations). None is a weak-table
witness. There is no complete-boot, target LOAD or acceptance claim.
The final compiler/runtime corpus passes 26,112 fresh comparisons with no
sampling; `%MAP-AREAS` and `%MAP-LFUNS` retain their previously declared native
heap-enumeration exclusions. The evidence pack retains source/tool identities,
original failures, diagnostic reproductions and the final comparison records:
`ccl-evidence/2026-09-26-weak-hash-r1/packet.json`.
