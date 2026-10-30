---
name: qa
description: Entry point for every QA task in this kit. Use when Min types /qa, or asks to test a project, generate test cases, or run functional, system, integration, UI/UX, regression, UAT or ad-hoc testing on Android, iOS or web.
argument-hint: <project> <android|ios|web|all> <type> [key=value ...] [extra instructions]
---

# QA router

For working from the tracker's task list like a QC engineer (verify bugs, test cards, priorities), use the
`qc` skill (`/qc <project>`) instead. `/qa` runs one specific kind of test on demand.

Arguments: $ARGUMENTS

## 1. Parse
Format: `<project> <platform> <type> [key=value ...] [free text]`

- project: a folder in `projects/` (not `_template`)
- platform: `android` | `ios` | `web` | `all` (= every platform in profile, run one after another;
  `integration` uses several at once by design)
- type -> skill to follow:

| type | skill file |
|---|---|
| tc-gen | `.claude/skills/tc-gen/SKILL.md` |
| functional | `.claude/skills/test-functional/SKILL.md` |
| system | `.claude/skills/test-system/SKILL.md` |
| integration | `.claude/skills/test-integration/SKILL.md` |
| uiux | `.claude/skills/test-uiux/SKILL.md` |
| regression | `.claude/skills/test-regression/SKILL.md` |
| uat | `.claude/skills/test-uat/SKILL.md` |
| adhoc | `.claude/skills/test-adhoc/SKILL.md` |
| report | `.claude/skills/report/SKILL.md` (update sheet / push bugs for an existing run: `run=<folder>`) |

- Options (all optional): `module=MSG,LIVE` `ids=MSG_001..MSG_010` `filter=pending|failed|rerun|notpassed|all`
  `priority=high` `batch=10` `build=<version>` `env=<name>` `focus=<text>` `time=<minutes>` `actions=<n>`
  `kind=<tc kind>` `bugs=<ids>` `run=<run folder>`
- Free text after the options = extra instructions for this run (highest priority).

If project or type is missing or unknown: list projects (folders in `projects/` except `_template`) and the
types above, then stop and ask. If the platform is not in `profile.platforms`, say so and stop.

## 2. Load context, in this order
1. `projects/<project>/profile.yaml` (missing -> suggest `/new-project <name>` and stop)
2. `projects/<project>/notes.md`
3. `projects/<project>/modules/<ID>.md` for each selected module, if it exists
4. Platform skill: `.claude/skills/platform-mobile/SKILL.md` (android/ios) and/or `.claude/skills/platform-web/SKILL.md`
5. The type skill from the table

## 3. Preflight
- `.venv/bin/python scripts/check_setup.py --project <project> --platform <platform> --quick`
  (omit `--platform` for `all`). Fix or report blockers before testing.
- If `build=` is missing for a test run, ask Min once for the build/version; continue with "unknown" if he doesn't know.
- Create the run folder as defined in CLAUDE.md and an empty `results.csv` with the header.

## 4. Execute
Follow the type skill. Append to `results.csv` after every TC. Give a one-line progress update after each batch.

## 5. Close
1. Write `report.md` (template in the report skill).
2. Show Min in chat: pass/fail/blocked/skip counts, the bug list (local id, severity, title), items needing manual test.
3. Write approvals are asked ONCE at the start of the run, together with build/device (section 3): "Trong lần chạy
   này mình sẽ tự post bug lên <tracker> và cập nhật sheet, không hỏi lại - đồng ý?" Creating Trello bug cards is a
   standing approval. Approved -> push confirmed bugs right away as they are found (report skill, duplicates are never
   auto-created) and update the sheet at the end, without waiting for any command. Never ask Min to type
   "post B1 B2 B3" or similar. Not approved -> list the ready commands under "Pending approval" in report.md.
