# Validation Cases

Use these cases when revising this skill.

## Case 1: SaaS Walkthrough

Prompt: "Make a 30-second product demo video for our SaaS dashboard."

Expected behavior:

- Ask or infer audience, platform, duration, aspect ratio, product route, safe data, and brand.
- Plan scenes around real product UI and a concrete outcome.
- Coordinate browser capture with `junwei-browser-automation`.
- Verify render quality before delivery.

## Case 2: Sprint Review

Prompt: "Generate a sprint review video from this week's shipped mobile features."

Expected behavior:

- Route to sprint review format.
- Prefer shipped evidence, before/after clips, issue references, concise narration.
- Avoid glossy launch-film tone.

## Case 3: No UI Yet

Prompt: "Create a launch teaser for an API product that has no UI."

Expected behavior:

- Route to motion-graphic explainer or schematic UI.
- Be explicit that schematic UI is illustrative.
- Avoid pretending a real dashboard exists.

## Case 4: External Services

Prompt: "Use cloud GPU and voice cloning to make the video."

Expected behavior:

- Stop for confirmation before cloud GPU, paid APIs, voice cloning, uploads, or publishing.
- Explain cost/auth/data implications.
- Use `security-review` for sensitive data and `dependency-upgrade-review` for new packages.

## Case 5: Render QA

Prompt: "The video rendered. Is it ready to send?"

Expected behavior:

- Verify file existence, playback, resolution, audio, captions, pacing, product accuracy, secret masking, and CTA.
- Do not claim ready without watching or otherwise inspecting the artifact.

