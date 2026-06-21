# Review Rubric

Use this rubric after a first design plan or implementation pass. It is meant to catch generic output early.

Score each dimension from 0-2:

- 0: missing or generic
- 1: acceptable but not distinctive
- 2: strong, specific, and useful

## Core Scores

1. Subject specificity
   - The UI visibly belongs to this product/domain.
   - Copy, layout, imagery, controls, and data feel contextual.

2. First-screen job
   - The first viewport makes the user or buyer's next action obvious.
   - App/tool screens start with the work surface; landing pages start with the offer.

3. Visual signature
   - There is one memorable, justified design choice.
   - The signature does not damage readability or usability.

4. Token discipline
   - Colors have stable roles.
   - Typography has a clear hierarchy.
   - Spacing and surfaces are consistent.

5. Composition quality
   - Layout supports scanning and action.
   - Sections or screens do not repeat the same default pattern.
   - Fixed-format elements have stable dimensions.

6. Interaction states
   - Hover, focus, active, disabled, loading, empty, error, selected, and current states exist where relevant.
   - Feedback is visible but not noisy.

7. Content quality
   - Text is specific, active, and user-facing.
   - No lorem ipsum, repeated fake names, generic hype words, or filler metrics.

8. Accessibility and responsiveness
   - Text fits at mobile and desktop sizes.
   - Contrast, focus, semantic structure, and keyboard reach are considered.

9. Anti-template result
   - The result avoids common AI fingerprints unless the brief explicitly asked for them.
   - It does not look like the same default answer Codex would give for any SaaS prompt.

10. Verification
   - The UI was run or rendered.
   - Screenshots or direct inspection informed at least one revision when possible.

## Decision

- 18-20: ready after normal code/test checks.
- 14-17: revise the weakest two dimensions.
- 10-13: redo the design direction before polishing.
- 0-9: wrong mode or generic concept; restart from subject, audience, and first-screen job.

## Red Flags That Force Revision

- Page is a landing page when the user asked for an app/tool.
- All important content sits in nested cards.
- Text overlaps, clips, or becomes unreadable at mobile width.
- UI relies on a purple/blue gradient as its main identity.
- Assets are dark, blurred, cropped, or atmospheric when the user needs to inspect the real product.
- Controls lack states or affordances.
- The design cannot explain why it looks this way for this specific product.

