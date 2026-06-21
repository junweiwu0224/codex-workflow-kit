---
name: junwei-product-demo-video
description: Use when planning, recording, composing, rendering, or reviewing product demo videos, SaaS walkthrough videos, launch films, sprint review demos, feature showcase clips, narrated browser demos, Remotion videos, product video scripts, demo storyboards, voiceover/audio planning, or video asset intake. Trigger for product demo, demo video, walkthrough recording, Remotion render, launch video, marketing reel, browser demo capture, or video QA.
risk: medium
source_repo: personal-workflow-kit
source_type: curated-local
date_added: 2026-06-22
setup: optional-local-tools
write_surface: project-artifacts
auth: task-dependent
network: local-by-default
status: pilot
---

# Junwei Product Demo Video

## Goal

Use this skill to turn a product or feature into a concise, credible demo video workflow. It distills high-value ideas from `digitalsamba/claude-code-video-toolkit`: project lifecycle, browser demo recording, Remotion-style composition, scene review, brand profiles, voice/music/tool separation, and final render QA. It does not vendor the external toolkit or default-enable cloud GPU/API services.

## Default Position

Prefer a local, evidence-first production path:

1. Product truth: real UI, real workflow, real claims.
2. Story structure: hook, problem/context, walkthrough, proof, CTA or handoff.
3. Asset intake: logo, brand colors, fonts, screenshots/recordings, copy, voice, music, aspect ratio, duration.
4. Capture: use `junwei-browser-automation` for browser walkthrough inputs when needed.
5. Compose: use the repo's existing video stack if present; otherwise recommend Remotion only when the user wants generated/rendered video artifacts.
6. Review: verify audio, captions, resolution, pacing, scene order, product accuracy, and sensitive data masking.

Read `references/demo-workflow.md` for the full workflow and `references/validation-cases.md` when revising this skill.

## Source Intake Position

`digitalsamba/claude-code-video-toolkit` is a strong inspiration and repo-local pilot candidate, not a default global install. Current source evidence: MIT license, active toolkit, skills for Remotion, FFmpeg, Playwright recording, frontend design, AI audio/image/video tools, commands such as `/video`, `/record-demo`, `/scene-review`, `/design`, `/brand`, and project tracking through planning/assets/review/audio/editing/rendering/complete. It may involve optional Python packages, Node tooling, FFmpeg, cloud GPU providers, paid APIs, external storage, voice cloning, and publishing flows.

Do not run `/setup`, deploy cloud GPU, configure API keys, publish to YouTube, clone voices, or install optional AI/video dependencies unless the user explicitly asks and the risk/cost is clear. Use `security-review` before sensitive recordings, auth/session capture, internal dashboards, customer data, external uploads, cloud services, or publishing.

## Workflow

1. Define the video job.
   - Audience, platform, duration, aspect ratio, one desired action, and where it will be used.

2. Intake assets and constraints.
   - Product URL or local app route, safe demo account/data, logo, colors, fonts, screenshots, existing recordings, script draft, voice/music preferences, brand restrictions.

3. Choose format.
   - Browser walkthrough, motion-graphic explainer, sprint review, launch film, vertical reel, or hybrid.

4. Plan scenes.
   - One idea per scene.
   - Every claim needs product evidence, UI proof, or a concrete example.
   - Keep scenes short and renderable.

5. Capture or create assets.
   - Use local browser automation or existing app tests for repeatable captures.
   - Mask secrets, customer data, tokens, emails, and internal URLs.
   - Prefer real product UI over abstract stock footage.

6. Compose and render.
   - Use project-local tooling first.
   - If adding Remotion or video dependencies, treat it as a dependency change and verify install/build/render.
   - Keep source assets, scripts, captions, and render output organized.

7. Review and iterate.
   - Watch the render end to end.
   - Check audio stream, captions, frame size, pacing, cursor timing, visual hierarchy, product accuracy, and CTA.
   - Fix the highest-impact issue, re-render, and re-check.

## Boundaries

- Do not publish externally, upload to cloud storage, configure paid APIs, clone voices, or deploy cloud GPU without explicit confirmation.
- Do not fabricate product claims, customer names, metrics, or logos.
- Do not expose secrets, real customer data, private URLs, access tokens, or internal dashboards in recordings.
- Do not turn every product demo into a glossy ad. Match the use case: sales, onboarding, sprint review, investor update, support article, or launch.
- Do not install the DigitalSamba toolkit globally; pilot repo-locally only when the project actually needs video production infrastructure.

## Verification

- For scripts/storyboards: check audience, duration, scene count, product truth, and CTA.
- For captured browser demos: check viewport, cursor path, sensitive data masking, and repeatability.
- For rendered video: verify MP4 exists, plays, has expected resolution, has audio if required, has captions when required, and shows the intended product states.
- For dependency/tooling changes: run the repo's install/build/render smoke and use `dependency-upgrade-review` if packages or lockfiles changed.

## Output Shape

```text
Product demo video result:
- Video job:
- Format:
- Assets/captures:
- Scene plan:
- Render/checks:
- External services/costs:
- Residual risks:
```
