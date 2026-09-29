# Generated Lisp callbacks

The eighth Stage 2 unit connects typed foreign callbacks to ordinary generated
Lisp through the product service. Execution and independent review are separate
in [the bound results](../../../../doc/WASM/stage2/foreign-lisp-callback-results.json).
No FMT or LL acceptance credit; no whole-file compilation/count movement.

```lisp
(let ((callback (ccl::register-wasm-callback library "integer"
                  (lambda (x) (+ x 42)))))
  (unwind-protect (ccl::wasm-call library "cb-call" callback 7)
    (ccl::deregister-wasm-callback callback)))
```

Registration takes a function, a declared callback type name and the library
identity. The service owns operations 12/13 within foreign selector 15. It
validates the wrapper's owned function object and installed code registry entry
before publishing a callback token. Callback parameters accept only callback
tokens with the declared library/type. Registration strongly roots the wrapper
and its captured function until explicit deregistration or library retirement.
Deregistration is idempotent. Slots remain tombstones and are never reused;
tokens and table slots are finite, as in the preceding callback unit.

The embedding supplies `callbackEnv` with the admitted Lisp `table` and
`code_registry`. The invoker boxes scalar arguments, reloads the rooted callable
after the allocation safepoint, and reserves a separate B argument/result area
above the suspended call. Its root chain links to the outer B roots. The normal
generated public B entry handles its own frames and bindings. The service reads
and validates the result vector while admitted, converts every result to a host
scalar, and restores its five temporary TCR fields. The owner independently
validates the remaining checkpoint and live heap before returning to FOREIGN.
No Lisp pointer enters foreign memory or its callback table.

The Lisp wrapper accepts a vector of arguments and returns a vector of multiple
values, including an empty vector for zero values. It catches ordinary errors.
An `unwind-protect` with a private catch also intercepts escaping `THROW` and
captured `RETURN-FROM` transfers, after inner cleanups run. Such failures return
NIL to the trusted invoker; the original condition or exit values are deliberately
not transported to the caller. The foreign trampoline supplies the declared
scalar fallback, suppresses subsequent callbacks in that foreign entry, and
reports an ordinary foreign-call error only after foreign frames return. The
library remains usable after these contained failures. A later foreign trap
remains primary and retires the library.

An exception escaping the generated wrapper is fatal and produces an
`AggregateError` with no retained Lisp payload. The Worker must be abandoned;
this does not establish recovery from engine traps or failed owner admission.
Audit 198 O-177's existing fatal states (FOREIGN after completed callback return,
RUNNING after most failed return validations) are now asserted along with
refusal of later foreign entry. They are not newly qualified Lisp states.
Nested foreign calls, deregistration, allocation and finalizer draining through
the foreign service during a callback refuse through the busy guard. Ordinary
Lisp allocation and synchronous collection on this Worker are supported.

## Verification

Qualification passes **187 checks in Node, Chromium, Firefox and WebKit / 80
killed mutants**. This adds 37 callback service cases, two O-179 finalizer cases
and 11 controls to the prior 148/69 suite. The post-READY witness matches **61
native rows**, including **16 new callback rows**, with **99 foreign entries,
74 moving collections during FOREIGN and nine explicit RUNNING collections**.
The lower callback regression passes **80 checks per engine / 63 mutants**
with the new O-177 state/refusal assertions. Product Lisp adds 25 lines (99
API lines total). Executed; independent review pending.

Four original development failures are retained: an unsaved-index fixture call,
a duplicate native oracle definition, an overly strict unchanged-allocation
frontier assertion, and a guessed count of ten forced collections where the
fixture contains nine. The scalar callback allocation failure was in the
fixture: TCR 48 advanced by 1688 bytes without collection. Its corrected check
requires a nondecreasing frontier and retains the other 63 word checks with the
previous five collector-word exemptions on a moving collection. The final
callback rows also match explicit contract expectations, so native/target
agreement alone cannot bless a changed containment outcome.

The shared API driver adds directed service cases and ordinary post-READY Lisp
rows to the scalar/buffer/finalizer/string witness. Browser Workers use the same
product service, real collector and real indirect calls, with a synthetic B entry
for controlled invalid outcomes. Generated Lisp runs under Node. Native CCL
executes the same containment wrapper; the native oracle models only the fixture
foreign library and transport. A fixture-only process selector 16 forces moving
collection while RUNNING, including inside callback bodies and unwind cleanups;
retired spaces are poisoned. The ordinary API library also collects after the
callback returns, before the foreign call exits.

Directed cases cover scalar types, signed zero, multiple/zero values, closure
state, registration-only roots, collection, contained errors/nonlocal exits,
once-only cleanup, suppression of a repeated callback, stale/tombstoned handles,
wrong function/type/library/token, result shape/arity/type, token exhaustion,
stack limits, reentry, fatal escape and registry admission. O-179 adds a live-heap
refusal before finalizer queue consumption and successful registration after a
refused anchor. The lower callback suite adds O-177 assertions.

Common scalar decoding and object-bound predicates reuse the API cases.
The service's callback library-affinity check has the same admitted domain as
the lower callback handle map, which also refuses the wrong library. The NIL
failure check also reaches the vector-shape refusal if removed; its purpose is
a stable failure classification. Valid compiler-owned functions and installed
registry rows retain the loader's metadata and generation obligations.

Audit 198 O-178's undeclared-table-export clause is retained as a reason-only
equivalence: the earlier binary admission already refuses that module.

## Reproduction

Verify the two RAM mounts per `CLAUDE.md`, then restore the
[pinned browser tools](../browser-tools/README.md). From the repository root:

```sh
work=/private/tmp/ccl-work/codex/foreign-lisp-callbacks
python3 -B tests/wasm/stage1/loader-target/build.py "$work/boot" --boot0
python3 -B tests/wasm/stage1/loader-target/build.py "$work/level1" --level1
python3 -B - <<'PY'
from pathlib import Path
sources = ['runtime/wasm32/foreign-api.lisp'] + [
    f'tests/wasm/stage2/{name}/checks.lisp' for name in
    ['foreign-api', 'foreign-finalizers', 'foreign-strings', 'foreign-lisp-callbacks']]
Path('/private/tmp/ccl-work/codex/foreign-lisp-callbacks/source.lisp').write_text(
    '\n'.join(Path(p).read_text() for p in sources))
PY
python3 -B tests/wasm/stage1/loader-target/build.py "$work/checks" \
  --postimage="$work/boot" --source="$work/source.lisp"
python3 -B tests/wasm/stage2/foreign-api/run.py \
  --boot "$work/boot" --level1 "$work/level1" --checks "$work/checks" \
  --output /private/tmp/ccl-work/codex/foreign-lisp-callback-tests/run \
  --playwright /private/tmp/ccl-work/codex/stage2-browser-tools/node_modules/playwright-core/index.mjs \
  --browser-config /absolute/path/to/browser-config.json
```

The lower callback regression uses its existing `run.py` and the same browser
options. Unchanged owner/scalar/buffer/collector product sources reuse audit 198
by exact source identity. The compiler corpus remains deferred until completion
of the whole FFI layer. Browser generated Lisp, mounted namespace providers and
multi-Worker D5 remain open. Successful generated artifacts are disposable;
the compact pack retains identities, results and minimal original failures.
