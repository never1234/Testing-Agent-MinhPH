---
name: report
description: Update the project's test sheet (Excel or Google Sheet) with run results, log or push bugs to a sheet, Jira, Trello or Mantis with duplicate checks, and write report.md. Use after any test run, or whenever Min says update sheet, update report, log bugs, push bugs, or /report.
argument-hint: <project> run=<runs/... folder>
---

# Reporting

Where results and bugs go is decided per project in `profile.yaml`:
- `testcases.source`: `excel` or `gsheet` -> results are written back into the same sheet
- `bug_tracker.type`: `sheet` | `trello` | `jira` | `mantis` | `none`

## bugs.json schema
```json
{
  "project": "shopx", "run": "2026-10-08_functional_android_MSG", "build": "1.4.2",
  "bugs": [{
    "local_id": "B1",
    "title": "Message sent while offline is lost after reconnect",
    "module": "MSG", "platform": "android",
    "severity": "critical|major|minor|trivial",
    "tc_ids": ["MSG_012"],
    "preconditions": "A and B are friends, A is offline",
    "steps": ["Turn off wifi on A", "Send 'hello' to B", "Turn wifi on"],
    "expected": "Message is sent after reconnect",
    "actual": "Message stays with a red error icon, never delivered",
    "frequency": "2/2",
    "device": "Xiaomi 14T Pro, HyperOS 2",
    "evidence": ["evidence/MSG_012_android_1.png"],
    "parent_task": "#45",
    "action": "push", "duplicate_of": "", "force_create": false,
    "remote_id": "", "remote_url": ""
  }]
}
```
- `title`: the symptom only; the script adds `[Platform][Module]` from `title_template`.
- Severity: critical = crash, data loss, security, core flow blocked; major = feature broken, no workaround;
  minor = broken with workaround or edge case; trivial = cosmetic.
- `evidence` paths are relative to the run folder.
- `parent_task` (optional): the tracker task/card the bug was found on; push_bugs links the new bug there.

## Approval gate (always)
Nothing is written to a sheet or tracker before Min approves in this session (inside /qc: per `workflow.autonomy`).
Approval is asked ONCE, at the start of the run (or /qc kickoff), and covers every write it lists for the whole run;
creating Trello bug cards is a standing approval. Once approved, do the writes right away as results come in: no
per-bug question, no waiting for "post B1 B2 B3" or any other typed syntax. Dry-run first, inline, and only stop when
it shows a problem (possible duplicate, invalid row).

## Order: bugs first, then the sheet
So the Bug ID column receives real tracker ids instead of B1, B2.

### 1. Push bugs
1. `.venv/bin/python scripts/push_bugs.py --project <p> --bugs <run>/bugs.json --dry-run`
2. No possible duplicate -> push it (approved writes). Possible duplicate -> do not create; add a "Reoccurs on ..."
   comment to the existing card when comments are approved, else list it for Min in report.md with the candidates.
   Only when this report skill runs on its own without approval, show Min each bug and let him decide per bug.
3. Record the decisions in bugs.json: `"action": "skip"`, `"duplicate_of": "#123"`, or `"force_create": true`
   (needed to create a bug that has a possible duplicate).
4. `.venv/bin/python scripts/push_bugs.py --project <p> --bugs <run>/bugs.json --results <run>/results.csv [--only B1,B3]`

### 2. Update the test sheet
1. `.venv/bin/python scripts/update_results.py --project <p> --results <run>/results.csv --dry-run`
   (regression: add `--overwrite failed`; new regressions file: `--overwrite all`)
2. Show the summary: updated / kept_existing (human status not overwritten) / not_found (IDs not in the sheet,
   e.g. ADHOC_/SYS_ rows - normal) / invalid.
3. Approved -> run without `--dry-run` right away. Excel: the file must be closed; a backup goes into the run folder.

## report.md template
```markdown
# <Project> - <type> test report
- Run: <run folder> | Date: <date> | Build: <build> | Env: <env>
- Platform/devices: <...> | Scope: <modules / ids / focus>
- Tester: Claude QA agent (reviewed by Min)

## Summary
| Platform | Total | Pass | Fail | Blocked | Skip | Pass rate |
|---|---|---|---|---|---|---|
(pass rate = pass / (total - skip))

## Bugs
| Local | Tracker | Severity | Title | TC |
|---|---|---|---|---|

## Failed / blocked details
- <ID>: <actual / reason>

## Needs manual testing
- <ID>: <why>

## Observations & risks
- ...
```
Add the type-specific sections required by the type skill (regression table, UAT sign-off, ad-hoc charter...).
