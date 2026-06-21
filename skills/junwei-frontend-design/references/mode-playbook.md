# Mode Playbook

Use this file when a frontend task is substantial, ambiguous, or at risk of becoming generic.

## Product App Or Tool

Primary goal: repeated use without friction.

- Start with the work surface, not a hero.
- Put primary actions where the user naturally reaches them.
- Use icon buttons with tooltips for tools; text buttons for commands.
- Include selected, active, empty, loading, disabled, and error states when the flow implies them.
- Prefer dense but calm layouts for operational tools.
- Keep panels, tabs, filters, and tables predictable.
- Make destructive, irreversible, or costly actions visibly distinct from routine actions.
- Preserve local keyboard shortcuts and command surfaces when they already exist.
- Avoid decorative cards and marketing copy inside the tool.

## Dashboard Or Ops UI

Primary goal: scan, compare, decide, act.

- Make filters, time range, search, and current scope visible.
- Use tabular figures for metrics and aligned columns for comparison.
- Use charts only when shape matters; use tables when exact values matter.
- Reserve bright color for status and exceptions.
- Add useful empty states and skeletons that match final layout.
- Distinguish data absence, loading, stale data, permission failure, and real zero values.
- Keep chart legends, axis labels, units, and time zones visible when decisions depend on them.
- Avoid oversized KPI cards unless the dashboard genuinely has only a few numbers.

## Landing Or Brand Page

Primary goal: make the offer unmistakable and memorable.

- First viewport must signal the actual product, brand, place, or offer.
- Use a hero image, product view, interactive scene, or real asset when available.
- Let the next section peek into the viewport.
- Avoid split hero as default; consider centered image canvas, bottom-left copy over media, editorial offset, or product-first composition.
- Every section needs a job: hook, proof, explain, compare, convert.
- Put proof near claims: product screenshots, real metrics, customer names, examples, or concrete workflow evidence.
- Keep CTAs consistent in wording and outcome across the page.
- Do not repeat identical layouts across sections.

## Mobile UI

Primary goal: native-feeling clarity in a small viewport.

- Choose iOS, Android, or cross-platform neutral before designing.
- Respect safe areas, tab bars, sheets, thumb reach, and keyboard overlap.
- Keep text readable at normal screenshot size.
- Design flows, not isolated pretty screens.
- Maintain one visual system across all screens.
- Account for long labels, dynamic type, keyboard appearance, and one-handed use.
- Use native-feeling transition/state patterns before inventing decorative motion.
- Avoid phone-sized websites, tiny text, random chart filler, and excessive cards.

## Redesign Existing UI

Primary goal: improve quality without breaking behavior.

- Read the codebase before planning visual changes.
- Identify current design tokens, typography, spacing, surfaces, and interaction states.
- Upgrade in this order: type, color roles, spacing, states, component patterns, motion, assets.
- Preserve routing, data shape, event handlers, accessibility hooks, and existing tests.
- Prefer targeted changes over rewrites.
- Keep user-learned locations stable unless the current structure is the problem.
- If changing hierarchy, make before/after behavior traceable from the code and QA notes.
- If the current UI is already opinionated, refine its direction instead of replacing it with a different aesthetic.

## Game Or Interactive Surface

Primary goal: feedback, legibility, play.

- Make the primary play state immediately visible.
- Keep controls stable and reachable.
- Use strong feedback for hover, press, success, failure, score, progress, and reset.
- Prefer richer visuals than an ops UI, but avoid hiding state under decoration.
- Keep HUD, score, timer, inventory, and reset controls visually stable during play.
- Make losing, winning, pausing, and restarting obvious without reading instructions.
- Verify canvas/3D/media content is nonblank and correctly framed.

## Visual Reference Or Mockup

Primary goal: produce references Codex can implement.

- One reference per section, screen, or state.
- Do not create a single tall compressed page unless explicitly requested.
- Keep composition readable and implementation-friendly.
- Vary section rhythm and anchor points.
- For mobile, show screens in clean device frames only when it helps presentation; the screen content remains the hero.
- Use imagery, texture, and composition deliberately, not as random atmosphere.
- Annotate implementation-relevant choices in prose after generating references: palette roles, type roles, spacing rhythm, signature element, and likely assets.
- If a reference cannot be faithfully implemented with the current stack, simplify it before coding.

