#!/usr/bin/env python3
"""Append new test cases (from tc-gen) to a module sheet. Creates the sheet if missing.

CSV headers may be either column keys (id, description, expected, precondition, steps, priority, type)
or the sheet's own header names from profile.yaml (e.g. "Expected Result").
  --auto-id  fill empty IDs as <id_prefix><NNN>, continuing after the highest existing number.
Existing IDs are never overwritten (skipped). Run with --dry-run first.
"""
import argparse
import csv
import re

from lib.config import COLUMN_ORDER, PLATFORMS, die, kit_path, load_profile, module_list, warn
from lib.sheets import iter_table, locate_table, open_testcase_book

CONTENT_KEYS = ("id", "description", "precondition", "steps", "expected", "priority", "type")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--module", required=True, help="one module id from profile.yaml")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--auto-id", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    prof = load_profile(a.project)
    cols = prof["testcases"]["columns"]
    mod = module_list(prof, a.module)[0]
    sheet = mod.get("sheet") or mod.get("id")
    prefix = mod.get("id_prefix") or f"{mod.get('id')}_"
    width = int(mod.get("id_digits", 3))

    # map CSV headers -> keys
    with open(kit_path(a.csv), newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header_map = {}
        for h in reader.fieldnames or []:
            hn = h.strip().lower()
            for key in CONTENT_KEYS:
                if hn == key or (cols.get(key) and hn == str(cols[key]).strip().lower()) or \
                        (key == "expected" and hn in ("expected", "expected result")):
                    header_map[h] = key
        new_rows = [{header_map[h]: (v or "").strip() for h, v in r.items() if h in header_map} for r in reader]
    if not new_rows:
        die("No rows in CSV")
    if "description" not in header_map.values():
        die(f"CSV needs a Description column. Got headers: {list(header_map)}")

    book = open_testcase_book(prof)
    created = False
    if sheet not in book.sheet_names():
        plats = [p for p in PLATFORMS if p in (prof.get("platforms") or {})]
        header_keys = [k for k in COLUMN_ORDER if cols.get(k) and (not k.startswith("status_") or k[7:] in plats)]
        header = [cols[k] for k in header_keys]
        print(f"Sheet '{sheet}' not found -> will create it with header: {header}")
        if not a.dry_run:
            book.add_sheet(sheet, header)
        created = True
        values = [header]
        hr, idx = 0, {k: (header_keys.index(k) if k in header_keys else None) for k in cols}
    else:
        values = book.values(sheet)
        hr, idx = locate_table(values, cols)
        if hr is None:
            die(f"Header row with '{cols['id']}' not found in '{sheet}'")

    existing = list(iter_table(values, hr, idx))
    existing_ids = {r["id"].upper() for r in existing}
    last_row = max([r["_row"] for r in existing], default=hr + 1)
    num_re = re.compile(rf"^{re.escape(prefix)}(\d+)$", re.I)
    max_num = max([int(m.group(1)) for r in existing if (m := num_re.match(r["id"]))], default=0)

    updates, added, skipped, dropped = [], [], [], set()
    row_no = last_row
    for r in new_rows:
        rid = r.get("id", "")
        if not rid:
            if not a.auto_id:
                die("Row without ID - use --auto-id or fill IDs")
            max_num += 1
            rid = f"{prefix}{max_num:0{width}d}"
        if rid.upper() in existing_ids:
            skipped.append(rid)
            continue
        existing_ids.add(rid.upper())
        row_no += 1
        r["id"] = rid
        for key, val in r.items():
            if val and idx.get(key) is not None:
                updates.append((row_no, idx[key] + 1, val))
            elif val and idx.get(key) is None and key != "id":
                dropped.add(key)
        added.append((row_no, rid, r.get("description", "")[:70]))

    if dropped:
        warn(f"No column in sheet for {sorted(dropped)} - those values were dropped (configure testcases.columns)")
    print(f"Sheet '{sheet}': add {len(added)}, skip {len(skipped)} existing ids {skipped[:10]}")
    for row_no, rid, desc in added[:200]:
        print(f"  row {row_no:<5} {rid:<12} {desc}")
    if a.dry_run:
        print("DRY RUN - nothing written.")
        return
    book.write(sheet, updates)
    book.save()
    print("Done.")
    if book.kind == "excel" or created:
        print("[CHECK] Dropdowns (data validation) and Summary formulas may not cover the new rows - "
              "extend their ranges in the sheet if needed.")


if __name__ == "__main__":
    main()
