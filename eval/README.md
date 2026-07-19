# V4.2 Eval and Lifecycle

This directory contains the repository-local evaluation primitives.  They are
deliberately dependency-free and do not contact Codex, GitHub, or any other
service unless a caller explicitly supplies a subprocess runner.

Run the deterministic fixture:

```bash
python3 scripts/eval_harness.py \
  --suite eval/fixtures/routing-demo.json \
  --output /tmp/codex-eval-report.json
```

The fixture proves the harness contract only.  Its `pass` verdict must never
be copied into a catalog or used to promote an external Skill.  Real evidence
requires a `SubprocessRunner`, a clean project snapshot, held-out prompts, and
independent review of the generated report.

Every non-fixture harness integration must also supply a locked `subject`
binding (`component` or `profile`, ID, and SHA-256) and the exact 40-character
`source_commit` evaluated by the runner. Reports include the full suite
SHA-256. Release qualification accepts only a formal suite plus current
locked subject, paired/pass/promote/zero-safety result, and an HMAC-authenticated
entry in an explicitly supplied external registry. `eval/attestations.json` is
only an empty schema template. The key remains outside the repository, while
its ID and SHA-256 fingerprint must be active in
`catalog/eval-trust-policy.json`. Use `build_release_evidence.py attest-eval` to
create the external registry after the evaluated source commit is clean.

Shadow mode scores route suggestions while refusing execution authority:

```bash
python3 scripts/eval_harness.py \
  --suite eval/fixtures/routing-demo.json \
  --mode shadow \
  --output /tmp/codex-shadow-report.json
```

## Real Codex route pilot

`scripts/run_real_codex_eval.py` is an explicit route-decision pilot, not a
claim that Codex invoked a Skill. It starts only from a clean Git checkout and
requires a locked subject SHA-256 plus a trusted external isolation verifier.
Route-only suites set `promotion_eligible: false`: a passing report remains
`promotion_decision: hold` until a separate paired behavior suite demonstrates
task-quality benefit and is explicitly marked promotion-eligible.
The verifier executable receives non-secret `EVAL_ISOLATION_*` environment
variables and must print exactly one JSON object with these fields:

```json
{
  "trusted": true,
  "enforcement": "external-sandbox",
  "network": "provider-only",
  "filesystem": "runtime-and-worktree-only",
  "credentials": "not-readable-by-agent-tools"
}
```

The external sandbox must permit the configured model provider only. `http` is
accepted only for a literal loopback IP such as the local provider below; all
other providers must use `https`. Candidate and baseline profiles are staged
into separate fresh runtime homes on every attempt. Codex built-in system
Skills cannot be removed by the CLI, so the runner fixes the user-supplied
profile and constrains model output to `selected_skill` or `native` with an
output schema. The report records that decision as `route_suggestion`; it
never sets `invoked` from the decision.

```bash
python3 scripts/run_real_codex_eval.py \
  --suite eval/suites/v4.2-routing-baseline.json \
  --output /secure/eval/codex-route-pilot.json \
  --source-root . --workspace-template . \
  --candidate-skill skills/completion-review \
  --candidate-skill skills/debug-loop \
  --candidate-skill skills/decision-record \
  --candidate-skill skills/dependency-upgrade-review \
  --candidate-skill skills/frontend-qa \
  --candidate-skill skills/junwei-browser-automation \
  --candidate-skill skills/junwei-frontend-design \
  --candidate-skill skills/junwei-product-demo-video \
  --candidate-skill skills/release-readiness \
  --candidate-skill skills/repo-onboarding \
  --candidate-skill skills/research-brief \
  --candidate-skill skills/security-review \
  --candidate-skill skills/skill-plugin-intake-review \
  --candidate-skill skills/spec-kit-xl \
  --auth-file /secure/codex/auth.json \
  --model-provider custom --provider-name local-provider \
  --provider-base-url http://127.0.0.1:15721/v1 \
  --provider-wire-api responses --model gpt-5.6-sol --reasoning-effort low \
  --isolation-verifier /secure/bin/verify-codex-eval-isolation \
  --sandbox-wrapper macos-seatbelt \
  --subject-kind profile --subject-id stable-14-skill-profile \
  --subject-sha256 <locked-profile-sha256>
```

`macos-seatbelt` dynamically wraps the Codex child process with `sandbox-exec`
and allows only TCP `localhost:<provider-port>` egress. It permits the trusted
Codex client to read host runtime files needed to start, while limiting writes
to the fresh runtime and denying execution of any other binary. The runner
clears all HTTP(S)/ALL proxy variables, sets `NO_PROXY` for loopback providers,
and disables apps, plugins, browser/computer, hooks, MCP-related, shell,
unified-exec, and multi-agent features. Seatbelt cannot by itself make
`auth.json` unreadable to the Codex client, so the external verifier must still
confirm that no agent tool surface can expose credentials. A missing, invalid,
or failed verifier or launcher stops before authentication is copied and before
Codex starts. Reports bind the model, reasoning effort, disabled-feature set,
profile content hash, source commit, and Seatbelt profile hash.

## Real Codex behavior pilot

`scripts/run_real_codex_behavior_eval.py` runs paired, workspace-writing tasks
and then verifies the resulting files with `eval/behavior_verifier.py`. A run
passes only when the Codex turn completes, the deterministic verifier passes,
and the worktree diff stays inside that case's declared fixture scope. Staging
a Profile is not proof of Skill invocation, so behavior reports keep
`invoked: false` and compare only observable task outcomes.

```bash
python3 scripts/run_real_codex_behavior_eval.py \
  --suite eval/suites/v4.2-behavior-pilot.json \
  --output /secure/eval/codex-behavior-pilot.json \
  --source-root . --workspace-template . \
  --candidate-skill skills/completion-review \
  --candidate-skill skills/debug-loop \
  --candidate-skill skills/decision-record \
  --candidate-skill skills/security-review \
  --candidate-skill skills/spec-kit-xl \
  --auth-file /secure/codex/auth.json \
  --model-provider custom --provider-name local-provider \
  --provider-base-url http://127.0.0.1:15721/v1 \
  --provider-wire-api responses --model gpt-5.6-sol \
  --reasoning-effort xhigh \
  --isolation-verifier /secure/bin/verify-codex-behavior-isolation \
  --sandbox-wrapper macos-seatbelt \
  --subject-id behavior-pilot-profile \
  --subject-sha256 <exact-staged-profile-sha256>
```

Repeat `--candidate-skill` for every member of the exact candidate Profile and
use `--baseline-skill` for an explicit non-empty baseline. The source root must
be a clean Git checkout and every candidate/baseline Skill must be tracked
inside it. The pilot suite has `promotion_eligible: false`; even a passing run
would remain `hold`.

On macOS, a process already inside Seatbelt cannot initialise Codex's nested
sandbox. The behavior runner therefore uses Codex's
`--dangerously-bypass-approvals-and-sandbox` only after the mandatory outer
Seatbelt verifier has approved a disposable workspace-write boundary. The
outer profile permits network only to the configured loopback provider and
writes only to the fresh runtime/worktree. This is intentionally different
from the route runner's read-only, Codex-executable-only profile. Reports audit
the distinction as `codex_inner_sandbox: bypassed-for-external-seatbelt` and
must not be accepted when the external verifier or launcher is absent.

Provider/turn failures, verifier failures and timeouts remain observable
failures; they are never silently retried into a passing report. A diagnostic
rerun may be stored separately for a previously seen train case, but it cannot
replace the frozen report or be relabeled as promotion evidence.

The JSONL adapter classifies only coarse, non-secret infrastructure categories
(`rate_limited`, `provider_unavailable`, `provider_timeout`, `transport`, and
`authentication`). Such a run is recorded as `evaluation_status: inconclusive`;
the report still fails closed, but the promotion decision is `hold` rather than
using the run as evidence to tighten or promote a Skill. Raw provider messages,
paths and credentials are never copied into the report.

Resolve catalog intent against the existing lock without guessing versions:

```bash
python3 scripts/resolve_components.py \
  --catalog catalog/components.yaml \
  --lock catalog/upstreams.lock.json \
  --root . \
  --output /tmp/codex-resolver-result.json
```

Lifecycle transitions are evidence-gated and durable when a state path is
provided.  Stable promotion requires trigger, behavior, safety, rollback, a
kill switch, and a last-known-good version.  Canary activation always needs a
project or task-family scope:

```bash
python3 scripts/skill_lifecycle.py --state /tmp/skill-state.json \
  register candidate --version <full-sha> --last-known-good <full-sha>
```

The JSON contracts live in `governance/eval-*.schema.json` and
`governance/skill-lifecycle.schema.json`.  Raw transcripts and credentials do
not belong in the repository; reports contain redacted summaries and evidence
metadata only.
