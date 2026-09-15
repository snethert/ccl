# Registry/body provenance correction — 15 September 2026

Claude's fifty-sixth audit correctly rejected `6be15c29` as a reviewable delivery.
Its commit message cited temporary outputs without retained source provenance
for the complete chain. This correction preserves that history and separates
what is currently supported from what was merely reported during development.

`CENSUS-REGISTRY-HISTORY-R1` retains the earlier body/registry analysis outputs,
available executed-source snapshots, native LAP and initializer probes, original
failures, and the 84-unit startup capture and terminal graph. Some stages never
captured their executed sources. That gap is explicit; no run record or source
version has been reconstructed and presented as original evidence.

The “4,373 read-only bodies finished” claim is withdrawn as a qualified delivery.
The archived terminal file reports zero remaining read-only bodies, but that
number alone does not establish reproducibility from the committed code. No
accepted record depended on it. Future use requires a bounded, source-bound
reproduction for the particular dependency being investigated.

The correlated base is already retained and externally reviewed at its declared
native scope. The final 167-unit compile and startup worklist are separately
retained in ON-DEMAND-CENSUS-R1: source unchanged, native output identical,
4,369 functions reached and 272 body gaps. That later execution remains pending
independent review. Its complete source/command artifacts supersede the earlier
84-unit run for current startup work; they do not retroactively qualify it.

The finite-expression result now has its own [fresh replay](finite-callees.md),
with 124 proofs and 1,438 unknown expressions. It regenerates only its needed
constructor body witness and does not rely on the broad body-completion claim.
The three source groups now have separate documentation and retained records.
The original commit and its DEFECT_FOUND audit remain in history.

This is a provenance correction, not a new observation or an accepted census
result. Gate counts remain forty accepted, eight missing and zero unreviewed.
LL15-b/c qualification publication is still unfinished. The approved on-demand
direction remains in force; no exhaustive resolver or body-closing campaign is
scheduled by this correction.
