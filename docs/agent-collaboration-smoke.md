# Agent Collaboration Smoke

Use this checklist when validating that V3.1 subagent collaboration works in the current Codex runtime. It is a runtime smoke, not a package verifier. Keep it manual/HITL until the multi-agent tool surface exposes a stable scriptable API.

## Scope

This smoke proves:

- the main agent can decide whether delegation is suitable;
- one or more subagents can be spawned with bounded Handoff Envelopes;
- subagents can return Return Envelopes with reviewable evidence;
- the main agent can review results, integrate or discard them, and close agents;
- the final answer can include a lifecycle ledger.

This smoke does not prove production safety, UI visibility, external writes, or automatic runtime enforcement of prompt contracts.

## Required Cases

### Case A: Read-Only Dual Explorer

Use when there are two independent read-only questions.

Handoff requirements:

- `source`
- `target role/card`
- `dispatch reason`
- `task`
- `scope`
- `allowed write set: none`
- `off-limits`
- `included context`
- `excluded context`
- `allowed commands/tools: local read-only only`
- `validation command`
- `lifecycle close condition`

Expected Return Envelope:

- `status`
- `summary`
- `files read`
- `files changed`
- `commands run`
- `evidence paths`
- `validation result`
- `risks`
- `main-agent decision needed`
- `close recommendation`

Pass criteria:

- two disjoint subagent tasks were dispatched;
- both returned Return Envelopes;
- main agent reviewed both results against source files or command output;
- both agents were closed when no longer needed;
- lifecycle ledger records `agent id`, `role/card`, `read/write`, `target`, `status`, `close_agent previous_status`, `evidence`, and `integrated/discarded`.

### Case B: No-Dispatch Strong Coupling

Use when the task touches the same file, same state, or same immediate blocking decision.

Pass criteria:

- main agent records `No-Dispatch Decision`;
- reason is one of: `strong coupling`, `shared writes`, `blocked dependency`, `safety boundary`, `unclear task`, `no independent subtask`, or `tool permission constraint`;
- main agent proceeds locally or asks the user only if a red line is reached.

### Case C: Local-Write Boundary

Use only with a temporary or clearly bounded write target.

Pass criteria:

- Handoff Envelope names the exact allowed write set;
- off-limits section excludes shared config, production data, credentials, release files, and unrelated docs;
- worker returns a file list and validation result;
- main agent performs diff/readback review before integration;
- worker is closed after review.

### Case D: Visibility Policy

Use when user inspectability of the subagent response matters.

Pass criteria:

- if the user needs to inspect the response, leave the subagent open until inspection is complete;
- otherwise close immediately after review and integration;
- final lifecycle check confirms no unneeded subagent remains open.

### Case E: Skill Coupling

Use when a skill such as `debug-loop`, `completion-review`, `security-review`, or `release-readiness` is active in the same task.

Pass criteria:

- skill output does not replace Return Envelope review;
- skill-specific verification is run by the main agent where applicable;
- subagent lifecycle is still closed explicitly.

## Lifecycle Ledger Template

```text
agent_id:
role/card:
read/write:
target:
status:
close_agent previous_status:
evidence:
decision: integrated|discarded
notes:
```

## Final Report Shape

```text
Subagent lifecycle:
- <agent id> / <role>: <integrated|discarded>, close previous_status=<status>, evidence=<paths or command>

No-dispatch decisions:
- <reason>: <why local execution was safer or more direct>

Gaps:
- <anything not proven by this smoke>
```

## Do Not

- Do not spawn agents for strongly coupled shared writes.
- Do not pass full conversation history, secrets, raw logs, or unrelated external output.
- Do not treat subagent success as final completion without main-agent review.
- Do not leave completed agents open unless the user needs to inspect them.
- Do not add a new orchestrator, planner, dispatcher, queue, daemon, or background runtime for this smoke.
