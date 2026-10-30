#!/usr/bin/env python3
"""Write a run's results.csv back into the project's test sheet (Excel or Google Sheet).

results.csv columns: ID, Platform, Status, Bug ID, Note[, Evidence]
  Status: pass | fail | blocked | skip  (or the sheet's own labels, e.g. Passed/Failed)
Rules:
  - Rows are matched by ID across all module sheets (skip_sheets excluded).
  - Only the platform's status column, Bug ID, Note and Date are touched.
  - Existing status is NOT overwritten unless --overwrite failed (replace Failed/Pending/blocked only)
    or --overwrite all (use only for confirmed regressions).
  - Note is appended (never replaced), prefixed with note_prefix and platform.
  - Bug ID is appended if a different id is already there.
Always run with --dry-run first and show the summary to the user.
"""
import argparse
import csv
from collections import Counter
from datetime import date

from lib.config import PLATFORMS, die, kit_path, load_profile, status_key_of
from lib.sheets import build_id_index, open_testcase_book


def norm_row(row: dict) -> dict:
    return {(k or "").strip().lower().replace("_", " "): (v or "").strip() for k, v in row.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--platform", choices=PLATFORMS, help="used when results.csv has no Platform column")
    ap.add_argument("--overwrite", default="none", choices=["none", "failed", "all"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    prof = load_profile(a.project)
    tc = prof["testcases"]
    labels, prefix = tc["status_labels"], tc["note_prefix"]
    res_path = kit_path(a.results)
    if not res_path.exists():
        die(f"Results file not found: {res_path}")
    with open(res_path, newline="", encoding="utf-8-sig") as f:
        results = [norm_row(r) for r in csv.DictReader(f)]

    book = open_testcase_book(prof)
    index = build_id_index(book, prof)
    pending: dict[tuple, object] = {}   # (sheet,row,col1) -> new value (lets several results chain)
    log, stats = [], Counter()

    def current(sheet, rec, idx, key):
        c = idx.get(key)
        if c is None:
            return None
        return pending.get((sheet, rec["_row"], c + 1), rec.get(key, ""))

    def put(sheet, rec, idx, key, value):
        pending[(sheet, rec["_row"], idx[key] + 1)] = value

    for r in results:
        rid = r.get("id", "")
        if not rid:
            continue
        plat = (r.get("platform") or a.platform or "").lower()
        ent = index.get(rid.upper())
        if not ent:
            stats["not_found"] += 1
            log.append((rid, plat, "not_found", ""))
            continue
        sheet, rec, idx = ent
        skey = f"status_{plat}"
        if plat not in PLATFORMS or idx.get(skey) is None:
            stats["no_status_column"] += 1
            log.append((rid, plat, "no_status_column", f"sheet={sheet}"))
            continue
        new_key = status_key_of(r.get("status", ""), labels)
        if new_key not in labels:
            stats["invalid_status"] += 1
            log.append((rid, plat, "invalid_status", r.get("status", "")))
            continue
        cur = current(sheet, rec, idx, skey) or ""
        cur_key = status_key_of(cur, labels)
        if cur_key == new_key:
            stats["unchanged"] += 1
            log.append((rid, plat, "unchanged", cur))
            continue
        allowed = (cur_key == "" or a.overwrite == "all"
                   or (a.overwrite == "failed" and cur_key in ("fail", "blocked")))
        if not allowed:
            stats["kept_existing"] += 1
            log.append((rid, plat, "kept_existing", f"{cur} (new would be {labels[new_key]})"))
            continue

        put(sheet, rec, idx, skey, labels[new_key])
        note = r.get("note", "")
        if note and idx.get("note") is not None:
            text = f"{prefix}[{plat}] {note}"
            old = current(sheet, rec, idx, "note") or ""
            if text not in old:
                put(sheet, rec, idx, "note", f"{old}\n{text}" if old else text)
        bug = r.get("bug id", "")
        if bug and idx.get("bug_id") is not None:
            old = current(sheet, rec, idx, "bug_id") or ""
            if bug.lower() not in old.lower():
                put(sheet, rec, idx, "bug_id", f"{old}, {bug}" if old else bug)
        if idx.get("date") is not None:
            put(sheet, rec, idx, "date", date.today())
        stats["updated"] += 1
        log.append((rid, plat, "updated", f"{cur or '(empty)'} -> {labels[new_key]} [{sheet} row {rec['_row']}]"))

    print(f"Summary: {dict(stats)}")
    for rid, plat, action, detail in log:
        if action != "updated" or a.dry_run:
            print(f"  {rid:<14} {plat:<8} {action:<17} {detail}")

    log_path = res_path.with_name(res_path.stem + (".dryrun" if a.dry_run else ".applied") + ".csv")
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ID", "Platform", "Action", "Detail"])
        w.writerows(log)

    if a.dry_run:
        print(f"DRY RUN - nothing written. Log: {log_path}")
        return
    if not pending:
        print("Nothing to write.")
        return
    by_sheet: dict[str, list] = {}
    for (sheet, row, col), v in pending.items():
        by_sheet.setdefault(sheet, []).append((row, col, v))
    bak = book.backup(res_path.parent)
    if bak:
        print(f"Backup: {bak}")
    for sheet, ups in by_sheet.items():
        book.write(sheet, ups)
    book.save()
    print(f"Written {len(pending)} cells in {len(by_sheet)} sheet(s). Log: {log_path}")


if __name__ == "__main__":
    main()
