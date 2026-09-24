# Projected-image READY join — R7

Original-definition credit remains **550 / 515 non-NIL**, with no LL15 slot
claim. This revision repairs all five standalone INVOKE-TYPE-METHOD callers
by compiling their complete `l1-typesys.lisp` environment. It carries the
reviewed R5 MAKE-STRING proposal without integration or compiler changes.

## Type-method dispatch and internal structures

CSUBTYPEP, CELL-CSUBTYPEP-2, TYPE=, TYPE-UNION2 and TYPE-INTERSECTION2 now bind
to whole-file class-mode modules. INVOKE-TYPE-METHOD expands normally instead
of becoming a missing function. The new native comparison exercises CSUBTYPEP
and TYPE=: identity, simple methods, absent complex methods, left-method
argument order, right-method precedence, multiple values and collections
inside callbacks. The method tables and callbacks are directed inputs; this
does not claim full CType-system initialization. Restoring either old
standalone binding is a retained refusal control.

The test exposed READY's old fixture shortcut that classified every internal
structure as a hash table. READY now installs the native `l1-clos-boot` ISTRUCT
classifier: use the cell's wrapper, otherwise FIND-CLASS by name, otherwise
INTERNAL-STRUCTURE. Its lambda is reader-compared with upstream, allowing only
three lexical symbols' package differences. The working class vector is
copied with the accepted typed-vector copy primitive, keeping the loaded
image graph unchanged. The table-binding witness no longer repeats
CORE-CONDITION-PREPARE after initialization and overwrites the new table.

Only the target needs this startup effect; native CCL already initialized its
static class table. Every native oracle entry asserts that table is unchanged.
The caller observes classification with a wrapper, with the wrapper cleared,
and with an unknown internal-structure name, with collection between states.

## Standalone macro screen

`macro-calls.json` checks every standalone `scan_*` module's emitted callees
against all upstream DEFMACRO name sites, and records which bindings READY
actually selects. This is a conservative name screen: reader conditionals,
lexical shadowing and same-name native functions need file-environment
qualification. It does not silently discard matches or count them as working
functions. A reintroduced INVOKE-TYPE-METHOD graph edge fails the census.
The screen covers 1,749 standalone modules against 1,182 macro names: 33
candidate edges in 30 modules. Thirty-one are superseded bindings; the two
unreached candidates are %INTEGER-ABS → NUMBER-CASE and
%GET-HASHED-HTAB-SYMBOL → HTVEC. Neither is counted as usable READY code.
No screened standalone macro-name candidate remains in the selected graph.

## Carried READY contract and limits

The native bignum printer, target radix tables, LDIFF/MAPC, generated image
admission, owner-installed public table bindings, moving heap keys and
class-based conditions remain covered. Four cold boots use both placements
and movement variants. Seven startup roots are checked on image refusal.
The copied radix initializer and ISTRUCT lambda are reader-checked startup
scaffolding, to be replaced by the real file's top-level initialization.
The per-name driver lists and READY qualification callers are interim too.
The heap-image/owner contracts and MAKE-STRING compiler capability are durable.

The full static dependency closure, upstream body attribution for the
replacement cap, printer stream-lock paths and all 35 registered callback
obligations remain open. Successful directed method-table inputs do not
resolve every indirect call. Corpus hashes bind one run; they are not semantic
cross-packet comparisons when symbol numbers change.

## Results

The author corpus passed 26,048 fresh comparisons. The writer and four cold
readers compare 50 type-method outcomes, 30 collecting callbacks and 15
internal-structure classifications, in addition to the carried READY cases.
Four cold boots make 314 collections. All 18 refusal controls pass, including
restoring standalone CSUBTYPEP (checked 2) and TYPE= (checked 4).

The conservative closure now has 652 modules, 113 operators and 31,081
occurrences, with 84 missing edges naming 60 functions and 41 indirect-call
modules. These counts still do not qualify LL15 closure.

Development records retain the initial checked failures, a probe dependency
on the unavailable CLASS-NAME generic (the observer now uses CCL's class-name
slot accessor), the attempted PROGV binding of native static variables, and
the COPY-SEQ/repeated-prepare failures. COPY-SEQ's unresolved array-type startup
state is not claimed fixed by selecting the typed-vector copy primitive.

## Reproduce

```sh
python3 tests/wasm/stage1/ready/packet.py verify ../ccl-evidence/2026-09-23-stage1-ready-join-r7 /private/tmp/ccl-work/claude/ready/verify
```

This runs the full corpus and the READY checks once. The author run executes
26,048 fresh corpus comparisons; submitted READY probe refinements reuse that
unchanged bound corpus, not a second claimed execution. Development inputs and
failures are retained. All 33 proposed compiler/CCL files remain byte-equal to
R5, so its native R6/R6a qualification is reused by exact identity.
`native-reuse.json` binds the qualification; no native rebuild is claimed.
Caches and scratch are disposable. The saved native compiler image is review
tooling, never the port's heap.
