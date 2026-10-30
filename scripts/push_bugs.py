#!/usr/bin/env python3
"""Push approved bugs from a run's bugs.json to the project's bug tracker, with duplicate check.

Tracker = profile.yaml bug_tracker.type: sheet | trello | jira | mantis | none
  sheet  -> a "Bugs" tab in the test-case book (Excel or Google Sheet) or a separate book
Workflow:
  1. --dry-run           list bugs + possible duplicates (title similarity), writes nothing
  2. user decides; edit bugs.json per bug: "action": "skip" | "duplicate_of": "<id>" | "force_create": true
  3. run without --dry-run [--results <run>/results.csv] -> creates issues, attaches evidence,
     writes remote_id/remote_url into bugs.json and replaces local ids (B1..) in results.csv
Options: --only B1,B3   restrict to these local ids
bugs[].parent_task (optional): task key the bug was found on (e.g. Trello #45) - the new bug is linked there.
"""
import argparse
import csv
import difflib
import json
import re
from pathlib import Path

from lib.config import kit_path, load_profile, warn
from lib.trackers import PLATFORM_NAMES, make_client, steps_text


# ---------- formatting ----------

def norm_title(t: str) -> str:
    t = re.sub(r"\[.*?\]", " ", (t or "").lower())
    t = re.sub(r"[^\w\s]", " ", t)
    return " ".join(t.split())


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, norm_title(a), norm_title(b)).ratio()


def make_title(cfg: dict, bug: dict) -> str:
    tpl = cfg.get("title_template", "[{platform}][{module}] {title}")
    return tpl.format(platform=PLATFORM_NAMES.get(bug.get("platform", ""), bug.get("platform", "")),
                      module=bug.get("module", ""), title=bug.get("title", "").strip(),
                      severity=bug.get("severity", ""))


def make_body(bug: dict, meta: dict, include_steps: bool = True) -> str:
    parts = [
        f"Module: {bug.get('module', '')}   Platform: {PLATFORM_NAMES.get(bug.get('platform', ''), bug.get('platform', ''))}",
        f"Device/OS: {bug.get('device', '')}   Build: {bug.get('build') or meta.get('build', '')}",
        f"Severity: {bug.get('severity', '')}   Frequency: {bug.get('frequency', '')}",
        f"Test case(s): {', '.join(bug.get('tc_ids') or [])}",
    ]
    if bug.get("preconditions"):
        parts += ["", "Preconditions:", bug["preconditions"]]
    if include_steps:
        parts += ["", "Steps to reproduce:", steps_text(bug)]
    parts += ["", "Expected:", bug.get("expected", ""), "", "Actual:", bug.get("actual", "")]
    if bug.get("notes"):
        parts += ["", "Notes:", bug["notes"]]
    if bug.get("parent_task"):
        parts += ["", f"Found while testing: {bug['parent_task']}"]
    parts += ["", f"Reported by Claude QA agent, reviewed by tester - run {meta.get('run', '')}"]
    return "\n".join(parts)


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--bugs", required=True, help="path to bugs.json")
    ap.add_argument("--only", default="", help="comma separated local ids, e.g. B1,B3")
    ap.add_argument("--results", default="", help="results.csv to rewrite local bug ids into tracker ids")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    prof = load_profile(a.project)
    bugs_path = kit_path(a.bugs)
    data = json.loads(bugs_path.read_text(encoding="utf-8"))
    bugs = data["bugs"] if isinstance(data, dict) else data
    meta = data if isinstance(data, dict) else {}
    only = {x.strip().upper() for x in a.only.split(",") if x.strip()}

    tracker, cfg = make_client(prof, a.dry_run)
    threshold = float(cfg.get("dedup_threshold", 0.6))
    existing = tracker.open_issues()
    print(f"Tracker: {cfg.get('type')} - {len(existing)} open items loaded for duplicate check")

    created = 0
    for bug in bugs:
        lid = str(bug.get("local_id", "")).upper()
        if only and lid not in only:
            continue
        title = make_title(cfg, bug)
        if bug.get("remote_id"):
            print(f"- {lid}: already pushed as {bug['remote_id']}")
            continue
        if bug.get("action") == "skip":
            print(f"- {lid}: skipped (action=skip)")
            continue
        if bug.get("duplicate_of"):
            bug["remote_id"] = bug["duplicate_of"]
            print(f"- {lid}: linked to existing {bug['duplicate_of']} (not created)")
            continue
        dups = sorted(((similarity(bug.get("title", ""), t), i, t, u) for i, t, u in existing), reverse=True)
        dups = [d for d in dups if d[0] >= threshold][:3]
        print(f"- {lid} [{bug.get('severity', '')}] {title}")
        for score, i, t, u in dups:
            print(f"    possible duplicate {score:.0%}: {i} {t} {u}")
        if a.dry_run:
            continue
        if dups and not bug.get("force_create"):
            print("    -> NOT created: possible duplicate. Set duplicate_of, action=skip or force_create=true.")
            continue
        files = []
        for ev in bug.get("evidence") or []:
            p = Path(ev)
            cand = [p] if p.is_absolute() else [bugs_path.parent / p, kit_path(p)]
            hit = next((c for c in cand if c.exists()), None)
            if hit:
                files.append(hit)
            else:
                warn(f"{lid}: evidence not found: {ev}")
        body = make_body(bug, meta, include_steps=tracker.kind != "mantis")
        rid, url = tracker.create_issue(bug, title, body, files)
        bug["remote_id"], bug["remote_url"] = rid, url
        existing.append((rid, title, url))
        created += 1
        print(f"    -> created {rid} {url}")
        parent = bug.get("parent_task")
        if parent and tracker.kind in ("trello", "mantis", "sheet"):
            tracker.comment(parent, f"QC found bug {rid}: {title} {url}".strip())
            print(f"    -> linked on parent task {parent}")

    if a.dry_run:
        print("DRY RUN - nothing created.")
        return
    tracker.finish()
    bugs_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Created {created} item(s). bugs.json updated.")

    if a.results:
        mapping = {str(b.get("local_id", "")).upper(): b["remote_id"] for b in bugs if b.get("remote_id")}
        rp = kit_path(a.results)
        with open(rp, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fields, rows = reader.fieldnames, list(reader)
        bug_col = next((c for c in fields if c.strip().lower().replace("_", " ") == "bug id"), None)
        if bug_col:
            for row in rows:
                toks = [t.strip() for t in (row.get(bug_col) or "").split(",") if t.strip()]
                row[bug_col] = ", ".join(mapping.get(t.upper(), t) for t in toks)
            with open(rp, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                w.writerows(rows)
            print(f"results.csv bug ids updated: {rp}")


if __name__ == "__main__":
    main()
