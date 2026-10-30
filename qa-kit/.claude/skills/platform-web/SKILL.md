---
name: platform-web
description: How to drive web apps with Playwright MCP in this QA kit. Load whenever a test runs on web.
user-invocable: false
---

# Web platform (Playwright MCP)

## Setup
- Base URL `profile.platforms.web.url`; viewports from `viewports` (default 1440x900). Resize with the browser resize tool.
- Fresh state per module (new context / clear storage) unless a TC needs previous state.
- Log in with `.venv/bin/python scripts/get_account.py --project <p> --account <alias>`.

## Interacting
- Use the accessibility snapshot to find elements; screenshots only for visual checks and evidence.
- After navigation, wait until the main content is visible before checking.
- After each TC, read console messages. JS errors -> add to Note as an observation; a fail only if there is a visible impact.
- On fail capture: screenshot, console errors, failed network requests (status >= 400: method, URL, status).

## Do not
- No real payments (sandbox data from notes.md only). No forms that email real people unless notes.md allows it.
