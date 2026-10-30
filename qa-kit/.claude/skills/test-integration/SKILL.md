---
name: test-integration
description: Integration testing - verify interactions between accounts, devices, platforms, backend and third-party services (sync, calls, notifications, deep links). Used by /qa ... integration.
user-invocable: false
---

# Integration testing

## Setup
- Roles from `profile.integration.roles` (actor / observer) or the TC. State the mapping before starting,
  e.g. "Actor = Android/A (Xiaomi), Observer = iOS/B (iPhone)".
- Both devices must be ready (check_setup). Use `platform=all` or the platforms named in the roles.

## Patterns
1. Cross-device sync: action on actor -> verify on observer (10s x 3 checks). Then swap roles and repeat.
2. Cross-platform: same account on mobile and web; change on one, verify on the other.
3. Backend: if `profile.api.base_url` is set, confirm with read-only GET requests that the UI action persisted.
   Never call mutating endpoints unless the TC says so.
4. Third-party: push notifications (observer in background and locked), deep links, share sheet,
   social login, payment sandbox.
5. Ordering & concurrency: rapid actions from both sides; check order, duplicates, unread counters.

## Recording
One results.csv row per TC (or INT_xx for derived checks). Fails in only one direction -> fail,
and the Note names the failing direction (e.g. "iOS -> Android OK, Android -> iOS not delivered after 30s").
