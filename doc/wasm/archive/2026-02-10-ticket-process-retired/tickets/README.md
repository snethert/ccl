# Runtime Replacement Ticket Subplans

This folder contains per-ticket implementation subplans referenced by:

- `doc/wasm/runtime-replacement-master-plan.md`

## Naming Convention

- `RPL-00-... .md`
- `RPL-01-... .md`
- `RPL-02-... .md`

Use `TICKET-SUBPLAN-TEMPLATE.md` as the starting point for each ticket document.

## Sync Rule

Whenever a ticket subplan is updated, update the corresponding ticket block in:

- `doc/wasm/runtime-replacement-master-plan.md`

using the active sync mode from
`doc/wasm/rpl-unattended-execution-playbook.md`:

1. Standard mode:
   - Update subplan + runtime master in the same change (status, notes,
     last-updated, immediate next step).
2. Single-document override mode:
   - Update exactly one target document in-cycle.
   - Record deferred sync items for each skipped required target in
     `Pending End-Merge Queue` per the playbook contract.

A ticket update is out of sync when required updates are neither applied
in-cycle nor represented by explicit deferred queue items.

## Minimum Completeness Checklist (Unattended Execution)

Every runtime ticket subplan should be executable in fresh context without extra
coordination. At minimum, include:

1. A single concrete `Immediate Next Step` action.
2. A single cycle goal sentence (`<ticket/doc>: <single action> -> <success evidence>`).
3. Deterministic validation commands/IDs for that action.
4. Explicit evidence output path(s) and expected terminal summary artifact.
5. Blocker handling and gap-ID policy.
6. Reopen criteria if the ticket is currently `done`.
7. Deferred-sync queue item details when single-document override mode is used.

The canonical unattended protocol is:

- `doc/wasm/rpl-unattended-execution-playbook.md`
