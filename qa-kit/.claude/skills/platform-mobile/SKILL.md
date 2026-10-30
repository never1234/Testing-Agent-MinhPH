---
name: platform-mobile
description: How to drive Android and iOS real devices with mobile-mcp in this QA kit. Load whenever a test runs on android or ios.
user-invocable: false
---

# Mobile platform (mobile-mcp)

## Before testing
1. List devices via mobile-mcp. Match `profile.platforms.<p>.device_name`. If several match or none, ask Min.
2. Check the app (app_id / bundle_id) is installed. If `build_path` is set (Android): `adb -s <serial> install -r <apk>`.
   iOS builds: ask Min to install via TestFlight/Xcode.
3. Record the app version for the report. Android: `adb -s <serial> shell dumpsys package <app_id> | grep versionName`.
   iOS: read it from the app's About/Settings screen or ask Min.
4. Fresh start per module: terminate and launch the app, unless a TC needs the previous state.
5. Log in with the platform's account: `.venv/bin/python scripts/get_account.py --project <p> --account <alias>`.

## Interacting
- Read the element tree first; target by text or accessibility id. Use coordinates only as a fallback and say so.
- After every action, confirm the screen changed as expected before the next one.
- If Unicode (Vietnamese) typing fails, retry once, then use ASCII test data and note it.
- Keyboard covering elements: Android back key / iOS tap outside or Return.
- Permission dialogs: grant by default unless the TC tests denial.

## Android helpers (always pass `-s <serial>`)
- Logs on fail/crash: `adb -s <serial> logcat -d -t 300 > <run>/evidence/<TC>_android_logcat.txt` and `adb -s <serial> logcat -b crash -d`
- Network: `adb -s <serial> shell svc wifi disable|enable`, `svc data disable|enable` (if refused, ask Min to toggle)
- Background/foreground: home key, wait, relaunch via mobile-mcp
- Deep link: `adb -s <serial> shell am start -a android.intent.action.VIEW -d "<url>"`

## iOS notes
- No logcat. On crash: record the exact time, screenshot, and ask Min to export the crash log from Xcode > Devices.
- WebDriverAgent can disconnect. On WDA errors, ask Min to restart it instead of retrying blindly.

## Crash / freeze / ANR
Screenshot + logs, mark the TC fail with severity critical, relaunch the app, continue with the next TC.
3 crashes in a row -> stop and tell Min.
