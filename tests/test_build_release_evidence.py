import json
from pathlib import Path

import pytest

from scripts.build_plugin import main as build_plugin_main
from scripts.build_release_evidence import (
    artifact_record,
    attestation_signature,
    build_manifest,
    build_notices,
    build_sbom,
    canonical_json_sha256,
    digest,
    eval_report_record,
    load_eval_attestations,
    main,
    plugin_record,
)


def _properties(component):
    return {item["name"]: item["value"] for item in component["properties"]}


def test_release_evidence_is_deterministic_and_tracks_resolved_content():
    root = Path(__file__).resolve().parents[1]
    first = build_manifest(root)
    second = build_manifest(root)
    assert first == second
    assert first["schema_version"] == "4.2"
    assert "sbom.cdx.json" in first["sbom"]
    assert first["unresolved_components"] == []
    assert first["repo_local_content_components"] == first["locked_components"] == 14
    assert first["reverse_dependencies"]["count"] >= 17
    assert first["reverse_dependencies"]["blocked_optional"] == ["pentestswarm-container"]
    assert first["reverse_dependencies"]["field_enforcement_counts"]["metadata-only"] > 0
    assert first["distribution"]["public_release_eligible"] is False
    assert first["distribution"]["policy"]["declared_public_release"] == "blocked-unless-separately-approved"
    assert first["governance_inputs"]["catalog"]["path"] == "catalog/components.yaml"
    assert len(first["governance_inputs"]["component_lock"]["sha256"]) == 64
    assert first["release_process"]["target"] == "portable-source-archive"

    notices = build_notices(root)
    assert "grants no open-source license" in notices
    assert "license=NOASSERTION" in notices
    assert "integrity:metadata-only" in notices
    assert notices == (root / "THIRD-PARTY-NOTICES.txt").read_text(encoding="utf-8")

    sbom = build_sbom(root)
    assert sbom["bomFormat"] == "CycloneDX"
    components = {component["bom-ref"]: component for component in sbom["components"]}
    repo_local = components["completion-review"]
    assert repo_local["version"].startswith("sha256:")
    assert _properties(repo_local)["resolution.kind"] == "repo-local-content"
    assert components["pentestswarm-container"]["version"] == "blocked"
    assert components["pentestswarm-container"]["licenses"] == [{"license": {"name": "NOASSERTION"}}]
    analyzer = components["anything-analyzer-git"]
    assert analyzer["name"] == "https://github.com/Mouseww/anything-analyzer.git"
    assert _properties(analyzer)["enforcement.commit"] == "enforced"


def test_release_evidence_cli_writes_and_verifies(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "evidence"
    assert main(["write", "--root", str(root), "--output", str(output)]) == 0
    assert main(["verify", "--root", str(root), "--output", str(output), "--require-resolved"]) == 0
    with pytest.raises(SystemExit) as exc_info:
        main(["verify", "--root", str(root), "--output", str(output), "--require-eval"])
    assert exc_info.value.code == 2
    with pytest.raises(SystemExit) as exc_info:
        main(["verify", "--root", str(root), "--output", str(output), "--public"])
    assert exc_info.value.code == 2
    assert json.loads((output / "release-manifest.json").read_text(encoding="utf-8"))["package"] == "codex-workflow-kit"


def test_plugin_directory_artifact_uses_deterministic_tree_hash(tmp_path):
    root = Path(__file__).resolve().parents[1]
    plugin = tmp_path / "junwei-core"
    (plugin / ".codex-plugin").mkdir(parents=True)
    (plugin / ".codex-plugin/plugin.json").write_text("{}\n", encoding="utf-8")
    (plugin / "skills/example").mkdir(parents=True)
    (plugin / "skills/example/SKILL.md").write_text("example\n", encoding="utf-8")

    first = artifact_record(plugin, root)
    second = artifact_record(plugin, root)

    assert first == second
    assert first["kind"] == "directory"
    assert first["file_count"] == 2
    assert len(first["sha256"]) == 64
    assert first["path"] == "external/junwei-core"

    before = first["sha256"]
    (plugin / "skills/example/SKILL.md").chmod(0o755)
    assert artifact_record(plugin, root)["sha256"] != before


def test_release_evidence_rejects_distribution_claim_that_differs_from_policy(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "evidence"
    assert main(["write", "--root", str(root), "--output", str(output)]) == 0
    manifest_path = output / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["distribution"]["public_release_eligible"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main(["verify", "--root", str(root), "--output", str(output), "--public"])
    assert exc_info.value.code == 2


def test_release_evidence_verify_rejects_self_consistent_but_forged_files(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "forged"
    output.mkdir()
    (output / "release-manifest.json").write_text(
        json.dumps({
            "schema_version": "4.2",
            "source": {"dirty": False},
            "unresolved_components": [],
            "distribution": {"public_release_eligible": False},
        }),
        encoding="utf-8",
    )
    (output / "sbom.cdx.json").write_text(
        json.dumps({"bomFormat": "CycloneDX"}), encoding="utf-8"
    )
    (output / "THIRD-PARTY-NOTICES.txt").write_text("forged\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main([
            "verify",
            "--root",
            str(root),
            "--output",
            str(output),
            "--require-resolved",
            "--require-clean-source",
        ])
    assert exc_info.value.code == 2


def test_release_evidence_binds_explicit_eval_report(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "evidence"
    report = tmp_path / "fixture-eval.json"
    suite = json.loads((root / "eval/fixtures/routing-demo.json").read_text(encoding="utf-8"))
    report.write_text(
        json.dumps({
            "schema_version": "4.2",
            "report_type": "eval",
            "run_id": "fixture-run",
            "suite_id": suite["suite_id"],
            "suite_sha256": canonical_json_sha256(suite),
            "subject": {"kind": "fixture", "id": "fixture-skill", "content_sha256": "f" * 64},
            "source_commit": None,
            "mode": "shadow",
            "fixture_only": True,
            "promotion_decision": "hold",
            "verdict": "pass",
            "metrics": {"safety": {"violations": 0, "passed": True}},
            "assertion_failures": 0,
            "safety_findings": [],
            "blind_review": {"required": False, "complete": True, "passed": True},
            "evidence": {"isolation_enforcement": "fixture-only"},
        }),
        encoding="utf-8",
    )
    args = ["--root", str(root), "--output", str(output), "--eval-report", str(report)]
    assert main(["write", *args]) == 0
    assert main(["verify", *args, "--require-resolved", "--require-eval"]) == 0
    with pytest.raises(SystemExit) as exc_info:
        main(["verify", *args, "--require-real-eval"])
    assert exc_info.value.code == 2
    report.write_text(report.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        main(["verify", *args, "--require-resolved"])
    assert exc_info.value.code == 2


def _real_report(root: Path) -> dict:
    suite = json.loads((root / "eval/suites/v4.2-routing-baseline.json").read_text(encoding="utf-8"))
    lock = json.loads((root / "catalog/upstreams.lock.json").read_text(encoding="utf-8"))
    component = next(entry for entry in lock["entries"] if entry["name"] == "completion-review")
    return {
        "schema_version": "4.2",
        "report_type": "eval",
        "run_id": "real-run",
        "suite_id": suite["suite_id"],
        "suite_sha256": canonical_json_sha256(suite),
        "subject": {
            "kind": "component",
            "id": "completion-review",
            "content_sha256": component["content"]["value"],
        },
        "source_commit": __import__("subprocess").check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "mode": "paired",
        "fixture_only": False,
        "promotion_decision": "promote",
        "verdict": "pass",
        "metrics": {
            "trigger": {
                "held_out": {"precision": 0.95, "recall": 0.90, "false_positive_rate": 0.01}
            },
            "behavior": {"passed": True},
            "safety": {"violations": 0, "passed": True},
        },
        "assertion_failures": 0,
        "safety_findings": [],
        "blind_review": {"required": False, "complete": True, "passed": True},
        "evidence": {"isolation_enforcement": "trusted-adapter-verified"},
    }


def test_nonfixture_self_claim_is_not_qualifying_without_repo_attestation(tmp_path):
    root = Path(__file__).resolve().parents[1]
    report = tmp_path / "real.json"
    report.write_text(json.dumps(_real_report(root)), encoding="utf-8")
    record = eval_report_record(report, root)
    assert record["qualification"] == "unattested"

    output = tmp_path / "evidence"
    args = ["--root", str(root), "--output", str(output), "--eval-report", str(report)]
    assert main(["write", *args]) == 0
    with pytest.raises(SystemExit) as exc_info:
        main(["verify", *args, "--require-real-eval"])
    assert exc_info.value.code == 2


def test_repo_attestation_binds_report_suite_subject_and_source_commit(tmp_path):
    root = Path(__file__).resolve().parents[1]
    report_path = tmp_path / "real.json"
    report = _real_report(root)
    report_path.write_text(json.dumps(report), encoding="utf-8")
    commit = __import__("subprocess").check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    attestation = {
        "report_sha256": digest(report_path),
        "run_id": report["run_id"],
        "suite_id": report["suite_id"],
        "suite_sha256": report["suite_sha256"],
        "subject": report["subject"],
        "source_commit": commit,
        "decision": "qualified",
        "reviewed_by": "repository-owner",
        "reviewed_at": "2026-07-19T00:00:00Z",
        "isolation_verifier": "test-trusted-broker",
        "key_id": "test-key",
    }
    attestation["signature"] = attestation_signature(attestation, b"x" * 32)
    attestation["_authenticated"] = True
    record = eval_report_record(
        report_path, root, attestations=[attestation], source_commit=commit
    )
    assert record["qualification"] == "hmac-attested"


def test_arbitrary_self_signed_key_is_not_a_trusted_eval_root(tmp_path):
    root = Path(__file__).resolve().parents[1]
    report_path = tmp_path / "real.json"
    report = _real_report(root)
    report_path.write_text(json.dumps(report), encoding="utf-8")
    commit = __import__("subprocess").check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    key = b"attacker-selected-key-material-32bytes"
    entry = {
        "report_sha256": digest(report_path),
        "run_id": report["run_id"],
        "suite_id": report["suite_id"],
        "suite_sha256": report["suite_sha256"],
        "subject": report["subject"],
        "source_commit": commit,
        "decision": "qualified",
        "reviewed_by": "self",
        "reviewed_at": "2026-07-19T00:00:00Z",
        "isolation_verifier": "self-claim",
        "key_id": "untrusted-key",
    }
    entry["signature"] = attestation_signature(entry, key)
    registry = tmp_path / "attestations.json"
    registry.write_text(
        json.dumps({"schema_version": "4.2", "attestations": [entry]}),
        encoding="utf-8",
    )

    manifest = build_manifest(
        root,
        eval_reports=[report_path],
        eval_attestation_key=key,
        eval_attestation_registry=registry,
    )
    assert manifest["eval_reports"][0]["qualification"] == "unattested"
    assert manifest["eval_attestations"]["path"] == "external/attestations.json"


def test_external_registry_authenticates_only_a_pinned_active_key(tmp_path):
    root = tmp_path / "kit"
    (root / "catalog").mkdir(parents=True)
    content_hash = "a" * 64
    (root / "catalog/upstreams.lock.json").write_text(
        json.dumps({"entries": [{"name": "subject", "content": {"value": content_hash}}]}),
        encoding="utf-8",
    )
    key = b"trusted-owner-eval-key-material-32bytes"
    (root / "catalog/eval-trust-policy.json").write_text(
        json.dumps({
            "schema_version": "4.2",
            "policy_id": "test",
            "keys": [{
                "key_id": "owner-2026",
                "algorithm": "hmac-sha256",
                "key_sha256": __import__("hashlib").sha256(key).hexdigest(),
                "status": "active",
            }],
        }),
        encoding="utf-8",
    )
    entry = {
        "report_sha256": "b" * 64,
        "run_id": "run",
        "suite_id": "suite",
        "suite_sha256": "c" * 64,
        "subject": {"kind": "component", "id": "subject", "content_sha256": content_hash},
        "source_commit": "d" * 40,
        "decision": "qualified",
        "reviewed_by": "owner",
        "reviewed_at": "2026-07-19T00:00:00Z",
        "isolation_verifier": "trusted-broker",
        "key_id": "owner-2026",
    }
    entry["signature"] = attestation_signature(entry, key)
    registry = tmp_path / "external-attestations.json"
    registry.write_text(json.dumps({"schema_version": "4.2", "attestations": [entry]}), encoding="utf-8")

    loaded = load_eval_attestations(root, key, registry)
    assert loaded[0]["_authenticated"] is True


def test_empty_metrics_cannot_claim_real_promotion(tmp_path):
    root = Path(__file__).resolve().parents[1]
    report = _real_report(root)
    report["metrics"] = {}
    report_path = tmp_path / "forged-real.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid V4.2 Eval report"):
        eval_report_record(report_path, root)


def test_report_cannot_hide_subjective_suite_blind_review_requirement(tmp_path):
    root = Path(__file__).resolve().parents[1]
    report = _real_report(root)
    report_path = tmp_path / "forged-blind-review.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    suites = {
        (report["suite_id"], report["suite_sha256"]): {
            "kind": "suite",
            "value": {"cases": [{"case_id": "subjective", "subjective": True}]},
            "path": "fixture",
        }
    }

    with pytest.raises(ValueError, match="blind-review requirement"):
        eval_report_record(report_path, root, suites=suites)


def test_promote_report_must_meet_held_out_and_behavior_thresholds(tmp_path):
    root = Path(__file__).resolve().parents[1]
    report = _real_report(root)
    report["metrics"]["trigger"]["held_out"]["recall"] = 0.5
    report_path = tmp_path / "forged-threshold.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ValueError, match="not supported by passing paired evidence"):
        eval_report_record(report_path, root)


def test_plugin_evidence_rejects_mutated_canonical_manifest(tmp_path):
    root = Path(__file__).resolve().parents[1]
    plugin = tmp_path / "junwei-core"
    assert build_plugin_main([
        "--root", str(root), "--output", str(plugin), "--profile", "stable"
    ]) == 0
    manifest_path = plugin / ".codex-plugin/plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["author"]["name"] = "forged-author"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="canonical profile build"):
        plugin_record(plugin, root, "stable")
