#!/usr/bin/env python3
"""QC work queue on the project's tracker (Trello / Jira / Mantis / Bugs sheet).

  pull    fetch the QC queue, prioritize it, save runs/<p>/_shift/<date>/queue.json, print the plan
  show    full details of one task: description, comments (dev fix notes), attachments, linked TCs
  update  claim / move to a workflow state / comment / attach evidence on one task (audit-logged)
  check   validate profile.workflow against the tracker (lists, statuses, JQL)

Examples (kit root):
  .venv/bin/python scripts/tasks.py pull --project shopx --minutes 120
  .venv/bin/python scripts/tasks.py show --project shopx --task "#45" --download
  .venv/bin/python scripts/tasks.py update --project shopx --task "#45" --claim --state in_progress \\
        --comment "QC started on build 1.4.3 (Android)" --dry-run
  .venv/bin/python scripts/tasks.py update --project shopx --task "#45" --state verified \\
        --comment-file runs/.../comment_45.md --attach runs/.../evidence/a.png,runs/.../evidence/b.png
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

from lib.config import KIT_ROOT, die, kit_path, load_profile, today
from lib.trackers import make_client

TYPES = ("verify_bug", "regression", "test_feature", "write_tc")
TYPE_RANK = {t: i for i, t in enumerate(TYPES)}
TYPE_LABEL = {"verify_bug": "Verify bug", "regression": "Regression", "test_feature": "Test feature",
              "write_tc": "Write TCs"}
DEFAULT_EST = {"verify_bug": 15, "regression": 60, "test_feature": 45, "write_tc": 30}
PRIO_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
DEFAULT_PRIO_MAP = {"blocker": "P0", "critical": "P0", "urgent": "P0", "immediate": "P0", "highest": "P0", "p0": "P0",
                    "high": "P1", "major": "P1", "p1": "P1",
                    "medium": "P2", "normal": "P2", "p2": "P2",
                    "low": "P3", "lowest": "P3", "minor": "P3", "trivial": "P3", "p3": "P3"}


# ---------------------------------------------------------------- helpers
def shift_dir(project: str, day: str | None = None) -> Path:
    d = KIT_ROOT / "runs" / project / "_shift" / (day or today())
    d.mkdir(parents=True, exist_ok=True)
    return d


def audit(project: str, line: str):
    with open(shift_dir(project) / "actions.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%H:%M:%S')} {line}\n")


def workflow(prof: dict) -> dict:
    wf = prof.get("workflow") or die("profile.yaml has no 'workflow' section (see projects/_template/profile.yaml)")
    wf.setdefault("queues", {})
    wf.setdefault("states", {})
    bad = [q for q in wf["queues"] if q not in TYPES]
    if bad:
        die(f"Unknown queue type(s) {bad}. Allowed: {list(TYPES)}")
    return wf


def tc_pattern(prof: dict):
    prefixes = {m.get("id_prefix") or f"{m.get('id')}_" for m in prof.get("modules") or [] if m.get("id")}
    if not prefixes:
        return None
    return re.compile(r"\b(" + "|".join(re.escape(p) for p in sorted(prefixes, key=len, reverse=True)) + r")(\d+)\b", re.I)


def linked_tcs(prof, *texts) -> list[str]:
    pat = tc_pattern(prof)
    if not pat:
        return []
    found = []
    for t in texts:
        for m in pat.finditer(t or ""):
            tid = (m.group(1) + m.group(2)).upper()
            if tid not in found:
                found.append(tid)
    return found


def parse_due(s: str):
    if not s:
        return None
    try:
        if len(s) == 10:
            return date.fromisoformat(s)
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone().date()
    except ValueError:
        return None


def priority_of(task, wf):
    m = {k.lower(): v for k, v in DEFAULT_PRIO_MAP.items()}
    m.update({str(k).lower(): v for k, v in (wf.get("priority_map") or {}).items()})
    best = None
    for raw in task.get("priority_raw") or []:
        p = m.get(str(raw).strip().lower())
        if p and (best is None or PRIO_RANK[p] < PRIO_RANK[best]):
            best = p
    return best or wf.get("default_priority", "P2")


def platforms_of(task, prof, wf):
    plat_map = {str(k).lower(): v for k, v in (wf.get("platform_labels") or
                                               {"android": "android", "ios": "ios", "web": "web"}).items()}
    found = [plat_map[lb.lower()] for lb in task.get("labels") or [] if lb.lower() in plat_map]
    for name, key in (("android", "android"), ("ios", "ios"), ("web", "web")):
        if re.search(rf"\[{name}\]", task.get("title", ""), re.I) and key not in found:
            found.append(key)
    avail = list((prof.get("platforms") or {}).keys())
    return [p for p in found if p in avail] or avail


def enrich(task, prof, wf, me_id):
    tday = date.today()
    task["type"] = task.get("queue") or "test_feature"
    task["priority"] = priority_of(task, wf)
    task["platforms"] = platforms_of(task, prof, wf)
    task["tc_ids"] = linked_tcs(prof, task.get("title"), task.get("desc"))
    waiting = {w.lower() for w in wf.get("waiting_labels") or []}
    task["waiting"] = any(lb.lower() in waiting for lb in task.get("labels") or [])
    task["mine"] = bool(me_id and me_id in (task.get("members") or []))
    due = parse_due(task.get("due", ""))
    task["due_in_days"] = (due - tday).days if due and not task.get("due_complete") else None
    est = dict(DEFAULT_EST)
    est.update(wf.get("estimates_min") or {})
    task["estimate_min"] = int(est.get(task["type"], 30))
    reasons = [task["priority"]]
    if task["due_in_days"] is not None:
        d = task["due_in_days"]
        reasons.append(f"overdue {-d}d" if d < 0 else "due today" if d == 0 else f"due in {d}d")
    reasons.append(TYPE_LABEL.get(task["type"], task["type"]))
    if task["waiting"]:
        reasons.append("WAITING label")
    task["reason"] = " | ".join(reasons)
    return task


def sort_key(t):
    d = t["due_in_days"]
    due_rank = 0 if d is not None and d <= 0 else 1 if d is not None and d <= 1 else 2
    return (1 if t["waiting"] else 0,
            0 if t["priority"] == "P0" else 1,
            due_rank,
            PRIO_RANK.get(t["priority"], 2),
            TYPE_RANK.get(t["type"], 9),
            d if d is not None else 9999,
            t.get("created") or "")


# ---------------------------------------------------------------- commands
def cmd_pull(a, prof, wf):
    client, _ = make_client(prof, dry=True)
    me = client.me()
    tasks = client.list_tasks(wf["queues"])
    mode = a.assignee or wf.get("assignee", "me_or_unassigned")
    if mode == "me":
        tasks = [t for t in tasks if me["id"] in t["members"]]
    elif mode == "me_or_unassigned":
        tasks = [t for t in tasks if not t["members"] or me["id"] in t["members"]]
    tasks = [enrich(t, prof, wf, me["id"]) for t in tasks]
    if a.platform:
        tasks = [t for t in tasks if a.platform in t["platforms"]]
    tasks.sort(key=sort_key)

    budget, used = a.minutes or wf.get("shift_minutes", 120), 0
    for i, t in enumerate(tasks, 1):
        t["order"] = i
        if t["waiting"]:
            t["plan"] = "waiting"
        elif used + t["estimate_min"] <= budget or used == 0:
            t["plan"] = "today"
            used += t["estimate_min"]
        else:
            t["plan"] = "later"

    out = shift_dir(a.project) / "queue.json"
    out.write_text(json.dumps({"project": a.project, "pulled_at": datetime.now(timezone.utc).isoformat(),
                               "me": me, "budget_min": budget, "tasks": tasks}, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"QC queue for {a.project} - me: {me['name']} - assignee filter: {mode} - {len(tasks)} task(s)")
    print(f"{'#':>2}  {'plan':<7} {'key':<10} {'type':<12} {'pri':<3} {'est':>4}  {'platforms':<16} title")
    for t in tasks:
        print(f"{t['order']:>2}  {t['plan']:<7} {t['key']:<10} {t['type']:<12} {t['priority']:<3} "
              f"{t['estimate_min']:>3}m  {','.join(t['platforms']):<16} {t['title'][:70]}")
        print(f"{'':>4}why: {t['reason']}" + (f" | TCs: {', '.join(t['tc_ids'])}" if t["tc_ids"] else "")
              + f" | {t['status']}")
    print(f"Planned today: {sum(1 for t in tasks if t['plan'] == 'today')} task(s), ~{used} of {budget} min. Saved {out}")


def cmd_show(a, prof, wf):
    client, _ = make_client(prof, dry=True)
    t = client.get_task(a.task)
    enrich(t, prof, wf or {}, client.me()["id"])
    t["tc_ids"] = linked_tcs(prof, t["title"], t["desc"], *[c["text"] for c in t["comments"]])
    folder = shift_dir(a.project) / "tasks" / re.sub(r"[^\w\-]", "", t["key"])
    if a.download:
        for att in t["attachments"]:
            p = client.download(att, folder / "attachments")
            if p:
                att["local"] = str(p.relative_to(KIT_ROOT))
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "task.json").write_text(json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{t['key']}  [{t['status']}]  {t['title']}\n{t['url']}")
    print(f"priority {t['priority']} | labels {t['labels']} | due {t['due'] or '-'} | platforms {t['platforms']}")
    for k in ("fix_versions", "fixed_in_version"):
        if t.get(k):
            print(f"{k}: {t[k]}")
    print(f"linked TCs: {', '.join(t['tc_ids']) or '-'}")
    print("\n--- description ---\n" + (t["desc"] or "(empty)"))
    print(f"\n--- comments ({len(t['comments'])}, oldest first) ---")
    for c in t["comments"]:
        print(f"[{c['date'][:16]}] {c['author']}: {c['text']}")
    print(f"\n--- attachments ({len(t['attachments'])}) ---")
    for att in t["attachments"]:
        print(f"- {att['name']} {att.get('local') or att['url']}")
    print(f"\nSaved {folder / 'task.json'}")


def cmd_update(a, prof, wf):
    client, _ = make_client(prof, dry=a.dry_run)
    state_name = None
    if a.state:
        state_name = (wf.get("states") or {}).get(a.state, None) if not a.raw_state else a.state
        if state_name is None:
            die(f"State '{a.state}' not in workflow.states {list((wf.get('states') or {}).keys())} (or use --raw-state)")
    text = a.comment or ""
    if a.comment_file:
        text = kit_path(a.comment_file).read_text(encoding="utf-8").strip()
    files = []
    for f in [x.strip() for x in (a.attach or "").split(",") if x.strip()]:
        p = kit_path(f)
        if not p.exists():
            die(f"Attachment not found: {p}")
        files.append(p)

    plan = []
    if a.claim:
        plan.append("claim")
    if state_name:
        plan.append(f"move -> '{state_name}'")
    elif a.state:
        plan.append(f"state '{a.state}' is empty in profile -> not moved")
    if text:
        plan.append(f"comment ({len(text)} chars)")
    if files:
        plan.append(f"attach {len(files)} file(s)")
    if not plan:
        die("Nothing to do: use --claim, --state, --comment/--comment-file or --attach")
    print(f"{a.task}: " + "; ".join(plan))
    if text:
        print("--- comment ---\n" + text + "\n---------------")
    if a.dry_run:
        print("DRY RUN - nothing changed.")
        return
    done = []
    if a.claim:
        done.append(client.claim(a.task))
    if files:
        client.attach(a.task, files)
        done.append(f"attached {len(files)}")
    if text:
        client.comment(a.task, text)
        done.append("commented")
    if state_name:
        done.append(client.move(a.task, state_name))
    client.finish()
    audit(a.project, f"{a.task}: {'; '.join(done)}")
    print("Done: " + "; ".join(done))


def cmd_check(a, prof, wf):
    client, _ = make_client(prof, dry=True)
    print(f"Tracker {client.kind}, I am '{client.me()['name']}'")
    warns = client.validate(wf)
    for w in warns:
        print(f"[WARN] {w}")
    print("Workflow OK." if not warns else f"{len(warns)} warning(s).")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pull")
    p.add_argument("--project", required=True)
    p.add_argument("--minutes", type=int, default=0, help="time budget for today's plan")
    p.add_argument("--platform", default="", help="only tasks that need this platform")
    p.add_argument("--assignee", choices=["me", "me_or_unassigned", "any"])
    p = sub.add_parser("show")
    p.add_argument("--project", required=True)
    p.add_argument("--task", required=True)
    p.add_argument("--download", action="store_true", help="download attached screenshots/videos")
    p = sub.add_parser("update")
    p.add_argument("--project", required=True)
    p.add_argument("--task", required=True)
    p.add_argument("--state", help="workflow state key, e.g. in_progress, verified, reopened, feature_passed")
    p.add_argument("--raw-state", action="store_true", help="--state is a raw list/status name")
    p.add_argument("--claim", action="store_true")
    p.add_argument("--comment", default="")
    p.add_argument("--comment-file", default="")
    p.add_argument("--attach", default="", help="comma separated files")
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("check")
    p.add_argument("--project", required=True)
    a = ap.parse_args()

    prof = load_profile(a.project)
    wf = workflow(prof) if a.cmd != "show" else (prof.get("workflow") or {})
    {"pull": cmd_pull, "show": cmd_show, "update": cmd_update, "check": cmd_check}[a.cmd](a, prof, wf)


if __name__ == "__main__":
    main()
