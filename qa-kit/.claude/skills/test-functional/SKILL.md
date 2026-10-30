---
name: test-functional
description: Execute functional test cases from the project's test sheet on a device or browser and record results. Used by /qa ... functional.
user-invocable: false
---

# Functional testing

1. Export the TCs:
   `.venv/bin/python scripts/read_testcases.py --project <p> --platform <pl> --module <m> --filter <filter or pending> [--ids ...] [--priority ...]`
   Tell Min how many will run. If more than 40, propose splitting by module and confirm.
2. TCs starting with `[Manual]` or listed as manual in notes -> status skip, note "manual".
3. For each TC (batch size `batch=` or 10):
   a. Set up the precondition. b. Execute. c. Compare with Expected literally - a partial match is a fail,
   and the Note states the exact difference. d. Append the row to results.csv immediately.
   e. On fail: re-run once, capture evidence, add a bug to bugs.json. Several TCs with the same root symptom
   share one bug (reuse the local id).
4. Note wording: fail -> "Actual: ...", blocked -> "Blocked: <reason>", pass -> empty unless there is an observation.
5. Progress line after each batch, e.g. "Batch 2/5: 8 pass, 1 fail (B2), 1 blocked".
