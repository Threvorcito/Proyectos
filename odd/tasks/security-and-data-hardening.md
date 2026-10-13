# Security and data hardening

## Objective
Fix the 19 findings from the 2026-10-13 repo audit: login brute-force, roster exposure, privilege escalation, committed database, unsafe settings, data races, missing transactions, point farming, tests, and lean cleanup.

## Why
The platform serves minors (grades 1-3). The audit found that any visitor can enumerate students and log in as them, an ADMIN-role user can become superuser, and several data bugs break student progress.

## Scope / constraints
- Branch: `fix/security-and-data-hardening` (from `main` at e978fd2).
- Tests run with the global Python: `DB_ENGINE=sqlite python manage.py test` (repo `venv/` is broken).
- Git history is NOT rewritten; tracked SQLite files are only untracked. Password rotation is a human action.
- Delivery strategy: `ask-on-risk`. Forecast ~600-900 authored lines; slicing decision deferred to PR time.

## Tasks
- [x] T1 Untrack SQLite DBs, remove lock file, dead `myapp/`, unused crispy deps, pin Django version (findings 6, 18, 19)
- [x] T2 Safe settings defaults: DEBUG False by default, require SECRET_KEY when not DEBUG, secure cookies/HSTS when not DEBUG; fast hasher for tests (7, 17)
- [x] T3 Privilege escalation: drop `is_superuser` from admin form, `is_staff` only by superusers; single teacher password (4, 5)
- [x] T4 Per-account login lockout (DB/cache backed) for visual-key and PIN/password login (1, 2)
- [ ] T5 Roster exposure on public student login flow (3) — needs product decision
- [ ] T6 `ensure_games` stops overwriting admin edits and stops writing on GET (8)
- [ ] T7 Progress race + point farming: unique constraints, atomic, F() updates, points only on first completion, server-side game score sanity (9, 13)
- [ ] T8 Transactions in quick student creation and admin delete audit order (12)
- [ ] T9 Admin plan teacher assignment; tutor password shown on creation (10, 11)
- [ ] T10 Report N+1 queries; JSON endpoints return 400 on bad input; unreachable branch removal (15, 16, 18)

Each task closes with its own regression tests (14) and a work-unit commit.

## Route log
| Task | Route | Evidence | Commit | Review tier |
|------|-------|----------|--------|-------------|
| T1 | delegated | writer | 5502f6e | pending |
| T2 | delegated | writer | 3578cd6 | pending |
| T3 | delegated | writer | 41f74ad | pending |
| T3b | delegated | writer | ef48832 | pending |
| T4 | delegated | writer | `fix(auth): lock accounts after repeated failed logins` | pending |

## Follow-ups noted
- Done in T3b: staff switch is rendered only when the form has `is_staff`; the dead "Superusuario" switch is removed; `seed_demo` no longer sets `TeacherProfile.set_password` (verified against a throwaway SQLite via `SQLITE_NAME`).
- Role ADMIN set by a non-superuser admin still implies `is_staff=True` in `AdminUserCreationForm.save` (by design).
- `TeacherCreationForm` still stores a pending profile password because the account is created lazily on first login; that login moves it to `CustomUser` and clears the profile hash.

## T4 notes
- Lockout lives in `accounts.LoginAttempt` (DB table) via `accounts/lockout.py`: no CACHES are configured, so the default LocMemCache would be per-process and reset on restart. Keys: `student:<id>` (visual key), `user:<pk>` for password login (username and email share one counter), `login:<identifier>` for unknown identifiers. The session attempt counter was removed as redundant.
- Known trade-off: anyone can lock a student for 15 minutes by guessing wrong; T5 classroom code limits who can reach the visual-key step.

## Next step
T5.
