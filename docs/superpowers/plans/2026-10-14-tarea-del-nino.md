# "Mi tarea de hoy" (Guided Child Tasks) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teachers turn the child part of their Plan Diario into a short step-by-step task that a child with dyslexia completes alone, with FAS phonics decoding and assisted writing, and teachers see per-child difficulties with a suggested SNEPA level.

**Architecture:** A new Django app `homework` owns tasks, steps, assignments and every per-child result; it reads `learning` (teachers, students, subjects, plans) and `readings` (Reading, K1 practice) but neither of them imports it, except `dashboard` (student dashboard card, teacher/parent links). Spanish syllabification, phonemes and tile/omission logic are pure Python modules; the server ships a per-page JSON decode map, so the browser never re-implements syllabification. Child pages are one step per page (server-rendered, resumable) with a small vanilla JS player posting JSON.

**Tech Stack:** Django 6, SQLite/PostgreSQL, Django templates, vanilla JS (no build), Web Speech API via `window.AppSpeech`, Bootstrap 5 classes already loaded.

**Spec:** `docs/superpowers/specs/2026-10-14-tarea-del-nino-design.md`

## Global Constraints

- No new Python or JS dependencies; `requirements.txt` unchanged; no JS framework, no bundler.
- Code, comments, test names and commit messages in English; all UI copy in neutral, child-friendly Spanish.
- Conventional Commits; never add `Co-Authored-By` or any AI attribution.
- Child pages: `body.kid-ui` + `static/css/kid.css` tokens (`--kid-tap: 48px`, `--kid-tap-main: 64px`, `--kid-good-*`, `--kid-try-*`), Lexend, no italics, no timers, no rankings, never show numbers/levels to the child, never the words "error", "incorrecto" or "mal"; Lumi via `window.Mascot?.react('cheer'|'encourage'|'hello', {say})`; every instruction has a `partials/listen_button.html`.
- Child CSS sizes in `rem`/`em` so the "Aa" panel (font size, letter/word spacing, line height) still applies.
- Animations only under `@media (prefers-reduced-motion: no-preference)` and `body:not(.reduce-motion)`; colours under `:not(.high-contrast)` as in `kid.css`.
- Teacher pages: same structure as `templates/dashboard/lesson_plan_list.html` (`admin-console` for admins, `data-table` tables, `admin-dialog` modals, `dashboard/partials/action_menu_toggle.html` row menus, `partials/pagination.html`, `RESOURCE_PAGE_SIZE = 10`).
- Phonemes: continuant consonants elongated ("mmm", "sss", "lll", "nnn", "fff", "rrr", "yyy", "jjj"); stops (p, t, c/k, b/v, d, g) said as their syllable with the following vowel; never the letter name. Every sound is replaceable by an audio file without touching other code.
- Ley 787: answers, decode-help words, omissions and SNEPA are visible only to admins (`is_report_admin_user`) and to teachers linked to the student (`TeacherProfile.students`) with `can_view_student_reports`. Parents see only "terminó la tarea" and encouragement.
- Wrong answers: hint (audio + highlight) and retry; after the 2nd wrong attempt the app models the answer and moves on (`MAX_ATTEMPTS = 2`).
- Steps editable until the first student starts the task; afterwards only adding students and changing the due date.
- Existing features (Planes de clase, Practicar lectura, actividades, reportes) keep working; all existing tests stay green.
- Tests: Django `TestCase` in `homework/tests_<topic>.py`; run with `DB_ENGINE=sqlite python manage.py test <label>` (global Python, Git Bash). Migrations: `python manage.py makemigrations homework --noinput </dev/null` (it can hang without the redirect).

## Review Focus

- Double tap / two tabs submitting the same item: attempts must not double count and the completion reward must be granted once (Task 4 tests `test_complete_assignment_awards_once`, `test_answer_on_closed_item_raises`).
- A teacher POSTing a step edit/delete/move directly after a student started (buttons hidden but URL reachable) must be refused (Task 3 test `test_locked_task_refuses_step_changes_by_post`).
- Child text with capitals, accents, ñ, ü and Spanish punctuation ("¿Leyeron?", "Pingüino", "Ñandú") must decode and build like the plain lowercase word (Task 8 / Task 9 tests `test_case_accents_and_punctuation`, `test_decode_map_keys_are_lowercase_words`).
- A parent, an unlinked teacher, or a linked teacher without report permission opening the per-child report URL must get no difficulty data (Task 15 test `test_detail_report_denied_without_report_permission_or_link`).
- A child opening another child's assignment, an archived task, or a task with zero steps: 404 and no dashboard card (Task 5 tests `test_student_cannot_open_other_students_assignment`, `test_dashboard_hides_archived_and_empty_tasks`).

---

## File Structure

| Path | Responsibility |
|---|---|
| `homework/models.py` | Task, TaskStep, TaskAssignment, StepResult, DecodeHelpEvent, OmissionEvent, SnepaLevel |
| `homework/payloads.py` | Typed payload schema per step type: `clean_payload`, `parse_blank`, limits |
| `homework/permissions.py` | Who can manage tasks / see difficulty data (wraps `dashboard.views` helpers) |
| `homework/services.py` | Assigning, editing lock, duplicating, ordering steps, child progress, completion reward |
| `homework/evaluation.py` | Checks one answer for one item, returns hint/model/omissions |
| `homework/syllables.py` | Spanish grapheme units + syllabification (pure) |
| `homework/phonemes.py` | Replaceable sound table + audio overrides (pure) |
| `homework/decoding.py` | `decode_word`, `decode_map`, `propose_hard_words` (pure) |
| `homework/writing.py` | Tile units, distractors, omission detection (pure) |
| `homework/levels.py` | SNEPA suggestion (pure) |
| `homework/forms.py` | TaskForm, AssignStudentsForm, one form per step type, SnepaOverrideForm |
| `homework/views_teacher.py`, `homework/views_student.py`, `homework/urls.py`, `homework/admin.py`, `homework/apps.py` | HTTP layer |
| `homework/templatetags/decoding.py` | `{% decode_map text %}` |
| `templates/homework/teacher/*.html` | task list, task detail (steps + students), task form, preview, task report, assignment report |
| `templates/homework/student/*.html`, `templates/homework/steps/<type>.html` | path page, step page, one partial per step type |
| `templates/homework/partials/decode_overlay.html` | FAS overlay markup |
| `templates/readings/partials/practice.html` | K1 practice section extracted from `readings/detail.html` |
| `static/js/homework/task-player.js`, `static/js/homework/decode.js`, `static/js/homework/tiles.js` | child step player, tap-a-word overlay, tile builder |
| `static/css/homework.css` | child task styles (kid tokens only) |

URLs (`homework/urls.py`, `app_name = 'homework'`, mounted at `path('tareas/', include('homework.urls'))` in `mysite/urls.py`):

| Pattern | View | Name |
|---|---|---|
| `''` | `views_teacher.task_list` | `task_list` |
| `nueva/` | `task_create` | `task_create` |
| `<int:pk>/` | `task_detail` | `task_detail` |
| `<int:pk>/editar/` | `task_update` | `task_update` |
| `<int:pk>/alumnos/` | `task_assign` (POST) | `task_assign` |
| `<int:pk>/pasos/nuevo/<slug:step_type>/` | `step_create` | `step_create` |
| `<int:pk>/pasos/<int:step_pk>/editar/` | `step_update` | `step_update` |
| `<int:pk>/pasos/<int:step_pk>/eliminar/` | `step_delete` (POST) | `step_delete` |
| `<int:pk>/pasos/<int:step_pk>/mover/` | `step_move` (POST `direction=up|down`) | `step_move` |
| `<int:pk>/duplicar/` | `task_duplicate` (POST) | `task_duplicate` |
| `<int:pk>/archivar/` | `task_archive` (POST) | `task_archive` |
| `<int:pk>/vista-previa/` | `task_preview` | `task_preview` |
| `<int:pk>/reporte/` | `task_report` | `task_report` |
| `seguimiento/<int:assignment_pk>/` | `assignment_report` | `assignment_report` |
| `seguimiento/<int:assignment_pk>/nivel/` | `assignment_level_update` (POST) | `assignment_level_update` |
| `mi-tarea/<int:assignment_pk>/` | `views_student.student_task` | `student_task` |
| `mi-tarea/<int:assignment_pk>/paso/<int:order>/` | `student_step` | `student_step` |
| `mi-tarea/<int:assignment_pk>/paso/<int:order>/listo/` | `step_done` (POST JSON) | `step_done` |
| `mi-tarea/<int:assignment_pk>/paso/<int:order>/responder/` | `step_answer` (POST JSON) | `step_answer` |
| `mi-tarea/<int:assignment_pk>/ayuda/` | `decode_help` (POST JSON) | `decode_help` |

Decisions taken here (spec §9): the permission to create/assign tasks is the existing `can_assign_lesson_plans` (no new flag; admins see every task and report but only teachers create). One `StepResult` row per assignment × step × item holds the attempt counters (no per-attempt rows). The child's own built answer is always checked on the server.

---

## Phase 1 — Create, assign and do a task (Mira, Lectura, Contesta)

### Task 1: `homework` app, models and typed payloads

**Files:**
- Create: `homework/__init__.py`, `homework/apps.py`, `homework/models.py`, `homework/payloads.py`, `homework/admin.py`, `homework/migrations/0001_initial.py` (generated)
- Modify: `mysite/settings.py:39-55` (add `'homework'` after `'readings'`)
- Test: `homework/tests_models.py`

**Interfaces:**
- Consumes: `learning.models.TeacherProfile, StudentProfile, Subject, LessonPlan`; `readings.models.Reading`.
- Produces:
  - `class SnepaLevel(models.TextChoices)`: `INITIAL='AI','Aprendizaje Inicial'`, `FUNDAMENTAL='AF','Aprendizaje Fundamental'`, `SATISFACTORY='AS','Aprendizaje Satisfactorio'`, `ADVANCED='AA','Aprendizaje Avanzado'`.
  - `Task`: `teacher` FK TeacherProfile CASCADE `related_name='tasks'`; `subject` FK Subject PROTECT `related_name='tasks'`; `grade` CharField(1, `StudentProfile.Grade.choices`); `title` CharField(160); `due_date` DateField(null, blank); `lesson_plan` FK LessonPlan SET_NULL null blank `related_name='tasks'`; `is_active` Bool default True; `created_at` auto_now_add; `updated_at` auto_now; `Meta.ordering = ['-created_at']`; property `is_locked -> bool` (any assignment with `started_at` set).
  - `TaskStep`: `class StepType(TextChoices)`: `MIRA='mira','Mira y comenta'`, `LECTURA='lectura','Lectura'`, `PALABRAS='palabras','Palabras difíciles'`, `CONTESTA='contesta','Contesta'`, `ARMA='arma','Arma o completa'`, `EJEMPLO='ejemplo','Ejemplo y práctica'`; fields `task` FK CASCADE `related_name='steps'`, `order` PositiveSmallInteger, `step_type` CharField(20), `payload` JSONField(default=dict), `image` ImageField(`upload_to='tasks/'`, blank, null), `reading` FK Reading SET_NULL null blank `related_name='task_steps'`; `Meta.ordering=['order']`, `UniqueConstraint(fields=['task','order'], name='unique_task_step_order')`; property `item_count -> int` (palabras: `len(words)`, ejemplo: `len(exercises)`, others 1); `clean()` calls `clean_payload` and requires `reading` or non-empty `payload['text']` for lectura; property `text -> str` (lectura: `reading.content` if reading else `payload['text']`).
  - `TaskAssignment`: `class Status(TextChoices)`: `ASSIGNED='assigned','Sin empezar'`, `IN_PROGRESS='in_progress','En curso'`, `COMPLETED='completed','Terminada'`; fields `task` FK CASCADE `related_name='assignments'`, `student` FK StudentProfile CASCADE `related_name='task_assignments'`, `status` default ASSIGNED, `assigned_at` auto_now_add, `started_at`/`completed_at` DateTime null, `points_awarded` PositiveSmallInteger default 0, `snepa_suggested` CharField(2, SnepaLevel, blank), `snepa_override` CharField(2, SnepaLevel, blank), `snepa_override_by` FK TeacherProfile SET_NULL null `related_name='+'`, `snepa_override_at` DateTime null; `UniqueConstraint(['task','student'], name='unique_task_assignment')`; property `snepa_level -> str` (override or suggested).
  - `StepResult`: `assignment` FK CASCADE `related_name='results'`, `step` FK TaskStep CASCADE `related_name='results'`, `item_index` PositiveSmallInteger default 0, `attempts` PositiveSmallInteger default 0, `first_answer` CharField(255, blank), `answer` CharField(255, blank), `first_try_correct` Bool null (null = not evaluated), `hints_used` PositiveSmallInteger default 0, `modeled` Bool default False, `completed_at` DateTime null; `UniqueConstraint(['assignment','step','item_index'], name='unique_step_result_item')`.
  - `DecodeHelpEvent`: `assignment` FK CASCADE `related_name='decode_helps'`, `step` FK TaskStep SET_NULL null, `word` CharField(80), `created_at` auto_now_add; `Index(fields=['assignment','word'])`.
  - `OmissionEvent`: `assignment` FK CASCADE `related_name='omissions'`, `step` FK TaskStep CASCADE, `target` CharField(255), `missing_unit` CharField(30), `position` PositiveSmallInteger, `created_at` auto_now_add.
  - `homework/payloads.py`: constants `MAX_TEXT = 255`, `PALABRAS_MIN = 3`, `PALABRAS_MAX = 6`, `OPTIONS_MIN = 2`, `OPTIONS_MAX = 4`, `EXAMPLE_STEPS_MAX = 5`, `EXERCISES_MAX = 5`; `clean_payload(step_type: str, data: dict) -> dict` (returns a normalized copy, raises `django.core.exceptions.ValidationError`); `parse_blank(text: str) -> tuple[str, str, str]` (before, blank, after; blank `''` when no brackets; raises ValidationError for more than one `[...]` pair or an empty `[]`).
  - Payload shapes: mira `{'question'}`; lectura `{'text'}`; palabras `{'words': [str]}`; contesta `{'question', 'kind': 'choice'|'build', 'options': [str], 'answer'}` (options required and containing `answer` only for `choice`); arma `{'text', 'unit': 'letter'|'syllable'|'word'}` (`text` may hold one `[blank]`); ejemplo `{'example_steps': [str], 'exercises': [{'prompt', 'answer', 'options': [str]}]}` (each `options` 2–4 and contains `answer`).
  - Admin: register all six models; `TaskStepInline` on `TaskAdmin`.

- [ ] **Step 1: Write the failing tests** in `homework/tests_models.py`

```python
class PayloadTests(SimpleTestCase):
    def test_contesta_choice_requires_answer_among_options(self):
        with self.assertRaises(ValidationError):
            clean_payload('contesta', {'question': '¿Qué come?', 'kind': 'choice', 'options': ['pan', 'sol'], 'answer': 'luna'})
    def test_palabras_count_limits(self):  # 2 words and 7 words raise; 3 distinct words pass
    def test_palabras_strip_and_deduplicate(self):
        self.assertEqual(clean_payload('palabras', {'words': [' casa', 'casa', 'perro', 'sol ']})['words'], ['casa', 'perro', 'sol'])
    def test_unknown_step_type_raises(self):
    def test_parse_blank(self):
        self.assertEqual(parse_blank('El [gato] come.'), ('El ', 'gato', ' come.'))
        self.assertEqual(parse_blank('Mi ma[má] me ama.'), ('Mi ma', 'má', ' me ama.'))
        self.assertEqual(parse_blank('Sin hueco'), ('Sin hueco', '', ''))
        for bad in ('Dos [a] y [b]', 'Vacío []'):
            with self.assertRaises(ValidationError): parse_blank(bad)
    def test_ejemplo_exercise_options_contain_answer(self):

class TaskModelTests(TestCase):
    def test_step_order_unique_per_task(self):  # second TaskStep(order=1) on same task -> IntegrityError
    def test_is_locked_after_first_start(self):
        self.assertFalse(task.is_locked); assignment.started_at = timezone.now(); assignment.save(); self.assertTrue(task.is_locked)
    def test_item_count_by_type(self):  # palabras with 4 words -> 4; ejemplo with 2 exercises -> 2; mira -> 1
    def test_lectura_text_prefers_reading(self):
    def test_snepa_level_prefers_override(self):
```

- [ ] **Step 2: Run** `DB_ENGINE=sqlite python manage.py test homework.tests_models -v 2` — Expected: FAIL (`ModuleNotFoundError: homework` / import errors).
- [ ] **Step 3: Implement** the app, models, payloads and admin listed in Interfaces; add `'homework'` to `INSTALLED_APPS`; run `python manage.py makemigrations homework --noinput </dev/null`.
- [ ] **Step 4: Run** `DB_ENGINE=sqlite python manage.py test homework.tests_models -v 2` — Expected: PASS. Then `DB_ENGINE=sqlite python manage.py check` — Expected: `System check identified no issues`.
- [ ] **Step 5: Commit** `git add homework mysite/settings.py && git commit -m "feat(homework): add task, step and assignment models"`

### Task 2: Teacher task list, create/edit and assignment

**Files:**
- Create: `homework/permissions.py`, `homework/forms.py`, `homework/views_teacher.py`, `homework/urls.py`, `templates/homework/teacher/task_list.html`, `templates/homework/teacher/task_detail.html` (students part; steps table added in Task 3), `templates/homework/teacher/task_form.html`
- Create (cont.): `homework/services.py`
- Modify: `mysite/urls.py` (add `path('tareas/', include('homework.urls'))`), `templates/dashboard/teacher_dashboard.html:42` (quick link "Tareas — Pasos cortos para tus alumnos" when `teacher_profile.can_assign_lesson_plans`), `templates/dashboard/partials/admin_sidebar.html:12` (link "📝 Tareas")
- Test: `homework/tests_teacher.py`

**Interfaces:**
- Consumes: Task 1 models; `dashboard.views.is_admin_user, is_report_admin_user, is_teacher, teacher_has_permission, teacher_can_access_student, write_audit, RESOURCE_PAGE_SIZE` (import from `dashboard.views`; `homework.services` and `homework.models` must never import `dashboard`, so `dashboard.views` can import them later without a cycle).
- Produces:
  - `permissions.can_manage_tasks(user) -> bool` = `is_teacher(user) and teacher_has_permission(user, 'can_assign_lesson_plans')`.
  - `permissions.can_view_task(user, task) -> bool` = admin (`is_admin_user`) or (`can_manage_tasks` and `task.teacher == user.teacher_profile`).
  - `permissions.can_view_difficulty_data(user, student) -> bool` = `is_report_admin_user(user) or (teacher_has_permission(user, 'can_view_student_reports') and teacher_can_access_student(user, student))` — deliberately not `user_can_view_student_report` (that one admits parents).
  - `services.group_students(teacher: TeacherProfile, grade: str) -> QuerySet[StudentProfile]` = `teacher.students.filter(grade=grade)`.
  - `services.assign_students(task: Task, students: Iterable[StudentProfile]) -> int` — creates missing assignments only for students in `task.teacher.students`, returns how many were created.
  - `forms.TaskForm(ModelForm)` fields `title, subject, grade, due_date, lesson_plan`; kwargs `teacher`, `locked: bool`; `lesson_plan` queryset = teacher's active plans; when a plan is chosen `clean()` copies `plan.subject` and `plan.grade`; when `locked`, every field except `due_date` is `disabled`.
  - `forms.AssignStudentsForm(Form)`: `students` (ModelMultipleChoice, CheckboxSelectMultiple, queryset `group_students(teacher, task.grade)`, required False), `whole_group` Boolean ("Todo mi grupo de este grado"); `clean()` requires one of them; `selected_students() -> QuerySet`.
  - Views: `task_list`, `task_create`, `task_update`, `task_detail`, `task_assign`, `task_archive` (sets `is_active=False`). Non-permitted users: `messages.error(..., 'No tienes permiso para gestionar tareas.')` + redirect `dashboard:teacher`; another teacher's task: 404.
  - `task_list` table columns: Título, Materia, Grado, Fecha, Avance (`"{completed}/{total} terminaron"` via `Count` annotations), row menu (Pasos, Vista previa, Reporte, Duplicar, Archivar). Search `q` on title; paginate `RESOURCE_PAGE_SIZE`.

- [ ] **Step 1: Write the failing tests** in `homework/tests_teacher.py` (setUp: teacher with `can_assign_lesson_plans=True`, two linked grade-1 students, one linked grade-2 student, one unlinked student, a second teacher)

```python
def test_task_list_requires_assign_permission(self):  # teacher without flag -> 302 to dashboard:teacher
def test_create_task_sets_teacher_and_redirects_to_detail(self):
    response = self.client.post(reverse('homework:task_create'), {'title': 'Los animales', 'subject': s.pk, 'grade': '1', 'due_date': '2026-10-20'})
    task = Task.objects.get(); self.assertEqual(task.teacher, self.teacher); self.assertRedirects(response, reverse('homework:task_detail', args=[task.pk]))
def test_lesson_plan_link_copies_subject_and_grade(self):
def test_cannot_link_other_teachers_plan(self):  # form error on lesson_plan
def test_whole_group_assigns_only_linked_students_of_task_grade(self):
    self.client.post(reverse('homework:task_assign', args=[task.pk]), {'whole_group': 'on'})
    self.assertEqual(set(task.assignments.values_list('student__name', flat=True)), {'Ana', 'Beto'})
def test_assign_ignores_unlinked_student_ids(self):
def test_assign_twice_does_not_duplicate(self):
def test_other_teacher_gets_404_on_task_detail(self):
def test_locked_task_update_changes_only_due_date(self):
    # started assignment; POST new title + new due_date -> title unchanged, due_date changed
def test_archived_task_hidden_from_list(self):  # task_archive POST -> is_active False, not listed
```

- [ ] **Step 2: Run** `DB_ENGINE=sqlite python manage.py test homework.tests_teacher -v 2` — Expected: FAIL (`NoReverseMatch: 'homework'`).
- [ ] **Step 3: Implement** permissions, services (`group_students`, `assign_students`), forms, views, URLs and templates per Interfaces. Templates mirror `lesson_plan_list.html` (admin branch wraps in `admin-console` with sidebar/topbar; teacher branch uses the same table/dialog classes). Fixed copy: list title "Tareas", empty state "Aún no tienes tareas. Crea la primera con solo la parte que hace el niño.", create button "Nueva tarea", assign button "Asignar", whole-group label "Todo mi grupo de este grado".
- [ ] **Step 4: Run** `DB_ENGINE=sqlite python manage.py test homework.tests_teacher dashboard -v 1` — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(homework): let teachers create and assign tasks"`

### Task 3: Step editor, edit lock and duplication (Mira, Lectura, Contesta forms)

**Files:**
- Modify: `homework/services.py`, `homework/forms.py`, `homework/views_teacher.py`, `templates/homework/teacher/task_detail.html`
- Create: `templates/homework/teacher/step_form.html`
- Test: `homework/tests_steps.py`

**Interfaces:**
- Consumes: Task 1 `clean_payload`, Task 2 permissions.
- Produces:
  - `services.TaskLocked(Exception)`; `services.ensure_editable(task: Task) -> None` (raises when `task.is_locked`).
  - `services.append_step(task, step_type: str, payload: dict, *, image=None, reading=None) -> TaskStep` (order = last + 1, starts at 1).
  - `services.delete_step(step: TaskStep) -> None` (renumbers 1..n in one transaction).
  - `services.move_step(step: TaskStep, direction: str) -> None` (`'up'|'down'`; swaps with neighbour; no-op at the edges; uses a temporary order `0` inside `transaction.atomic()` to respect the unique constraint).
  - `services.duplicate_task(task: Task) -> Task` (copy with title `f'{task.title} (copia)'`, same subject/grade/plan, `due_date=None`, steps copied with payload, image name and reading; no assignments).
  - `forms.StepForm(Form)` base: `step_type: str`, `to_payload() -> dict`, `classmethod initial_from(step) -> dict`; subclasses `MiraStepForm` (`image` required on create, `question`), `LecturaStepForm` (`reading` ModelChoice of active readings with `grade=task.grade`, optional; `text` Textarea optional; exactly one required), `ContestaStepForm` (`question`, `kind` radio choice/build, `options` Textarea "Una opción por línea", `answer`). Registry `STEP_FORMS: dict[str, type[StepForm]]` (Tasks 10, 12, 13 add `palabras`, `arma`, `ejemplo`); `step_create` returns 404 for a type not in `STEP_FORMS`.
  - `task_detail` steps table: N.º, Tipo (`get_step_type_display`), Resumen (question/text truncated 60), menu (Editar, Subir, Bajar, Eliminar). "Agregar paso" opens an `admin-dialog` with one button per registered type. When locked: no edit controls and the notice "Un alumno ya empezó esta tarea. Para cambiar los pasos, duplícala."

- [ ] **Step 1: Write the failing tests** in `homework/tests_steps.py`

```python
def test_append_steps_get_consecutive_orders(self):  # orders [1, 2, 3]
def test_move_step_up_swaps_orders(self):
def test_move_first_step_up_is_noop(self):
def test_delete_step_renumbers(self):  # delete order 2 of 3 -> remaining orders [1, 2]
def test_duplicate_copies_steps_not_assignments(self):
    copy = duplicate_task(task); self.assertEqual(copy.title, 'Los animales (copia)')
    self.assertEqual(list(copy.steps.values_list('step_type', 'payload')), list(task.steps.values_list('step_type', 'payload')))
    self.assertEqual(copy.assignments.count(), 0); self.assertFalse(copy.is_locked)
def test_create_contesta_step_via_view_stores_payload(self):
    self.client.post(reverse('homework:step_create', args=[task.pk, 'contesta']), {'question': '¿Qué come el conejo?', 'kind': 'choice', 'options': 'zanahoria\npiedra', 'answer': 'zanahoria'})
    self.assertEqual(task.steps.get().payload, {'question': '¿Qué come el conejo?', 'kind': 'choice', 'options': ['zanahoria', 'piedra'], 'answer': 'zanahoria'})
def test_lectura_step_requires_reading_or_text(self):
def test_lectura_reading_choices_match_task_grade(self):
def test_unregistered_step_type_is_404(self):  # step_type 'desconocido' -> 404
def test_locked_task_refuses_step_changes_by_post(self):
    # started assignment; POST to step_create, step_update, step_delete, step_move -> steps unchanged, message "Un alumno ya empezó esta tarea. Para cambiar los pasos, duplícala."
def test_duplicate_view_redirects_to_copy(self):
```

- [ ] **Step 2: Run** `DB_ENGINE=sqlite python manage.py test homework.tests_steps -v 2` — Expected: FAIL (`ImportError: append_step`).
- [ ] **Step 3: Implement** the services, forms, views (`step_create`, `step_update`, `step_delete`, `step_move`, `task_duplicate`) and template changes. Every mutating step view calls `ensure_editable` and, on `TaskLocked`, shows the lock message and redirects to `task_detail`.
- [ ] **Step 4: Run** `DB_ENGINE=sqlite python manage.py test homework -v 1` — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(homework): edit task steps until a student starts"`

### Task 4: Child progress services (start, items, answers, completion reward)

**Files:**
- Modify: `homework/services.py`
- Create: `homework/evaluation.py`
- Test: `homework/tests_progress.py`

**Interfaces:**
- Consumes: Task 1 models.
- Produces:
  - `MAX_ATTEMPTS = 2`, `TASK_POINTS = 10`, `TASK_STARS = 1`.
  - `evaluation.InvalidAnswer(ValueError)`; `@dataclass Evaluation(correct: bool, answer_text: str, model_answer: str, hint: dict, omissions: list[tuple[int, str]] = field(default_factory=list), target: str = '')`; `evaluation.evaluate(step: TaskStep, item_index: int, payload: dict) -> Evaluation`. In this task only contesta `kind='choice'`: payload `{'choice': int}` (index into options; non-int/out-of-range → `InvalidAnswer`); hint `{'say': question, 'hole_index': None, 'kind': 'try_again'}`; `model_answer = payload['answer']`. Other types raise `InvalidAnswer` until Tasks 12/13.
  - `@dataclass ItemOutcome(status: str, hint: dict | None, model_answer: str, step_done: bool, task_done: bool)`; `status ∈ {'done', 'correct', 'try_again', 'modeled'}`.
  - `services.ItemClosed(Exception)`.
  - `services.next_assignment_for(student) -> TaskAssignment | None`: not completed, `task.is_active`, task has ≥ 1 step; order by `due_date` ascending with nulls last, then `assigned_at`.
  - `services.start_assignment(assignment) -> None`: sets `started_at=now`, `status=IN_PROGRESS` once (`select_for_update`).
  - `services.current_step(assignment) -> TaskStep | None`: first step (by order) with fewer completed results than `item_count`.
  - `@dataclass StepState(step: TaskStep, done: bool, current: bool)`; `services.step_states(assignment) -> list[StepState]`.
  - `services.mark_item_done(assignment, step, item_index: int) -> ItemOutcome` (non-evaluated items; idempotent: second call returns `status='done'` without changes).
  - `services.submit_answer(assignment, step, item_index: int, payload: dict) -> ItemOutcome`: locks the assignment row; raises `ItemClosed` if that result is completed; increments `attempts`; stores `first_answer` on attempt 1 and `answer` always; attempt 1 sets `first_try_correct`; correct → close, `'correct'`; wrong and `attempts < MAX_ATTEMPTS` → `hints_used += 1`, `'try_again'` with hint; wrong at `MAX_ATTEMPTS` → `modeled=True`, close, `'modeled'` with `model_answer`. Omissions from the evaluation are saved as `OmissionEvent` rows on every attempt.
  - `services.complete_assignment(assignment) -> int` (points awarded): when every step is done; locks `StudentProfile` with `select_for_update()` and the assignment row; if `completed_at` is already set returns 0; else sets `status=COMPLETED`, `completed_at`, `points_awarded=TASK_POINTS`, updates `points`, `stars`, `experience` with `F()` and `last_activity_at` (same pattern as `progress.services.complete_reading_practice`). Called by `mark_item_done`/`submit_answer` when the last item closes (`task_done=True`). Task 14 adds the SNEPA suggestion here.
  - `services.item_index_valid(step, item_index) -> bool` (`0 <= item_index < step.item_count`).

- [ ] **Step 1: Write the failing tests** in `homework/tests_progress.py` (task with steps mira(1), contesta choice(2) options `['zanahoria', 'piedra']`, answer `'zanahoria'`)

```python
def test_next_assignment_prefers_nearest_due_date_then_undated(self):
def test_dashboard_candidate_skips_completed_archived_and_empty(self):
def test_start_sets_started_once(self):  # second call keeps first started_at
def test_current_step_advances_after_mark_done(self):
def test_correct_first_try(self):
    out = submit_answer(a, contesta, 0, {'choice': 0})
    self.assertEqual((out.status, out.step_done, out.task_done), ('correct', True, True))
    r = StepResult.objects.get(); self.assertTrue(r.first_try_correct); self.assertEqual(r.attempts, 1); self.assertEqual(r.answer, 'zanahoria')
def test_wrong_then_wrong_models_answer(self):
    self.assertEqual(submit_answer(a, contesta, 0, {'choice': 1}).status, 'try_again')
    out = submit_answer(a, contesta, 0, {'choice': 1})
    self.assertEqual((out.status, out.model_answer), ('modeled', 'zanahoria'))
    r = StepResult.objects.get(); self.assertEqual((r.first_try_correct, r.hints_used, r.modeled, r.first_answer), (False, 1, True, 'piedra'))
def test_wrong_then_right_keeps_first_try_false(self):
def test_answer_on_closed_item_raises(self):  # ItemClosed
def test_invalid_choice_raises_invalid_answer(self):  # {'choice': 9}, {'choice': 'a'}, {}
def test_complete_assignment_awards_once(self):
    # after finishing: student.points == 10, stars == 1; complete_assignment(a) again returns 0 and points stay 10
def test_mark_item_done_is_idempotent(self):
```

- [ ] **Step 2: Run** `DB_ENGINE=sqlite python manage.py test homework.tests_progress -v 2` — Expected: FAIL (`ImportError: submit_answer`).
- [ ] **Step 3: Implement** the services and evaluation per Interfaces.
- [ ] **Step 4: Run** `DB_ENGINE=sqlite python manage.py test homework -v 1` — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(homework): track child progress through task steps"`

### Task 5: Child path page, Mira and Contesta steps, dashboard card

**Files:**
- Create: `homework/views_student.py`, `templates/homework/student/task_path.html`, `templates/homework/student/step.html`, `templates/homework/steps/mira.html`, `templates/homework/steps/contesta.html`, `static/js/homework/task-player.js`, `static/css/homework.css`, `homework/copy.py`
- Modify: `homework/urls.py`, `dashboard/views.py:815-837` (`student_dashboard` adds `today_task = next_assignment_for(student)`), `templates/dashboard/student_dashboard.html:20` (task card first in the grid)
- Test: `homework/tests_student.py`

**Interfaces:**
- Consumes: Task 4 services; `core.json_payload.parse_json_object, parse_id`.
- Produces:
  - `homework/copy.py` fixed child copy (exact strings):
    - `INSTRUCTIONS = {'mira': 'Mira la imagen y escucha la pregunta. Cuéntale a tu profe lo que ves. Cuando termines, toca Listo.', 'lectura': 'Primero escucha la lectura. Después léela tú.', 'palabras': 'Toca cada palabra. Escucha sus sonidos y júntalos.', 'contesta': 'Escucha la pregunta y toca tu respuesta.', 'contesta_build': 'Escucha la pregunta y arma tu respuesta con las fichas.', 'arma': 'Toca las fichas en orden para armarlo.', 'arma_blank': 'Completa lo que falta con las fichas.', 'ejemplo': 'Mira el ejemplo paso a paso. Después, inténtalo tú.'}`
    - `FEEDBACK = {'correct': '¡Muy bien!', 'try_again': 'Casi. Escucha otra vez y vuelve a intentar.', 'omission': 'Aquí falta un sonido. ¡Escúchalo y búscalo!', 'modeled': 'Mira, así es: {answer}. ¡Sigamos!', 'task_done': '¡Terminaste tu tarea! ¡Lo hiciste muy bien!'}`
    - Dashboard card: title "Mi tarea de hoy", subtitle "Tu profe preparó pasos para ti", action "¡Vamos!"; Lumi on load `data-mascot-on-load="hello" data-mascot-say="¡Hoy tienes una tarea! ¡Vamos juntos!"`.
  - Views (all `@login_required`; non-students redirect `dashboard:redirect`; assignment lookup `get_object_or_404(TaskAssignment, pk=..., student=request.user.student_profile, task__is_active=True)`):
    - `student_task` renders the path: one `<li>` per `StepState` (done → ⭐ + `is-done`; current → `is-current`, `aria-current="step"`), big link "¡Vamos!" to the current step, or the celebration (`FEEDBACK['task_done']`, `data-mascot-on-load="cheer"`) when completed. Query `?hecho=1` triggers `Mascot.react('cheer', {say: '¡Muy bien!'})`.
    - `student_step(order)`: calls `start_assignment`; a step after the current one redirects to `student_task`; renders `step.html` which includes `homework/steps/<step_type>.html` with context `step`, `assignment`, `instruction`, `preview=False`, `done_url`, `answer_url`, `help_url`.
    - `step_done(order)` POST `{'item_index': int}` → `mark_item_done`; `step_answer(order)` POST `{'item_index': int, 'choice'?: int, 'tiles'?: [str]}` → `submit_answer`. JSON response `{'status', 'hint', 'model_answer', 'step_done', 'task_done', 'next_url'}` where `next_url` is `student_task?hecho=1` when the step is done; errors `{'saved': False, 'reason': 'payload'|'closed'|'step'}` with 400/409/404.
  - `task-player.js`: reads `[data-task-step]` root (`data-done-url`, `data-answer-url`, `data-preview`); exposes `window.TaskPlayer = {done(itemIndex), answer(itemIndex, body) -> Promise<outcome>, showFeedback(outcome)}`; `showFeedback` speaks the feedback copy with `AppSpeech.speak`, uses `--kid-good-*`/`--kid-try-*` styles, calls `Mascot.react('cheer'|'encourage')`, and on `step_done` shows a 64 px "Seguir" link to `next_url`. Feedback strings arrive from the server-rendered `json_script` of `FEEDBACK`. In preview (`data-preview="1"`) it never fetches.
  - `steps/mira.html`: image (alt = question), question with listen button, 64 px button "Listo" → `TaskPlayer.done(0)`. `steps/contesta.html` (choice): question + listen, one big button per option (each with its own listen icon), one question per screen.

- [ ] **Step 1: Write the failing tests** in `homework/tests_student.py`

```python
def test_dashboard_shows_task_card_above_choices(self):
    html = self.client.get(reverse('dashboard:student')).content.decode()
    self.assertIn('Mi tarea de hoy', html); self.assertLess(html.index('Mi tarea de hoy'), html.index('Practicar'))
def test_dashboard_hides_archived_and_empty_tasks(self):
def test_path_marks_current_step_and_never_shows_levels(self):
    # assertContains 'aria-current="step"'; assertNotContains 'Aprendizaje'
def test_student_cannot_open_other_students_assignment(self):  # 404 on student_task and student_step
def test_opening_first_step_starts_assignment(self):
def test_future_step_redirects_to_path(self):
def test_step_done_json_flow_completes_task(self):
    r = self.client.post(done_url, data='{"item_index": 0}', content_type='application/json')
    self.assertEqual(r.json()['step_done'], True)
def test_step_answer_try_again_then_modeled(self):
    self.assertEqual(post({'item_index': 0, 'choice': 1}).json()['status'], 'try_again')
    body = post({'item_index': 0, 'choice': 1}).json(); self.assertEqual((body['status'], body['model_answer']), ('modeled', 'zanahoria'))
def test_step_answer_bad_payload_400_and_closed_409(self):
def test_teacher_cannot_post_child_answers(self):  # teacher login -> redirect, nothing saved
def test_existing_lesson_plan_block_still_rendered(self):  # today_plan section still present
```

- [ ] **Step 2: Run** `DB_ENGINE=sqlite python manage.py test homework.tests_student -v 2` — Expected: FAIL (`NoReverseMatch: student_task`).
- [ ] **Step 3: Implement** views, templates, copy, JS and CSS. `homework.css` loaded via `{% block extra_css %}` with `?v=20261014-tasks-1`; path uses kid tokens: current step `--kid-primary-soft` ring, done steps `--kid-sun-fill` star, buttons `min-height: var(--kid-tap-main)`.
- [ ] **Step 4: Run** `DB_ENGINE=sqlite python manage.py test homework dashboard -v 1` — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(homework): child task path with look and answer steps"`

### Task 6: Lectura step reusing "Practicar lectura"

**Files:**
- Create: `templates/readings/partials/practice.html` (the `<section … data-reading-practice>` block and its `json_script` moved verbatim from `templates/readings/detail.html`)
- Modify: `templates/readings/detail.html` (include the partial), `static/js/reading-practice.js` (completion event + silent last read), `templates/homework/steps/lectura.html` (create), `templates/homework/student/step.html` (load `reading-practice.css`/`.js` for lectura)
- Test: `homework/tests_student.py` (add), `readings/tests.py` (existing tests must stay green)

**Interfaces:**
- Consumes: Task 5 `TaskPlayer.done`; K1 `readings:save_practice_attempt`, `PRACTICE_READS`, `MIN_READ_MS`, `MAX_READ_MS`.
- Produces:
  - Partial params: `practice_text` (string, json_script id stays `reading-practice-text`), `save_url` (optional), `practice_reads`, `practice_min_ms`, `practice_max_ms`, `in_task` (bool: hides "Volver al cuento", adds `data-silent-last="1"`).
  - `reading-practice.js`: when the result step shows, `root.dispatchEvent(new CustomEvent('reading-practice:done', {bubbles: true}))`; with `data-silent-last="1"` the last read's message is "Ahora lee en silencio, solo con los ojos." (spec: modelo → lee él → en silencio).
  - Lectura step: `save_url` is the K1 endpoint only when `step.reading` is active and `step.reading.grade == student.grade` (so practice history/points keep accruing); otherwise omitted (K1 offline mode). `task-player.js` listens for `reading-practice:done` and calls `TaskPlayer.done(0)`.

- [ ] **Step 1: Write the failing tests**

```python
def test_lectura_step_renders_practice_with_task_text(self):
    # typed text 'El sapo salta.' -> assertContains 'data-reading-practice', '"El sapo salta."', 'data-silent-last="1"'
def test_lectura_step_with_same_grade_reading_uses_k1_save_url(self):
def test_lectura_step_with_other_grade_reading_has_no_save_url(self):
def test_reading_detail_still_renders_practice(self):  # readings:detail contains 'data-reading-practice' and 'Volver al cuento'
```

- [ ] **Step 2: Run** `DB_ENGINE=sqlite python manage.py test homework.tests_student readings -v 1` — Expected: the new tests FAIL.
- [ ] **Step 3: Implement** the partial extraction, JS event, silent-last copy and lectura step template.
- [ ] **Step 4: Run** `DB_ENGINE=sqlite python manage.py test homework readings -v 1` — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(homework): reading step reuses repeated reading practice"`

### Task 7: Teacher preview "como la ve el niño"

**Files:**
- Create: `templates/homework/teacher/task_preview.html`
- Modify: `templates/base.html:17-25` (`kid_layout` flag), `homework/views_teacher.py` (`task_preview`)
- Test: `homework/tests_teacher.py` (add)

**Interfaces:**
- Consumes: step partials from Tasks 5–6 (and later 10, 12, 13 — they render here automatically).
- Produces: `base.html` loads `kid.css`/`mascot.css` and sets `class="kid-ui"` when `kid_layout` is truthy, otherwise keeps today's rule (`{% if kid_layout %}…{% elif not adult_layout %}{% if not request.user.is_authenticated or request.user.role == 'STUDENT' %}…`). `task_preview` renders every step stacked with `preview=True` (no URLs, `data-preview="1"`), a top banner "Vista previa: así verá la tarea el niño" and a link "Volver a la tarea"; contesta options mark the correct one with "✓ correcta" only in preview.

- [ ] **Step 1: Write the failing tests**

```python
def test_preview_renders_kid_layout_for_teacher(self):  # assertContains 'class="kid-ui"', 'Vista previa'
def test_preview_has_no_answer_urls(self):  # assertNotContains '/responder/'
def test_teacher_pages_keep_adult_layout(self):  # task_list response assertNotContains 'kid-ui'
def test_preview_forbidden_for_other_teacher(self):  # 404
```

- [ ] **Step 2: Run** `DB_ENGINE=sqlite python manage.py test homework.tests_teacher -v 2` — Expected: new tests FAIL.
- [ ] **Step 3: Implement** the flag and view.
- [ ] **Step 4: Run** `DB_ENGINE=sqlite python manage.py test homework dashboard accounts -v 1` — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(homework): preview a task as the child sees it"`

---

## Phase 2 — FAS decoding

### Task 8: Spanish syllabification

**Files:**
- Create: `homework/syllables.py`
- Test: `homework/tests_syllables.py`

**Interfaces:**
- Produces: `class Unit(NamedTuple): text: str; is_vowel: bool`; `word_units(word: str) -> list[Unit]` (unit texts are slices of the original word, case and accents kept); `syllable_units(word: str) -> list[list[Unit]]`; `split_syllables(word: str) -> list[str]` (`''.join(result) == word` always). Input is a single word (letters only); callers extract words with `WORD = re.compile(r'[^\W\d_]+')`, defined here.

Rules (the implementer cannot infer these; follow exactly, comparing on `word.lower()`):

```text
VOWELS = a e i o u á é í ó ú ü
STRONG = a e o á é í ó ú        # accented i/u act as strong: rí-o, pa-ís
INSEPARABLE = pl pr bl br fl fr cl cr gl gr kl kr tr dr tl    # tl kept together (Latin American: a-tle-ta)

1. Units, left to right:
   - 'ch', 'll', 'rr' -> one consonant unit.
   - 'qu' or 'gu' followed by e/é/i/í -> one consonant unit (silent u): que-so, gui-ta-rra.
   - 'y' -> vowel when it is the last letter or the next letter is not a vowel (rey, muy, hoy, y);
     otherwise consonant (le-ye-ron, cons-tru-yó).
   - other vowel letters -> vowel unit ('ü' is a weak vowel: pin-güi-no).
   - any other letter, including 'h' -> consonant unit.
2. Nuclei: a maximal run of vowel units, split between every two adjacent STRONG vowels
   (a-é-re-o, le-ón); everything else stays together (ciu-dad, ca-mión, buey).
3. Consonant units between two nuclei, n = count:
   n = 0 -> boundary between the nuclei (hiatus).
   n = 1 -> V | C V
   n = 2 -> C1C2 in INSEPARABLE ? V | C1C2 V : V C1 | C2 V
   n = 3 -> C2C3 in INSEPARABLE ? V C1 | C2C3 V : V C1C2 | C3 V
   n >= 4 -> V C1C2 | C3.. V
4. Consonants before the first nucleus join the first syllable; after the last, the last.
5. No vowel unit -> [word].
```

- [ ] **Step 1: Write the failing tests** in `homework/tests_syllables.py` (`SimpleTestCase`, one `subTest` per case)

```python
CASES = {
    'leyeron': ['le', 'ye', 'ron'], 'construyó': ['cons', 'tru', 'yó'], 'carro': ['ca', 'rro'],
    'muchacho': ['mu', 'cha', 'cho'], 'guitarra': ['gui', 'ta', 'rra'], 'árbol': ['ár', 'bol'],
    'pájaro': ['pá', 'ja', 'ro'], 'aéreo': ['a', 'é', 're', 'o'], 'blanco': ['blan', 'co'],
    'insecto': ['in', 'sec', 'to'], 'queso': ['que', 'so'], 'pingüino': ['pin', 'güi', 'no'],
    'río': ['rí', 'o'], 'país': ['pa', 'ís'], 'ciudad': ['ciu', 'dad'], 'ahora': ['a', 'ho', 'ra'],
    'hoy': ['hoy'], 'muy': ['muy'], 'rey': ['rey'], 'reyes': ['re', 'yes'], 'camión': ['ca', 'mión'],
    'atleta': ['a', 'tle', 'ta'], 'extraño': ['ex', 'tra', 'ño'], 'calle': ['ca', 'lle'],
    'pequeño': ['pe', 'que', 'ño'], 'agua': ['a', 'gua'], 'guerra': ['gue', 'rra'],
    'instante': ['ins', 'tan', 'te'], 'hablar': ['ha', 'blar'], 'y': ['y'], 'león': ['le', 'ón'],
}
def test_split_cases(self): ...  # split_syllables(word) == expected
def test_case_accents_and_punctuation(self):
    self.assertEqual(split_syllables('Leyeron'), ['Le', 'ye', 'ron'])
    self.assertEqual(split_syllables('Ñandú'), ['Ñan', 'dú'])
    self.assertEqual(WORD.findall('¿Leyeron el Pingüino?'), ['Leyeron', 'el', 'Pingüino'])
def test_units_digraphs(self):
    self.assertEqual([u.text for u in word_units('carro')], ['c', 'a', 'rr', 'o'])
    self.assertEqual([u.text for u in word_units('queso')], ['qu', 'e', 's', 'o'])
    self.assertEqual([u.is_vowel for u in word_units('rey')], [False, True, True])
def test_join_is_identity(self):  # ''.join(split_syllables(w)) == w for every case
def test_no_vowel_word(self):  # split_syllables('psst') == ['psst']
```

- [ ] **Step 2: Run** `DB_ENGINE=sqlite python manage.py test homework.tests_syllables -v 2` — Expected: FAIL (`ModuleNotFoundError`).
- [ ] **Step 3: Implement** `homework/syllables.py` following the rule list.
- [ ] **Step 4: Run** the same command — Expected: PASS (all subtests).
- [ ] **Step 5: Commit** `git commit -m "feat(homework): add Spanish syllabification"`

### Task 9: Replaceable phoneme table, decode map and template tag

**Files:**
- Create: `homework/phonemes.py`, `homework/decoding.py`, `homework/templatetags/__init__.py`, `homework/templatetags/decoding.py`
- Test: `homework/tests_decoding.py`

**Interfaces:**
- Consumes: Task 8 `word_units`, `syllable_units`, `WORD`.
- Produces:
  - `phonemes.SOUND_TABLE: dict[str, str]` = `{'m': 'mmm', 'n': 'nnn', 'ñ': 'ñññ', 'l': 'lll', 's': 'sss', 'z': 'sss', 'f': 'fff', 'j': 'jjj', 'r': 'rrr', 'rr': 'rrr', 'y': 'yyy', 'll': 'yyy', 'h': '', 'w': 'u'}`; `STOPS = frozenset({'p', 't', 'c', 'k', 'qu', 'b', 'v', 'd', 'g', 'gu', 'ch', 'x'})`; `SOFT_BEFORE_E_I = {'c': 'sss', 'g': 'jjj'}`; vowels say themselves (`'ü'` and vowel `'y'` say `'u'` / `'i'`).
  - `phonemes.PHONEME_AUDIO: dict[str, str] = {}` keyed by the spoken string (`'mmm'`, `'pa'`, …) → static URL; `phonemes.audio_for(say: str) -> str` returns `''` when absent. Recording a sound later = adding one entry; no other code changes.
  - `decoding.decode_word(word: str) -> dict` (works on `word.lower()`): `{'word': str, 'letters': [{'text', 'say', 'audio'}], 'syllables': [{'text', 'blend': [int]}]}`, `blend` = indexes into `letters`. Rules:
    - `say` of a consonant: `SOFT_BEFORE_E_I` when the next letter is e/é/i/í; else `SOUND_TABLE`; else if in `STOPS`, the syllable substring from this unit through its first following vowel unit (`t` in "tra" → `'tra'`), or the whole syllable when no vowel follows (coda, `c` in "sec" → `'sec'`).
    - `blend`: units of the syllable in order, skipping `say == ''`, skipping coda stops, and skipping the vowel/consonant units already covered by a preceding stop's `say`.
  - `decoding.decode_map(text: str, limit: int = 400) -> dict[str, dict]`: keys = distinct `WORD` matches lowercased, first `limit` only.
  - `decoding.propose_hard_words(text: str, count: int = 6) -> list[str]`: distinct lowercased words ordered by syllable count desc, then length desc, then first appearance; words with fewer than 3 letters excluded.
  - Template tag `{% load decoding %}{% decode_map text %}` → `django.utils.html.json_script(decode_map(text), f'decode-map-{secrets.token_hex(4)}')`.

- [ ] **Step 1: Write the failing tests** in `homework/tests_decoding.py`

```python
def blends(d): return [[d['letters'][i]['say'] for i in s['blend']] for s in d['syllables']]
def test_continuants_elongated(self):
    d = decode_word('leyeron')
    self.assertEqual([l['text'] for l in d['letters']], ['l', 'e', 'y', 'e', 'r', 'o', 'n'])
    self.assertEqual(blends(d), [['lll', 'e'], ['yyy', 'e'], ['rrr', 'o', 'nnn']])
def test_stops_said_as_syllable(self):
    self.assertEqual(blends(decode_word('pato')), [['pa'], ['to']])
    self.assertEqual(decode_word('pato')['letters'][0]['say'], 'pa')
    self.assertEqual(blends(decode_word('tren')), [['tre', 'nnn']])
    self.assertEqual(blends(decode_word('queso')), [['que'], ['sss', 'o']])
def test_soft_c_and_g(self):
    self.assertEqual(blends(decode_word('cena')), [['sss', 'e'], ['nnn', 'a']])
    self.assertEqual(blends(decode_word('gente')), [['jjj', 'e', 'nnn'], ['te']])
    self.assertEqual(blends(decode_word('gato')), [['ga'], ['to']])
def test_silent_h_and_coda_stop(self):
    self.assertEqual(blends(decode_word('hola')), [['o'], ['lll', 'a']])
    self.assertEqual(blends(decode_word('insecto')), [['i', 'nnn'], ['sss', 'e'], ['to']])
def test_never_letter_names(self):  # no say in {'eme', 'ese', 'ele', 'ene', 'pe', 'te', 'be', 'de'} for a sample text
def test_audio_override(self):
    with mock.patch.dict(PHONEME_AUDIO, {'mmm': '/static/audio/m.mp3'}):
        self.assertEqual(decode_word('mesa')['letters'][0]['audio'], '/static/audio/m.mp3')
def test_decode_map_keys_are_lowercase_words(self):
    self.assertEqual(set(decode_map('¿Leyeron el libro? ¡Leyeron!')), {'leyeron', 'el', 'libro'})
def test_propose_hard_words(self):
    self.assertEqual(propose_hard_words('El murciélago y la mariposa leyeron un libro', 3), ['murciélago', 'mariposa', 'leyeron'])
def test_template_tag_outputs_json_script(self):  # rendered contains 'id="decode-map-' and '"leyeron"'
```

- [ ] **Step 2: Run** `DB_ENGINE=sqlite python manage.py test homework.tests_decoding -v 2` — Expected: FAIL.
- [ ] **Step 3: Implement** phonemes, decoding and the tag.
- [ ] **Step 4: Run** the same command — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(homework): FAS phoneme table and decode map"`

### Task 10: Tap-a-word FAS overlay, help logging and Palabras step

**Files:**
- Create: `static/js/homework/decode.js`, `templates/homework/partials/decode_overlay.html`, `templates/homework/steps/palabras.html`
- Modify: `static/js/main.js:135-157` (speech end callback + sequence), `homework/views_student.py` (`decode_help`), `homework/services.py` (`record_decode_help`), `homework/forms.py` (`PalabrasStepForm`, register in `STEP_FORMS`), `templates/homework/steps/*.html` (child texts get `data-decodable` + `{% decode_map %}`), `templates/homework/student/step.html` and `task_preview.html` (include overlay + `decode.js`), `templates/readings/detail.html:24-33` (`data-decodable` on the reading blocks + `{% decode_map reading.content %}` + overlay)
- Test: `homework/tests_decoding.py` (add view/service tests), `homework/tests_steps.py` (palabras form)

**Interfaces:**
- Consumes: Task 9 tag; Task 4 `mark_item_done`; `window.AppSpeech`, `window.Mascot`.
- Produces:
  - `AppSpeech.speak(text, options)` additionally accepts `options.onend` (called on utterance `end` or `error`, and immediately when speech is unavailable); new `AppSpeech.speakSequence(items: string[], {gapMs = 250, rate}) -> Promise<void>`.
  - `decode.js`: wraps each word text node inside `[data-decodable]` (skipping buttons, inputs and `[data-no-decode]`) in `<button type="button" class="decode-word" data-word="<lowercase>">`; merges every `script[id^="decode-map-"]`; on tap opens the overlay and dispatches `decode:help` (`detail: {word}`, bubbles) from the tapped button; letters tap → play that letter; "Juntar los sonidos" → for each syllable play `blend` items (audio file if `audio`, else `AppSpeech.speakSequence` at `rate: 0.7`), highlight the syllable, then speak the syllable, then the whole word; at the end dispatch `decode:done` (`detail: {word}`). Exposes `window.Decode = {open(word)}`. Words missing from the map are spoken whole. Works without speech (visual steps still run on a timer).
  - Overlay copy: heading "Vamos a leer esta palabra", hint "Toca cada letra para escuchar su sonido.", buttons "Juntar los sonidos", "Otra vez", "Cerrar" (`aria-label`); letters ≥ 2.5rem, separated by "·"; `<dialog class="decode-overlay">`.
  - `services.record_decode_help(assignment, step: TaskStep | None, word: str) -> DecodeHelpEvent` (word stripped, lowercased, truncated to 80).
  - `decode_help` view POST `{'word': str, 'step_order': int|null}` → `{'saved': True}`; empty word → 400. `task-player.js` posts it on `decode:help` inside `[data-task-step]` (not in preview, not on palabras steps — there tapping is the exercise, so only `decode:done` matters).
  - `PalabrasStepForm`: `words` Textarea "Una palabra por línea (3 a 6)"; initial from `propose_hard_words(<text of the task's first lectura step>)` when one exists; each word must match `^[^\W\d_]+$`, ≤ 30 chars.
  - `steps/palabras.html`: one big word card per word; finishing `decode:done` on word *i* calls `TaskPlayer.done(i)` and marks the card ⭐.

- [ ] **Step 1: Write the failing tests**

```python
def test_decode_help_records_event(self):
    self.client.post(help_url, data='{"word": "Leyeron", "step_order": 2}', content_type='application/json')
    e = DecodeHelpEvent.objects.get(); self.assertEqual((e.word, e.step.order), ('leyeron', 2))
def test_decode_help_rejects_empty_word(self):  # 400
def test_decode_help_other_student_404(self):
def test_contesta_step_ships_decode_map_and_decodable_text(self):  # 'data-decodable', 'decode-map-'
def test_reading_detail_is_decodable(self):
def test_palabras_form_initial_proposes_words_from_lectura(self):
def test_palabras_items_complete_step(self):  # 3 words: done(0), done(1) -> step not done; done(2) -> done
```

- [ ] **Step 2: Run** `DB_ENGINE=sqlite python manage.py test homework -v 1` — Expected: new tests FAIL.
- [ ] **Step 3: Implement** per Interfaces. CSS in `homework.css`: `.decode-word` inherits font, dotted underline `--kid-primary`, min target 48 px via padding; syllable highlight `--kid-sun-soft`; animations behind reduced-motion guards.
- [ ] **Step 4: Run** `DB_ENGINE=sqlite python manage.py test homework readings -v 1` — Expected: PASS. Manual check in the browser on `/lecturas/<pk>/` and a task step: tapping "leyeron" shows l · e · y · e · r · o · n and plays "lll-e → le" etc.
- [ ] **Step 5: Commit** `git commit -m "feat(homework): tap any word to decode it with FAS sounds"`

---

## Phase 3 — Assisted writing

### Task 11: Tiles, distractors and omission detection

**Files:**
- Create: `homework/writing.py`
- Test: `homework/tests_writing.py`

**Interfaces:**
- Consumes: Task 8 `word_units`, `split_syllables`, `WORD`.
- Produces:
  - `BUILD_MAX_UNITS = 12`; `CONFUSABLE = {'b': 'd', 'd': 'b', 'p': 'q', 'q': 'p', 'm': 'n', 'n': 'm', 'u': 'n'}`; `FILLER_WORDS = ('el', 'la', 'los', 'un', 'una')`; vowel neighbour cycle `a→e→i→o→u→a`.
  - `split_units(text: str, unit: str) -> list[str]`: `'letter'` → unit texts of `word_units` (single word only), `'syllable'` → `split_syllables` (single word only), `'word'` → `WORD.findall(text)`; raises `ValueError` for a multi-word letter/syllable target.
  - `build_tiles(units: list[str], unit: str, seed: int) -> list[str]`: all target units plus `2` distractors when `len(units) <= 2` else `3`, shuffled with `random.Random(seed)`. Candidates, in order: for each target unit, (1) its first `CONFUSABLE` letter swapped (`'ba'→'da'`, `'m'→'n'`), (2) its first vowel shifted along the cycle, repeated up to 4 times; then fallback pools — letters `'bdpqmnaeiou'`, words `FILLER_WORDS`. Keep the first candidates that are distinct and never equal (casefold) to a target unit.
  - `@dataclass BuildCheck(status: str, missing: list[tuple[int, str]], hole_index: int | None)`; `check_build(target: list[str], answer: list[str]) -> BuildCheck` with casefold comparison using `difflib.SequenceMatcher(autojunk=False)`: equal → `'correct'`; only `equal`/`delete` opcodes with ≥ 1 delete → `'omission'` (each deleted target unit with its index; `hole_index` = first index); anything else → `'wrong'`, `missing=[]`, `hole_index=None`.

- [ ] **Step 1: Write the failing tests** in `homework/tests_writing.py`

```python
def test_split_units(self):
    self.assertEqual(split_units('carro', 'letter'), ['c', 'a', 'rr', 'o'])
    self.assertEqual(split_units('mariposa', 'syllable'), ['ma', 'ri', 'po', 'sa'])
    self.assertEqual(split_units('El gato come.', 'word'), ['El', 'gato', 'come'])
    with self.assertRaises(ValueError): split_units('el gato', 'syllable')
def test_build_tiles_counts_and_distractors(self):
    tiles = build_tiles(['ca', 'sa'], 'syllable', seed=1)
    self.assertEqual(len(tiles), 4); self.assertTrue({'ca', 'sa'} <= set(tiles))
    tiles = build_tiles(['m', 'a', 'm', 'á'], 'letter', seed=1)
    self.assertEqual(len(tiles), 7); self.assertIn('n', tiles)
def test_build_tiles_deterministic(self):  # same seed -> same list; different seed may differ
def test_distractors_never_equal_targets(self):  # for 20 seeds over ['b','d','a']
def test_check_build(self):
    self.assertEqual(check_build(['ca', 'sa'], ['Ca', 'sa']).status, 'correct')
    c = check_build(['ma', 'ri', 'po', 'sa'], ['ma', 'po', 'sa']); self.assertEqual((c.status, c.missing, c.hole_index), ('omission', [(1, 'ri')], 1))
    self.assertEqual(check_build(['g', 'a', 't', 'o'], ['g', 'a']).missing, [(2, 't'), (3, 'o')])
    self.assertEqual(check_build(['g', 'a', 't', 'o'], ['g', 'a', 'd', 'o']).status, 'wrong')
    self.assertEqual(check_build(['ca', 'sa'], ['sa', 'ca']).status, 'wrong')
```

- [ ] **Step 2: Run** `DB_ENGINE=sqlite python manage.py test homework.tests_writing -v 2` — Expected: FAIL.
- [ ] **Step 3: Implement** `homework/writing.py`.
- [ ] **Step 4: Run** the same command — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(homework): tile building and omission detection"`

### Task 12: Arma/completa step and built Contesta answers

**Files:**
- Create: `templates/homework/steps/arma.html`, `templates/homework/partials/tiles.html`, `static/js/homework/tiles.js`
- Modify: `homework/evaluation.py`, `homework/payloads.py` (arma/contesta-build unit limit via `split_units`), `homework/forms.py` (`ArmaStepForm`, register), `templates/homework/steps/contesta.html` (build mode), `homework/views_student.py` (tiles in context)
- Test: `homework/tests_writing.py` (add evaluation + view tests)

**Interfaces:**
- Consumes: Task 11; Task 4 `submit_answer`/`Evaluation`; Task 9 `decode_word` (hint sounds).
- Produces:
  - arma target: `before, blank, after = parse_blank(text)`; target text = `blank or text`; `unit` from payload. contesta `kind='build'`: target = `answer`, unit `'word'` if it has a space else `'syllable'`.
  - Payload validation: target units 1..`BUILD_MAX_UNITS`; letter/syllable targets single word (form error "Para letras o sílabas usa una sola palabra.").
  - `evaluate` for arma / contesta build: payload `{'tiles': [str]}` (non-list, empty, non-strings or > 2×`BUILD_MAX_UNITS` → `InvalidAnswer`); `answer_text` = tiles joined (`''` for letters/syllables, `' '` for words); `omission` → `hint = {'say': <sound>, 'hole_index': i, 'kind': 'omission'}` where sound = `decode_word(target)['letters'][i]['say']` for letters, the unit text otherwise; `wrong` → `hint = {'say': target text, 'hole_index': None, 'kind': 'try_again'}`; `omissions` = `missing` (saved as `OmissionEvent(target=target text, missing_unit, position)` by `submit_answer`); `model_answer` = full text with the blank filled.
  - View context: `tiles = build_tiles(units, unit, seed=assignment.pk * 1000 + step.pk)`; template shows `before` / hole / `after` for blanks.
  - `tiles.js`: tap a tile → appends to the answer row (tap a placed tile → returns it); "Revisar" (64 px) → `TaskPlayer.answer(0, {tiles})`; on `kind: 'omission'` inserts a 👀 placeholder at `hole_index`, plays the sound and shows `FEEDBACK['omission']`; on `'modeled'` shows the model answer in the row and speaks it; drag is optional, tapping always works.

- [ ] **Step 1: Write the failing tests**

```python
def test_arma_omission_records_event_and_hint(self):
    # payload {'text': 'mariposa', 'unit': 'syllable'}
    body = post({'item_index': 0, 'tiles': ['ma', 'po', 'sa']}).json()
    self.assertEqual(body['status'], 'try_again'); self.assertEqual(body['hint'], {'say': 'ri', 'hole_index': 1, 'kind': 'omission'})
    o = OmissionEvent.objects.get(); self.assertEqual((o.target, o.missing_unit, o.position), ('mariposa', 'ri', 1))
def test_letter_omission_hint_is_phoneme(self):  # 'gato' letters, answer g,a,o -> hint say 'to'
def test_blank_sentence_checks_only_blank(self):  # 'El [gato] come.' unit word, tiles ['gato'] -> correct; model_answer 'El gato come.'
def test_second_failure_models_full_text(self):
def test_contesta_build_uses_word_tiles(self):
def test_arma_form_rejects_multiword_letter_target(self):
def test_tiles_rendered_include_distractors(self):  # step page shows 4 tiles for 'casa' syllables
def test_bad_tiles_payload_400(self):  # {'tiles': 'ma'} and {'tiles': []}
```

- [ ] **Step 2: Run** `DB_ENGINE=sqlite python manage.py test homework.tests_writing -v 2` — Expected: new tests FAIL.
- [ ] **Step 3: Implement** per Interfaces.
- [ ] **Step 4: Run** `DB_ENGINE=sqlite python manage.py test homework -v 1` — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(homework): assisted writing with tiles and omission hints"`

---

## Phase 4 — Worked example and practice

### Task 13: Ejemplo y práctica step

**Files:**
- Create: `templates/homework/steps/ejemplo.html`
- Modify: `homework/forms.py` (`EjemploStepForm` + `ExerciseFormSet`, register), `templates/homework/teacher/step_form.html` (render formset), `homework/evaluation.py`, `static/js/homework/task-player.js` (example walkthrough)
- Test: `homework/tests_ejemplo.py`

**Interfaces:**
- Consumes: Task 4 `submit_answer`; `clean_payload('ejemplo', …)`.
- Produces:
  - `EjemploStepForm`: `example_steps` Textarea "Un paso del ejemplo por línea (1 a 5)", `image` optional; `ExerciseFormSet = formset_factory(ExerciseForm, extra=3, min_num=1, max_num=EXERCISES_MAX, validate_min=True)` where `ExerciseForm` has `prompt`, `answer`, `distractors` ("Otras opciones, separadas por coma", 1–3); payload exercise `options = [answer] + distractors` (deduplicated; order shuffled on render with `random.Random(assignment.pk + step.pk + index)`).
  - `evaluate` for ejemplo: `item_index` = exercise index, payload `{'choice': int}` into the *stored* `options`; hint `{'say': prompt, 'hole_index': None, 'kind': 'try_again'}`; `model_answer = answer`. The rendered choice buttons carry the stored option index, not the shuffled position.
  - Child UI: example shown one line at a time with its own listen button and "Siguiente" (64 px); after the last line "¡Ahora yo!" reveals exercise 1; one exercise per screen; each exercise item closes through `submit_answer`.

- [ ] **Step 1: Write the failing tests** in `homework/tests_ejemplo.py`

```python
def test_formset_builds_payload(self):
    # example_steps '2 + 1 = ?\nCuento 2 y sumo 1\n2 + 1 = 3'; exercise prompt '3 + 1 = ?', answer '4', distractors '5, 3'
    self.assertEqual(step.payload['exercises'], [{'prompt': '3 + 1 = ?', 'answer': '4', 'options': ['4', '5', '3']}])
def test_formset_requires_one_exercise(self):
def test_exercise_items_close_step(self):  # 2 exercises: answer both -> step_done True
def test_exercise_wrong_twice_models_answer(self):  # model_answer '4'
def test_rendered_option_buttons_use_stored_indexes(self):
```

- [ ] **Step 2: Run** `DB_ENGINE=sqlite python manage.py test homework.tests_ejemplo -v 2` — Expected: FAIL.
- [ ] **Step 3: Implement** per Interfaces.
- [ ] **Step 4: Run** `DB_ENGINE=sqlite python manage.py test homework -v 1` — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(homework): worked example and practice step"`

---

## Phase 5 — Teacher reports

### Task 14: SNEPA suggested level

**Files:**
- Create: `homework/levels.py`
- Modify: `homework/services.py` (`complete_assignment` stores `snepa_suggested`)
- Test: `homework/tests_levels.py`

**Interfaces:**
- Consumes: Task 1 `SnepaLevel`, `StepResult`, `DecodeHelpEvent`.
- Produces: `suggest_snepa(evaluated: int, first_try_correct: int, helps: int) -> str` and `suggest_for_assignment(assignment) -> str`. `evaluated` = results with `first_try_correct` not null; `helps` = `sum(hints_used)` + count of `modeled` + `DecodeHelpEvent`s whose step is not a palabras step (decoding there is the exercise). With `accuracy = first_try_correct / evaluated` and `help_rate = helps / evaluated`:

```text
evaluated == 0                                   -> ''   (shown to the teacher as "Sin datos suficientes")
accuracy >= 0.9 and help_rate <= 0.25            -> 'AA'
accuracy >= 0.7 and help_rate <= 0.75            -> 'AS'
accuracy >= 0.4                                  -> 'AF'
otherwise                                        -> 'AI'
```

- [ ] **Step 1: Write the failing tests** in `homework/tests_levels.py`

```python
def test_thresholds(self):
    self.assertEqual(suggest_snepa(10, 9, 2), 'AA')
    self.assertEqual(suggest_snepa(10, 9, 3), 'AS')   # help_rate 0.3
    self.assertEqual(suggest_snepa(10, 7, 7), 'AS')
    self.assertEqual(suggest_snepa(10, 7, 8), 'AF')
    self.assertEqual(suggest_snepa(10, 4, 20), 'AF')
    self.assertEqual(suggest_snepa(10, 3, 0), 'AI')
    self.assertEqual(suggest_snepa(0, 0, 5), '')
def test_palabras_decode_help_not_counted(self):
def test_completion_stores_suggestion(self):  # finish a task with one first-try-correct contesta -> snepa_suggested 'AA'
```

- [ ] **Step 2: Run** `DB_ENGINE=sqlite python manage.py test homework.tests_levels -v 2` — Expected: FAIL.
- [ ] **Step 3: Implement** `levels.py` and call it inside `complete_assignment` (same transaction).
- [ ] **Step 4: Run** `DB_ENGINE=sqlite python manage.py test homework -v 1` — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(homework): suggest SNEPA level from first tries and helps"`

### Task 15: Task and per-child reports, SNEPA override, parent view

**Files:**
- Create: `templates/homework/teacher/task_report.html`, `templates/homework/teacher/assignment_report.html`, `homework/reports.py`
- Modify: `homework/views_teacher.py` (`task_report`, `assignment_report`, `assignment_level_update`), `homework/forms.py` (`SnepaOverrideForm`), `dashboard/views.py:1137-1147` (`parent_dashboard` adds recent completed tasks), `templates/dashboard/parent_dashboard.html` (completion lines), `templates/dashboard/student_report.html` (link "Tareas" per assignment only when `can_view_difficulty_data`)
- Test: `homework/tests_reports.py`

**Interfaces:**
- Consumes: Task 2 permissions; Task 14 `SnepaLevel`.
- Produces:
  - `reports.task_rows(task) -> list[dict]` (`assignment`, `student`, `status`, `steps_done`, `steps_total`) and `reports.assignment_detail(assignment) -> dict` with `answers` (per step/item: step type, prompt, `first_answer`, `answer`, `first_try_correct`, `hints_used`, `modeled`), `decode_words` (`[(word, count)]` most-asked first), `omissions` (`[(target, missing_unit, count)]`).
  - `task_report`: owner or admin; table Alumno, Estado (Sin empezar / En curso / Terminada), Pasos (`3/5`); columns "Nivel" and "Detalle" render only for rows where `can_view_difficulty_data(user, student)`.
  - `assignment_report`: 404 unless `can_view_difficulty_data(request.user, assignment.student)` (any linked teacher with report permission, not only the owner; admins). Sections "Respuestas", "Palabras que pidió decodificar", "Omisiones al escribir", "Nivel SNEPA" (suggested label, or "Sin datos suficientes", plus override form).
  - `SnepaOverrideForm`: `level` ChoiceField (`[('', 'Usar el sugerido')] + SnepaLevel.choices`); `assignment_level_update` saves `snepa_override`, `snepa_override_by`, `snepa_override_at`, writes `write_audit(request, 'override_task_level', assignment, {'level': level})`.
  - Parent dashboard: per linked student, the last 3 completed assignments as "{name} terminó la tarea «{title}». ¡Celebren juntos su esfuerzo!"; nothing else from `homework`.

- [ ] **Step 1: Write the failing tests** in `homework/tests_reports.py`

```python
def test_owner_with_report_permission_sees_detail(self):
    # assertContains 'leyeron' (decode word), 'ri' omission row, 'Aprendizaje Avanzado'
def test_detail_report_denied_without_report_permission_or_link(self):
    # owner without can_view_student_reports -> 404; linked teacher without permission -> 404; unlinked teacher with permission -> 404; parent -> 404 (or redirect), never contains 'leyeron'
def test_linked_teacher_with_permission_who_is_not_owner_sees_detail(self):
def test_task_report_hides_level_column_without_permission(self):  # assertNotContains 'Nivel'
def test_override_level(self):  # POST level 'AF' -> snepa_level 'AF', AuditLog row 'override_task_level'; POST '' -> back to suggested
def test_parent_sees_only_completion(self):
    # assertContains 'terminó la tarea «Los animales»'; assertNotContains 'leyeron', 'Aprendizaje', 'omisi'
def test_student_never_sees_levels(self):  # student_task after completion: assertNotContains 'Aprendizaje'
```

- [ ] **Step 2: Run** `DB_ENGINE=sqlite python manage.py test homework.tests_reports -v 2` — Expected: FAIL.
- [ ] **Step 3: Implement** per Interfaces; tables use `data-table` + `table-stack` classes like `lesson_plan_report.html`.
- [ ] **Step 4: Run the full suite** `DB_ENGINE=sqlite python manage.py test -v 1` — Expected: `OK` (all apps).
- [ ] **Step 5: Commit** `git commit -m "feat(homework): teacher task reports with difficulties and SNEPA"`

---

## Spec coverage map

| Spec | Task |
|---|---|
| §5.1 create task: subject, grade, students/group, 6 step types, preview, duplicate | 2, 3, 7, 10, 12, 13 |
| §5.2 child path, audio instructions, resume, celebration, dashboard first | 5, 6 |
| §5.3 FAS decoding in any child text, Spanish syllables, help logged | 8, 9, 10 |
| §5.4 tiles, hole marker with sound, omissions logged | 11, 12 |
| §5.5 teacher progress, answers, decode words, omissions, SNEPA editable; parent completion only | 14, 15 |
| §6 replaceable phoneme table, light pages, Ley 787, accessibility, existing features | 9, 10, 15, Global Constraints |
| §8 lock after start, 2-attempt modeling, group by grade, plan link, distractors 2–3, nearest due date first | 2, 3, 4, 11 |
