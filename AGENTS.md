# Agent Operating Rules (WASM Startup Work)

These rules are mandatory for every session in this repository.

## No Redundant Re-Runs

Do not re-run expensive checks by default when all of the following are unchanged:
- `git rev-parse HEAD`
- `git status --short`

If unchanged, use existing recorded results and run only targeted checks for files touched in the current session.

## Re-Run Policy

Full repro or full smoke re-runs are allowed only when at least one is true:
- code changed in startup/kernel/runtime/wasm build paths
- build artifacts changed
- requested explicitly by the user
- prior evidence is missing or contradictory

## Logging Policy

- Prefer compact signature capture over large repeated logs.
- Keep telemetry code feature-flagged or commented until final ship cleanup.
