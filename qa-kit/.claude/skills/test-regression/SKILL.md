---
name: test-regression
description: Regression testing on a new build - re-run failed/blocked TCs, TCs linked to fixed bugs and the high-priority smoke set, then classify fixed / still failing / new regression. Used by /qa ... regression.
user-invocable: false
---

# Regression testing

1. A build version is required (`build=`); ask if missing.
2. Build the list for the selected modules (`module=` or all):
   a. Previously failed/blocked: `read_testcases.py ... --filter rerun`
   b. Smoke: `read_testcases.py ... --filter all --priority high` (skip if `scope=failed-only`; needs a Priority column,
      otherwise use the module notes or ask Min for the smoke list)
   c. Fixed bugs: `read_testcases.py ... --filter all --bug-ids <bugs=>`
   De-duplicate and show counts; confirm before running.
3. Execute like test-functional.
4. Classify each TC against its previous status:
   - was fail/blocked, now pass -> Note "Fixed in <build>"
   - still fail -> Note "Still failing in <build>", keep the same Bug ID, no new bug
   - was pass, now fail -> NEW regression: new bug, severity >= major, title starts with "Regression:"
5. Write two files: `results.csv` (all rows except new regressions) and `regressions.csv` (new regressions only).
   Sheet update: results.csv with `--overwrite failed`; regressions.csv with `--overwrite all` (only after Min approves).
6. report.md adds a table: Fixed / Still failing / New regression.
