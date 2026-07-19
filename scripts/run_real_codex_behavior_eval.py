#!/usr/bin/env python3
"""Run a verifier-backed, paired Codex behavior evaluation.

Unlike the route pilot, this command permits workspace writes only inside a
fresh copied worktree. A successful Codex turn is insufficient: every case
must provide a deterministic ``verification_id`` that passes after execution.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.codex_behavior_runner import CodexBehaviorRunner
from eval.codex_runner import CodexProvider, CommandIsolationVerifier, MacOSSandboxExecLauncher
from eval.harness import EvalError, EvalHarness, load_suite, write_report


def _source_commit(root: Path) -> str:
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EvalError("source root must be a clean Git checkout") from exc
    if status.returncode != 0 or revision.returncode != 0 or status.stdout.strip():
        raise EvalError("source root must be a clean Git checkout for source_commit binding")
    commit = revision.stdout.strip()
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise EvalError("git did not return a full lowercase source commit")
    return commit


def _tracked_workspace_directory(source_root: Path, workspace_template: Path) -> Path:
    if not workspace_template.is_dir() or workspace_template.is_symlink():
        raise EvalError("workspace template must be a non-symlink directory")
    try:
        relative = workspace_template.relative_to(source_root)
    except ValueError as exc:
        raise EvalError("workspace template must be inside source root") from exc
    pathspec = relative.as_posix() if relative.parts else "."
    try:
        tracked = subprocess.run(
            ["git", "ls-files", "-z", "--", pathspec],
            cwd=source_root,
            text=False,
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EvalError("cannot verify that workspace template is tracked") from exc
    if tracked.returncode != 0 or not tracked.stdout:
        raise EvalError("workspace template must be a source-root tracked directory")
    return workspace_template


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a real paired Codex behavior eval with deterministic verification.")
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--workspace-template", type=Path)
    parser.add_argument("--candidate-skill", type=Path, action="append", default=[])
    parser.add_argument("--baseline-skill", type=Path, action="append", default=[])
    parser.add_argument("--auth-file", type=Path, required=True)
    parser.add_argument("--model-provider", required=True)
    parser.add_argument("--provider-name", required=True)
    parser.add_argument("--provider-base-url", required=True)
    parser.add_argument("--provider-wire-api", required=True)
    parser.add_argument("--provider-does-not-require-openai-auth", action="store_true")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument(
        "--reasoning-effort",
        choices=("minimal", "low", "medium", "high", "xhigh", "max", "ultra"),
        default="xhigh",
    )
    parser.add_argument("--codex-binary", default="codex")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--isolation-verifier", type=Path, required=True)
    parser.add_argument("--isolation-verifier-timeout", type=float, default=15.0)
    parser.add_argument("--sandbox-wrapper", choices=("macos-seatbelt",), required=True)
    parser.add_argument("--sandbox-exec", type=Path, default=Path("/usr/bin/sandbox-exec"))
    parser.add_argument("--subject-id", required=True)
    parser.add_argument("--subject-sha256", required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--repetitions", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        source_root = args.source_root.resolve()
        source_commit = _source_commit(source_root)
        workspace_template = _tracked_workspace_directory(source_root, (args.workspace_template or source_root).resolve())
        if not args.candidate_skill:
            raise EvalError("behavior evaluation requires at least one candidate Skill")
        provider = CodexProvider(
            identifier=args.model_provider,
            name=args.provider_name,
            base_url=args.provider_base_url,
            wire_api=args.provider_wire_api,
            requires_openai_auth=not args.provider_does_not_require_openai_auth,
        )
        runner = CodexBehaviorRunner(
            auth_file=args.auth_file,
            provider=provider,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            candidate_skills=args.candidate_skill,
            baseline_skills=args.baseline_skill,
            codex_binary=args.codex_binary,
            timeout=args.timeout,
            isolation_verifier=CommandIsolationVerifier([str(args.isolation_verifier)], args.isolation_verifier_timeout),
            sandbox_launcher=MacOSSandboxExecLauncher(args.sandbox_exec),
        )
        if args.subject_sha256 != runner.candidate_profile_sha256:
            raise EvalError("profile subject SHA-256 must match the staged candidate profile")
        harness = EvalHarness(
            runner,
            seed=args.seed,
            workspace_template=workspace_template,
            isolation_verifier=runner.verify_for_harness,
            subject={
                "kind": "profile",
                "id": args.subject_id,
                "content_sha256": args.subject_sha256,
            },
            source_commit=source_commit,
        )
        report = harness.run(load_suite(args.suite), repetitions=args.repetitions, mode="paired")
        write_report(report, args.output)
    except (EvalError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"output": str(args.output), "verdict": report["verdict"], "run_id": report["run_id"]}, sort_keys=True))
    return 0 if report["verdict"] in {"pass", "needs_human_review"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
