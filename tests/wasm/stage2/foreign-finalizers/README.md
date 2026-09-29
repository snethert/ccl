# Collector-queued foreign buffer finalization

This fifth Stage 2 unit is executed, awaiting independent review. Whole-file
movement is zero; product Lisp adds 10 lines (60 total API lines). It has no
FMT/LL credit. It supplies buffer lifetime machinery needed by later callbacks;
Lisp callbacks and general Lisp finalizer functions remain unimplemented.

```lisp
(ccl::finalize-wasm-buffer buffer lifetime-object)
(ccl::drain-wasm-finalizers)
```

Registration associates one live allocation with a weak Lisp lifetime anchor.
The anchor must be an actual object in the owning collector's moving heap:
conses and admitted heap vectors/objects qualify; immediate values, image
constants, interior pointers and stack callables do not. Registration is once
per allocation, and refusal leaves that allocation releasable. Several
allocations may share an anchor. This is opt-in: existing integer tokens are
not themselves collectible, and dropping a token alone schedules nothing.
Keep the anchor reachable through the buffer's last use, including outstanding
ranges. Merely naming an otherwise unused lexical variable is not a lifetime
guarantee. This does not resurrect the anchor or pass it to the destructor.

`CollectorOwner.registerFinalizer` stores a weak identity and a trusted host
action. Host actions may retain capabilities but must not capture Lisp pointers;
the product buffer action captures only the library and allocation handle.
After each successful copying pass, including heap relocation, the owner queries
`weak_forward` in the collector's completed forwarding map before scratch reuse.
Live identities follow their new addresses. Dead identities enter a Worker-local
queue and leave the watch set. The query is read-only, after the weak-table fixed
point; it cannot keep an anchor or its cycle alive. Failed or inhibited copying
does not newly queue work. The collector's existing 96-byte configuration and
transactional commit remain unchanged. `weak_forward` is a trusted internal
query requiring the just-completed configuration, not a new untrusted pointer API.

Collection only queues. `drain-wasm-finalizers` is the explicit scheduling point
and runs one snapshot of the queue on the owning Worker in RUNNING state,
outside a safepoint, FOREIGN, collection or another drain. Each destructor uses
the ordinary FOREIGN bracket and may itself collect; newly queued work waits
for another drain. No JavaScript `FinalizationRegistry`, timer or other-Worker
execution participates. Automatic event-loop pumping is deferred. The return
value counts actions completed by that batch, including zero for an empty batch.

Explicit release cancels both watching and queued registrations. Close, foreign
trap and fatal instance retirement cancel every remaining registration of that
library. A dequeued action is consumed before running and never retried after
an exception. A recoverable destructor exception leaves later actions queued;
a destructor trap retires its library and cancels that library's remaining work.
Other libraries' pending actions survive and can be drained later. Errors use
the existing Lisp API transport. Drain is explicit, so it does not replace an
unrelated primary Lisp error during cleanup. O-170's conservative policy still
applies if the owner refuses a destructor entry: the allocation stays retired.

## Verification and admission

The extended API suite runs **106 cases in Node and Chromium/Firefox/WebKit**,
with **55 source mutants killed on directed cases**. It includes the original
63 API cases, six O-174 admission cases, and 37 finalizer cases. Scalar result
cases now assert both floating headers. The ten new ordinary post-READY Lisp
rows plus the original twenty match native CCL: **30 rows, 81 foreign entries,
60 moving collections**, with retired-space poisoning and full fixture TCR
checks. Native weak-key tables model anchor reachability; the native oracle
models the declared foreign library, as in the original API witness.

The collector regression passes 128 cases / 11 controls; the FOREIGN owner
passes 53 cases per engine / 38 controls, 59 owner dependency cases and its
12 native rows. Buffers pass 66 cases per engine / 28 controls and seven native
rows; scalars pass 126 cases per engine / 16 controls. These are changed-code
and direct-dependency checks. The compiler corpus stays deferred until the FFI
layer is complete. Shared compiler and upstream kernel sources are unchanged.

The new admission clauses have directed refusals or these equivalences:

- `integer(word)` is defensive once the lowtag equality, finite heap bounds and
  exact-object validation all succeed. The heap upper bound overlaps exact-object
  validation; the lower bound excludes otherwise valid image objects. Tests cover
  invalid numbers, both lowtags, interiors, immediates and heap limits.
- Drain's collector-busy guard is implied by its safepoint guard: copying can only
  start at an owner safepoint. Cancellation has its own directed critical-section
  refusal. Registration reuses the independently tested safepoint guard.
- The forwarding query's source bound and failed-lookup clauses both reject
  addresses outside the completed source inventory. The source bound is an early
  refusal of those same inputs. The lowtag and scan-kind clauses discriminate
  pointer kinds; successful live/dead queries, interior/wrong-kind inputs and a
  refused map are exercised without writes. The sentinel check in the owner is
  defensive for a violated internal protocol: registrations validate identities,
  and only successful collector maps can reach that call site.
- Finalizer registration reuses the library's tested idle/live-handle admission.
  The service reuses the tested vector arity and buffer-token checks. No additional
  admission authority is inferred from the host-action API.

O-174's size/offset fixnum, object tag, body span, buffer-as-library token, open
capacity and f32/f64 header gaps now have directed cases; all six clause groups
have killed controls. O-175 has a [persistent toolchain recipe](../browser-tools/README.md).
O-176's literal-double printing refusal remains a separate unresolved frontier.
Five retained development failures are fixture/build-control mistakes: frontier
reuse, a deliberately malformed header left in the heap, a duplicate native
fixture definition, refusal-state observation ordering and a stale mutation
anchor. None is silently discarded or reported as a product pass.

## Reproduction

Verify the two RAM mounts as required by `CLAUDE.md`. Use the shared compiler
cache and [pinned browser driver](../browser-tools/README.md). From the repo root:

```sh
work=/private/tmp/ccl-work/codex/foreign-finalizers
python3 -B tests/wasm/stage1/loader-target/build.py "$work/boot" --boot0
python3 -B tests/wasm/stage1/loader-target/build.py "$work/level1" --level1
cat runtime/wasm32/foreign-api.lisp > "$work/source.lisp"
printf '\n' >> "$work/source.lisp"
cat tests/wasm/stage2/foreign-api/checks.lisp >> "$work/source.lisp"
printf '\n' >> "$work/source.lisp"
cat tests/wasm/stage2/foreign-finalizers/checks.lisp >> "$work/source.lisp"
printf '\n' >> "$work/source.lisp"
cat tests/wasm/stage2/foreign-strings/checks.lisp >> "$work/source.lisp"
python3 -B tests/wasm/stage1/loader-target/build.py "$work/checks" \
  --postimage="$work/boot" --source="$work/source.lisp"
python3 -B tests/wasm/stage2/foreign-api/run.py \
  --boot "$work/boot" --level1 "$work/level1" --checks "$work/checks" \
  --output "$work/run" --playwright /absolute/path/to/playwright-core/index.mjs \
  --browser-config /absolute/path/to/browser-config.json
python3 -B tests/wasm/stage1/loader-target/collector.py "$work/collector-regression"
```

The API driver composes the original fixture with this unit's cases and controls;
there is one suite, not a duplicated integration harness. Run the owner, buffer
and scalar drivers as in their READMEs using the new collector and boot. Their
results, build identities and the five minimal failures are retained in
`ccl-evidence/2026-09-28-stage2-foreign-finalizers-r1`. Successful generated
WAT/Wasm and full compiler records are disposable. No compiler image or compiled
artifact archive is retained in the pack.

The current shared driver also composes the subsequent [UTF-8 string unit](../foreign-strings/README.md):
148 checks / 69 controls and 45 native-matched Lisp rows. Its review status
is separate; use the pinned historical commit to reproduce this unit alone.

## Review acceptance

User-supplied Claude audit 198 (`94b410d0`, imported as `0244319d`) finds no
defect and accepts the finalizer, string and callback-boundary stack at the
executed single-Worker scopes above. This supersedes the historical pending
review statements. No FMT/LL credit and no unchanged-test replay.
