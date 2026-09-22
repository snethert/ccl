# D1 callable storage after audit 158

Steve's instruction, “address the obligations and accept/integrate”, accepts the
reviewed funcallable design along with arch macros and hyperbolic math. This is a
storage decision; method selection is not qualified by it.

Ordinary functions keep the six-field header (1578) and their existing 32-byte
allocation. Code id, environment, version, arity record, debug record and literal
pool occupy words at byte offsets 4 through 24; offset 28 is padding.

Funcallable instances use the seven-field header (1834), also in 32 bytes. Offset
28 points to a traced seven-element simple vector. Its logical indices are CCL's:
code descriptor, class wrapper, slots, dispatch table, discriminating code, hash,
and bits. `nth-immediate` and its setter operate on this vector. Ordinary function
immediates remain a checked refusal. Constructors clone the supplied vector;
collector, pinned-image owner and installer validate it before publication.
The fixture snapshot reader also validates and relocates it. Production image
materialization remains owed.

## Ordinary function metadata: audit 158 O-6 decision

The keyword vector's home is **element 6 of the existing seven-element arity
record**, reached through the function's arity word at byte offset 16. The record
already contains schema version, required count, optional count, rest flag,
keys flag, allow-other-keys flag and the key vector. It is installed from the
literal pool and traced today; neither a new function field nor an image
migration is needed. The accepted compiler's `metadata-arity` builds this record.

Implement the ordinary-function `lfun-keyvect` target branch against this
metadata, returning NIL when the keys flag is false and the key vector otherwise.
Validate the callable and metadata schema using the existing admission checks;
retain the key vector's symbol identities. Do not interpret ordinary
`nth-immediate` index 1 as this metadata: index 1 means the class wrapper for a
funcallable instance. Do not infer native `lfun-bits` from a Wasm code id.

This paragraph settles the storage decision, **not accessor execution**. The
reviewed implementation still refuses ordinary `nth-immediate` with checked code
4. Its admitted callers get no execution credit until the target accessor is
implemented and tested, including no-key, empty-key, ordinary keyword, aliased
keyword and closure cases before and after collection. Code coverage notes and
native trampoline reflection have no D1 implementation and remain explicit
obligations. Generic-function keyword introspection must follow the dispatch
metadata contract rather than treating its wrapper as a keyword vector.

## Representation observer: audit 158 O-7

For `1.5s0` (bits `3fc00000`), native x86-64 reports T for both
`immediate-p-macro` and `hashed-by-identity`. D1 follows x8632 and boxes single
floats, so both results are NIL. The acceptance runner retains the raw native
answers and checks the target answers below and above 2 GiB, before and after
movement. This is a declared representation difference, not a native match or
additional executed-definition credit.

## Installer admission: audit 158 O-8

Installation now admits the existing floating-owner profile in addition to the
legacy profile, so the generated constructor can use allocation retry. This
widens admission. Loader digest and trusted bundle identity checks still apply;
the range reader's default still refuses function imports. The installer binds
the explicit immediate-vector manifest field to the new header and actual
pointer. Ordinary function manifests and metadata retain their old checks.

## Remaining CLOS work

Invocation still executes the template code from the callable prefix; storing a
new discriminating function at immediate index 4 does not redirect a call.
Method selection, class/wrapper construction and fixtures, real image roots,
production materialization and the CLOS READY join remain unqualified. The next
execution work covers the 175 admitted numeric definitions without execution
and the roughly 90 newly admitted CLOS accessors; acceptance of this storage
layout does not count those as executed.
