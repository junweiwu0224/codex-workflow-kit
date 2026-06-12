# Workflow Kit V2 Adoption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the delivered Codex Workflow Kit V1 into a measured, repeatable V2 adoption system across real repositories.

**Architecture:** Keep V1 stable as the portable baseline, then collect evidence from real repo usage before promoting hooks, MCP/code graph, memory, or subagent automation. Every promotion must have a rollback path, documented trigger conditions, and verification evidence.

**Tech Stack:** Codex global/repo `AGENTS.md`, Superpowers, personal skills, shell scripts, Python verifier scripts, Markdown docs, release tarball checksums.

---

## File Structure

- Modify: `outputs/codex-workflow-kit/WORKFLOW-REVIEW.md`
  - Add V2 adoption status and link to this plan after the first adoption cycle completes.
- Modify: `outputs/codex-workflow-kit/QUICKSTART.md`
  - Keep the V1 quickstart short; add only one link to the V2 plan if needed.
- Modify: `outputs/codex-workflow-kit/repo-template/docs/codex-usage.md`
  - Add concrete fields only if real trials show the current table misses important signal.
- Modify: `outputs/codex-workflow-kit/repo-template/docs/quality-gates.md`
  - Promote verified hook candidates only after repeated evidence.
- Modify: `outputs/codex-workflow-kit/repo-template/docs/subagents.md`
  - Promote subagent patterns only after real parallel task wins.
- Create or modify in each target repo: `<repo>/docs/codex-usage.md`
  - Record 3-5 representative M/L/XL tasks before changing defaults.
- Create or modify in each target repo: `<repo>/docs/decisions/*.md`
  - Capture durable choices such as enabling a hook or MCP server.
- Create or modify in each target repo: `<repo>/AGENTS.md`
  - Add only repo-specific facts and proven rules.

Do not change global `AGENTS.md` during this plan unless at least two real repos show the same stable improvement.

---

### Task 1: Freeze V1 Baseline Before Adoption

**Files:**
- Read: `outputs/codex-workflow-kit/QUICKSTART.md`
- Read: `outputs/codex-workflow-kit/WORKFLOW-REVIEW.md`
- Read: `outputs/codex-workflow-kit/MANIFEST.sha256`
- Verify: `outputs/codex-workflow-kit/releases/codex-workflow-kit-2026.06.07.tar.gz`

- [ ] **Step 1: Verify toolkit package integrity**

Run:

```bash
cd <toolkit-root>
python3 scripts/verify_toolkit.py
```

Expected:

```text
Workflow toolkit OK
```

- [ ] **Step 2: Verify release checksum**

Run:

```bash
cd <toolkit-root>/releases
env LC_ALL=C LANG=C LC_CTYPE=C shasum -a 256 -c codex-workflow-kit-2026.06.07.tar.gz.sha256
```

Expected:

```text
codex-workflow-kit-2026.06.07.tar.gz: OK
```

- [ ] **Step 3: Confirm V1 remains the baseline**

Check:

```bash
rg "implementation-plan|QUICKSTART.md|Workflow toolkit OK|Context pack OK" <toolkit-root>
```

Expected:

```text
implementation-plan
```

only appears in documentation that says it must remain removed. `QUICKSTART.md` exists and the verifier passes.

- [ ] **Step 4: Do not promote any candidate yet**

Leave these as documented candidates:

```text
hooks
MCP/code graph/memory
subagents automation
browser/frontend QA defaults
new global rules
```

Exit criterion: V1 artifact is verified and treated as immutable baseline for the adoption cycle.

---

### Task 2: Select 3-5 Representative Trial Repositories

**Files:**
- Modify in each repo: `<repo>/docs/codex-usage.md`
- Modify in each repo: `<repo>/AGENTS.md` only if repo-specific facts are discovered

- [ ] **Step 1: Choose trial repo mix**

Pick 3-5 repos with different task shapes:

```text
Repo A: existing app with frontend or dashboard
Repo B: backend/service or data-heavy repo
Repo C: documentation/tooling-heavy repo
Repo D: optional library/CLI repo
Repo E: optional high-risk or legacy repo
```

Selection criteria:

```text
Has active tasks
Can run local verification
Does not require production credentials for basic tests
Has enough complexity to exercise M/L workflow
```

- [ ] **Step 2: Install context pack into each trial repo**

Run for each repo:

```bash
cd <toolkit-root>
./install.sh --repo /path/to/repo --dry-run
./install.sh --repo /path/to/repo --backup
```

Expected:

```text
Install plan complete.
```

If dry-run reports conflicts, manually merge instead of forcing overwrite.

- [ ] **Step 3: Verify context pack in each repo**

Run:

```bash
cd /path/to/repo
python3 scripts/verify_context_pack.py
```

If the repo uses a virtual environment, run:

```bash
.venv/bin/python scripts/verify_context_pack.py
```

Expected:

```text
Context pack OK
```

- [ ] **Step 4: Record baseline state**

Append one row to `<repo>/docs/codex-usage.md`:

```markdown
| YYYY-MM-DD | Baseline context pack install | M | repo-onboarding, context pack verifier | `python3 scripts/verify_context_pack.py` -> Context pack OK | Repo has portable commands/testing/quality docs; no hooks enabled yet | Collect 3-5 real task records before promotion |
```

Exit criterion: each selected repo has a verified context pack and one baseline usage row.

---

### Task 3: Run Real M/L/XL Tasks Without Changing Defaults

**Files:**
- Modify in each repo: actual task files
- Modify in each repo: `<repo>/docs/codex-usage.md`
- Optional modify in each repo: `<repo>/docs/decisions/*.md`

- [ ] **Step 1: For each repo, choose at least one real task**

Task mix:

```text
M: multi-file bugfix or small user-visible behavior change
L: cross-module behavior, build/test config, or architecture-sensitive change
XL: formal product/engineering spec only if the repo naturally has one
```

- [ ] **Step 2: Use workflow routing**

Apply this routing exactly:

```text
XS/S: direct implementation and targeted verification
M: Superpowers for lightweight planning/TDD/verification
L: investigation first, then Superpowers plan
XL: spec-kit-xl first, then Superpowers plan and execution
```

- [ ] **Step 3: Record every representative task**

Append a row to `<repo>/docs/codex-usage.md`:

```markdown
| YYYY-MM-DD | <task and scope> | M/L/XL | <Superpowers/spec-kit/debug-loop/frontend-qa/etc.> | `<exact command>` -> `<result>` | <positive or negative reusable signal> | <keep, revise, or observe> |
```

Good effect signals:

```text
Found missing test before implementation
Prevented overuse of spec-kit on small task
Caught frontend regression with browser QA
Reduced repeated context questions
Identified command with hidden side effects
```

Bad effect signals:

```text
Flow too heavy for task size
Verifier missed important repo-specific command
Hook candidate wrote cache/report files
Subagent integration cost exceeded benefit
MCP setup cost exceeded search benefit
```

- [ ] **Step 4: Keep candidates manual**

Do not enable hooks, MCP, memory, or default subagent automation during these first tasks. Use them only when the task explicitly justifies the experiment.

Exit criterion: at least 3-5 real task rows exist across trial repos, with exact validation commands and effect signals.

---

### Task 4: First Adoption Review

**Files:**
- Modify in each repo: `<repo>/docs/codex-usage.md`
- Optional modify: `<repo>/AGENTS.md`
- Optional modify: `<repo>/docs/testing.md`
- Optional modify: `<repo>/docs/quality-gates.md`
- Optional modify: `<repo>/docs/codex-playbook.md`

- [ ] **Step 1: Count representative records**

Run in each repo:

```bash
cd /path/to/repo
rg "^\\| 20[0-9]{2}-[0-9]{2}-[0-9]{2} \\|" docs/codex-usage.md
```

Expected:

```text
At least one baseline row and enough task rows to support a review.
```

- [ ] **Step 2: Write the phase review**

Append to `<repo>/docs/codex-usage.md`:

```markdown
## 阶段复盘：首次真实采用后

结论基于 YYYY-MM-DD 到 YYYY-MM-DD 的真实任务记录。当前优先减少误判、漏测和不必要流程。

保留并继续使用：

- <rule or workflow that repeatedly helped>

保持文档化、暂不自动启用：

- <candidate that helped once but lacks enough evidence>

暂不推进：

- <candidate that added cost or risk>

下一轮观察：

- <specific signal to collect next>
```

- [ ] **Step 3: Promote only narrow repo-specific improvements**

Allowed promotions:

```text
Add exact test command to docs/testing.md
Add exact targeted gate to docs/quality-gates.md
Add repo-specific boundary to AGENTS.md
Add one durable workaround to docs/codex-playbook.md
Create ADR for enabling a hook/MCP/subagent pattern
```

Disallowed promotions:

```text
Changing global AGENTS.md after one repo
Enabling blocking hooks without repeated stable evidence
Adding memory for one-off observations
Making spec-kit default for normal M tasks
Making subagents default for shared-state implementation
```

Exit criterion: each trial repo has a short phase review and only narrow, evidence-backed adjustments.

---

### Task 5: Evaluate Hooks Candidates

**Files:**
- Modify: `<repo>/docs/quality-gates.md`
- Optional create: `<repo>/docs/decisions/YYYY-MM-DD-enable-local-hooks.md`
- Optional create: `<repo>/.pre-commit-config.yaml` or project-native hook config only after approval

- [ ] **Step 1: List candidate commands**

In `<repo>/docs/quality-gates.md`, fill:

```markdown
### Hooks 候选集

| 候选命令 | 等级 | 是否可默认阻断 | 原因 / 条件 |
|---|---|---|---|
| `python3 scripts/verify_context_pack.py` | A | 是 | 文档结构和敏感模式检查；无业务数据写入 |
| `<targeted test command>` | A | 条件允许 | 连续真实任务中稳定、短耗时、无外部依赖 |
| `<lint/typecheck command>` | A/B | 待确认 | 需确认是否写 cache/report |
```

- [ ] **Step 2: Check side effects**

Before promoting a command, run:

```bash
cd /path/to/repo
git status --short
<candidate command>
git status --short
```

Expected:

```text
No unexpected modified, deleted, or untracked generated files.
```

- [ ] **Step 3: Measure runtime**

Run:

```bash
time <candidate command>
```

Promotion rule:

```text
Default hook candidate should normally finish in under 10 seconds.
Commands over 10 seconds stay manual unless the repo explicitly accepts the cost.
```

- [ ] **Step 4: Write an ADR before enabling blocking hooks**

Create `<repo>/docs/decisions/YYYY-MM-DD-enable-local-hooks.md`:

```markdown
# Enable Local Quality Hooks

## Status

Proposed

## Context

The repo has repeated evidence that the following commands are stable, fast, and low side effect:

- `<command>`: `<evidence>`

## Decision

Enable only the listed commands as local hooks. Do not include external services, app lifecycle checks, database writes, coverage, screenshots, traces, deployment, or migrations.

## Consequences

- Expected benefit:
- Known cost:
- Rollback:
```

Exit criterion: hook candidates are documented with side effects and runtime; no blocking hook is enabled without ADR and user approval.

---

### Task 6: Evaluate MCP, Code Graph, and Memory

**Files:**
- Modify: `<repo>/docs/codex-playbook.md`
- Optional modify: `<repo>/docs/decisions/*.md`
- Do not modify: global MCP/memory defaults until repeated cross-repo evidence exists

- [ ] **Step 1: Identify repeated context failures**

Look for usage records that mention:

```text
Repeatedly missed call graph or ownership
Repeatedly searched same architecture facts
Repeatedly forgot user/repo preference
Repeatedly needed API docs unavailable from repo
```

- [ ] **Step 2: Match the lightest tool**

Use this decision table:

```text
Missing repo facts -> update AGENTS.md or docs
Missing commands/testing paths -> update docs/commands.md or docs/testing.md
Missing architecture relationships -> update docs/architecture.md or add code graph candidate
Repeated personal preference across repos -> consider global AGENTS.md or memory
External tool/API behavior changes -> use official docs or MCP if available
```

- [ ] **Step 3: Run one explicit MCP/code graph experiment**

Record in `<repo>/docs/codex-usage.md`:

```markdown
| YYYY-MM-DD | MCP/code graph experiment | L | MCP/code graph candidate | `<verification command>` -> `<result>` | <what became faster or safer> | Keep candidate / reject / promote to ADR |
```

- [ ] **Step 4: Reject noisy memory candidates**

Do not store:

```text
One-off task facts
Sensitive info
Repo facts that belong in repo docs
Speculative preferences
Temporary debugging observations
```

Exit criterion: MCP/code graph/memory remains manual unless repeated evidence shows clear benefit that docs cannot solve better.

---

### Task 7: Evaluate Subagents Parallelism

**Files:**
- Modify: `<repo>/docs/subagents.md`
- Modify: `<repo>/docs/codex-usage.md`
- Optional modify: `<repo>/docs/decisions/*.md`

- [ ] **Step 1: Pick only independent work**

First run a subagent suitability check for L/XL tasks, existing implementation plans, cross-module tasks, multiple independent failure sources, multi-file reviews, or investigations that look parallelizable. If there are 2+ independent, non-overlapping subtasks with no shared write state, proactively dispatch subagents. If not using subagents, record why: tightly coupled work, blocked sequencing, file ownership conflict, shared-state risk, or high-risk external operation.

Acceptable subagent tasks:

```text
Read-only code review across separate modules
Independent test coverage analysis
Separate docs audit
Independent UI route inspection
Parallel investigation with no writes
```

Avoid subagents for:

```text
Shared schema/storage changes
App lifecycle changes
Transaction/trading/production paths
Same file ownership
Unclear requirements
```

- [ ] **Step 2: Record ownership boundaries before dispatch**

Add to `<repo>/docs/subagents.md`:

```markdown
## Trial: YYYY-MM-DD <task>

- Main agent owns:
- Subagent A owns:
- Subagent B owns:
- Files that must not overlap:
- Merge/review checkpoint:
```

- [ ] **Step 3: Verify subagent output**

For each subagent result:

```bash
git diff -- <files claimed by subagent>
<targeted verification command>
```

Do not accept subagent success reports without checking the diff and running verification.

- [ ] **Step 4: Decide keep or reject**

Append to `<repo>/docs/codex-usage.md`:

```markdown
| YYYY-MM-DD | Subagent trial | L | Superpowers subagent-driven development | `<verification>` -> `<result>` | <saved time or added merge/review cost> | Keep only for <specific boundary> / reject |
```

Exit criterion: subagents have a documented, narrow boundary; when not used, the reason is explicit and tied to coupling, sequencing, ownership, shared-state risk, or high-risk external operations.

Post-V2 refinement: the portable toolkit now treats subagents as proactive for large/planned/cross-module work when ownership is safe. This is not shared-state default implementation; the main agent still owns decomposition, integration, diff review and final verification.

---

### Task 8: Browser and Frontend QA Calibration

**Files:**
- Modify: `<repo>/docs/testing.md`
- Modify: `<repo>/docs/quality-gates.md`
- Modify: `<repo>/docs/codex-usage.md`

- [ ] **Step 1: Classify frontend change types**

Document in `<repo>/docs/testing.md`:

```markdown
## Frontend Verification Matrix

| Change type | Minimum check | Recommended check |
|---|---|---|
| Pure JS data mapping | frontend contract/unit test | targeted browser smoke if user-visible |
| Empty/error/loading text | targeted test | browser smoke for affected route |
| CSS/layout/responsive | browser smoke | desktop + mobile screenshots |
| Forms/navigation | browser interaction | E2E if workflow critical |
| Canvas/3D/chart/media | browser screenshot and pixel/resource check | multi-viewport check |
```

- [ ] **Step 2: Run browser QA only when justified**

Trigger browser QA when:

```text
CSS/layout changed
route or navigation changed
real browser APIs changed
canvas/chart/media/3D changed
user-visible interaction changed
automated contract tests cannot cover the risk
```

- [ ] **Step 3: Record evidence**

Append:

```markdown
| YYYY-MM-DD | Frontend QA calibration | M/L | frontend-qa/browser | `<test command>`, `<browser route>` | <bug caught or cost observed> | Keep trigger / narrow trigger |
```

Exit criterion: browser QA is neither skipped for visual risk nor forced onto pure logic changes without evidence.

---

### Task 9: Prepare V2 Toolkit Update

**Files:**
- Modify: `outputs/codex-workflow-kit/WORKFLOW-REVIEW.md`
- Modify: `outputs/codex-workflow-kit/QUICKSTART.md`
- Modify: `outputs/codex-workflow-kit/repo-template/docs/*.md` as justified
- Modify: `outputs/codex-workflow-kit/VERSION`
- Modify via script: `outputs/codex-workflow-kit/MANIFEST.sha256`
- Modify via script: `outputs/codex-workflow-kit/releases/*`

- [ ] **Step 1: Summarize evidence**

In `WORKFLOW-REVIEW.md`, add:

```markdown
## V2 Adoption Review

Evidence source:

- Repo:
- Task count:
- Verified commands:
- Promotions:
- Rejections:
- Remaining candidates:
```

- [ ] **Step 2: Apply only proven template changes**

Allowed changes:

```text
Better wording in docs templates
More precise trigger conditions
Verified command placeholders
Clearer side-effect warnings
Narrow subagent boundary examples
```

Avoid:

```text
New general-purpose planning skill
Default blocking hooks without strong evidence
Global memory rules from one repo
Heavy MCP defaults
Making XL/spec-kit normal for M tasks
```

- [ ] **Step 3: Bump version**

Edit `VERSION` for this adoption checkpoint:

```text
2026.06.07.10
```

Use `.1`, `.2`, etc. for same-day iteration. Use the actual date for future-day releases.

- [ ] **Step 4: Rebuild release**

Run:

```bash
cd <toolkit-root>
python3 scripts/build_release.py
```

Expected:

```text
Release archive: ...
Checksum file: ...
```

Exit criterion: V2 changes are evidence-backed, versioned, and packaged.

---

### Task 10: Final V2 Verification and Migration Drill

**Files:**
- Verify: `outputs/codex-workflow-kit/scripts/verify_toolkit.py`
- Verify: `outputs/codex-workflow-kit/tests/test_verify_toolkit.py`
- Verify: `outputs/codex-workflow-kit/repo-template/tests/test_verify_context_pack.py`
- Verify: `outputs/codex-workflow-kit/releases/*.tar.gz`

- [ ] **Step 1: Run toolkit verifier**

Run:

```bash
cd <toolkit-root>
python3 scripts/verify_toolkit.py
```

Expected:

```text
Workflow toolkit OK
```

- [ ] **Step 2: Run toolkit tests**

Run with a Python environment that has pytest:

```bash
python3 -m pytest -p no:cacheprovider tests/test_verify_toolkit.py -q
```

Expected:

```text
passed
```

- [ ] **Step 3: Run repo-template verifier and tests**

Run:

```bash
cd <toolkit-root>/repo-template
python3 scripts/verify_context_pack.py
python3 -m pytest -p no:cacheprovider tests/test_verify_context_pack.py -q
```

Expected:

```text
Context pack OK
passed
```

- [ ] **Step 4: Verify archive checksum**

Run:

```bash
cd <toolkit-root>/releases
env LC_ALL=C LANG=C LC_CTYPE=C shasum -a 256 -c codex-workflow-kit-<VERSION>.tar.gz.sha256
```

Expected:

```text
codex-workflow-kit-<VERSION>.tar.gz: OK
```

- [ ] **Step 5: Run temporary install drill**

Run:

```bash
tmpdir="$(mktemp -d)"
tar -xzf codex-workflow-kit-<VERSION>.tar.gz -C "$tmpdir"
cd "$tmpdir/codex-workflow-kit"
python3 scripts/verify_toolkit.py
./install.sh --codex-home "$tmpdir/codex-home" --agents-home "$tmpdir/agents-home" --dry-run
./install.sh --codex-home "$tmpdir/codex-home" --agents-home "$tmpdir/agents-home"
```

Expected:

```text
Workflow toolkit OK
Install plan complete.
```

Exit criterion: V2 package can be verified, checksum-checked, unpacked, dry-run installed, and installed into temporary homes.

---

## Self-Review

Spec coverage:

- Real adoption is covered by Tasks 2-4.
- hooks promotion is covered by Task 5.
- MCP/code graph/memory evaluation is covered by Task 6.
- subagents evaluation is covered by Task 7.
- frontend QA calibration is covered by Task 8.
- V2 packaging and migration proof are covered by Tasks 9-10.

Placeholder scan:

- No `TBD`, `TODO`, or unspecified implementation steps are required for execution.
- Every promotion has concrete evidence and rollback requirements.

Type consistency:

- The plan consistently treats V1 as baseline and V2 as evidence-backed adoption changes.
- Candidate capabilities remain manual until repeated evidence supports promotion.
