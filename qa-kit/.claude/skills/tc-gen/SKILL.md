---
name: tc-gen
description: Generate test cases from SRS, user stories or designs and append them to the project's test sheet (Excel or Google Sheet). Use for /qa <project> <platform> tc-gen, or whenever Min asks to write or add test cases for a module.
user-invocable: false
---

# Test case generation

Options: `module=<ID>` (one module per run, required), `kind=functional|system|integration|uiux|uat|mixed`
(default functional), `count=<max>`, `focus=<area>`.

## Steps
1. Read sources: `profile.srs` and the module's parts of `docs/` (convert PDF/DOCX to text first and keep it in
   `docs/_text/`), plus notes.md and the module notes.
2. Read existing TCs to avoid duplicates and continue numbering:
   `.venv/bin/python scripts/read_testcases.py --project <p> --module <ID> --platform <any profile platform> --filter all`
3. Draft into `runs/<p>/<date>_tc-gen_<ID>/new_testcases.csv` with headers ID, Description, Expected Result
   (+ Precondition, Steps, Priority, Type only if those columns are configured in profile.yaml).
   Leave ID empty to let the script number them.
4. Show Min: count by area and priority + 5 sample rows. Wait for approval or edits.
5. `.venv/bin/python scripts/append_testcases.py --project <p> --module <ID> --csv <file> --auto-id --dry-run`,
   show the result, then run again without `--dry-run`.

## Writing rules
- One behavior per TC. Description = action + condition ("Send a 1,000-character text message").
  Expected = only observable results.
- Cover: happy path, validation and boundaries, error/empty/loading states, permissions, interruptions
  (background, network loss), effects seen by another account.
- Prefer fewer meaningful TCs over many trivial ones; merge trivial variants into one TC.
- Priority: high = core flow, data loss, security; medium = common alternatives; low = cosmetic or rare.
- Prefix `[Manual]` in Description for TCs the agent cannot execute (audio/video quality, real SMS OTP, physical).
- kind=system: end-to-end journeys across modules + install/upgrade, restart persistence, offline, interruptions.
- kind=integration: interactions between accounts, devices, platforms, backend and 3rd-party services.
- kind=uiux: per screen - layout, copy, states, consistency, accessibility basics.
- kind=uat: business scenarios from user stories; Description as Given/When/Then, Expected = acceptance criterion.
