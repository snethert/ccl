# Initializer binding

S0-LL15-a executes a hand-built bootstrap closure: three phases, four wasm32
modules and nine required initializers. The loader validates the closure
manifest against the supplied modules before instantiating anything, seeds
its own dependencies (the phase-0 loader module that owns the event log,
the completion ledger and the code-installation service) before any bundle
exists, binds every initializer to its prerequisites' physical completion
words and required service state, checks each completion physically after
the initializer returns, and publishes ready only after every required
initializer completed. An omitted required module, a missing initializer
export, an import mismatch, a deferred required module, an unknown
prerequisite, a cycle, a forward phase dependency, an unseeded loader
dependency, a bundle in the loader phase, a wrong or unwritten completion,
a raised initializer, a clobbered prerequisite and wrong service state are
all refused before dependents run. Eight loader mutants, including a no-load
path that fakes every completion, are rejected by the unchanged oracle,
which reconstructs each case's whole memory image.

```sh
python3 tests/wasm/stage0/initializer-binding/run.py --output /private/tmp/ccl-initializer-binding-fresh
python3 tests/wasm/stage0/initializer-binding/run.py --verify /private/tmp/ccl-initializer-binding-fresh
```

Requires macOS with Node, WABT `wat2wasm` and `wasm-objdump` on PATH. Use a
fresh output directory outside the checkout. `closure.json` is the manifest,
`abi.json` the loader/module interface, `loader.mjs` the loader, `oracle.py`
the independent expectations. This is not the qualified census closure
(S0-LL15-b/c), the production loader, the image format or generated code;
the accepted S0-LL01-a control covers failing initializers and diagnostic
continuation.

See [scope and results](../../../../doc/WASM/stage0/initializer-binding.md).
