# Validation Cases

Use these cases when revising this skill. They are regression prompts, not user-facing examples. A good revision should route each case to the right mode, avoid generic AI design, and preserve implementation discipline.

## Case 1: Product Tool

Prompt: "Build a browser-based CSV cleaning tool with upload, column profiling, filter chips, preview table, undo, and export."

Expected behavior:

- Route to product-app/tool, not landing.
- Start with the data work surface.
- Include upload, preview, filters, undo, export, empty, loading, error, and disabled states.
- Keep density practical and controls stable.

## Case 2: Ops Dashboard

Prompt: "Create a dashboard for support managers to triage refund risk, SLA breaches, and overloaded agents."

Expected behavior:

- Route to dashboard/ops UI.
- Show filters, time scope, status exceptions, tabular numbers, and decision-oriented lists.
- Distinguish no data from loading and zero values.
- Avoid oversized generic KPI cards as the whole page.

## Case 3: Landing Page

Prompt: "Design a landing page for a desktop sensor that tracks sourdough starter fermentation for bakeries."

Expected behavior:

- Route to landing/brand page.
- First viewport should reveal the product/category immediately.
- Use product-relevant imagery, material cues, proof, and process detail.
- Avoid generic AI SaaS gradients or abstract blobs.

## Case 4: Mobile Flow

Prompt: "Design a premium iOS habit app onboarding and home flow for shift workers."

Expected behavior:

- Route to mobile UI.
- Choose iOS-native premium mode.
- Show a logical flow across multiple screens, not isolated posters.
- Account for readable text, safe areas, one-handed use, and worker schedule context.

## Case 5: Existing Redesign

Prompt: "This React settings screen works but looks AI-generated. Redesign it without changing behavior."

Expected behavior:

- Route to redesign.
- Inspect existing framework, styling, components, event handlers, and tests first.
- Preserve behavior and user-learned locations where possible.
- Upgrade type, spacing, color roles, states, and component hierarchy.

## Case 6: Game Surface

Prompt: "Make a browser puzzle game interface with timer, score, hints, pause, win, and fail states."

Expected behavior:

- Route to game/interactive.
- Prioritize primary play state and stable controls.
- Include feedback for score, timer, hint, pause, win, fail, reset.
- Verify media/canvas/interaction surfaces if used.

## Case 7: Visual References

Prompt: "Generate frontend mockup references for an 8-section website for a boutique architecture studio."

Expected behavior:

- Route to visual-reference.
- Produce one reference per section or a clearly separated section set, not one compressed poster.
- Vary composition and anchor points.
- Summarize implementation-relevant tokens, spacing, imagery, and signature choices.

## Case 8: Should Not Over-Trigger

Prompt: "Fix the backend API route that calculates invoice tax."

Expected behavior:

- Do not apply this skill unless UI output changes.
- Preserve frontend scope and focus on backend validation.

## Case 9: Tiny UI Fix

Prompt: "The save button wraps to two lines on mobile."

Expected behavior:

- Apply only the relevant UI constraint guidance.
- Fix sizing, layout, and label behavior without redesigning the screen.
- Verify mobile width.

