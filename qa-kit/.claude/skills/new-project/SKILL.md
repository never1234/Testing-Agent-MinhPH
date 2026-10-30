---
name: new-project
description: Add a new project to the QA kit (profile.yaml, notes.md, modules). Use for /new-project or when Min wants to set up testing for a new app or website.
argument-hint: <project-name>
---

# New project

1. Run `.venv/bin/python scripts/new_project.py $ARGUMENTS`.
2. Ask Min in ONE message for what is still unknown (skip anything he already gave or that is in attached docs):
   - platforms and app id / bundle id / URL, device names
   - test cases: Excel file path or Google Sheet link (extract the id from the link), header names of its columns
   - status dropdown values in the sheet (Passed/Failed/... )
   - bug tracker: sheet / trello (board link, list name) / jira (project key, cloud or server) / mantis (project id)
   - test account aliases (A, B...) and which device uses which
   - SRS / user stories / design files to put in `projects/<name>/docs/`
3. Fill `profile.yaml` and `notes.md`. Tell Min the exact `.env` variable NAMES to add (never ask him to paste secrets in chat).
4. If the test sheet already exists, run `.venv/bin/python scripts/check_setup.py --project <name>`: it lists all tabs.
   Propose a `modules:` entry per test tab (id = short uppercase code, id_prefix = the prefix used in that tab's IDs).
5. Re-run check_setup until it reports "All good" (or only items Min must do himself), and summarize what's left.
