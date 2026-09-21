# Joined startup resets and configuration

One scheduler now executes all eighteen selected callbacks over the same
21 global cells. The generated CPU reset and spin callback use the same cell;
no host store repairs its state between calls. Both initially warm CPU caches
are cleared before the native cache acquisition/write runs. Configuration and
literal reset effects remain visible through the final generated readback.

The compiler is unchanged. The thirteen reset functions are recompiled with
completion tokens 201–213 because their original 101–113 overlap the
configuration tokens. This preserves the scheduler's unique-token admission.
Their native registered callbacks run again. The seven R2 configuration modules
and native configuration answers are reused by digest, including the fixed
CPU-cache body; the original R1 body is never used. The joined oracle composes
retained native post-states in the declared order, with independently tracked
dirty globals. It does not claim a native whole-bootstrap replay.

The run covers 36 owner configurations, two initially dirty states, Node and
pinned Chromium Workers at 4 MiB and 2 GiB. Both full-TCR restoration and the
R2 foreign-region checks apply after every generated invocation. Completion,
all global effects, and installed binary digests are checked. Missing binaries,
a matching omission from the selected plan, skipped or forged CPU reset,
a separate cache cell, a late reset, and missing completion refuse.
The selected-membership check is an independent fixture oracle; the generic
scheduler trusts the owner's selection and does not know the census.

```
python3 tests/wasm/stage1/startup-joined/run.py --evidence ../ccl-evidence --output /new/joined
python3 tests/wasm/stage1/startup-joined/packet.py verify --evidence ../ccl-evidence --packet ../ccl-evidence/2026-09-20-stage1-startup-joined-r1 --output /new/replay
```

This is an auxiliary composition proposal, with no LL15 credit or shared source
change. The 35-entry snapshot is not complete bootstrap membership. Seventeen
callbacks, definition effects, ordinary condition activation and production
symbol materialization remain open. Browser coverage keeps R2's engine limits.
