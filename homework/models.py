from django.core.exceptions import ValidationError
from django.db import models

from learning.models import LessonPlan, StudentProfile, Subject, TeacherProfile
from readings.models import Reading

from . import dictation
from .payloads import MAX_TEXT, clean_payload

MISSING_UNIT_MAX = 30


class SnepaLevel(models.TextChoices):
    INITIAL = 'AI', 'Aprendizaje Inicial'
    FUNDAMENTAL = 'AF', 'Aprendizaje Fundamental'
    SATISFACTORY = 'AS', 'Aprendizaje Satisfactorio'
    ADVANCED = 'AA', 'Aprendizaje Avanzado'


class Task(models.Model):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='tasks')
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='tasks')
    grade = models.CharField(max_length=1, choices=StudentProfile.Grade.choices)
    title = models.CharField(max_length=160)
    due_date = models.DateField(null=True, blank=True)
    lesson_plan = models.ForeignKey(LessonPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def is_locked(self) -> bool:
        return self.assignments.filter(started_at__isnull=False).exists()


class TaskStep(models.Model):
    class StepType(models.TextChoices):
        MIRA = 'mira', 'Mira y comenta'
        LECTURA = 'lectura', 'Lectura'
        PALABRAS = 'palabras', 'Palabras difíciles'
        CONTESTA = 'contesta', 'Contesta'
        ARMA = 'arma', 'Arma o completa'
        EJEMPLO = 'ejemplo', 'Ejemplo y práctica'
        DICTADO = 'dictado', 'Dictado'

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='steps')
    order = models.PositiveSmallIntegerField()
    step_type = models.CharField(max_length=20, choices=StepType.choices)
    payload = models.JSONField(default=dict)
    image = models.ImageField(upload_to='tasks/', blank=True, null=True)
    reading = models.ForeignKey(Reading, on_delete=models.SET_NULL, null=True, blank=True, related_name='task_steps')

    class Meta:
        ordering = ['order']
        constraints = [
            models.UniqueConstraint(fields=['task', 'order'], name='unique_task_step_order'),
        ]

    def __str__(self):
        return f'{self.task_id} #{self.order} {self.step_type}'

    @property
    def item_count(self) -> int:
        if self.step_type == self.StepType.PALABRAS:
            return len(self.payload.get('words', []))
        if self.step_type == self.StepType.EJEMPLO:
            return len(self.payload.get('exercises', []))
        if self.step_type == self.StepType.DICTADO:
            return dictation.ITEMS
        return 1

    @property
    def text(self) -> str:
        if self.step_type != self.StepType.LECTURA:
            return ''
        if self.reading_id:
            return self.reading.content
        return self.payload.get('text', '')

    def clean(self):
        super().clean()
        self.payload = clean_payload(self.step_type, self.payload)
        if self.step_type == self.StepType.LECTURA and not self.reading_id and not self.payload['text']:
            raise ValidationError('La lectura necesita una lectura de la biblioteca o un texto.')


class TaskAssignment(models.Model):
    class Status(models.TextChoices):
        ASSIGNED = 'assigned', 'Sin empezar'
        IN_PROGRESS = 'in_progress', 'En curso'
        COMPLETED = 'completed', 'Terminada'

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='assignments')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='task_assignments')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ASSIGNED)
    assigned_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    points_awarded = models.PositiveSmallIntegerField(default=0)
    snepa_suggested = models.CharField(max_length=2, choices=SnepaLevel.choices, blank=True)
    snepa_override = models.CharField(max_length=2, choices=SnepaLevel.choices, blank=True)
    snepa_override_by = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    snepa_override_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['task', 'student'], name='unique_task_assignment'),
        ]

    def __str__(self):
        return f'{self.task_id} -> {self.student_id} ({self.status})'

    @property
    def snepa_level(self) -> str:
        return self.snepa_override or self.snepa_suggested


class StepResult(models.Model):
    assignment = models.ForeignKey(TaskAssignment, on_delete=models.CASCADE, related_name='results')
    step = models.ForeignKey(TaskStep, on_delete=models.CASCADE, related_name='results')
    item_index = models.PositiveSmallIntegerField(default=0)
    attempts = models.PositiveSmallIntegerField(default=0)
    first_answer = models.CharField(max_length=255, blank=True)
    answer = models.CharField(max_length=255, blank=True)
    first_try_correct = models.BooleanField(null=True, blank=True)
    hints_used = models.PositiveSmallIntegerField(default=0)
    modeled = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['assignment', 'step', 'item_index'], name='unique_step_result_item'),
        ]

    def save(self, *args, **kwargs):
        # Child input may be longer than the column; never overflow on PostgreSQL.
        self.first_answer = self.first_answer[:MAX_TEXT]
        self.answer = self.answer[:MAX_TEXT]
        super().save(*args, **kwargs)


class DecodeHelpEvent(models.Model):
    assignment = models.ForeignKey(TaskAssignment, on_delete=models.CASCADE, related_name='decode_helps')
    step = models.ForeignKey(TaskStep, on_delete=models.SET_NULL, null=True, blank=True)
    word = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['assignment', 'word'])]

    def save(self, *args, **kwargs):
        self.word = self.word[:80]
        super().save(*args, **kwargs)


class OmissionEvent(models.Model):
    assignment = models.ForeignKey(TaskAssignment, on_delete=models.CASCADE, related_name='omissions')
    step = models.ForeignKey(TaskStep, on_delete=models.CASCADE)
    target = models.CharField(max_length=255)
    missing_unit = models.CharField(max_length=MISSING_UNIT_MAX)
    position = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.target = self.target[:MAX_TEXT]
        self.missing_unit = self.missing_unit[:MISSING_UNIT_MAX]
        super().save(*args, **kwargs)
