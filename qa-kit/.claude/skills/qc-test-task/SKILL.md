---
name: qc-test-task
description: Playbook to test a feature/story/task card - read requirements, map or write test cases, run them (functional + UI/UX + integration as needed), log bugs linked to the card, decide pass/fail and update the card and test sheet. Used by the qc skill for test_feature tasks.
user-invocable: false
---

# Test a feature task

Run folder: `runs/<p>/<date>_task_<key>/`.

## 1. Analyze the task (like a QC in refinement)
- Read description, acceptance criteria, checklists, comments, attached designs/specs, linked docs in `docs/`.
- Identify: module(s), platforms, screens, roles/accounts, data needed, dependencies (backend, other features).
- Ambiguity that changes the expected result -> ask on the card (need_info) for that part; test what is clear.
- Write a 3-6 line test scope in the run's report.md: in scope, out of scope, risks.

## 2. Map test cases
1. Find existing TCs: card tc_ids, then `read_testcases.py --project <p> --module <m> --platform <pl> --filter all`
   and match by description keywords.
2. Gaps vs acceptance criteria -> draft new TCs with the tc-gen rules into `new_testcases.csv`
   (mark the source: Note or Description suffix "(<key>)"). Adding them to the sheet follows autonomy
   (append_testcases.py, dry-run first). Execute drafted TCs anyway - IDs can be assigned when appended.
3. Target size: every acceptance criterion covered by >= 1 positive and the obvious negative/boundary TC.

## 3. Execute
- Functional TCs first (test-functional rules), on each platform in scope.
- Add UI/UX checks if the task changes screens (test-uiux checklist, only the touched screens).
- Add integration checks if the feature involves another account/device/platform/backend (test-integration).
- 10-15 minutes of exploratory testing around the feature (test-adhoc heuristics) - real QCs always poke around.

## 4. Bugs
- One bug per root symptom, `"parent_task": "<key>"` in bugs.json; severity per report skill.
- Bugs go through push_bugs (dedup) per autonomy; the script comments the bug link on the parent card.

## 5. Decide and close
| Outcome | Condition | Tracker state |
|---|---|---|
| PASSED | all criteria met, no open bug >= major (minor ones allowed if `feature_pass_with_minor`) | `feature_passed`, comment lists minor bugs as known issues |
| FAILED | any criterion not met or any bug >= major | `feature_failed`, comment lists failing criteria + bug keys |
| NEED INFO | key behavior undefined / env not ready | `need_info`, comment with the question; report partial results |
Comment with the qc template, attach the 1-3 most useful screenshots, update the sheet for every executed TC.
