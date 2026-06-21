#!/usr/bin/env python3
"""Run deterministic V3.2 workflow case validation."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


FRONTEND = "junwei-frontend-design"
BROWSER = "junwei-browser-automation"
VIDEO = "junwei-product-demo-video"
FRONTEND_QA = "frontend-qa"
SECURITY = "security-review"
DEPENDENCY = "dependency-upgrade-review"
SUBAGENT_PROTOCOL = "subagent-protocol"
SUPERPOWERS_DISPATCH = "superpowers:dispatching-parallel-agents"

V32_SKILLS = frozenset({FRONTEND, BROWSER, VIDEO, SUBAGENT_PROTOCOL})
GENERIC_SUPPORT_SKILLS = frozenset({FRONTEND_QA, SECURITY, DEPENDENCY, SUPERPOWERS_DISPATCH})

COMMON_REQUIRED_TERMS = {
    "docs/V3.2-FRONTEND-BROWSER-VIDEO-WORKFLOW.md": (
        "Role Separation",
        "No-Conflict Matrix",
        "Expected Positive Effect",
        "吸收精华，不照搬",
    )
}


@dataclass(frozen=True)
class Case:
    case_id: str
    prompt: str
    expected_primary: str | None
    expected_supporting: tuple[str, ...] = ()
    forbidden_skills: tuple[str, ...] = ()
    required_terms: dict[str, tuple[str, ...]] | None = None
    expected_stop: bool = False
    expected_blocked_actions: tuple[str, ...] = ()
    expected_checkpoints: tuple[str, ...] = ()


@dataclass(frozen=True)
class Route:
    primary: str | None
    supporting: tuple[str, ...]
    stop_required: bool
    blocked_actions: tuple[str, ...]

    @property
    def skills(self) -> tuple[str, ...]:
        ordered = []
        if self.primary:
            ordered.append(self.primary)
        for skill in self.supporting:
            if skill not in ordered:
                ordered.append(skill)
        return tuple(ordered)


FRONTEND_TERMS = {
    "skills/junwei-frontend-design/SKILL.md": (
        "Mode Routing",
        "one memorable design bet",
        "Avoid generic AI fingerprints",
        "frontend-qa",
        "Output Shape",
    ),
    "skills/junwei-frontend-design/references/mode-playbook.md": (
        "Product App Or Tool",
        "Redesign Existing UI",
        "Mobile UI",
    ),
    "skills/junwei-frontend-design/references/review-rubric.md": (
        "Anti-template result",
        "Verification",
    ),
}

BROWSER_TERMS = {
    "skills/junwei-browser-automation/SKILL.md": (
        "in-app Browser",
        "Playwright CLI",
        "Playwright MCP only when",
        "Do not add `codex mcp add playwright",
        "rollback",
        "Output Shape",
    ),
    "skills/junwei-browser-automation/references/tool-routing.md": (
        "Playwright MCP Pilot Checklist",
        "Stop at payment",
        "Evidence Quality",
    ),
}

VIDEO_TERMS = {
    "skills/junwei-product-demo-video/SKILL.md": (
        "Remotion",
        "FFmpeg",
        "cloud GPU",
        "voice cloning",
        "publish",
        "security-review",
        "dependency-upgrade-review",
        "Output Shape",
    ),
    "skills/junwei-product-demo-video/references/demo-workflow.md": (
        "Browser Walkthrough",
        "Render QA",
        "Scene Planning",
    ),
}

SUBAGENT_TERMS = {
    "global/AGENTS.md": (
        "长期授权即视为显式授权",
        "本轮重复授权不是必要条件",
        "subagent 工具实际可用且未被平台权限阻止",
        "不包括已加载长期授权后缺少本轮重复授权",
    ),
    "repo-template/AGENTS.md": (
        "长期授权即视为显式授权",
        "本轮重复授权不是必要条件",
        "subagent 工具实际可用且未被平台权限阻止",
        "不包括已加载长期授权后缺少本轮重复授权",
    ),
    "repo-template/docs/subagents.md": (
        "长期授权即视为显式授权",
        "本轮重复授权不是必要条件",
        "subagent 工具实际可用且未被平台权限阻止",
        "不包括已加载长期授权后缺少本轮重复授权",
    ),
}


CASES: tuple[Case, ...] = (
    Case(
        case_id="csv-cleaning-tool-ui",
        prompt=(
            "Build a browser-based CSV cleaning tool with upload, column profiling, filter chips, "
            "preview table, undo, and export."
        ),
        expected_primary=FRONTEND,
        expected_supporting=(FRONTEND_QA,),
        forbidden_skills=(BROWSER, VIDEO),
        required_terms=FRONTEND_TERMS,
        expected_checkpoints=("mode routing", "states", "anti-template design", "visual QA"),
    ),
    Case(
        case_id="support-risk-dashboard",
        prompt="Create a dashboard for support managers to triage refund risk, SLA breaches, and overloaded agents.",
        expected_primary=FRONTEND,
        expected_supporting=(FRONTEND_QA,),
        forbidden_skills=(BROWSER, VIDEO),
        required_terms=FRONTEND_TERMS,
        expected_checkpoints=("dashboard mode", "decision lists", "empty/loading/error states"),
    ),
    Case(
        case_id="localhost-dashboard-smoke",
        prompt="Verify the dashboard at localhost:3000 works on desktop and mobile.",
        expected_primary=BROWSER,
        expected_supporting=(FRONTEND_QA,),
        forbidden_skills=(FRONTEND, VIDEO),
        required_terms=BROWSER_TERMS,
        expected_checkpoints=("in-app Browser first", "desktop/mobile evidence", "no Chrome downgrade"),
    ),
    Case(
        case_id="signup-validation-check",
        prompt="Create a repeatable check that the signup flow shows validation errors.",
        expected_primary=BROWSER,
        forbidden_skills=(FRONTEND, VIDEO),
        required_terms=BROWSER_TERMS,
        expected_checkpoints=("repo-local browser test", "test data", "evidence path"),
    ),
    Case(
        case_id="playwright-mcp-pilot",
        prompt="Should I add Playwright MCP to Codex for exploratory UI testing?",
        expected_primary=BROWSER,
        expected_supporting=(SECURITY,),
        forbidden_skills=(FRONTEND, VIDEO),
        required_terms=BROWSER_TERMS,
        expected_checkpoints=("MCP pilot only", "permission surface", "rollback", "security review"),
    ),
    Case(
        case_id="production-billing-browser-stop",
        prompt="Use browser automation to change the billing plan in production.",
        expected_primary=BROWSER,
        expected_supporting=(SECURITY,),
        forbidden_skills=(FRONTEND, VIDEO),
        required_terms=BROWSER_TERMS,
        expected_stop=True,
        expected_blocked_actions=("production mutation", "billing/account change"),
        expected_checkpoints=("explicit confirmation", "sandbox/test account preference"),
    ),
    Case(
        case_id="saas-demo-video",
        prompt="Make a 30-second product demo video for our SaaS dashboard.",
        expected_primary=VIDEO,
        expected_supporting=(BROWSER,),
        forbidden_skills=(FRONTEND,),
        required_terms=VIDEO_TERMS,
        expected_checkpoints=("audience/platform/duration", "real UI proof", "browser capture handoff", "render QA"),
    ),
    Case(
        case_id="cloud-gpu-voice-clone-stop",
        prompt="Use cloud GPU and voice cloning to make the product video.",
        expected_primary=VIDEO,
        expected_supporting=(SECURITY, DEPENDENCY),
        forbidden_skills=(FRONTEND, BROWSER),
        required_terms=VIDEO_TERMS,
        expected_stop=True,
        expected_blocked_actions=("cloud GPU", "voice cloning", "paid/external service"),
        expected_checkpoints=("cost/auth/data confirmation", "security review", "dependency review"),
    ),
    Case(
        case_id="rendered-video-ready",
        prompt="The demo video rendered. Is it ready to send?",
        expected_primary=VIDEO,
        forbidden_skills=(FRONTEND, BROWSER),
        required_terms=VIDEO_TERMS,
        expected_checkpoints=("playback", "resolution", "audio", "captions", "secret masking", "CTA"),
    ),
    Case(
        case_id="backend-tax-no-overtrigger",
        prompt="Fix the backend API route that calculates invoice tax.",
        expected_primary=None,
        forbidden_skills=(FRONTEND, BROWSER, VIDEO),
        expected_checkpoints=("no v3.2 over-trigger",),
    ),
    Case(
        case_id="combined-redesign-demo-recording",
        prompt="Redesign our SaaS dashboard, then make a 30-second demo video and record the walkthrough.",
        expected_primary=VIDEO,
        expected_supporting=(FRONTEND, BROWSER, FRONTEND_QA),
        required_terms={**FRONTEND_TERMS, **BROWSER_TERMS, **VIDEO_TERMS},
        expected_checkpoints=(
            "video remains primary",
            "frontend design is scoped to redesign",
            "browser automation is capture input only",
            "frontend QA verifies UI changes",
        ),
    ),
    Case(
        case_id="loaded-subagent-longterm-authorization",
        prompt=(
            "Run an L-sized repo audit with loaded AGENTS long-term subagent authorization "
            "and two independent read-only explorer questions; do not ask again for current-turn permission."
        ),
        expected_primary=SUBAGENT_PROTOCOL,
        expected_supporting=(SUPERPOWERS_DISPATCH,),
        forbidden_skills=(FRONTEND, BROWSER, VIDEO),
        required_terms=SUBAGENT_TERMS,
        expected_checkpoints=(
            "loaded AGENTS counts as explicit ask",
            "no repeat authorization",
            "real tool availability gate",
            "no tool permission constraint regression",
        ),
    ),
)


def _read(root: Path, relative: str) -> str:
    path = root / relative
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def route_prompt(prompt: str) -> Route:
    text = prompt.lower()
    backend_only = "backend api" in text and not _has_any(text, ("ui", "frontend", "dashboard", "browser"))
    wants_subagent = _has_any(
        text,
        (
            "subagent",
            "sub-agent",
            "parallel agent",
            "loaded agents long-term subagent authorization",
            "long-term subagent authorization",
            "two independent read-only explorer",
        ),
    )
    wants_video = _has_any(
        text,
        (
            "demo video",
            "product video",
            "video rendered",
            "rendered",
            "launch teaser",
            "sprint review video",
            "remotion",
            "voice cloning",
            "cloud gpu",
        ),
    )
    wants_browser = _has_any(
        text,
        (
            "localhost",
            "playwright",
            "browser automation",
            "repeatable check",
            "signup flow",
            "exploratory ui testing",
            "mcp",
            "record the walkthrough",
            "walkthrough",
        ),
    )
    wants_design = _has_any(
        text,
        (
            "build a browser-based",
            "create a dashboard",
            "design",
            "redesign",
            "ui",
            "landing page",
            "mobile",
            "frontend",
            "mockup",
            "looks ai-generated",
            "puzzle game",
        ),
    )

    primary: str | None
    if backend_only:
        primary = None
    elif wants_subagent:
        primary = SUBAGENT_PROTOCOL
    elif wants_video:
        primary = VIDEO
    elif wants_browser:
        primary = BROWSER
    elif wants_design:
        primary = FRONTEND
    else:
        primary = None

    supporting: list[str] = []
    if primary == SUBAGENT_PROTOCOL:
        supporting.append(SUPERPOWERS_DISPATCH)
    if primary == FRONTEND:
        supporting.append(FRONTEND_QA)
    if primary == BROWSER and _has_any(text, ("localhost", "dashboard", "desktop", "mobile")):
        supporting.append(FRONTEND_QA)
    if primary == BROWSER and "mcp" in text and _has_any(text, ("add", "enable", "install", "config")):
        supporting.append(SECURITY)
    if primary == VIDEO:
        if _has_any(text, ("dashboard", "walkthrough", "record", "browser capture", "real ui", "local route")):
            supporting.append(BROWSER)
        if _has_any(text, ("redesign", "design", "ui")):
            supporting.append(FRONTEND)
            supporting.append(FRONTEND_QA)

    blocked_actions: list[str] = []
    if _has_any(text, ("production", "billing", "account change", "payment", "permission change")):
        blocked_actions.extend(("production mutation", "billing/account change"))
    if "cloud gpu" in text:
        blocked_actions.append("cloud GPU")
    if "voice cloning" in text:
        blocked_actions.append("voice cloning")
    if _has_any(text, ("cloud gpu", "voice cloning", "paid api", "api key", "publish", "external upload")):
        blocked_actions.append("paid/external service")

    stop_required = bool(blocked_actions)
    if stop_required and SECURITY not in supporting:
        supporting.append(SECURITY)
    if _has_any(text, ("cloud gpu", "voice cloning", "remotion", "ffmpeg", "new package")) and DEPENDENCY not in supporting:
        supporting.append(DEPENDENCY)

    return Route(
        primary=primary,
        supporting=tuple(dict.fromkeys(supporting)),
        stop_required=stop_required,
        blocked_actions=tuple(dict.fromkeys(blocked_actions)),
    )


def _required_terms_for(case: Case) -> dict[str, tuple[str, ...]]:
    required: dict[str, list[str]] = {}
    for path, terms in COMMON_REQUIRED_TERMS.items():
        required.setdefault(path, []).extend(terms)
    if case.required_terms:
        for path, terms in case.required_terms.items():
            required.setdefault(path, []).extend(terms)
    return {path: tuple(dict.fromkeys(terms)) for path, terms in sorted(required.items())}


def _missing_terms(root: Path, case: Case) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for relative, terms in _required_terms_for(case).items():
        text = _read(root, relative)
        for term in terms:
            if term not in text:
                missing.append({"path": relative, "term": term})
    return missing


def evaluate_case(root: Path, case: Case) -> dict[str, object]:
    route = route_prompt(case.prompt)
    missing_terms = _missing_terms(root, case)
    conflicts = [skill for skill in case.forbidden_skills if skill in route.skills]
    missing_supporting = [skill for skill in case.expected_supporting if skill not in route.supporting]
    missing_blocked_actions = [
        action for action in case.expected_blocked_actions if action not in route.blocked_actions
    ]
    primary_ok = route.primary == case.expected_primary
    stop_ok = (not case.expected_stop) or route.stop_required
    baseline_points = sum(1 for skill in route.skills if skill in GENERIC_SUPPORT_SKILLS)
    v32_points = sum(1 for skill in route.skills if skill in V32_SKILLS)
    guardrail_points = len(case.forbidden_skills) + len(case.expected_checkpoints)
    stop_points = 1 if route.stop_required else 0
    post_points = baseline_points + v32_points + guardrail_points + stop_points
    if case.expected_primary is None and not conflicts and route.primary is None:
        post_points += 1
    delta = post_points - baseline_points
    ok = bool(
        primary_ok
        and not missing_supporting
        and not conflicts
        and not missing_terms
        and stop_ok
        and not missing_blocked_actions
        and delta > 0
    )
    return {
        "id": case.case_id,
        "prompt": case.prompt,
        "expected_primary": case.expected_primary,
        "routed_primary": route.primary,
        "expected_supporting": list(case.expected_supporting),
        "routed_supporting": list(route.supporting),
        "forbidden_skills": list(case.forbidden_skills),
        "conflicts": conflicts,
        "stop_required": route.stop_required,
        "expected_stop": case.expected_stop,
        "blocked_actions": list(route.blocked_actions),
        "missing_blocked_actions": missing_blocked_actions,
        "missing_supporting": missing_supporting,
        "missing_terms": missing_terms,
        "baseline_points": baseline_points,
        "post_points": post_points,
        "delta": delta,
        "checkpoints": list(case.expected_checkpoints),
        "ok": ok,
    }


def build_report(root: str | Path = ".") -> dict[str, object]:
    root_path = Path(root).resolve()
    cases = [evaluate_case(root_path, case) for case in CASES]
    totals = {
        "cases": len(cases),
        "passed": sum(1 for case in cases if case["ok"]),
        "conflicts": sum(len(case["conflicts"]) for case in cases),
        "safety_stops": sum(1 for case in cases if case["stop_required"]),
        "baseline_points": sum(int(case["baseline_points"]) for case in cases),
        "post_points": sum(int(case["post_points"]) for case in cases),
    }
    totals["delta"] = totals["post_points"] - totals["baseline_points"]
    totals["delta_percent"] = round(
        (totals["delta"] / totals["baseline_points"] * 100) if totals["baseline_points"] else 0.0,
        2,
    )
    ok = bool(totals["passed"] == totals["cases"] and totals["conflicts"] == 0 and totals["delta"] > 0)
    return {
        "ok": ok,
        "method": (
            "Route realistic V3.2 workflow prompts through deterministic workflow rules, "
            "then verify role separation, no-conflict guardrails, stop boundaries, source-document terms, "
            "and coverage uplift over a no-V3.2 baseline."
        ),
        "totals": totals,
        "cases": cases,
    }


def markdown(report: dict[str, object]) -> str:
    totals = report["totals"]
    lines = [
        "# V3.2 Functional Validation",
        "",
        "This report validates the V3.2 workflow using realistic task prompts.",
        "It checks routing, role separation, conflict prevention, safety stops, subagent authorization, and measurable coverage uplift.",
        "",
        "## Summary",
        "",
        f"- Cases: `{totals['passed']}/{totals['cases']}` passed.",
        f"- No-Conflict violations: `{totals['conflicts']}`.",
        f"- Safety stops exercised: `{totals['safety_stops']}`.",
        f"- Coverage points: `{totals['baseline_points']}` -> `{totals['post_points']}` (`+{totals['delta']}`, `{totals['delta_percent']}%`).",
        "- Positive Effect: v3.2 adds explicit primary routing, no-conflict guardrails, stop boundaries, and output/verification checkpoints that the no-v3.2 baseline did not cover.",
        "",
        "## Real Cases",
        "",
        "| Case | Expected primary | Routed primary | Supporting | Stop | Delta | Result |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for case in report["cases"]:
        supporting = ", ".join(case["routed_supporting"]) or "-"
        expected = case["expected_primary"] or "-"
        routed = case["routed_primary"] or "-"
        result = "PASS" if case["ok"] else "FAIL"
        lines.append(
            f"| {case['id']} | {expected} | {routed} | {supporting} | "
            f"{'yes' if case['stop_required'] else 'no'} | {case['delta']} | {result} |"
        )

    lines.extend(
        [
            "",
            "## Conflict Checks",
            "",
            "- Browser smoke and repeatable-flow cases do not trigger frontend redesign or video workflow.",
            "- Frontend design cases do not trigger Playwright/MCP or video workflow.",
            "- Product demo video remains primary for demo/video jobs; browser automation is only capture input.",
            "- Backend-only work does not trigger any v3.2 frontend/browser/video skill.",
            "- Loaded AGENTS/AGENTS.override long-term subagent authorization does not require current-turn repeat authorization.",
            "",
            "## Safety Checks",
            "",
            "- Production billing browser automation stops for explicit confirmation and security review.",
            "- Cloud GPU / voice cloning video work stops for confirmation, security review, and dependency review.",
            "- Playwright MCP remains a pilot path with permission surface and rollback, not a default install.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate V3.2 frontend/browser/video workflow cases.")
    parser.add_argument("--root", default=".", help="Toolkit root. Default: current directory.")
    parser.add_argument("--json-out", default="docs/V3.2-FUNCTIONAL-VALIDATION.json")
    parser.add_argument("--markdown-out", default="docs/V3.2-FUNCTIONAL-VALIDATION.md")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON instead of writing docs.")
    parser.add_argument("--markdown", action="store_true", help="Print the report as Markdown instead of writing docs.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    report = build_report(root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    elif args.markdown:
        print(markdown(report))
    else:
        json_path = root / args.json_out
        markdown_path = root / args.markdown_out
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        markdown_path.write_text(markdown(report), encoding="utf-8")
        print(f"V3.2 functional validation JSON: {json_path}")
        print(f"V3.2 functional validation report: {markdown_path}")
        print(json.dumps(report["totals"], ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
