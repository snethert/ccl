# Startup Symbol Next-Session Prompt Template

Use this as the single copy-paste source for resume prompts.

Fill placeholders before sending:
- `<STEP_ANCHOR>`
- `<NEXT_STEP_ID>`
- `<OBJECTIVE>`
- `<HOT_FILES_BULLETS>`
- `<PRIMARY_LOG>`
- `<CANDIDATE_LOGS_BULLETS>`
- `<COMMAND_BATCHES>`
- `<DONE_WHEN_BULLETS>`

```text
Resume WASM startup-symbol investigation from current local state.

Working directory:
- /Users/buildsomething/Source
Repo root:
- /Users/buildsomething/Source/ccl
Shell:
- zsh

FAST_RESUME_MARKER:
- step_anchor: <STEP_ANCHOR>
- next_step_id: <NEXT_STEP_ID>
- objective: <OBJECTIVE>
- hot_files:
  <HOT_FILES_BULLETS>
- primary_log: <PRIMARY_LOG>
- candidate_logs:
  <CANDIDATE_LOGS_BULLETS>

BATCHED_WORK_RULE_FOR_FOLLOWUP_PROMPT (explicit):
- Continue executing sequential steps in the same prompt until blocked by a concrete dependency blocker or an explicit user decision.
- If at least one executable next step exists, execute it immediately.
- Objective completion alone is not a stop reason.
- Do not stop after minimum required work while executable steps remain.
- Single-step followup is allowed only when genuinely blocked by a concrete dependency or explicit user decision.

NON_STOP_EXECUTION_GUARD:
- Forbidden stop reasons:
  - objective_complete
  - minimum_required_work_complete
  - prepared_next_prompt_while_steps_remain
  - need_followup_without_blocker_evidence
- Allowed stop reasons:
  - blocked_dependency
  - user_decision

TERMINATION_CHECKLIST (must be printed before stopping):
- termination_reason=blocked_dependency|user_decision
- next_executable_step_exists=yes|no
- if_yes_why_not_executed=concrete blocker only
- attempted_mitigations=list
- next_step_id=updated value
- next_session_prompt_emitted=yes (required)
- if_no_why=concrete blocker only

BLOCKED_REPORT_FORMAT (required if blocked):
- blocker_type:
- failing_command:
- exact_error_output:
- dependency_needed:
- mitigation_attempt_1:
- mitigation_attempt_2:
- why_no_further_local_step_is_executable:

OUTPUT_REQUIREMENT:
- Final assistant response must include NEXT_SESSION_PROMPT inline (copy-paste block), not only a file path.

command_batch_1 (Step <NEXT_STEP_ID>):
<COMMAND_BATCHES>

done_when:
<DONE_WHEN_BULLETS>
```
