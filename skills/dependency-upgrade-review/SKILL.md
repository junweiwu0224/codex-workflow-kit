---
name: dependency-upgrade-review
description: Use when adding, removing, updating, pinning, auditing, or reviewing dependencies, lockfiles, package managers, Docker base images, GitHub Actions, vendored code, CVEs, advisories, licenses, or supply-chain risk.
---

# dependency-upgrade-review

## Goal

Review dependency changes for compatibility, security, licensing, supply-chain risk, lockfile integrity, tests, and rollback. This skill narrows upgrades to the user's goal; it is not a default full-upgrade workflow.

## When to Use

Use when changes touch:

- `package.json`, lockfiles, `pyproject.toml`, `requirements*.txt`, `poetry.lock`, `go.mod`, `go.sum`, `Cargo.toml`, `Cargo.lock`, Maven/Gradle files.
- Docker base images, GitHub Actions versions, vendored dependencies, submodules, package manager config.
- Dependabot/Renovate PRs, CVEs, advisories, SBOM, license or provenance questions.
- New runtime dependencies, build plugins, CI actions, parsers, auth/crypto/network/database/web framework packages.
- Major version upgrades, large lockfile churn, peer dependency shifts, engine/runtime changes, or install scripts.

Do not use for source-only edits that merely import an existing dependency.

## Workflow

1. Define the upgrade scope.
   - Identify direct vs transitive dependency changes.
   - Distinguish runtime, dev, build, test, CI, container, and vendored impact.
   - Confirm whether the goal is feature support, security advisory, compatibility, or cleanup.

2. Inspect local evidence.
   - Review manifest and lockfile diffs.
   - Look for unexpected package additions, version jumps, engine/peer changes, postinstall scripts, binary downloads, license changes, source URLs, and maintainer/provenance signals.
   - Check lockfile reachability: why each meaningful new transitive dependency is present, which direct dependency pulls it in, and whether the lockfile churn matches the intended scope.
   - For CI actions, container images, packages with install scripts, vendored code, or publish paths, check publisher identity, provenance/attestation, SBOM availability, signing or checksum guidance when the ecosystem supports it.
   - Check repo docs for manual-only test policy or dependency rules.

3. Check current primary sources when facts can change.
   - Release notes, changelogs, migration guides, package registry metadata, security advisories, CVE/GHSA pages, official docs.
   - If sources are unavailable or rate-limited, say so and mark the evidence weak rather than guessing.

4. Choose verification by risk.
   - Minimal: lockfile review plus targeted tests for affected code.
   - Broader: typecheck, lint, build, package-specific tests, integration/E2E when runtime behavior changes.
   - Manual/approval first: installs with network, downloads, Docker pulls, service startup, migrations, production, credentials, publish/release, or external writes.

5. Report decision and rollback.
   - Recommend accept, hold, split, pin, revert, or escalate.
   - Name breaking changes, migration steps, tests run, tests not run, rollback path, and residual risk.
   - Use `security-review` if the dependency affects auth, crypto, parsing untrusted input, execution, CI, install scripts, MCP/plugin trust, or known vulnerabilities.
   - Use `decision-record` if accepting risk, pinning long-term, changing platform/runtime, or adding a new strategic dependency.

6. Apply publish and supply-chain guards when relevant.
   - If a workflow, script, package, container, or action can publish, release, deploy, upload artifacts, or use secrets, require explicit scope review before running it.
   - Prefer pinned actions/images/packages when the repo policy supports it; document why tag-only or floating references are acceptable when they remain.
   - Treat SBOM, attestation, provenance, signature, checksum, license, and publisher checks as evidence inputs, not as automatic approval.

## Output Shape

```text
Dependency review:
- Scope:
- Direct changes:
- Transitive / lockfile notes:
- Security / license / provenance:
- Compatibility and migration:
- Verification:
- Recommendation:
- Rollback:
```

## Boundaries

- Do not upgrade unrelated packages to "clean things up".
- Do not run dependency installs, downloads, Docker pulls, publish/release, or external actions without checking repo policy and approval boundaries.
- Do not replace deterministic tools such as dependency review, secret scanning, or SBOM generation; use their output as evidence when available.
- Do not treat a lockfile diff as harmless just because direct manifests look small; inspect reachable transitive churn when the blast radius matters.
