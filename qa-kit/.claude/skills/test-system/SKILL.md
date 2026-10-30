---
name: test-system
description: System testing - validate the whole app end to end in near-real conditions (journeys across modules, persistence, interruptions, network, install/upgrade). Used by /qa ... system.
user-invocable: false
---

# System testing

Goal: the app works as one complete system, not only feature by feature.

## Scenario source
- If a module with system TCs is selected (`module=`), run them like test-functional.
- Otherwise derive 5-15 scenarios (IDs SYS_01...) from the SRS + notes and show the list to Min for approval first.

## Scenario areas (pick what applies)
- End-to-end journeys across modules (e.g. sign up -> join community -> livestream -> viewer chats -> notification).
- State & persistence: kill/relaunch, logout/login, data consistent everywhere it is shown.
- Interruptions: background/foreground, screen lock, rotation, incoming call (ask Min to trigger it).
- Network: offline mid-action, wifi <-> mobile data switch, recovery and retry, no duplicate submissions.
- Install/upgrade: upgrade from the previous build keeps data (only if a previous build is provided).
- Long session / large data: long lists, big media, `time=` minutes of use. Report timings in seconds
  (timestamp before/after), never vague words like "slow".
- Visible security basics: session expiry, logout clears data, sensitive content hidden in notifications/app switcher.

## Recording
One results.csv row per scenario. Bugs found here get the module where the symptom appears.
