#!/usr/bin/env python3
"""Export test cases from the project's test sheet (Excel or Google Sheet) to a CSV that Claude executes.

Examples (run from kit root):
  .venv/bin/python scripts/read_testcases.py --project shopx --module MSG --platform android
  .venv/bin/python scripts/read_testcases.py --project shopx --module all --platform ios --filter notpassed
  .venv/bin/python scripts/read_testcases.py --project shopx --module MSG --platform android --ids MSG_001..MSG_010
Filters: pending (status empty, default) | failed | blocked | rerun (failed+blocked) | notpassed (empty+failed+blocked) | all
"""
import argparse
import csv
from collections import Counter

from lib.config import KIT_ROOT, PLATFORMS, die, kit_path, load_profile, module_list, parse_id_filter, status_key_of, warn
from lib.sheets import iter_table, locate_table, open_testcase_book

FILTERS = {
    "pending": lambda k: k == "",
    "failed": lambda k: k == "fail",
    "blocked": lambda k: k == "blocked",
    "rerun": lambda k: k in ("fail", "blocked"),
    "notpassed": lambda k: k in ("", "fail", "blocked"),
    "all": lambda k: True,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--platform", required=True, choices=PLATFORMS)
    ap.add_argument("--module", default="all", help="module id(s) from profile, comma separated, or 'all'")
    ap.add_argument("--filter", default="pending", choices=list(FILTERS))
    ap.add_argument("--ids", default="", help="e.g. MSG_001..MSG_010,MSG_015")
    ap.add_argument("--priority", default="", help="e.g. high or high,medium (needs a Priority column)")
    ap.add_argument("--bug-ids", default="", help="only rows whose Bug ID cell contains one of these ids")
    ap.add_argument("--out", default="", help="output CSV path (default runs/<project>/_testcases/...)")
    a = ap.parse_args()

    prof = load_profile(a.project)
    tc = prof["testcases"]
    cols, labels = tc["columns"], tc["status_labels"]
    status_key = f"status_{a.platform}"
    if not cols.get(status_key):
        die(f"No status column configured for {a.platform} (testcases.columns.{status_key})")
    mods = module_list(prof, a.module)
    if not mods:
        die("No modules in profile.yaml")

    book = open_testcase_book(prof)
    idf = parse_id_filter(a.ids)
    prios = {p.strip().lower() for p in a.priority.split(",") if p.strip()}
    bug_ids = [b.strip().lower() for b in a.bug_ids.split(",") if b.strip()]
    keep = FILTERS[a.filter]

    rows, stats = [], Counter()
    for m in mods:
        sheet = m.get("sheet") or m.get("id")
        if sheet not in book.sheet_names():
            warn(f"Sheet '{sheet}' (module {m.get('id')}) not found - skipped")
            continue
        values = book.values(sheet)
        hr, idx = locate_table(values, cols)
        if hr is None:
            warn(f"Header row with '{cols['id']}' not found in sheet '{sheet}' - skipped")
            continue
        if idx.get(status_key) is None:
            warn(f"Column '{cols[status_key]}' not found in sheet '{sheet}' - skipped")
            continue
        for rec in iter_table(values, hr, idx):
            if not idf(rec["id"]):
                continue
            k = status_key_of(rec.get(status_key, ""), labels)
            stats[(m.get("id"), k or "empty")] += 1
            if not keep(k):
                continue
            if prios and rec.get("priority", "").lower() not in prios:
                continue
            if bug_ids and not any(b in rec.get("bug_id", "").lower() for b in bug_ids):
                continue
            rows.append({
                "Module": m.get("id"), "Sheet": sheet, "Row": rec["_row"], "ID": rec["id"],
                "Description": rec.get("description", ""), "Precondition": rec.get("precondition", ""),
                "Steps": rec.get("steps", ""), "Expected": rec.get("expected", ""),
                "Priority": rec.get("priority", ""), "Current Status": rec.get(status_key, ""),
                "Bug ID": rec.get("bug_id", ""), "Note": rec.get("note", ""),
            })

    out = kit_path(a.out) if a.out else (KIT_ROOT / "runs" / a.project / "_testcases"
                                         / f"{a.module.replace(',', '+')}_{a.platform}_{a.filter}.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["Module", "Sheet", "Row", "ID", "Description", "Precondition", "Steps", "Expected",
              "Priority", "Current Status", "Bug ID", "Note"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"Selected {len(rows)} test cases -> {out}")
    print("Status overview (module: status=count):")
    for mid in dict.fromkeys(m for m, _ in stats):
        parts = ", ".join(f"{s}={c}" for (mm, s), c in sorted(stats.items()) if mm == mid)
        print(f"  {mid}: {parts}")


if __name__ == "__main__":
    main()
