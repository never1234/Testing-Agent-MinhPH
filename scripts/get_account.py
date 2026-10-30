#!/usr/bin/env python3
"""Print a TEST account's login for Claude to type into the app (Claude must not read .env directly).
Never use this for real/personal accounts.
  .venv/bin/python scripts/get_account.py --project shopx --account A
"""
import argparse

from lib.config import die, env, load_profile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--account", required=True, help="alias from profile.yaml accounts, e.g. A")
    a = ap.parse_args()
    prof = load_profile(a.project)
    acc = (prof.get("accounts") or {}).get(a.account)
    if not acc:
        die(f"Account '{a.account}' not in profile.yaml accounts: {list((prof.get('accounts') or {}).keys())}")
    print(f"account={a.account}")
    for field in ("user", "password", "phone", "otp"):
        var = acc.get(f"{field}_env")
        if var:
            print(f"{field}={env(var)}")
    if acc.get("display_name"):
        print(f"display_name={acc['display_name']}")


if __name__ == "__main__":
    main()
