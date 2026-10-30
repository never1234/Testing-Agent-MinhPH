#!/usr/bin/env python3
"""Check that the kit and a project are ready to test. Never prints secret values.
  .venv/bin/python scripts/check_setup.py                       # kit only
  .venv/bin/python scripts/check_setup.py --project shopx     # + devices, sheet, tracker
  .venv/bin/python scripts/check_setup.py --project shopx --platform android --quick
"""
import argparse
import importlib
import shutil
import subprocess

from lib.config import KIT_ROOT, PLATFORMS, kit_path, load_profile

OK, BAD, WARN = "OK  ", "FAIL", "WARN"
problems = 0


def report(state, msg):
    global problems
    if state == BAD:
        problems += 1
    print(f"[{state}] {msg}")


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout
    except Exception as e:  # noqa: BLE001
        return f"ERROR {e}"


def check_kit():
    for mod in ("openpyxl", "gspread", "yaml", "dotenv", "requests"):
        try:
            importlib.import_module(mod)
            report(OK, f"python package {mod}")
        except ImportError:
            report(BAD, f"python package {mod} missing -> .venv/bin/pip install -r requirements.txt")
    report(OK if (KIT_ROOT / ".env").exists() else BAD, ".env file (copy from .env.example)")
    for tool in ("node", "npx"):
        report(OK if shutil.which(tool) else BAD, f"{tool} installed (needed for MCP servers)")


def check_env_var(var, label):
    import os
    report(OK if os.getenv(var) else BAD, f"{label}: {var} set in .env")


def check_project(name, only_platform, quick):
    prof = load_profile(name)
    report(OK, f"profile.yaml loaded ({name})")
    plats = prof.get("platforms") or {}
    for p in PLATFORMS:
        if p not in plats or (only_platform and p != only_platform):
            continue
        cfg = plats[p] or {}
        if p == "android":
            if not shutil.which("adb"):
                report(BAD, "adb not found -> brew install android-platform-tools")
                continue
            lines = [ln for ln in run(["adb", "devices", "-l"]).splitlines()[1:] if ln.strip()]
            ready = [ln for ln in lines if " device " in ln + " "]
            report(OK if ready else BAD, f"android devices: {len(ready)} ready" + (f" / {len(lines)} seen" if lines else ""))
            for ln in lines:
                print(f"       {ln}")
        elif p == "ios":
            if not shutil.which("xcrun"):
                report(BAD, "xcrun not found -> install Xcode")
                continue
            out = run(["xcrun", "xctrace", "list", "devices"])
            section = out.split("== Simulators ==")[0]
            devs = [ln for ln in section.splitlines()[1:] if ln.strip() and "==" not in ln]
            want = cfg.get("device_name", "")
            hit = any(want.lower() in d.lower() for d in devs) if want else bool(devs)
            report(OK if hit else WARN, f"ios device '{want}' visible to Xcode")
            for d in devs:
                print(f"       {d}")
        elif p == "web":
            url = cfg.get("url")
            if url:
                import requests
                try:
                    r = requests.get(url, timeout=15)
                    report(OK if r.status_code < 500 else WARN, f"web {url} -> HTTP {r.status_code}")
                except Exception as e:  # noqa: BLE001
                    report(BAD, f"web {url} unreachable: {e}")
    for alias, acc in (prof.get("accounts") or {}).items():
        for k, var in acc.items():
            if k.endswith("_env"):
                check_env_var(var, f"account {alias} {k[:-4]}")

    tc = prof["testcases"]
    src = tc.get("source")
    if src == "gsheet":
        check_env_var("GOOGLE_SERVICE_ACCOUNT_JSON", "google service account")
    elif src == "excel":
        report(OK if kit_path(tc.get("excel_path", "")).exists() else BAD, f"excel file {tc.get('excel_path')}")
    if not quick:
        from lib.sheets import locate_table, open_testcase_book
        book = open_testcase_book(prof)
        names = book.sheet_names()
        report(OK, f"test sheet opened ({src}): tabs = {names}")
        for m in prof.get("modules") or []:
            sheet = m.get("sheet") or m.get("id")
            if sheet not in names:
                report(BAD, f"module {m.get('id')}: sheet '{sheet}' not found")
                continue
            hr, idx = locate_table(book.values(sheet), tc["columns"])
            if hr is None:
                report(BAD, f"module {m.get('id')}: header '{tc['columns']['id']}' not found in '{sheet}'")
                continue
            missing = [tc["columns"][f"status_{p}"] for p in plats if p in PLATFORMS and idx.get(f"status_{p}") is None]
            report(WARN if missing else OK, f"module {m.get('id')}: '{sheet}' header row {hr + 1}"
                   + (f", missing columns {missing}" if missing else ""))
        listed = {m.get("sheet") or m.get("id") for m in prof.get("modules") or []}
        extra = [n for n in names if n not in listed and n not in tc.get("skip_sheets", [])]
        if extra:
            report(WARN, f"tabs not listed as modules (add to modules or skip_sheets): {extra}")

    bt = prof.get("bug_tracker") or {}
    kind = (bt.get("type") or "none").lower()
    need = {"trello": ["TRELLO_KEY", "TRELLO_TOKEN"], "mantis": ["MANTIS_BASE_URL", "MANTIS_TOKEN"],
            "jira": ["JIRA_BASE_URL"] + (["JIRA_EMAIL", "JIRA_API_TOKEN"]
                                         if (bt.get("jira") or {}).get("deployment", "cloud") == "cloud" else ["JIRA_PAT"])}
    for var in need.get(kind, []):
        check_env_var(var, f"bug tracker {kind}")
    if not quick and kind in ("trello", "jira", "mantis") and problems == 0:
        from lib.trackers import make_client
        try:
            tracker, _ = make_client(prof, dry=True)
            report(OK, f"bug tracker {kind}: {len(tracker.open_issues())} open items readable, I am '{tracker.me()['name']}'")
            wf = prof.get("workflow") or {}
            if wf:
                warns = tracker.validate(wf)
                for w in warns:
                    report(WARN, f"workflow: {w}")
                if not warns:
                    report(OK, "workflow: queues and states match the tracker")
        except SystemExit:
            report(BAD, f"bug tracker {kind}: connection failed (see error above)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project")
    ap.add_argument("--platform", choices=PLATFORMS)
    ap.add_argument("--quick", action="store_true", help="skip sheet and tracker network checks")
    a = ap.parse_args()
    check_kit()
    if a.project:
        check_project(a.project, a.platform, a.quick)
    print("\nAll good." if problems == 0 else f"\n{problems} problem(s) to fix.")


if __name__ == "__main__":
    main()
