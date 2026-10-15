from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from accounts.models import CustomUser
from learning.models import Level, StudentProfile, Subject, TeacherProfile
from readings.models import Reading

from .models import OmissionEvent, SnepaLevel, StepResult, Task, TaskAssignment, TaskStep
from .payloads import MAX_LECTURA_TEXT, clean_payload, parse_blank


class PayloadTests(SimpleTestCase):
    def test_contesta_choice_requires_answer_among_options(self):
        with self.assertRaises(ValidationError):
            clean_payload('contesta', {'question': '¿Qué come?', 'kind': 'choice', 'options': ['pan', 'sol'], 'answer': 'luna'})

    def test_contesta_choice_valid(self):
        data = clean_payload('contesta', {'question': ' ¿Qué come? ', 'kind': 'choice', 'options': ['pan', 'sol'], 'answer': 'pan'})
        self.assertEqual(data, {'question': '¿Qué come?', 'kind': 'choice', 'options': ['pan', 'sol'], 'answer': 'pan'})

    def test_contesta_build_needs_no_options(self):
        data = clean_payload('contesta', {'question': '¿Cómo se llama?', 'kind': 'build', 'answer': 'sol'})
        self.assertEqual(data['kind'], 'build')
        self.assertEqual(data['options'], [])

    def test_palabras_count_limits(self):
        for words in (['a1', 'b2'], [f'p{i}' for i in range(7)]):
            with self.assertRaises(ValidationError):
                clean_payload('palabras', {'words': words})
        self.assertEqual(clean_payload('palabras', {'words': ['sol', 'luna', 'mar']})['words'], ['sol', 'luna', 'mar'])

    def test_palabras_strip_and_deduplicate(self):
        self.assertEqual(clean_payload('palabras', {'words': [' casa', 'casa', 'perro', 'sol ']})['words'], ['casa', 'perro', 'sol'])

    def test_unknown_step_type_raises(self):
        with self.assertRaises(ValidationError):
            clean_payload('baile', {})

    def test_mira_requires_question(self):
        with self.assertRaises(ValidationError):
            clean_payload('mira', {'question': '  '})
        self.assertEqual(clean_payload('mira', {'question': ' ¿Qué ves? '}), {'question': '¿Qué ves?'})

    def test_lectura_allows_empty_text_and_long_text(self):
        self.assertEqual(clean_payload('lectura', {}), {'text': ''})
        long_text = 'a' * 3000
        self.assertEqual(clean_payload('lectura', {'text': long_text})['text'], long_text)
        with self.assertRaises(ValidationError):
            clean_payload('lectura', {'text': 'a' * (MAX_LECTURA_TEXT + 1)})

    def test_arma_validates_unit_and_blank(self):
        data = clean_payload('arma', {'text': 'El [gato] come.', 'unit': 'word'})
        self.assertEqual(data, {'text': 'El [gato] come.', 'unit': 'word'})
        with self.assertRaises(ValidationError):
            clean_payload('arma', {'text': 'El [gato] come.', 'unit': 'phrase'})
        with self.assertRaises(ValidationError):
            clean_payload('arma', {'text': 'Dos [a] y [b]', 'unit': 'letter'})

    def test_text_over_max_raises(self):
        with self.assertRaises(ValidationError):
            clean_payload('mira', {'question': 'q' * 256})

    def test_non_dict_payload_raises(self):
        with self.assertRaises(ValidationError):
            clean_payload('mira', ['not', 'a', 'dict'])

    def test_parse_blank(self):
        self.assertEqual(parse_blank('El [gato] come.'), ('El ', 'gato', ' come.'))
        self.assertEqual(parse_blank('Mi ma[má] me ama.'), ('Mi ma', 'má', ' me ama.'))
        self.assertEqual(parse_blank('Sin hueco'), ('Sin hueco', '', ''))
        for bad in ('Dos [a] y [b]', 'Vacío []'):
            with self.assertRaises(ValidationError):
                parse_blank(bad)

    def test_ejemplo_exercise_options_contain_answer(self):
        good = {'prompt': '2+2', 'answer': '4', 'options': ['3', '4']}
        data = clean_payload('ejemplo', {'example_steps': ['Suma'], 'exercises': [good]})
        self.assertEqual(data['exercises'], [good])
        bad = {'prompt': '2+2', 'answer': '5', 'options': ['3', '4']}
        with self.assertRaises(ValidationError):
            clean_payload('ejemplo', {'example_steps': ['Suma'], 'exercises': [bad]})
        with self.assertRaises(ValidationError):
            clean_payload('ejemplo', {'example_steps': ['Suma'], 'exercises': [dict(good, options=['4'])]})

    def test_ejemplo_limits(self):
        good = {'prompt': 'p', 'answer': 'a', 'options': ['a', 'b']}
        with self.assertRaises(ValidationError):
            clean_payload('ejemplo', {'example_steps': ['s'] * 6, 'exercises': [good]})
        with self.assertRaises(ValidationError):
            clean_payload('ejemplo', {'example_steps': ['s'], 'exercises': [good] * 6})
        with self.assertRaises(ValidationError):
            clean_payload('ejemplo', {'example_steps': ['s'], 'exercises': []})


class TaskModelTests(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial')
        self.subject = Subject.objects.create(name='Lengua y Literatura')
        self.teacher = TeacherProfile.objects.create(name='Maestra Ana', is_active=True)
        user = CustomUser.objects.create_user(username='nino', password='x')
        self.student = StudentProfile.objects.create(user=user, name='Nino', grade='1', reading_level=self.level, current_level=self.level)
        self.task = Task.objects.create(teacher=self.teacher, subject=self.subject, grade='1', title='Tarea 1')

    def _step(self, order, step_type, payload, **extra):
        return TaskStep.objects.create(task=self.task, order=order, step_type=step_type, payload=payload, **extra)

    def test_step_order_unique_per_task(self):
        self._step(1, 'mira', {'question': 'q'})
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._step(1, 'mira', {'question': 'q2'})

    def test_is_locked_after_first_start(self):
        assignment = TaskAssignment.objects.create(task=self.task, student=self.student)
        self.assertFalse(self.task.is_locked)
        assignment.started_at = timezone.now()
        assignment.save()
        self.assertTrue(self.task.is_locked)

    def test_assignment_unique_per_student(self):
        TaskAssignment.objects.create(task=self.task, student=self.student)
        with self.assertRaises(IntegrityError), transaction.atomic():
            TaskAssignment.objects.create(task=self.task, student=self.student)

    def test_item_count_by_type(self):
        self.assertEqual(self._step(1, 'palabras', {'words': ['a', 'b', 'c', 'd']}).item_count, 4)
        ex = {'prompt': 'p', 'answer': 'a', 'options': ['a', 'b']}
        self.assertEqual(self._step(2, 'ejemplo', {'example_steps': ['s'], 'exercises': [ex, ex]}).item_count, 2)
        self.assertEqual(self._step(3, 'mira', {'question': 'q'}).item_count, 1)

    def test_lectura_text_prefers_reading(self):
        reading = Reading.objects.create(title='R', content='Texto de la lectura', level=self.level)
        step = self._step(1, 'lectura', {'text': 'Texto propio'}, reading=reading)
        self.assertEqual(step.text, 'Texto de la lectura')
        own = self._step(2, 'lectura', {'text': 'Texto propio'})
        self.assertEqual(own.text, 'Texto propio')

    def test_lectura_requires_reading_or_text(self):
        with self.assertRaises(ValidationError):
            TaskStep(task=self.task, order=1, step_type='lectura', payload={'text': ''}).clean()
        reading = Reading.objects.create(title='R', content='c', level=self.level)
        TaskStep(task=self.task, order=2, step_type='lectura', payload={}, reading=reading).clean()
        TaskStep(task=self.task, order=3, step_type='lectura', payload={'text': 'hola'}).clean()

    def test_clean_normalizes_payload(self):
        step = TaskStep(task=self.task, order=1, step_type='palabras', payload={'words': [' sol', 'sol', 'mar', 'luz']})
        step.clean()
        self.assertEqual(step.payload['words'], ['sol', 'mar', 'luz'])

    def test_snepa_level_prefers_override(self):
        assignment = TaskAssignment.objects.create(task=self.task, student=self.student, snepa_suggested=SnepaLevel.INITIAL)
        self.assertEqual(assignment.snepa_level, 'AI')
        assignment.snepa_override = SnepaLevel.ADVANCED
        self.assertEqual(assignment.snepa_level, 'AA')

    def test_child_answer_fields_are_truncated_on_save(self):
        assignment = TaskAssignment.objects.create(task=self.task, student=self.student)
        step = self._step(1, 'arma', {'text': 'sol', 'unit': 'word'})
        result = StepResult.objects.create(assignment=assignment, step=step, first_answer='x' * 400, answer='y' * 400)
        self.assertEqual((len(result.first_answer), len(result.answer)), (255, 255))
        event = OmissionEvent.objects.create(assignment=assignment, step=step, target='t' * 400, missing_unit='m' * 90, position=0)
        self.assertEqual((len(event.target), len(event.missing_unit)), (255, 30))
