# Logical debugger-frame proof

This isolated fixture executes S0-LL23-b on the macOS reference host. Codex authored it. Execution and same-author verification do not constitute independent review or acceptance. It extends the reviewed integrated fixture by linking a separate `frames.c` object; the existing collector, suspension protocol, C boundary and Worker actor remain unchanged.

From the repository root, with the pinned Homebrew LLVM/LLD 21.1.8, WABT and Node tools installed:

```sh
node tests/wasm/stage0/debug-frames/run.mjs --output /tmp/ccl-debug-frames-fresh
```

The output must be empty and outside the checkout. The runner first executes the integrated fixture, including its boundary prerequisites and 1,000 seeded schedules. It then builds and runs eleven frame cases and eleven deliberate rejection controls. A failed case retains its first failure and terminates every Worker. Each artifact, source snapshot, compiler executable, inventory and build identifier is hashed. The result envelope contains the five prerequisite IDs and S0-LL23-b; every new result is `NOT_REVIEWED`.

## What executes

Emitted WAT publishes nested outer/inner frames and an interrupt-entered debugger frame. Actual blocking C requests suspend them while another admitted Worker moves their cons objects and poisons the old space. Inspection executes on the owning, admitted Worker; its C reader follows the published logical frames and reloads their GC roots. A separate host oracle checks raw header bytes only at controlled stops. Host debugger replies contain serialized value summaries in owned, nonmoving storage, with an atomic final length publication and full build ID. Reply storage is never reused within a case, and earlier replies must remain byte-identical after collection and frame reuse.

Cases cover all eight frame slots across moving GC, zero and six complete values, unequal arguments, shadowed `x` bindings, a shared heap cell retained by the permanent root after frame exit, debug policies 3 and 1, nested suspension, ordinary and nested nonlocal exits, collection during the exceptional idle handoff, live and stale frame handles, owner lifetime, and versioned metadata. Every return restores roots, frame cursor/head, VSP/TSP/CSP, binding/handler checkpoints, result ownership and active request, then parks. Exceptional paths cancel abandoned live requests and wait for host acknowledgement before subsequent collection.

The shared cell is a fixture graph handed to the owning Worker while all Workers are parked. A permanent Worker root also retains it, so survival after frame exit demonstrates shared-cell relocation and inspection, not capture or escape semantics. The versioned exports are hand-built old/new code entries, with the old entry called again after the new one. These establish frame representation and metadata pairing; they do not implement a Lisp closure compiler, symbol redefinition or a production debugger. Inspection is of the owning Worker's frames, not an arbitrary live target. Full tail-frame elimination, condition/restart semantics, saved images, generated Lisp frames and D3 candidate performance remain later obligations.

## Layout and metadata

`schema.json` specifies the [64-byte header contract](../../../../doc/WASM/contracts/debug-frames.md), explicit lexical identities, source scopes, slot widths, live sites and availability reasons. `program.mjs` emits the header independently of the C structure reader and its static assertions. The host byte oracle uses literal contract offsets. The generated `source-sites.json` binds site IDs to exact lines and operations in the hashed `program.wat` for the outer/inner/debugger semantic corpus and the separate capacity driver. The capacity driver uses dedicated source sites in the outer descriptor to stress the maximum frame/reply bounds. The packet build ID binds the generator, schema, C reader, prerequisite objects and toolchain.

Each 160-byte frame has six tagged root words at offsets 72–92, an intentionally pointer-shaped unboxed word at 96, an unavailable poison word at 100, and restoration checkpoints at 104–136. Root and debugger maps have separate roles: a value unavailable to the debugger can remain a mandatory GC root. Lower-policy unavailability is explicit metadata in this materialized fixture, not a claim of optimized storage or measured savings. Each Worker owns eight frame records and 24 one-use 4,096-byte reply slots, in bounded regions after the link-derived runtime allocation. Generation exhaustion and frame overflow trap; storage is not silently recycled. Handles are meaningful only within the same memory instance, build and TCR owner, with matching thread lifetime, frame address and generation.

The C reader validates each frame's metadata and membership in the actual published root chain. During EH restoration only, vanished C root records are discarded without traversing them; no poll, allocation or inspection occurs until every surviving checkpoint is restored. The collector's existing bounded root scan remains in force.

## Rejection controls

The ordinary semantic oracle rejects a stale relocated slot, reuse of a frame generation, rejection of a valid live handle, wrong code version, wrong source site, fabricated unavailable value, collapsed lexical identity, omitted frame restoration and omitted root publication. Generation exhaustion and explicit-stack overflow must trap with their specific recorded failure codes. A timeout or unrelated assertion does not count as the expected rejection.

The fixture does not select D3, qualify the full engine feature matrix or close Stage 0. See [current status](../../../../doc/WASM/STATUS.md) and the [evidence index](../../../../doc/WASM/evidence/index.json) for retained runs and review dispositions.

Results use version 2 [per-test contract binding](../../../../doc/WASM/contracts/evidence-binding.md). Unrelated inventory additions preserve existing results; changed contracts, prerequisites or inventory versions fail compatibility. Claude reviewed the r3 frame mechanism with no defect found; subsequent evidence-wrapper changes require their own review and do not confer acceptance.
