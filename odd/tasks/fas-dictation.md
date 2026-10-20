# FAS Dictation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Dictado" homework step (5 words + 2 sentences for one FAS letter) that the child builds with tiles, scored by a 3-criterion FAS checklist that yields a per-child break point for the teacher.

**Architecture:** New `TaskStep.StepType.DICTADO` inside the existing homework flow (`Task → TaskStep → TaskAssignment → StepResult`, one `StepResult` per item, 7 items). Pure scoring logic lives in a new `homework/dictation.py`; the break point is computed on read, never stored. Teacher sees it in the task report and in a printable instrument; parents see nothing new (Ley 787).

**Tech Stack:** Django, Django test runner, vanilla JS (`static/js/homework/`), Web Speech API via existing `data-speak-text`.

**Spec:** `docs/superpowers/specs/2026-10-20-dictado-fas-design.md`

**Feature branch:** `feat/fas-dictation` (cut from `552e835`, top of the unmerged `fix/security-and-data-hardening` chain, because the homework app only exists there).

**Delivery strategy:** `ask-on-risk`. Forecast ≈ 700–900 authored lines, so the chain strategy will be asked before the PR.

## Global Constraints

- Identifiers and code in English; UI strings, choice labels and URL paths in Spanish (project convention).
- Child-facing copy never shows numbers, "error" or "mal" (`homework/copy.py` rule).
- Parents never see answers, difficulties, levels or break points (`dashboard/views.py:1163`, `homework/permissions.py:20`).
- Dictation is exactly 5 words and 2 sentences.
- Thresholds (spec §4): sound-letter achieved if the letter is right in ≥4 of 5 words; words achieved if ≥4 of 5 words are correct on the first try; sentences achieved if both sentences end correct within `MAX_ATTEMPTS` (i.e. not modeled).
- Break point = first non-achieved criterion in order sound-letter → words → sentences; "Sin quiebre" if all achieved; "Incompleto" if any of the 7 items is not completed.
- Test command: `DB_ENGINE=sqlite python manage.py test homework` (global Python; repo `venv/` is broken).

## Review Focus

1. Uppercase or accented words ("Mamá", "María"): the letter check and tile check must casefold and keep accents as the teacher typed them.
2. Digraph letters ("ll", "rr", "ch", "qu") as the dictation letter: the letter check works on `word_units`, not on single characters.
3. A child omits a different letter ("mesa" → "msa"): the target letter "m" still counts as right (alignment, not raw index).
4. The child reloads mid-dictation: the page resumes at the first unfinished item.
5. The sentence has punctuation ("Mi mamá me ama."): word tiles come from `split_units(text, 'word')`, so punctuation never becomes a tile.

---

### Task 1: Dictation domain — step type, payload, item model, scoring, break point

Route: delegated writer (2+ non-trivial files).

**Files:**
- Modify: `homework/models.py` (StepType + `item_count`), `homework/payloads.py` (`_clean_dictado`), `homework/evaluation.py` (dictado branch), `homework/services.py` (`EVALUATED_STEP_TYPES`)
- Create: `homework/dictation.py`, `homework/migrations/00XX_taskstep_dictado.py` (via `makemigrations`)
- Test: `homework/tests_dictation.py`

**Interfaces:**
- Produces:
  - `TaskStep.StepType.DICTADO = 'dictado'`, label `'Dictado'`; `item_count == 7` for it.
  - Payload shape: `{'letter': str, 'words': list[str] (5), 'sentences': list[str] (2)}`.
  - `homework.dictation`:
    - `WORDS = 5`, `SENTENCES = 2`, `ITEMS = 7`
    - `item_target(payload: dict, item_index: int) -> BuildTarget` — index 0–4 → `BuildTarget('', word, '', 'letter')`, 5–6 → `BuildTarget('', sentence, '', 'word')`; raises `IndexError` outside 0–6.
    - `letter_ok(word: str, answer: str, letter: str) -> bool`
    - `class BreakPoint(TextChoices)`: `INCOMPLETE='incomplete','Incompleto'`, `SOUND_LETTER='sound_letter','Sonido-letra'`, `WORDS='words','Palabras'`, `SENTENCES='sentences','Oraciones'`, `NONE='none','Sin quiebre'`
    - `@dataclass Criteria: sound_letter: bool; words: bool; sentences: bool`
    - `score(payload: dict, results: Mapping[int, StepResult]) -> tuple[BreakPoint, Criteria | None]` — `results` keyed by item_index; `Criteria` is `None` when incomplete.

- [ ] **Step 1: Write failing tests in `homework/tests_dictation.py`** (`SimpleTestCase` for pure logic, `TeacherTaskTestCase`/`StudentTaskTestCase` from `homework/tests_student.py` for the step):
  - `test_clean_dictado_normalizes`: `clean_payload('dictado', {'letter': ' M ', 'words': ['mesa','mamá','cama','lima','humo'], 'sentences': ['Mi mamá me ama.', 'Amo a mi mamá.']})` returns `letter == 'm'` and the same lists stripped.
  - `test_clean_dictado_rejects`: raises `ValidationError` for 4 words, 6 words, duplicate words, a word with a space, a word without the letter ("sol" with letter "m"), 1 sentence, a one-word sentence, a letter with digits, an empty letter.
  - `test_item_count_is_seven`: a saved dictado step has `item_count == 7`.
  - `test_item_target`: index 0 → unit `'letter'`, text `'mesa'`; index 6 → unit `'word'`, text `'Amo a mi mamá.'`; index 7 raises `IndexError`.
  - `test_letter_ok`: `letter_ok('mesa','mesa','m')` True; `letter_ok('mesa','nesa','m')` False; `letter_ok('mesa','msa','m')` True (Review Focus 3); `letter_ok('Mamá','mamá','m')` True (RF 1); `letter_ok('calle','cale','ll')` False and `letter_ok('calle','calle','ll')` True (RF 2); `letter_ok('mesa','','m')` False.
  - `test_score_incomplete`: 6 completed results → `(BreakPoint.INCOMPLETE, None)`.
  - `test_score_sound_letter`: 2 of 5 words with the letter wrong in `first_answer` → `SOUND_LETTER`.
  - `test_score_words`: letter right in all 5 but only 3 `first_try_correct` → `WORDS`.
  - `test_score_sentences`: words fine, one sentence `modeled=True` → `SENTENCES`.
  - `test_score_none`: everything right → `(BreakPoint.NONE, Criteria(True, True, True))`.
  - `test_submit_dictado_word_and_sentence`: student posts `{'item_index': 0, 'tiles': ['m','e','s','a']}` → status `'correct'`; posts `{'item_index': 5, 'tiles': [...]}` wrong twice → `'modeled'`; `mark_item_done` on a dictado step raises `InvalidAnswer`.
  - `test_submit_dictado_sentence_punctuation`: tiles `['Mi','mamá','me','ama']` for "Mi mamá me ama." → `'correct'` (RF 5).

- [ ] **Step 2: Run** `DB_ENGINE=sqlite python manage.py test homework.tests_dictation` → FAIL (module/step type missing).

- [ ] **Step 3: Implement.**
  - `models.py`: add `DICTADO`; `item_count` returns `dictation.ITEMS` for it (import inside the property to avoid a cycle if needed).
  - `payloads.py`: `_clean_dictado(data)`; letter: `_text`, stripped, casefolded, 1–3 letters only (`str.isalpha`); words: `_unique(_text_list(...))`, exactly `WORDS`, each a single word (`split_units(w, 'letter')` must not raise, ≤ `BUILD_MAX_UNITS` units) and containing the letter as a unit (casefold compare on `word_units`); sentences: `_text_list`, exactly `SENTENCES`, each 2..`BUILD_MAX_UNITS` words via `split_units(s, 'word')`. Register in `_CLEANERS`. Error copy in Spanish, e.g. `'Dictado: escribe exactamente 5 palabras distintas.'`, `'Cada palabra del dictado debe tener la letra «m».'`.
  - `dictation.py`: `letter_ok` aligns `split_units(word,'letter')` with `split_units(answer,'letter')` (casefolded) using `difflib.SequenceMatcher(autojunk=False)`; True iff every unit index of the target letter falls inside an `'equal'` opcode. Empty/unsplittable answer → False. `score` follows Global Constraints thresholds using `first_answer`, `first_try_correct`, `modeled`, `completed_at`.
  - `evaluation.py`: split `_evaluate_build(step, payload)` into `_evaluate_build_target(target: BuildTarget, payload) -> Evaluation` plus the existing wrapper; in `evaluate`, `if step.step_type == DICTADO:` validate index (`InvalidAnswer('item')`) and call `_evaluate_build_target(item_target(step.payload, item_index), payload)`. The omission hint must not reveal the word's spelling beyond the missing sound (reuse `_missing_sound`).
  - `services.py`: add `DICTADO` to `EVALUATED_STEP_TYPES`.
  - `python manage.py makemigrations homework` (choices-only `AlterField`).

- [ ] **Step 4: Run** `DB_ENGINE=sqlite python manage.py test homework` → all PASS.

- [ ] **Step 5: Commit** `feat(homework): dictado step type with FAS break-point scoring`

### Task 2: Teacher authoring and child dictation screen

Route: delegated writer.

**Files:**
- Modify: `homework/forms.py` (`DictadoStepForm`, `STEP_FORMS`), `homework/views_teacher.py` (`_summary`, preview), `homework/views_student.py` (`step_context`, `_done_items`, `_instruction_key`), `homework/copy.py` (`INSTRUCTIONS['dictado']`), `templates/homework/student/step.html`, `templates/homework/teacher/task_preview.html`, `static/js/homework/task-player.js` and/or `tiles.js`, `static/css/homework.css`
- Create: `templates/homework/steps/dictado.html`
- Test: `homework/tests_dictation_views.py`

**Interfaces:**
- Consumes: `dictation.item_target`, `ITEMS`, `writing.build_tiles`, `split_units`.
- Produces: `step_context(step)` returns `{'dictado': {'letter': str, 'items': [{'index': int, 'unit': 'letter'|'word', 'say': str, 'tiles': list[str]}]}}` for dictado steps (tiles seeded `step.task_id * 1000 + step.pk + index`).

- [ ] **Step 1: Write failing tests:**
  - `test_teacher_creates_dictado`: POST to `homework:step_create` with `step_type='dictado'`, `letter='m'`, `words` (5 lines), `sentences` (2 lines) → step saved with the normalized payload; invalid (4 words) re-renders with the Spanish error.
  - `test_dictado_in_step_type_menu`: `task_detail` context `step_types` includes `('dictado', 'Dictado')`.
  - `test_student_step_renders_listen_not_text`: GET the student step → contains one `data-speak-text="mesa"` button per word and does **not** render `mesa` as visible item text (assert the visible label/heading blocks don't include it — check the template's item markup class).
  - `test_student_resumes_dictado`: after completing items 0–2, GET the step → `done_items == {0,1,2}` in context (RF 4).
  - `test_preview_renders_dictado`: teacher preview of the task returns 200 and shows the 7 items.
- [ ] **Step 2: Run** `DB_ENGINE=sqlite python manage.py test homework.tests_dictation_views` → FAIL.
- [ ] **Step 3: Implement.**
  - `DictadoStepForm(StepForm)`: `step_type='dictado'`; fields `letter` (CharField, max 3, label `'Letra o sonido que se estudia'`), `words` (Textarea, `'5 palabras (una por línea)'`), `sentences` (Textarea, `'2 oraciones (una por línea)'`); `to_payload` splits lines, drops blanks; `initial_from` joins with `'\n'`.
  - Child copy: `INSTRUCTIONS['dictado'] = 'Escucha y arma lo que oyes con las fichas.'`
  - `dictado.html`: one item at a time (hidden others), a big listen button (`partials/listen_button.html` with the item's `say`; can replay), the tile tray (reuse `homework/partials/tiles.html` markup), "Listo" posts `{item_index, tiles}` to `answer_url`; on `correct`/`modeled` move to the next unfinished item; `try_again` shows the hint as arma does. Items in `done_items` start hidden/completed. Never print the target text.
  - JS: extend the existing player instead of a new file if it already supports multi-item steps (palabras/ejemplo); otherwise add a small `dictado` handler in `task-player.js`. Bump the `?v=` query strings you touch.
  - `_done_items`: include `DICTADO`.
- [ ] **Step 4: Run** `DB_ENGINE=sqlite python manage.py test homework` → all PASS.
- [ ] **Step 5: Commit** `feat(homework): teacher dictado form and child dictation screen`

### Task 3: Teacher break-point report and printable instrument

Route: delegated writer.

**Files:**
- Modify: `homework/reports.py` (`task_rows`, `break_point_groups`), `homework/views_teacher.py` (`task_report`, new `dictation_instrument`), `homework/urls.py`, `templates/homework/teacher/task_report.html`, `templates/homework/teacher/task_detail.html` (link to instrument)
- Create: `templates/homework/teacher/dictation_instrument.html`
- Test: `homework/tests_dictation_report.py`

**Interfaces:**
- Consumes: `dictation.score`, `BreakPoint`, `Criteria`.
- Produces:
  - Each `task_rows` row gains `'break_point': BreakPoint | None` (None when the task has no dictado step; uses the task's first dictado step) and `'criteria': Criteria | None`. Still a fixed number of queries.
  - `break_point_groups(rows) -> list[tuple[str, list]]` — label → students, ordered `SOUND_LETTER, WORDS, SENTENCES, INCOMPLETE, NONE`, empty groups omitted.
  - URL `homework:dictation_instrument` at `tareas/<int:pk>/dictado/<int:step_pk>/instrumento/` (match the existing teacher URL prefix style in `homework/urls.py`).
- [ ] **Step 1: Write failing tests:**
  - `test_task_rows_break_point`: two assigned students, one finished with sound-letter failures, one not started → rows carry `SOUND_LETTER` and `INCOMPLETE`.
  - `test_task_rows_query_count`: `assertNumQueries` stays the same for 1 and 3 assignments.
  - `test_report_groups_by_break_point`: `task_report` response shows group headings `Sonido-letra` and `Incompleto` with the right student names.
  - `test_instrument_lists_items_and_students`: GET instrument → 200, contains the letter, 5 words, 2 sentences, every assigned student's name, and the three criterion headers.
  - `test_instrument_permissions`: another teacher → same denial as `task_report`; a parent or student → denied.
  - `test_parent_dashboard_hides_break_point`: parent of a scored student → `dashboard:parents` response contains none of the `BreakPoint` labels (Ley 787 guard).
- [ ] **Step 2: Run** `DB_ENGINE=sqlite python manage.py test homework.tests_dictation_report` → FAIL.
- [ ] **Step 3: Implement.** Instrument page: printable (`@media print` hides nav), header with letter, numbered words and sentences, a table with one row per assigned student, 7 item columns (blank boxes for paper use, pre-marked ✓/✗ from `first_try_correct` when the child already did it in the app), and 3 criterion columns plus "Punto de quiebre". Report: add a "Punto de quiebre" column and a grouped section "Agrupar para reforzar" above the table.
- [ ] **Step 4: Run** `DB_ENGINE=sqlite python manage.py test homework dashboard` → all PASS.
- [ ] **Step 5: Commit** `feat(homework): FAS break point in task report and printable dictation instrument`

### Task 4: Browser verification

Route: inline (parent).

- [ ] Seed or create a dictado task as a teacher, do it as a student in mobile viewport, open the report and the instrument; screenshot each.

## Progress

| Task | Status | Commit | Checks | Review tier |
|---|---|---|---|---|
| T1 | pending | | | |
| T2 | pending | | | |
| T3 | pending | | | |
| T4 | pending | | | |

## Next step

T1.
