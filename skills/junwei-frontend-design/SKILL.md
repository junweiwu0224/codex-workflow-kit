---
name: junwei-frontend-design
description: Use when creating, redesigning, or polishing user-visible web or app UI, including landing pages, SaaS dashboards, product tools, mobile screens, design systems, visual references, responsive layout, component styling, and frontend QA. Trigger for frontend design, UI design, page/app/site/tool/game visuals, better taste, premium design, less generic AI design, product UI polish, redesign, mobile UI, landing page art direction, or generated frontend mockups/references.
risk: low
source_repo: personal-workflow-kit
source_type: curated-local
date_added: 2026-06-22
setup: none
write_surface: task-dependent
auth: none
network: none-by-default
status: active
---

# Junwei Frontend Design

## Goal

Use this skill as Junwei's design director layer for frontend work: distinctive taste, practical implementation, and real visual QA. It absorbs the strongest ideas from Anthropic `frontend-design` and Leonxlnx `taste-skill` without copying their source text: subject-grounded direction, one justified aesthetic risk, anti-template critique, composition variety, web/mobile separation, and implementation-friendly visual references.

## Workflow

Before editing UI, write or infer this compact direction in working notes:

```text
Subject:
Audience:
Screen job:
Mode: product-app | landing | dashboard | mobile | redesign | game/tool | visual-reference
Mood:
Palette roles:
Type roles:
Layout idea:
Signature:
Restraint:
QA risks:
```

Only show the direction to the user when it clarifies a meaningful choice. If a field is unknown and low-risk, make a concrete assumption and keep going. Ask only when the missing choice changes product, brand, data, legal/compliance posture, or paid/external assets.

## Mode Routing

Use one primary mode per task.

- Product app/tool: prioritize task flow, state clarity, density, controls, and repeated use. Avoid hero marketing composition.
- Dashboard/ops UI: use quiet structure, tabular numbers, clear filters, empty/loading/error states, and efficient scanning.
- Landing/brand page: make the first viewport a thesis for the product or offer. Use real product/place/object imagery when possible.
- Mobile UI: choose iOS, Android, or neutral cross-platform before designing. Respect safe areas, thumb reach, readable text, and consistent screen flows.
- Redesign: read the current implementation first. Diagnose generic patterns, then make targeted upgrades without changing behavior or tech stack.
- Game/interactive: let visuals serve feedback, legibility, and play.
- Visual reference/mockup: produce one focused reference per section, screen, or state; never compress a whole product into one vague poster.

Read `references/mode-playbook.md` for substantial or ambiguous tasks. Read `references/review-rubric.md` when the first pass feels generic. Use `references/validation-cases.md` as the fixed regression set when revising this skill.

## Non-Negotiables

- Build the actual usable experience first. Do not make a marketing landing page when the user asked for an app, tool, dashboard, game, or product surface.
- Ground design choices in product domain, audience, and first-screen job.
- Make one memorable design bet, then keep the rest controlled.
- Avoid generic AI fingerprints: purple-blue glow, floating blobs, glass cards everywhere, nested cards, fake stats strips, meaningless 01/02/03 labels, beige luxury by reflex, dark slate dashboards by reflex, and repeated left-text/right-image sections.
- Use the project's existing framework, styling system, components, icon library, and constraints unless there is a clear reason to extend them.
- Verify in a browser or rendered output whenever possible, at desktop and mobile sizes.

## Scope Boundaries

Do not force this skill onto pure backend, data, infrastructure, prose-only, or tiny copy changes unless user-visible UI materially changes. If the task only fixes existing behavior, preserve the current visual system and apply design guidance only where the fix affects layout, states, affordance, or clarity.

When another specialized skill applies, combine deliberately:

- Use `junwei-browser-automation` or `frontend-qa` for real browser verification and browser workflow automation.
- Use image generation only for bitmap references, visual assets, textures, product mockups, or hero/media direction that cannot be better built in code.
- Use `security-review` or `dependency-upgrade-review` for trust boundaries, auth, production config, new packages, or external services.
- Use this skill as the taste and interface layer, not as a replacement for tests, accessibility checks, browser verification, or product requirements.

## Recovery Loop

When a design feels weak, do not polish the weak version. Diagnose the failure:

- Generic: change the subject anchor, signature, or composition before tweaking colors.
- Pretty but unusable: reduce decoration and strengthen controls, hierarchy, and states.
- Broken on mobile: rebuild layout constraints before changing type or palette.
- Over-styled: remove the loudest effect and let typography, spacing, and one signature element carry the design.
- Conflicts with existing product: adapt to the local design system instead of imposing a new one.

## Verification

- Run the app or render the file.
- Inspect desktop and mobile.
- Check blank screens, console/resource errors, clipped text, overlap, scroll traps, missing states, broken controls, weak contrast, and one-note palettes.
- Compare the result to the design direction and remove one decorative choice that is not carrying meaning.
- If browser tooling is unavailable, state what was not visually verified and use targeted tests, DOM/API contracts, screenshots, or code review as weaker evidence.

## Output Shape

```text
Frontend design result:
- Mode:
- Design direction:
- Files changed:
- States covered:
- Browser/visual QA:
- Residual risks:
```

