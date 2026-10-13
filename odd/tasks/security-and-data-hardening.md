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
- [x] T5 Roster exposure on public student login flow (3) — product decision: classroom code
- [x] T6 `ensure_games` stops overwriting admin edits and stops writing on GET (8)
- [x] T7 Progress race + point farming: unique constraints, atomic, F() updates, points only on first completion, server-side game score sanity (9, 13)
- [x] T8 Transactions in quick student creation and admin delete audit order (12)
- [x] T9 Admin plan teacher assignment; tutor password shown on creation (10, 11)
- [x] T10 Report N+1 queries; JSON endpoints return 400 on bad input; unreachable branch removal (15, 16, 18)

Each task closes with its own regression tests (14) and a work-unit commit.

## Route log
| Task | Route | Evidence | Commit | Review tier |
|------|-------|----------|--------|-------------|
| T1 | delegated | writer | 5502f6e | pending |
| T2 | delegated | writer | 3578cd6 | pending |
| T3 | delegated | writer | 41f74ad | pending |
| T3b | delegated | writer | ef48832 | pending |
| T4 | delegated | writer | 53118fd | pending |
| T5 | delegated | writer | eb70684 | pending |
| T6 | delegated | writer | 29d541a | pending |
| T7 | delegated | writer | 40510b0 | pending |
| T8 | delegated | writer | 9d6f652 | pending |
| T9 | delegated | writer | 230b5ce | pending |
| T10 | delegated | writer | 1540769 | pending |

## Follow-ups noted
- Done in T3b: staff switch is rendered only when the form has `is_staff`; the dead "Superusuario" switch is removed; `seed_demo` no longer sets `TeacherProfile.set_password` (verified against a throwaway SQLite via `SQLITE_NAME`).
- Role ADMIN set by a non-superuser admin still implies `is_staff=True` in `AdminUserCreationForm.save` (by design).
- `TeacherCreationForm` still stores a pending profile password because the account is created lazily on first login; that login moves it to `CustomUser` and clears the profile hash.

## T4 notes
- Lockout lives in `accounts.LoginAttempt` (DB table) via `accounts/lockout.py`: no CACHES are configured, so the default LocMemCache would be per-process and reset on restart. Keys: `student:<id>` (visual key), `user:<pk>` for password login (username and email share one counter), `login:<identifier>` for unknown identifiers. The session attempt counter was removed as redundant.
- Known trade-off: anyone can lock a student for 15 minutes by guessing wrong; T5 classroom code limits who can reach the visual-key step.

## T5 notes
- `TeacherProfile.classroom_code`: 6 chars from `ABCDEFGHJKMNPQRSTUVWXYZ23456789`, unique, auto-generated (migration 0017 backfills existing teachers). Shown on the teacher dashboard with a "Crear código nuevo" action.
- `/cuentas/estudiantes/` asks for the code; a valid code stores teacher id + code in the session and a signed `classroom` cookie (30 days, `teacherpk:code`). The roster is served only when the stored code still matches, so changing ids or regenerating the code denies access. `teacher_id` POSTs are ignored.
- Wrong codes use the T4 lockout keyed `classroom-ip:<REMOTE_ADDR>` with 20 failures / 15 min; the key is never reset on success so a known code cannot refill guesses. Behind a reverse proxy REMOTE_ADDR is the proxy address (shared limit) until proxy headers are trusted.

## T6 notes
- `ensure_games()` reads existing built-in slugs (1 query) and only `get_or_create`s missing ones; existing rows are never updated. Views still call it so a fresh DB gets the games, but a GET with all games present does no writes. A deleted built-in game is recreated on the next visit; admins should deactivate (`is_active`) instead of deleting.

## T7 notes
- Unique constraints: `StudentProgress(student, activity)` and `StudentDifficulty(student, difficulty_type, character_a, character_b, syllable, word)` (the exact `get_or_create` key). Migration `progress/0002` merges duplicates first, keeping the lowest id: progress keeps completed-if-any and max percentage/score/attempts/latest date; difficulty sums `error_count` and keeps the latest date. Verified on a throwaway SQLite with seeded duplicates.
- `register_attempt` runs in `transaction.atomic()` and locks the student row (`select_for_update`), so attempt numbers, progress and points are serialized per student; counters use `F()`. Points/stars/experience are awarded only when progress flips to completed. The activity page says "Ya ganaste los puntos de esta actividad." on repeats.
- Games award no points (only `GameAttempt` rows, score computed server-side 0-100). Anti-farming there is a clamp: `total_questions` is capped at `MAX_GAME_QUESTIONS = 100`.

## T8 notes
- `QuickStudentCreationForm.save` wraps the whole creation (student user, profile, visual key, teacher link, tutor) in `transaction.atomic()`.
- `admin_resource_delete` runs each branch inside `transaction.atomic()`; `delete` audit rows are written after the delete with the pk and label captured beforehand (`write_audit` gained `object_id`/`object_repr`). A `ProtectedError` rolls back and leaves no audit row.

## T9 notes
- `LessonPlanForm(choose_teacher=True)` adds a required `plan_teacher` field (active teachers only); `lesson_plan_create` uses it for admins. Teachers never get the field and always own their plans. Plan edit keeps the current owner.
- New tutors created from `QuickStudentCreationForm` expose `created_parent_credentials`; the teacher students page and admin modal flash "Tutor: <usuario> / Contraseña: <clave>" once, and the quick student page/admin form page render it in the credentials card (quick page now also gets the visual key it already tried to show).
- Removed the unused `TeacherStudentUpdateForm` (the other tutor-creation site; never instantiated).

## T10 notes
- Student report: reading rows annotate `total_questions` and fetch answered/correct counts in one grouped query; query count is constant (test compares 1 vs 5 rows).
- `core/json_payload.py`: `parse_json_object` (dict or None; handles invalid UTF-8/JSON and non-object JSON) and `parse_id`. Game and reading JSON endpoints return `{'saved': False}` with 400 instead of 500; a missing/non-numeric `question_id`/`answer_id` is 400.
- Removed the unreachable `isinstance(instance, (Reading, Game))` branch in `resource_has_history` (both types return earlier). The unused `TeacherStudentUpdateForm` was removed in T9; no other dead code listed in this doc remains.

## Next step
All tasks done. Native review of e978fd2..41f74ad (lineage review-b2e45b1e50be41bf) granted but blocked: `claude` CLI not on PATH; retry once installed, then review T3b-T10. Manual smoke test on a DB copy passed (classroom code flow, teacher dashboard). Then PR/slicing decision (user).
