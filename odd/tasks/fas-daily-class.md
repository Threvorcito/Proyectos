# FAS Daily Class Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A teacher page listing the official MINED FAS letter sequence, where one click creates a ready, editable "Mi tarea" with the FAS steps for that letter, using only letters already taught.

**Architecture:** Pure data modules (`homework/fas_sequence.py`, `homework/fas_content.py`) plus a builder (`homework/fas_lessons.py`) that creates a normal `Task` with existing step types through `services.append_step`. No new models: a letter's status is derived from the teacher's active tasks whose dictado step has that `letter`.

**Tech Stack:** Django, Django test runner.

**Spec:** `docs/superpowers/specs/2026-10-21-clase-fas-del-dia-design.md`

**Feature branch:** `feat/fas-daily-class`, cut from `feat/fas-dictation` (`9fc5958`) because it reuses the dictado step.

**Delivery strategy:** `ask-on-risk`. Forecast ≈ 600–800 authored lines (much of it content data).

## Global Constraints

- Official order (MINED Tomo I, PDF p38): i, u, y → a, e, o → m, p, b, v → s, c, z → l, n → f, t, d → r, rr → ñ, ll, y, h, ch → k, c, q, g, j. x and w apart; h before ch.
- One entry per grapheme at its first position (c only in the s, c, z group; the consonant y only in the ñ group; the vowel-group y is skipped).
- Content exists for m, p, b, v, s, c, z, l, n, f, t, d. Other consonants are listed without a create button; vowels are labelled "Aprestamiento".
- Every word, sentence and reading for letter X uses only vowels (a e i o u, accents allowed) and consonants up to and including X in the sequence (compare with accents removed, case-insensitive, on `writing.split_units(..., 'letter')` units; punctuation ignored).
- Every word for X contains X as a unit.
- New child-facing copy has no second-person verbs (neither "tú" nor "vos"/"usted" forms); use impersonal phrasing, e.g. "El sonido de hoy: mmm. ¿Qué palabras tienen este sonido?".
- Code in English; UI copy in Spanish. Test command: `DB_ENGINE=sqlite python manage.py test` (global Python).

## Review Focus

1. A content word sneaks in a letter not yet taught ("mesa" in the m lesson needs s, which comes later): the bank test must catch it.
2. Clicking "Crear clase" twice: a second task is created (allowed), and the page still shows one status per letter.
3. A teacher without task permission, a student or a parent opens the sequence page or posts the create URL: denied like `task_create`.
4. A letter outside the content (e.g. "r") or an unknown slug posted to the create URL: 404, no task created.
5. "Lengua y Literatura" subject missing in the DB: the create view shows a clear error message instead of crashing.

---

### Task 1: Official sequence and content bank

Route: delegated writer.

**Files:**
- Create: `homework/fas_sequence.py`, `homework/fas_content.py`, `homework/tests_fas_content.py`

**Interfaces:**
- `homework.fas_sequence`:
  - `VOWELS = ('a', 'e', 'i', 'o', 'u')`
  - `GROUPS: tuple[tuple[str, tuple[str, ...]], ...]` — `(label, letters)` in official order, labels in Spanish as in the tome (e.g. `('Consonantes bilabiales', ('m', 'p', 'b', 'v'))`); the vowel groups first, labelled with "Aprestamiento" in the label.
  - `CONSONANTS: tuple[str, ...]` — consonant graphemes in order, de-duplicated per Global Constraints.
  - `known_letters(letter: str) -> frozenset[str]` — vowels + consonants up to and including `letter`; raises `KeyError` for a letter not in `CONSONANTS`.
- `homework.fas_content`:
  - `@dataclass(frozen=True) LetterLesson: letter: str; words: tuple[str, ...] (exactly 6); sentences: tuple[str, ...] (exactly 2); build_word: str; reading: str`
  - `LESSONS: dict[str, LetterLesson]` for m, p, b, v, s, c, z, l, n, f, t, d.
  - `lesson_for(letter: str) -> LetterLesson | None`

- [x] **Step 1: failing tests** in `homework/tests_fas_content.py` (`SimpleTestCase`):
  - `test_sequence_order`: `CONSONANTS[:4] == ('m', 'p', 'b', 'v')`, `'h'` comes before `'ch'`, each grapheme appears once.
  - `test_known_letters`: `known_letters('m') == frozenset('aeioum')`; `'s' not in known_letters('v')`; `known_letters('r')` raises nothing; `known_letters('x')` raises `KeyError`.
  - `test_lessons_cover_m_to_d`: `set(LESSONS) == {'m','p','b','v','s','c','z','l','n','f','t','d'}`.
  - `test_lessons_use_only_known_letters` (RF 1): for every lesson, every unit of every word, sentence, `build_word` and the reading's words is in `known_letters(letter)` (accent-stripped, casefolded). Failure message names the lesson, the text and the offending unit.
  - `test_words_contain_letter`: each of the 6 words contains the lesson letter as a unit.
  - `test_payloads_validate`: for every lesson, `clean_payload` accepts `palabras {'words': words}`, `arma {'text': build_word, 'unit': 'syllable'}`, `arma {'text': sentences[0], 'unit': 'word'}`, `lectura {'text': reading}`, `dictado {'letter', 'words': words[:5], 'sentences': sentences}`.
- [x] **Step 2: run** `DB_ENGINE=sqlite python manage.py test homework.tests_fas_content` → FAIL.
- [x] **Step 3: implement.** Author the content: common, concrete, child-friendly Spanish words (Nicaragua), 1–3 syllables, letter in different positions where possible; sentences 3–6 words; reading 2–4 short sentences. Iterate until the tests pass — fix content, never loosen tests.
- [x] **Step 4: run** `DB_ENGINE=sqlite python manage.py test homework` → PASS.
- [x] **Step 5: commit** `feat(homework): official FAS letter sequence and lesson content bank`

### Task 2: Daily class builder and Secuencia FAS page

Route: delegated writer.

**Files:**
- Create: `homework/fas_lessons.py`, `templates/homework/teacher/fas_sequence.html`, `homework/tests_fas_lessons.py`
- Modify: `homework/views_teacher.py`, `homework/urls.py`, `templates/homework/teacher/task_list.html` (link "Secuencia FAS")

**Interfaces:**
- Consumes: `fas_sequence.GROUPS/CONSONANTS/known_letters`, `fas_content.lesson_for`, `services.append_step`.
- Produces:
  - `build_daily_class(teacher: TeacherProfile, letter: str, subject: Subject) -> Task` — atomic; title `f'Clase FAS de la «{letter}»'`; grade `StudentProfile.Grade.FIRST`; steps in order: `mira {'question': f'El sonido de hoy: {sound}. ¿Qué palabras tienen este sonido?'}` (sound from `phonemes.SOUND_TABLE`, else the letter followed by "a" for stops, e.g. "pa"), `palabras {'words': words}`, `arma build_word / syllable`, `arma sentences[0] / word`, `lectura {'text': reading}`, `dictado {'letter', 'words': words[:5], 'sentences': sentences}`. Raises `ValueError` when there is no lesson.
  - `letter_statuses(teacher) -> dict[str, str]` — `'created'` or `'assigned'` per letter, from the teacher's active tasks whose dictado step has that letter (assigned wins); one or two queries.
  - URLs: `homework:fas_sequence` at `secuencia-fas/` (GET), `homework:fas_class_create` at `secuencia-fas/<str:letter>/crear/` (POST only) → redirect to `homework:task_detail` with a success message `'Clase de la «m» creada. Revísela y asígnela a sus alumnos.'` (match the voice of existing teacher messages if they use "puedes"; keep consistent with them).
  - Subject: the `Subject` named "Lengua y Literatura"; if missing, redirect back with an error message (RF 5).
- [x] **Step 1: failing tests** in `homework/tests_fas_lessons.py` (reuse `TeacherTaskTestCase` from `homework/tests_student.py` / existing fixtures):
  - `test_build_daily_class_steps`: for "m" → 6 steps with types `mira, palabras, arma, arma, lectura, dictado`, dictado letter `'m'`, task grade FIRST.
  - `test_build_unknown_letter`: `ValueError` for "r".
  - `test_sequence_page_lists_groups`: GET → 200, shows "Aprestamiento", every consonant, a create form for "m" and none for "r".
  - `test_create_posts_and_redirects`: POST for "m" → redirect to the new task's detail; task exists.
  - `test_status_after_create_and_assign`: after create → "Clase creada" for m; after `assign_students` → "Asignada".
  - `test_double_create` (RF 2): two POSTs → two tasks; page shows m once.
  - `test_permissions` (RF 3): student, parent and a teacher without task permission are denied on both URLs (same response as `task_create`); GET on create URL → 405.
  - `test_unknown_letter_404` (RF 4): POST for "r" and for "qq" → 404, no task.
  - `test_missing_subject` (RF 5): with "Lengua y Literatura" deleted → redirect to the sequence page with an error message, no task.
- [x] **Step 2: run** `DB_ENGINE=sqlite python manage.py test homework.tests_fas_lessons` → FAIL.
- [x] **Step 3: implement** per Interfaces; the page groups letters as in the tome, shows the status badge, and a POST button "Crear clase" for letters with a lesson.
- [x] **Step 4: run** `DB_ENGINE=sqlite python manage.py test` → PASS.
- [x] **Step 5: commit** `feat(homework): Secuencia FAS page that builds a daily FAS class`

### Task 3: Browser verification

Route: inline (parent). Teacher opens Secuencia FAS, creates the m class, reviews the task detail and preview, assigns it; status shows "Asignada".

## Progress

| Task | Status | Commit | Checks | Review tier |
|---|---|---|---|---|
| T1 | done | ed9b303 (+ label fix 36a8e0e) | RED: ModuleNotFoundError homework.fas_content; GREEN: tests_fas_content 7 OK; homework 300 OK | |
| T2 | done | 566781f | RED: ModuleNotFoundError homework.fas_lessons; GREEN: tests_fas_lessons 15 OK; full suite 574 OK | |
| T3 | done | (this commit) | Browser: Secuencia FAS shows tome groups, vowels as Aprestamiento, r onward "Contenido en preparación"; "Crear clase" for p → task with 6 FAS steps and success message; assigned to 2 students → p "Asignada" (m "Asignada" from the earlier dictado task). Found and fixed: palabras step had no summary on task detail (pre-existing); full suite 574 OK | n/a |

## Next step

- Teacher review of the content bank (weak words: pomo, mimo, boa; "Papá bebe café").
- Content for r onward; vowel (aprestamiento) activities.
- Calendar by dates when the teacher's calendar arrives.
