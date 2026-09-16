# Native registry and startup analysis

These are observation and analysis helpers, not a Wasm backend. Run native work
only in disposable pristine U1 copies under the reversible-observation rules.
For new questions use the [on-demand query entry point](../query/README.md).

| Work | Retained basis and status |
| --- | --- |
| Correlated build, binding and registry observation (`build.py`, `build-observer.lisp`, `scan.py`) | `CORRELATED-QUERY-BASE-R1`, reviewed by Claude's fifty-sixth audit; native R6 and recovery at its declared scope |
| Final 167-unit source compile and startup graph (`seed_compile.py`, `seed_bodies.py`, `seed_bindings.py`, `seed_transitive_graph.py`) | `ON-DEMAND-CENSUS-R1`, executed and retained with source pins; independent review pending |
| Earlier body, loader, registry, LAP and initializer analyses | `CENSUS-REGISTRY-HISTORY-R1`, historical artifacts with incomplete executed-source provenance; not qualified completion evidence |

The original large source commit `6be15c29` is recorded as DEFECT_FOUND. Merely
committing its helper files did not publish reproducible deliverables. The
earlier “4,373 bodies finished” statement is withdrawn as a qualified claim.
The archive preserves terminal outputs and original failures; it does not
invent missing run records or label the later committed code as executed source.

The older 84-unit compile, 109-function match and 351-gap startup projection are
retained for history. Current startup work uses the separately retained 167-unit
capture: 4,369 reached functions and 272 explicit body gaps. Those are execution
results awaiting review, not a complete census or a bound on all runtime callees.

The [finite-callee replay](../finite-callees/README.md) regenerates its single
required CONSTANTLY body correspondence directly from retained streams. It no
longer borrows the unpublished broad body analysis as a premise.

Do not restart the broad body or computed-call drain to qualify Stage 0. The
approved policy is to retain explicit unknowns and answer concrete implementation
questions on demand. Old helpers can inform a bounded experiment, but any new
claim needs its actual inputs, executed sources and results retained together.
See the [provenance correction](../../../../doc/WASM/stage0/registry-history.md).
