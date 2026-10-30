---
name: test-adhoc
description: Ad-hoc / exploratory testing session with a charter, time or action limit and a session log. Used by /qa ... adhoc.
user-invocable: false
---

# Ad-hoc / exploratory

Options: `focus=<area>` (ask if missing), `time=<minutes>` (default 20), `actions=<n>` (default 40).

1. Charter at the top of report.md: mission, area, risks to explore (from notes, SRS, recent bugs in `runs/`).
2. Explore with these heuristics: boundaries (empty, max length, emoji, Vietnamese text, special characters),
   interruptions (background, rotate, network off mid-action), rapid repeat taps / double submit,
   back navigation mid-flow, permissions denied, concurrent actions from the second device or account,
   stale state after relaunch.
3. Keep `session_log.md`: numbered action -> observation. Stop at the time or action limit.
4. results.csv: one row per finding (ID ADHOC_01...), status fail for bugs. No pass rows needed.
5. report.md: findings, areas covered, areas not covered, suggested new TCs (offer to add them via tc-gen).
