---
name: qc-verify-bug
description: Playbook to verify a bug the developer marked fixed - reproduce with the original steps on the new build, check related areas for regressions, then close as verified or reopen with evidence. Used by the qc skill for verify_bug tasks.
user-invocable: false
---

# Verify a fixed bug

Input: task.json from `tasks.py show` (description, dev comments, attachments, linked TCs), build under test.
Run folder: `runs/<p>/<date>_verify_<key>/` (results.csv, bugs.json, evidence/, report.md as usual).

## 1. Understand before touching the device
- Original symptom, steps, expected, platform(s), device/OS, frequency (from description + first comments + attachments).
- Dev fix note: what was changed, in which build/version, any side effects mentioned. If no fix note and no
  build info -> comment asking which build contains the fix (need_info) unless the card is clearly in the fixed list
  for the current build.
- Build check: build on device must be >= the fix build. Older -> need_info ("build X on device, fix is in Y").
- Platforms to verify: those in the bug + every platform where the same code path exists (iOS and Android both,
  if the bug is in shared logic/backend). Reported platform first.

## 2. Reproduce the original steps exactly
- Same data/conditions as reported (account type, network, message length, app state).
- Run the steps the number of times needed for confidence: always-reproducible bug -> 2 runs;
  intermittent (frequency like 1/3) -> at least 5 runs.
- Screenshot the key step and the final state each time; Android logcat if it was a crash.

## 3. Check around the fix (regression radius)
- Linked TCs (task tc_ids, or sheet rows whose Bug ID column holds this key:
  `read_testcases.py --project <p> --platform <pl> --module all --filter all --bug-ids <key>`).
- Up to `workflow.regression_radius` related TCs in the same module (same screen/flow), plus 2-3 quick
  exploratory variations of the fixed scenario (boundary, interruption, other account).

## 4. Decide
| Outcome | Condition | Tracker | Sheet (linked TCs) |
|---|---|---|---|
| VERIFIED | not reproducible in all runs on all checked platforms, expected behavior observed | comment + state `verified` | pass, Note "Verified <key> on <build>" (`--overwrite failed`) |
| REOPENED | still reproducible (any run) on a platform the fix claims to cover | comment with x/y frequency, new evidence, build, state `reopened` | stays fail, Note "Still failing on <build>" |
| PARTIAL | fixed on one platform, not on another / main case fixed, variant not | reopen (same bug) and state which part fails | fail with note |
| NEW ISSUE | original bug fixed but a different symptom appears | verify this bug; log a NEW bug (parent_task = this key, title not "Reopen") | new bug id in Bug ID |
| NEED INFO | cannot reach the precondition, build mismatch, unclear steps | comment the exact question, state `need_info` | blocked note |

Never verify on "looks fine" - the expected result from the bug must be observed. Never reopen for a
different symptom (that is a new bug). Reopen and new bugs follow the autonomy rules in the qc skill.

## 5. Record
- results.csv rows for the original TC(s) and regression TCs (Platform per row).
- bugs.json only for NEW ISSUE bugs, each with `"parent_task": "<key>"`.
- Comment file `runs/<p>/_shift/<date>/tasks/<key>/comment.md` (qc template), then
  `tasks.py update --task <key> --state <verified|reopened|need_info> --comment-file ... --attach <evidence>`.
