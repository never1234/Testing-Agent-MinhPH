---
name: qc
description: Work one shift as the project's senior QC engineer - kickoff (collect everything needed from Min up front, one message), then work autonomously until the time budget ends - verify fixed bugs, test features, regression, exploratory, write/update test cases, update the tracker and test sheet - and hand over a shift report. Use for /qc, or when Min says "làm việc như QC", "check task", "verify bug", "làm task hôm nay", "start shift".
argument-hint: <project> [platform] [duration e.g. 30m|1h|1h30m] [minutes=120] [only=verify_bug|test_feature|write_tc|regression] [task=#45,#46] [build=x.y.z] [resume]
---

# QC shift - behave like a real senior QC engineer

Arguments: $ARGUMENTS
Parse: first word = project (required), optional platform (android|ios|web), options `minutes=`, `only=`,
`task=` (work only these keys), `build=`, `resume` (continue today's shift). Free text = extra instructions.

**Duration (time budget of this session):** an optional token matching `^(\d+h)?(\d+m)?$` (case-insensitive,
not empty), e.g. `30m`, `1h`, `2h`, `1h30m`, anywhere after the project. `h` = hours, `m` = minutes -> convert to
minutes (`1h30m` = 90). It means "work as QC for this long, then stop and report". Same as `minutes=N`; if both are
given, the duration token wins (say so). Neither given -> old behaviour: `profile.workflow.shift_minutes`, else 120.
Reject 0 or more than 8h (480 min) and ask Min. With `resume`, the duration is the budget of this new session.

Load, in order: `projects/<p>/profile.yaml`, `notes.md`, `CLAUDE.md` rules, then the platform skill(s) when testing.
Shift folder: `runs/<p>/_shift/<YYYY-MM-DD>/` holds `queue.json`, `kickoff.md`, `plan.md`, `log.md`, `actions.log`,
`questions.md`, `report.md`, `tasks/<key>/` (task.json, attachments, comment drafts). Per-task test runs still go to
`runs/<p>/<run-id>/`.

## The shape of a shift
1. **Kickoff (interactive, before the clock starts)** - find everything that could stop you later and ask Min for
   all of it in ONE message: device, build, accounts, environment, test data, access, computer permissions,
   unclear tasks, write approvals. This is the only time you ask Min anything.
2. **Autonomous run (the clock runs)** - work until `Wrap-up at` without asking or waiting. New questions go to
   `questions.md`; approved writes (bugs, card updates, comments, sheet) are done right away as each result comes in,
   never batched for a later "post B1 B2" command; writes that are not approved go to "Pending approval"; a blocker
   makes you switch work, not stop.
3. **Handover** - finish the report before the deadline.

**Clock:** the budget starts when the autonomous run starts (Min's "go", Kickoff step 6), not when /qc is typed.
At that moment run `date '+%Y-%m-%d %H:%M'` and record `Start`, `Budget`, `Deadline` (= start + budget) and
`Wrap-up at` (= deadline - reserve; reserve = 10% of the budget, min 5, max 15 min) at the top of `plan.md` and as the
first line of this session in `log.md`. Re-check with `date` (never estimate from memory) before each task and after
each long step.

## Phase 1 - Kickoff: readiness check (aim <= 10 min, before the clock)
1. `resume` or `runs/<p>/_shift/<today>/log.md` exists -> read log.md + plan.md + questions.md, note what is
   done/left, then still do steps 3-6 (readiness can change) and carry the left tasks into the new plan.
2. Read the last handover: newest `runs/<p>/_shift/*/report.md` (carry-over, blocked items, bugs waiting for fix,
   open questions and whether Min answered them, what Min was asked to prepare).
3. **Check every dependency yourself first** - only ask Min for what you cannot check or fix alone:
   | Area | How to check | Typical ask to Min |
   |---|---|---|
   | Tools / venv | `.venv/bin/python scripts/check_setup.py --project <p> --quick [--platform <pl>]` | install / fix setup |
   | Device / browser | platform skill: adb devices, simulator, Chrome extension / browser pane | connect phone, unlock, open app |
   | Build under test | `build=`, read from device/site, compare with tasks' fix builds and dev comments | install build X / which build to test |
   | Environment | URL reachable, which env (staging/prod), maintenance windows | env URL, VPN, whitelisting |
   | Accounts | `scripts/get_account.py` for each role the planned tasks need (never print secrets) | create/share account, OTP device |
   | Test data | data the tasks need (orders, songs, groups, payment sandbox, files) | seed data, sandbox cards |
   | Tracker / sheet | `tasks.py pull` works, test sheet readable (`read_testcases.py ... --filter all`) | access / token |
   | Specs | task description, `docs/`, designs - enough to know the expected result | answer the open question |
   | Computer permissions | try each tool the plan needs once (see "Permissions to request at kickoff") | approve / turn on / connect it now |
   | Fast paths | deep link scheme / page URLs, Android main activity, simulator allowed?, last report "Fast paths learned" | allow animations off on Android for this run? |
4. Pull the queue: `.venv/bin/python scripts/tasks.py pull --project <p> [--platform <pl>] --minutes <budget>`
   (budget = duration minus wrap-up reserve). `only=` / `task=` -> filter afterwards. Read every planned task
   (`tasks.py show ... --download`) NOW, so ambiguities and missing preconditions surface at kickoff, not mid-run.
5. Build the plan (Phase 2 rules), including the fallback work for leftover time.
6. **Send ONE kickoff message** (Vietnamese, short; save the same text to `kickoff.md`):
   - Readiness: one line per area - OK / missing (what exactly).
   - "Cần bạn làm trước khi chạy:" numbered actions for Min (connect device X, install build Y, give account Z...).
   - Questions about tasks (max 5, each answerable in one line, each with your default:
     "Nếu bạn không trả lời, mình sẽ hiểu là ...").
   - The plan table + fallback work + what will NOT be done and why.
   - "Quyền trên máy cần cấp ngay:" every computer permission the plan needs that is not already working (list in
     "Permissions to request at kickoff"). Trigger the approval prompts NOW (connect the device, start Remote Control,
     call one harmless action per tool) so Min clicks them all before the clock starts, not mid-run.
   - Write approvals for the whole run, as ONE list Min approves with one word: "Trong ca này mình sẽ tự làm, không
     hỏi lại: tạo bug card mới, cập nhật/comment card, chuyển trạng thái, reopen bug, cập nhật sheet, thêm TC mới."
     Standing approvals already count (creating Trello bug cards is a standing approval in project memory) - mark
     them "đã duyệt sẵn" and do not ask again. Min can strike items in the reply ("go, không reopen").
   - Last line: "Trả lời 'go' (kèm sửa nếu có) là mình bắt đầu chạy <duration>: tự post bug và cập nhật card ngay khi
     có kết quả, không hỏi thêm cho tới khi xong."
   "go" (or "ok", "chạy", "được") without exclusions = every write in that list is approved for the whole run.
   Then wait for Min's reply. When it arrives: apply the answers, re-check what Min fixed (device, build...),
   drop/replace tasks whose blocker is still there, start the clock, post one line
   "Bắt đầu HH:MM, kết thúc HH:MM, <n> task" and enter Phase 3.
   Nothing to ask and Min wrote "chạy luôn"/"không cần hỏi" in the command, or `autonomy: full` -> post the kickoff
   message as information and start immediately.

## Phase 2 - Plan (risk-based, fitted to the budget)
Priority rules (tasks.py orders by them; you may adjust with a stated reason):
1. P0 (blocker/critical/hotfix) first, whatever the type.
2. Overdue / due today.
3. Higher priority (P1 > P2 > P3).
4. Same priority: verify fixed bugs before new features (fast, unblocks devs), then regression, features, writing TCs.
5. Earlier due date, then older task.
6. Waiting labels (Blocked / Need info) are not planned; mention them.
Group tasks on the same module/platform when it saves app restarts, but never move a P0/overdue task later.

**Smoke first:** new build (different from the last handover) -> plan a 10-15 min smoke check of the critical paths
(launch, login, main flows of high-priority modules) as task #0. Smoke fails on a core flow -> log a critical bug
first, then re-plan around what is still testable.

**Fit the budget:** sum of `Est` <= budget minus wrap-up reserve. A P0 task that does not fit still goes first
(say it may overrun or be split). Short budget (<= 30m): 1-2 quick tasks or one task split into a clear first part;
never start something that cannot reach a usable result in time.

**Fallback work (never idle):** if the queue is empty, finishes early, or a task gets blocked mid-run, take the next
item from this ladder, highest first, each time-boxed:
1. Regression around bugs fixed in this build / recently changed modules (`regression_radius` TCs per area).
2. Re-run TCs that are fail/blocked in the sheet whose bug may be fixed, or that were blocked by something now ready.
3. Execute never-run TCs of high-priority modules (`priority: high` in profile).
4. Exploratory session (20-30 min charter: "Explore <area> with <resource> to discover <risk>"), test-adhoc
   heuristics, session notes in the run folder. Rotate areas across shifts (check old reports).
5. Write TCs for modules/flows with no or thin coverage (tc-gen), or review existing TCs for outdated steps.
6. Read specs/designs for gaps and contradictions -> add to `questions.md`.
Put the fallback items you expect to use in the plan as "Nếu còn thời gian".

Write `plan.md` (header: Start / Budget / Deadline / Wrap-up at, filled when the clock starts):
| # | Task | Type | Pri | Platform | Est | Cumulative | Why first |
plus: fallback items, tasks left for later, waiting tasks, build under test, device status, what you will NOT do
and why.

## Phase 3 - Autonomous work loop (one task at a time, in plan order)
**Do not ask Min anything and do not wait for him in this phase.** Instead:
- Unclear requirement -> test with the most reasonable interpretation, state it in the result, add the question to
  `questions.md` (and a `need_info` comment on the card if writes are allowed), continue.
- Missing access/data/device for one task -> mark it blocked in log.md with the exact reason, take the next task or
  a fallback item. Retry it once later if the cause may be temporary (network, session expired).
- **Approved writes happen immediately, no command needed.** Bug confirmed (2x repro + duplicate check) -> create
  the card right away in Bug card style, put its link in results.csv/bugs.json, move on. Task result ready -> comment
  + move the card right away. Never ask Min to type "post B1 B2 B3", "push", "update card" or any other syntax, and
  never hold approved writes until the end of the run. Local ids B1, B2 are only for the moment before the card exists.
  A write that fails (network, auth) -> retry once, then queue it under "Pending approval" with the reason; continue.
- Severity never gates posting: Low/Medium bugs are posted right away like High/Critical, unless Min excluded them
  at kickoff. Old plans or notes saying "wait for post Bx" are replaced by this rule.
- Possible duplicate (similar open card) -> do not create; add a "Reoccurs on ..." comment to the existing card if
  card comments are approved, else queue it.
- Write not approved at kickoff -> prepare it fully (dry-run output, comment file, bug json) and list it under
  "Pending approval" in report.md; do not stop.
- Min writes during the run -> answer briefly, apply it, keep going (he can always stop or re-plan the shift).

Token saving: follow CLAUDE.md "Token saving". In a shift that means: read notes/profile once at kickoff and keep
the summary in `plan.md`; per task read the card + comments once, open only the linked TCs; snapshot only the area
under test; screenshots only for fail/confirm; progress messages one line; no subagents.

Speed: follow CLAUDE.md "Fast but accurate testing". In a shift that means: risk-first order inside each task,
one setup per screen/account group, deep links / direct URLs / adb / xcrun for preconditions only (the step under
test always through the UI), quick bug sweep on each screen, and every bug reproduced 2x from a clean state.

For each task:
1. **Read it like a senior QC**: description, ALL comments (dev fix notes, what changed, which build), attachments,
   linked TCs. Think about what else the change could break (shared components, other platforms, other roles).
2. **Claim** (if `claim_on_start` and allowed): `tasks.py update --task <key> --claim --state in_progress --comment "QC started on build <b> (<platforms>)"`
3. **Do the work** with the matching playbook:
   - verify_bug -> `.claude/skills/qc-verify-bug/SKILL.md`
   - test_feature -> `.claude/skills/qc-test-task/SKILL.md`
   - write_tc -> `.claude/skills/tc-gen/SKILL.md` (module/kind from the card; card key in the run notes)
   - regression -> `.claude/skills/test-regression/SKILL.md` (build from the card)
4. **Senior habits on every bug found**: reproduce twice (frequency), check `notes.md` Known issues and the board
   for duplicates, try the other platform/viewport/account to define the scope, collect logs (web console + failed
   network calls, Android logcat, crash time), cut the steps down to the minimum, set severity by user impact.
5. **Close the loop on the tracker** (when allowed): result comment (template below) + evidence + move to the
   target state.
6. **Update the test sheet** for the TCs touched (report skill, `update_results.py`, dry-run first).
7. Append one line to `log.md`: time, key, outcome, bugs, TCs updated, minutes spent. Then a one-line progress
   message to Min with time used, e.g. "35/60m - 3/6 xong: #45 verified, #47 reopened, #52 2 bug mới". Do not
   expect a reply.
8. Check the time with `date`:
   - Next task's Est does not fit before `Wrap-up at` -> pick a smaller planned task or a fallback item that fits.
   - `Wrap-up at` reached in the middle of a task -> finish the current TC (append results.csv), save a partial
     comment draft in `tasks/<key>/` (do not move the card), mark the task "in progress - carry over" in log.md,
     and go to Phase 4. Never leave a write half done.
   - Time left and nothing planned left -> fallback ladder. Finishing early is only OK when nothing is testable.
   - Deadline is hard: Phase 4 must be finished by the deadline, even if work is left.

Stop early only if nothing at all is testable (all devices/envs down, every account broken) after trying the
fallback items that need no device (write TCs, review specs). Then report right away with the blocker and the exact
action Min must take. A P0 bug that blocks most tasks: tell Min immediately in one message (no question), then
continue with what is still testable.

## Tracker comment template (in report_language, short, factual)
Use "QC comments" from CLAUDE.md "Bug card style" when it applies; otherwise:
```
QC result: VERIFIED | REOPENED | PASSED | FAILED | NEED INFO
Build: <build> | Env: <env> | Devices: <device (OS)>, ...
Checked:
- <what was checked, 1 line each, with TC ids>
Result:
- <observed behavior; for reopen: still reproducible x/y, what differs from expected>
Bugs: <new bug keys or "none">   TCs updated: <ids or "none">
Evidence: attached (<n> files)
```

## Phase 4 - Wrap-up / handover
1. Write `runs/<p>/_shift/<today>/report.md`:
   - Summary: tasks done / planned, time used vs budget (start - end), stop reason
     (time up | all planned work done | blocked | stopped by Min)
   - Table: Task | Type | Outcome | Bugs | TCs updated
   - Bugs verified / reopened / new (by severity), with links
   - Coverage: test-sheet progress per module (before -> after), exploratory areas covered
   - Blocked items and the exact action that unblocks each
   - Questions for Min / PO / dev (from `questions.md`) with the assumption you used
   - Bugs posted / cards updated during the run, with links
   - Pending approval: only writes Min excluded at kickoff or that failed twice (ready-to-run commands)
   - Risks & observations (flaky areas, crash trends, slow screens, untested areas and why)
   - Fast paths learned (deep links, page URLs, activity names, selectors) for the next shift; restore any
     device setting changed for speed (e.g. Android animation scales back to 1) before writing this
   - Not finished because of time: tasks/TCs left, partial progress, where to continue (`/qc <p> resume <duration>`)
   - Next shift: carry-over in priority order + suggested focus + what Min should prepare before it
2. Show Min a short version in chat (5-8 lines, first line e.g. "Hết 1h: 4/6 task xong, 2 bug mới ..."), then the
   questions and pending approvals - now is the right moment to ask.

## Permissions to request at kickoff
Find out at kickoff which of these the plan needs, try each once, and get every missing one approved before "go".
Never discover a permission prompt mid-run; if one appears anyway, switch to other work and note it in log.md.
| Need | When | How to get it at kickoff |
|---|---|---|
| Folder access to the QC kit (`/Users/lethingocmai/Documents/QC`) | always | device folder approval / connect device |
| Remote Control session on Min's Mac | web testing (cloud and Mac VM shell cannot reach most sites), local tools, signed-in accounts | start it, Min approves the prompt |
| Claude in Chrome extension (site permission for the domain under test) | web testing, Trello boards the connector cannot reach | open one page of the domain, ask Min to allow the site |
| Built-in browser pane | web testing when Chrome is not used | open one page of the domain |
| Trello (connector, or Chrome for boards the connector cannot see) | bug posting, card updates | read the target list once |
| Google Sheets / test sheet | test-sheet updates | `read_testcases.py ... --filter all` once |
| adb (USB debugging, "Allow this computer") | Android | `adb devices` shows `device`, not `unauthorized` |
| xcrun / Xcode device trust, Developer Mode | iOS | `xcrun devicectl list devices` shows the phone as available |
| Computer use (screen control) | only for desktop-app steps no other tool covers | turn it on and approve the app |
| macOS prompts (Screen Recording, Accessibility, Automation) | when the tools above need them | ask Min to allow them in System Settings now |

## Write permissions by autonomy
| Write | cautious | standard | full |
|---|---|---|---|
| claim / in_progress / progress comment | ask | auto (planned tasks) | auto |
| result comment + move verified/passed | ask | auto (planned tasks) | auto |
| reopen a bug / feature_failed | ask | ask | auto |
| create new bugs (push_bugs) | ask | ask | auto (possible duplicates are never auto-created) |
| update test sheet (update_results) | ask | auto with dry-run shown in log | auto |
| add new TCs (append_testcases) | ask | ask | auto |
| anything outside the plan | ask | ask | ask |
"ask" = ask at KICKOFF, once, for the whole run (one list, approved by "go"). Approved -> auto for this run: done
the moment the result is ready, without any further command or syntax from Min.
Not approved / not answered -> prepare it and queue it under "Pending approval" in report.md; never stop to ask
mid-run. Standing approvals written in CLAUDE.md, notes.md or project memory count as approved.
Always: dry-run first, keep `actions.log` (tasks.py writes it), never delete or archive cards, never edit
other people's comments, never change assignee away from someone else, never close a bug you did not verify.
