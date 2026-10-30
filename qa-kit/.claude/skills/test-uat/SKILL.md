---
name: test-uat
description: User acceptance testing - run business scenarios from user stories and acceptance criteria with realistic data, then prepare an acceptance recommendation and sign-off table for humans. Used by /qa ... uat.
user-invocable: false
---

# UAT

UAT checks the product meets business needs from the end user's point of view. Final acceptance is a human
decision: the agent prepares evidence and a recommendation and never signs off.

## Inputs
`projects/<p>/docs/uat.md` (user stories + acceptance criteria) or a UAT tab in the sheet (`module=`).
Otherwise derive scenarios from the SRS and get Min's confirmation of the list first (IDs UAT_01...).

## Steps
1. For each story, write the scenario as Given/When/Then and run it with realistic data and personas from notes.md
   (no "aaa"/"test123" data).
2. Judge every acceptance criterion: met / not met / partially met, with evidence.
3. Record usability friction even when the criterion is met (Note "friction: ..."). It is not a bug unless it blocks the goal.
4. Status per story: pass = all criteria met, fail = any not met, blocked = cannot verify.

## report.md extras
- Story table: story | criteria met x/y | status | bugs
- Open bugs blocking acceptance
- Recommendation: "Ready for acceptance" or "Not ready", with reasons
- Sign-off table left blank: Role | Name | Decision | Date
