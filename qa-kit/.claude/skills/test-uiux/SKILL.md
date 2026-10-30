---
name: test-uiux
description: UI/UX testing - compare screens with designs and check layout, copy, states, consistency, accessibility and usability heuristics on mobile and web. Used by /qa ... uiux.
user-invocable: false
---

# UI/UX testing

## Inputs
- Designs: `projects/<p>/docs/design/<screen>.png` and/or `docs/ui-guidelines.md`.
  If none, test against the heuristics only and say so in the report.
- Scope: screens of `module=` or the list in `modules/<ID>.md`; if unclear, propose a list and ask.

## Per screen (each platform; web: each viewport)
1. Screenshot. 2. Compare with the design: layout/spacing/alignment, colors, typography, icons, exact copy,
   states (empty/loading/error/disabled). 3. Heuristic checklist:
   - Truncated/overlapping text, Vietnamese diacritics, long names, number/date formats
   - Touch targets roughly >= 44pt (iOS) / 48dp (Android), estimated from element bounds
   - Consistency across screens and between iOS/Android/web (terms, icons, back behavior)
   - Feedback: loading indicators, success/error messages, why a button is disabled
   - Dark mode and large font scaling (ask Min before changing device settings; restore after)
   - Icon-only buttons have accessibility labels in the element tree
   - Usability: system status visible, errors prevented, recognition over recall

## Recording
- One row per screen check: ID `UI_<SCREEN>_<nn>`.
- Severity: minor/trivial unless it blocks a task. Design mismatch bugs include the design image path + screenshot.
- Quota: cap around 30 screenshots per session (or `time=`); tell Min if more are needed.
