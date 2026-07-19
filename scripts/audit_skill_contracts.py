#!/usr/bin/env python3
"""Audit packaged Codex skills for trigger, boundary, output, and validation contracts."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


REQUIRED_METADATA = ("name", "description")
REQUIRED_CATALOG_METADATA = (
    "risk",
    "source_repo",
    "source_type",
    "date_added",
    "setup",
    "write_surface",
    "auth",
    "network_policy",
)
BOUNDARY_TERMS = ("不要做", "Do not", "don't", "Do Not")
VALIDATION_TERMS = ("Verification", "验证", "Completion Conditions", "完成条件", "Acceptance")
SUPERPOWERS_TERMS = ("Superpowers", "implementation-plan", "orchestrator", "planner", "dispatcher", "queue")


@dataclass(frozen=True)
class SkillContract:
    name: str
    path: str
    metadata_keys: tuple[str, ...]
    missing_metadata: tuple[str, ...]
    catalog_metadata_keys: tuple[str, ...]
    missing_catalog_metadata: tuple[str, ...]
    has_trigger: bool
    has_output_shape: bool
    has_boundaries: bool
    has_validation: bool
    has_progressive_disclosure: bool
    has_superpowers_boundary: bool
    status: str

    @property
    def ok(self) -> bool:
        return (
            not self.missing_metadata
            and not self.missing_catalog_metadata
            and self.has_trigger
            and self.has_output_shape
            and self.has_boundaries
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "path": self.path,
            "metadata_keys": list(self.metadata_keys),
            "missing_metadata": list(self.missing_metadata),
            "catalog_metadata_keys": list(self.catalog_metadata_keys),
            "missing_catalog_metadata": list(self.missing_catalog_metadata),
            "has_trigger": self.has_trigger,
            "has_output_shape": self.has_output_shape,
            "has_boundaries": self.has_boundaries,
            "has_validation": self.has_validation,
            "has_progressive_disclosure": self.has_progressive_disclosure,
            "has_superpowers_boundary": self.has_superpowers_boundary,
            "status": self.status,
            "ok": self.ok,
        }


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("\"'")
    return data


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def _skill_files(root: Path) -> list[Path]:
    skills_root = root / "skills"
    if not skills_root.exists():
        return []
    return sorted(skills_root.glob("*/SKILL.md"))


def _catalog_entries(root: Path) -> dict[str, dict[str, object]]:
    """Read governance metadata from catalog without making it frontmatter."""
    try:
        try:
            # Works when this file is executed directly from scripts/.
            from validate_governance import load_catalog
        except ImportError:
            # Works when imported as scripts.audit_skill_contracts in tests.
            from scripts.validate_governance import load_catalog

        catalog = load_catalog(root / "catalog/components.yaml")
    except (ImportError, OSError, ValueError):
        return {}
    rows = catalog.get("skills", [])
    if not isinstance(rows, list):
        return {}
    return {
        row.get("name"): row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("name"), str)
    }


def audit_skill_file(
    root: Path,
    skill_file: Path,
    catalog_entry: dict[str, object] | None = None,
) -> SkillContract:
    text = _read_text(skill_file)
    metadata = _frontmatter(text)
    missing = tuple(key for key in REQUIRED_METADATA if key not in metadata)
    catalog_metadata = catalog_entry.get("metadata", {}) if catalog_entry else {}
    if not isinstance(catalog_metadata, dict):
        catalog_metadata = {}
    missing_catalog = tuple(key for key in REQUIRED_CATALOG_METADATA if key not in catalog_metadata)
    relative = skill_file.relative_to(root).as_posix()
    skill_root = skill_file.parent
    has_references = (skill_root / "references").exists() or "references/" in text
    has_agents = (skill_root / "agents").exists() or "agents/" in text
    return SkillContract(
        name=metadata.get("name") or skill_file.parent.name,
        path=relative,
        metadata_keys=tuple(sorted(metadata)),
        missing_metadata=missing,
        catalog_metadata_keys=tuple(sorted(catalog_metadata)),
        missing_catalog_metadata=missing_catalog,
        has_trigger=bool(metadata.get("description", "").strip()),
        has_output_shape="## Output Shape" in text,
        has_boundaries=_contains_any(text, BOUNDARY_TERMS),
        has_validation=_contains_any(text, VALIDATION_TERMS),
        has_progressive_disclosure=has_references or has_agents,
        has_superpowers_boundary=_contains_any(text, SUPERPOWERS_TERMS),
        status=str(catalog_entry.get("status", "unknown")) if catalog_entry else "unknown",
    )


def build_report(root: str | Path = ".") -> dict[str, object]:
    root = Path(root).resolve()
    catalog_entries = _catalog_entries(root)
    contracts = [
        audit_skill_file(root, path, catalog_entries.get(path.parent.name))
        for path in _skill_files(root)
    ]
    totals = {
        "skills": len(contracts),
        "ok": sum(1 for contract in contracts if contract.ok),
        "with_output_shape": sum(1 for contract in contracts if contract.has_output_shape),
        "with_boundaries": sum(1 for contract in contracts if contract.has_boundaries),
        "with_validation": sum(1 for contract in contracts if contract.has_validation),
        "with_progressive_disclosure": sum(1 for contract in contracts if contract.has_progressive_disclosure),
        "with_superpowers_boundary": sum(1 for contract in contracts if contract.has_superpowers_boundary),
    }
    return {
        "ok": totals["skills"] > 0 and totals["ok"] == totals["skills"],
        "root": str(root),
        "totals": totals,
        "skills": [contract.to_dict() for contract in contracts],
    }


def _markdown(report: dict[str, object]) -> str:
    lines = [
        "# Skill Contract Audit",
        "",
        f"- Root: `{report['root']}`",
        f"- Skills: `{report['totals']['skills']}`",
        f"- OK: `{report['totals']['ok']}`",
        "",
        "| Skill | Metadata | Trigger | Output | Boundaries | Validation | Progressive | Superpowers | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for skill in report["skills"]:
        metadata_ok = "yes" if not skill["missing_metadata"] else "no"
        row = [
            skill["name"],
            metadata_ok,
            "yes" if skill["has_trigger"] else "no",
            "yes" if skill["has_output_shape"] else "no",
            "yes" if skill["has_boundaries"] else "no",
            "yes" if skill["has_validation"] else "no",
            "yes" if skill["has_progressive_disclosure"] else "no",
            "yes" if skill["has_superpowers_boundary"] else "no",
            skill["status"],
        ]
        lines.append("| " + " | ".join(str(cell).replace("|", r"\|") for cell in row) + " |")
    lines.append("")
    return "\n".join(lines)


def _print_text(report: dict[str, object]) -> None:
    print("Skill contract audit OK" if report["ok"] else "Skill contract audit found issues")
    totals = report["totals"]
    print(
        "Coverage: "
        f"{totals['ok']}/{totals['skills']} ok, "
        f"output={totals['with_output_shape']}, "
        f"boundaries={totals['with_boundaries']}, "
        f"validation={totals['with_validation']}, "
        f"progressive={totals['with_progressive_disclosure']}, "
        f"superpowers={totals['with_superpowers_boundary']}"
    )
    for skill in report["skills"]:
        if skill["ok"]:
            continue
        missing = ",".join(
            [*skill["missing_metadata"], *skill["missing_catalog_metadata"]]
        ) or "contract"
        print(f"[warning] {skill['name']}: missing {missing}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit packaged skill contracts.")
    parser.add_argument("--root", default=".", help="Toolkit root. Default: current directory.")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable JSON report.")
    parser.add_argument("--markdown", action="store_true", help="Print a Markdown matrix.")
    args = parser.parse_args(argv)

    report = build_report(args.root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    elif args.markdown:
        print(_markdown(report))
    else:
        _print_text(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
