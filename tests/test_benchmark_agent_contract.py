from scripts.benchmark_agent_contract import _metrics, _score_kit, build_report


def test_score_kit_counts_agent_contract_terms(tmp_path):
    kit = tmp_path / "kit"
    (kit / "repo-template/docs").mkdir(parents=True)
    (kit / "global").mkdir()
    (kit / "repo-template").mkdir(exist_ok=True)
    (kit / "scripts").mkdir()
    (kit / "docs").mkdir()

    subagents = (
        "Handoff Envelope\nReturn Envelope\nHistory/Input Filter\nCommand/Tool Risk Policy\n"
        "Step Budget / Stop Condition\nLifecycle Ledger\nNo-Dispatch Decision\n"
        "docs-only\nread-only local\nlocal write\ndev server/service\nnetwork/external read\n"
        "external write\ndestructive / production-risk\n"
        "NEEDS_CONTEXT\nBLOCKED\nSTOPPED_BY_BUDGET\n"
        "id\nrole/card\nread/write\ntarget\nprevious_status\nintegrated/discarded\n"
        "### read-only code mapper\n"
        "Handoff Envelope\nHistory/Input Filter\nCommand/Tool Risk Policy\n"
        "Step Budget / Stop Condition\nReturn Envelope\n"
    )
    (kit / "repo-template/docs/subagents.md").write_text(subagents, encoding="utf-8")
    (kit / "global/AGENTS.md").write_text("Handoff Envelope\nReturn Envelope\nLifecycle Ledger\n", encoding="utf-8")
    (kit / "repo-template/AGENTS.md").write_text("Handoff Envelope\nReturn Envelope\nLifecycle Ledger\n", encoding="utf-8")
    (kit / "scripts/verify_toolkit.py").write_text("Handoff Envelope\nReturn Envelope\n", encoding="utf-8")
    (kit / "scripts/render_usage_row.py").write_text(
        "subagent-contract\nagent-lifecycle-ledger\nagent-eval-evidence\n",
        encoding="utf-8",
    )
    (kit / "docs/V3.1-ADOPTION-EVIDENCE.md").write_text("Handoff Envelope\nReturn Envelope\n", encoding="utf-8")
    (kit / "docs/V3.1-AGENT-CONTRACT-BENCHMARK.md").write_text("Lifecycle Ledger\n", encoding="utf-8")
    (kit / "docs/V3.1-AGENT-RESEARCH-20.md").write_text(
        "\n".join(
            [
                "langchain-ai/langgraph",
                "microsoft/autogen",
                "openai/openai-agents-python",
                "browser-use/browser-use",
                "langfuse/langfuse",
            ]
        ),
        encoding="utf-8",
    )

    scores = _score_kit(kit)

    assert scores["Core contract terms in subagents.md"] == 7
    assert scores["Command/tool risk levels"] == 7
    assert scores["Stop-condition statuses"] == 3
    assert scores["Lifecycle ledger fields"] == 6
    assert scores["Prompt card contract coverage"] == 5
    assert scores["Usage pilot defaults"] == 3
    assert scores["Agent research source coverage"] == 5


def test_metrics_report_positive_delta_for_current_package(tmp_path):
    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    with __import__("tempfile").TemporaryDirectory() as temp_name:
        pre = __import__("pathlib").Path(temp_name) / "pre"
        post = __import__("pathlib").Path(temp_name) / "post"
        pre.mkdir()
        post.mkdir()
        for base in (pre, post):
            (base / "repo-template/docs").mkdir(parents=True)
            (base / "global").mkdir()
            (base / "repo-template").mkdir(exist_ok=True)
            (base / "scripts").mkdir()
            (base / "docs").mkdir()
        (pre / "repo-template/docs/subagents.md").write_text("V3.1 Prompt Contract\n", encoding="utf-8")
        (post / "repo-template/docs/subagents.md").write_text(
            "Handoff Envelope\nReturn Envelope\nHistory/Input Filter\nCommand/Tool Risk Policy\n"
            "Step Budget / Stop Condition\nLifecycle Ledger\nNo-Dispatch Decision\n",
            encoding="utf-8",
        )

        metrics = _metrics(pre, post)

    total_delta = sum(metric.delta for metric in metrics)
    assert total_delta > 0
    assert root.exists()


def test_build_report_uses_current_release_archive():
    root = __import__("pathlib").Path(__file__).resolve().parents[1]

    report = build_report(root, "2026.06.12.1")

    assert report["versions"]["pre-agent-contract"] == "2026.06.12.1"
    assert report["totals"]["post_agent_contract"] >= report["totals"]["pre_agent_contract"]
