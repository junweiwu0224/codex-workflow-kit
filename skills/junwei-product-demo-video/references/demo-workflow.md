# Product Demo Video Workflow

Use this reference when a demo video task is more than a short script.

## Intake

Collect or infer:

- Product and feature.
- Audience and platform.
- Duration and aspect ratio.
- Product URL or local route.
- Safe demo account/data.
- Brand colors, logo, typography, and voice.
- Required claims and proof.
- Existing screenshots, recordings, or product assets.
- Voiceover, captions, and music expectations.
- Output format and destination.

## Format Patterns

### Browser Walkthrough

Best for real product flows.

- Use `junwei-browser-automation` for repeatable capture inputs.
- Script every step before recording.
- Keep cursor movement slow enough to read.
- Mask secrets and private data.
- Use captions or callouts for key actions.

### Motion-Graphic Explainer

Best when the product has limited UI or a conceptual value prop.

- Keep claims concrete.
- Use product screenshots or schematic UI only when true UI is unavailable.
- Avoid stock footage as proof.
- Make every scene explain one idea.

### Sprint Review

Best for internal engineering/product updates.

- Use real shipped changes, issue IDs when appropriate, before/after clips, and concise narration.
- Avoid marketing hype.
- Include known limitations or next steps when useful.

### Launch Film

Best for public announcement or homepage hero.

- Lead with the product or offer.
- Use proof near claims.
- End with one CTA.
- Keep tone aligned with brand and audience.

## Scene Planning

Default 30-45s structure:

1. Hook: one concrete product outcome.
2. Context: the pain or old workflow.
3. Walkthrough: the product action.
4. Proof: result, saved time, comparison, or concrete example.
5. CTA/handoff: what the viewer should do next.

Rules:

- One idea per scene.
- One primary visual focus per scene.
- Narration should not describe what is already obvious on screen unless it adds context.
- Captions must be readable on the target platform.
- Keep transition style subordinate to product clarity.

## Render QA

Before delivery:

- Watch the full render.
- Confirm MP4 exists and plays.
- Confirm resolution/aspect ratio matches the target.
- Confirm audio stream exists when required.
- Confirm captions are readable and timed.
- Confirm browser captures are not blurry, cropped, or leaking secrets.
- Confirm product claims match what the UI shows.
- Confirm final CTA is present and consistent.

## Escalation

Use `dependency-upgrade-review` when adding video packages, Remotion, FFmpeg wrappers, TTS clients, or lockfile changes.

Use `security-review` when recordings include auth, internal data, customer data, private dashboards, upload flows, or external publishing.

Use `release-readiness` when shipping a reusable video toolkit, template pack, or installable artifact.

