# Generated B calls through lazy installation

This auxiliary LL05 unit supplies a single-Worker loader for the unchanged,
reviewed tail-call compiler output. It admits a trusted catalog binding code ID,
version, table slot, profile, module digest, imports and both export roles.
The role proof is that those specific bytes and exports belong to that catalog
entry. It is not code signing or a sandbox for an untrusted catalog owner.

A matching public B stub and internal three-argument tail stub occupy each pair
of table slots. Both call the synchronous installer, then use Wasm
`return_call_indirect` with the original SELF, count and (for tail entry)
continuation. Required, optional, keyword, rest and closure entries all use the
same B signature; the generated callee still checks its Lisp arity. There is no
specialized exact-arity native calling convention hidden in these stubs.

Before instantiation, the loader checks the actual bytes and export signatures,
requires the shared wasm32 profile and exact imports, and refuses start, data,
element, defined memory/table/global and unknown sections. Imported functions
are forbidden. The parser deliberately accepts only this compiler's surface;
the engine validates instruction bodies. Missing or changed bytes fail before
publication. The installer checks the shared registry against the private
catalog and both table slots against their recorded function identities.
Both exports are prepared before the pair is replaced, with no callback or
suspension between the two stores. This is atomic with respect to execution in
one Worker; it is not concurrent publication across Workers.

An install error leaves both stubs available for retry. Reentrancy is refused.
A held stub can be called after installation; it checks the ready pair before
forwarding. Registry/table identity failures preserve designator error code 4;
other installation failures use call-error code 7. These are checked Wasm
exceptions, **not yet the production Lisp condition machinery**. The generated
continuation unwinds normally if loading fails inside a call.

The owner supplies the read-only byte provider and the trusted stub/observer
modules. Import dictionaries are copied without invoking getters; identity
globals are immediate values. The loader never writes Lisp memory. It performs
no collection, Lisp callback or asynchronous fetch during installation. Observer
wrappers are only used in the instrumented tests; host calls bypass those
wrappers as they did in the reviewed eager harness. The reset method is an
owner/test unload operation legal only when no Lisp invocation is active.

`prepare.py` changes only installation in the prior tail-call harness. Its
native/model cases, root checks, heap accounting, resource checks and long
chains remain unchanged, and the result excluding loader events must equal
the accepted run exactly. Each case starts cold. This includes escaping
closures, temporary literal APPLY, long argument/results, optional/keyword
calls, self/mutual/local recursion and 100,000-step chains in 2 KiB.
`controls.mjs` also checks both tables and every memory byte on installation
refusal, retry after a generated caller unwinds, same-signature wrong-code
substitution, actual table corruption and immutable admitted descriptors.
Compiler/native bytes are unchanged, so the prior reviewed R6/R6a evidence is
reused instead of running another native build.

Run and replay from the repository root:

```sh
python3 tests/wasm/stage1/b-lazy-calls/run.py --evidence ../ccl-evidence --output /tmp/b-lazy-run
python3 tests/wasm/stage1/b-lazy-calls/verify.py --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-16-stage1-b-lazy-calls-r1
```

Full LL05 remains open: Lisp conditions, dynamic cleanup/binding extent,
collection, profile materialization and production image installation are not
claimed here. This unit changes no shared compiler source and claims no slot.
