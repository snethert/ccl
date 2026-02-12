# Agent Operating Rules (WASM Startup Work)

These rules are mandatory for every session in this repository.

## Required Session Flow

1. First command in a new session:
   - `scripts/wasm/restore-session.sh`
2. Last command before yielding after diagnostics/build/test work:
   - `scripts/wasm/snapshot-session.sh`

Do not skip these two commands.

## No Redundant Re-Runs

Do not re-run expensive checks by default when all of the following are unchanged:
- `git rev-parse HEAD`
- `git status --short`
- key artifact hashes already captured in `doc/wasm/session-handoff.json`

If unchanged, use existing recorded results and run only targeted checks for files touched in the current session.

## Re-Run Policy

Full repro or full smoke re-runs are allowed only when at least one is true:
- code changed in startup/kernel/runtime/wasm build paths
- build artifacts changed
- requested explicitly by the user
- prior evidence is missing or contradictory

## Logging Policy

- Prefer compact signature capture over large repeated logs.
- Preserve blocker signature lines in `doc/wasm/session-handoff.json`.
- Keep telemetry code feature-flagged or commented until final ship cleanup.
