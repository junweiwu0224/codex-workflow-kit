#!/usr/bin/env python3
"""Run a real APK decode smoke against the installed reverse pack."""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ApkDecodeSmokeIssue:
    severity: str
    code: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "path": self.path,
            "message": self.message,
        }


def _parse_key_values(output: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def run_apk_decode_smoke(
    apk_fixture: str | Path,
    codex_home: str | Path | None = None,
    output_root: str | Path | None = None,
    task_name: str = "apk-decode-smoke",
) -> tuple[list[ApkDecodeSmokeIssue], dict]:
    apk_path = Path(apk_fixture).expanduser().resolve()
    codex_home_path = Path(codex_home).expanduser().resolve() if codex_home else Path.home() / ".codex"
    output_root_path = Path(output_root).expanduser().resolve() if output_root else apk_path.parent / "out"
    decode_script = codex_home_path / "reverse-skill/skills/apk-reverse/scripts/decode.sh"

    issues: list[ApkDecodeSmokeIssue] = []
    if not apk_path.exists():
        issues.append(
            ApkDecodeSmokeIssue(
                severity="error",
                code="missing-apk-fixture",
                path=str(apk_path),
                message="APK decode smoke fixture is missing.",
            )
        )
    if not decode_script.exists():
        issues.append(
            ApkDecodeSmokeIssue(
                severity="error",
                code="missing-decode-script",
                path=str(decode_script),
                message="Installed decode.sh is missing from the reverse pack.",
            )
        )
    if issues:
        report = {
            "ok": False,
            "apk_fixture": str(apk_path),
            "codex_home": str(codex_home_path),
            "decode_script": str(decode_script),
            "output_root": str(output_root_path),
            "command": None,
            "exit_code": None,
            "summary": {},
            "stdout": "",
            "stderr": "",
            "issues": [issue.to_dict() for issue in issues],
        }
        return issues, report

    command = [
        "bash",
        str(decode_script),
        str(apk_path),
        "--name",
        task_name,
        "--out",
        str(output_root_path),
        "--clean",
    ]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    summary = _parse_key_values(completed.stdout)

    apktool_exit = summary.get("apktool_exit_code")
    package_name = summary.get("package", "")
    smali_dirs = int(summary.get("smali_dirs", "0") or "0")

    if completed.returncode != 0:
        issues.append(
            ApkDecodeSmokeIssue(
                severity="error",
                code="decode-command-failed",
                path=str(decode_script),
                message=f"decode.sh returned non-zero exit code: {completed.returncode}.",
            )
        )
    if apktool_exit not in {"0", 0}:
        issues.append(
            ApkDecodeSmokeIssue(
                severity="error",
                code="apktool-decode-failed",
                path=str(apk_path),
                message=f"apktool decode did not finish cleanly (apktool_exit_code={apktool_exit}).",
            )
        )
    if not package_name:
        issues.append(
            ApkDecodeSmokeIssue(
                severity="error",
                code="missing-package-name",
                path=str(apk_path),
                message="Decoded APK summary does not include a package name.",
            )
        )
    if smali_dirs <= 0:
        issues.append(
            ApkDecodeSmokeIssue(
                severity="error",
                code="missing-smali-output",
                path=str(apk_path),
                message="Decoded APK summary reports no smali output directories.",
            )
        )

    report = {
        "ok": not any(issue.severity == "error" for issue in issues),
        "apk_fixture": str(apk_path),
        "codex_home": str(codex_home_path),
        "decode_script": str(decode_script),
        "output_root": str(output_root_path),
        "command": command,
        "exit_code": completed.returncode,
        "summary": summary,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "issues": [issue.to_dict() for issue in issues],
    }
    return issues, report


def _print_report(report: dict) -> None:
    print("APK decode smoke OK" if report["ok"] else "APK decode smoke failed")
    print(f"- apk_fixture: {report['apk_fixture']}")
    print(f"- decode_script: {report['decode_script']}")
    print(f"- exit_code: {report['exit_code']}")
    for key in ("package", "jadx_exit_code", "apktool_exit_code", "java_files", "smali_dirs", "so_files"):
        if key in report["summary"]:
            print(f"- {key}: {report['summary'][key]}")
    for issue in report["issues"]:
        print(f"[{issue['severity']}] {issue['code']} {issue['path']}: {issue['message']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a real APK decode smoke using the installed reverse pack.")
    parser.add_argument("--apk-fixture", required=True, help="Path to a real APK used for decode smoke.")
    parser.add_argument("--codex-home", default=None, help="Codex home containing reverse-skill. Default: ~/.codex")
    parser.add_argument("--output-root", default=None, help="Output root for decode artifacts. Default: <apk-dir>/out")
    parser.add_argument("--task-name", default="apk-decode-smoke", help="Task name used under the output root.")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable JSON report.")
    args = parser.parse_args(argv)

    _, report = run_apk_decode_smoke(args.apk_fixture, args.codex_home, args.output_root, args.task_name)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_report(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
