import re

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import formset_factory

from learning.models import LessonPlan, Subject
from readings.models import Reading

from .decoding import propose_hard_words
from .models import SnepaLevel, Task, TaskStep
from .payloads import ARMA_UNITS, EXAMPLE_STEPS_MAX, EXERCISES_MAX, clean_payload
from .services import group_students


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'subject', 'grade', 'due_date', 'lesson_plan']
        labels = {
            'title': 'Título',
            'subject': 'Materia',
            'grade': 'Grado',
            'due_date': 'Fecha de entrega',
            'lesson_plan': 'Plan de clase (opcional)',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'grade': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'lesson_plan': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, teacher, locked=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.locked = locked
        current = self.instance
        # The current plan/subject stay valid even if they were deactivated since.
        self.fields['lesson_plan'].queryset = LessonPlan.objects.filter(
            Q(teacher=teacher, is_active=True) | Q(pk=current.lesson_plan_id)
        ).select_related('subject')
        self.fields['subject'].queryset = Subject.objects.filter(Q(is_active=True) | Q(pk=current.subject_id))
        if locked:
            for name, field in self.fields.items():
                if name != 'due_date':
                    field.disabled = True

    def clean(self):
        cleaned = super().clean()
        plan = cleaned.get('lesson_plan')
        if plan and not self.locked:
            cleaned['subject'] = plan.subject
            cleaned['grade'] = plan.grade
            self.instance.subject = plan.subject
            self.instance.grade = plan.grade
        return cleaned


class AssignStudentsForm(forms.Form):
    students = forms.ModelMultipleChoiceField(
        label='Alumnos',
        queryset=None,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    whole_group = forms.BooleanField(label='Todo mi grupo de este grado', required=False)

    def __init__(self, *args, teacher, task, **kwargs):
        super().__init__(*args, **kwargs)
        self.teacher = teacher
        self.task = task
        self.fields['students'].queryset = group_students(teacher, task.grade)

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('whole_group') and not cleaned.get('students'):
            raise forms.ValidationError('Elige al menos un alumno o todo tu grupo.')
        return cleaned

    def selected_students(self):
        if self.cleaned_data.get('whole_group'):
            return group_students(self.teacher, self.task.grade)
        return self.cleaned_data['students']


class SnepaOverrideForm(forms.Form):
    level = forms.ChoiceField(
        label='Nivel SNEPA final',
        required=False,
        choices=[('', 'Usar el sugerido')] + SnepaLevel.choices,
    )


class StepForm(forms.Form):
    """Base for one step type: validates the teacher's input and builds the stored payload."""

    step_type = ''

    def __init__(self, *args, task, step=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.task = task
        self.step = step

    def to_payload(self) -> dict:
        raise NotImplementedError

    def extras(self) -> dict:
        """Keyword arguments for the services that are not part of the JSON payload."""
        return {}

    @classmethod
    def initial_from(cls, step) -> dict:
        return dict(step.payload)

    def clean(self):
        cleaned = super().clean()
        if not self.errors:
            try:
                clean_payload(self.step_type, self.to_payload())
            except ValidationError as error:
                raise ValidationError(error.messages)
        return cleaned


class MiraStepForm(StepForm):
    step_type = 'mira'
    image = forms.ImageField(label='Imagen', widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}))
    question = forms.CharField(
        label='Pregunta o consigna', max_length=255, widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.step is not None and self.step.image:
            self.fields['image'].required = False
            self.fields['image'].help_text = 'Déjala vacía para conservar la imagen actual.'

    def to_payload(self):
        return {'question': self.cleaned_data['question']}

    def extras(self):
        return {'image': self.cleaned_data.get('image')}


class LecturaStepForm(StepForm):
    step_type = 'lectura'
    reading = forms.ModelChoiceField(
        label='Lectura de la biblioteca (opcional)',
        queryset=Reading.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    text = forms.CharField(
        label='O escribe el texto (opcional)',
        required=False,
        max_length=5000,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current = self.step.reading_id if self.step is not None else None
        self.fields['reading'].queryset = Reading.objects.filter(
            Q(is_active=True, grade=self.task.grade) | Q(pk=current)
        ).order_by('title')

    def clean(self):
        cleaned = super().clean()
        if not self.errors and bool(cleaned.get('reading')) == bool(cleaned.get('text', '').strip()):
            raise ValidationError('Elige una lectura de la biblioteca o escribe un texto, pero no las dos cosas.')
        return cleaned

    def to_payload(self):
        return {'text': self.cleaned_data.get('text', '')}

    def extras(self):
        return {'reading': self.cleaned_data.get('reading')}

    @classmethod
    def initial_from(cls, step):
        return {'reading': step.reading_id, 'text': step.payload.get('text', '')}


class ContestaStepForm(StepForm):
    step_type = 'contesta'
    question = forms.CharField(
        label='Pregunta', max_length=255, widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    kind = forms.ChoiceField(
        label='Tipo de respuesta',
        choices=[('choice', 'Elegir una opción'), ('build', 'Armar la respuesta con fichas')],
        initial='choice',
        widget=forms.RadioSelect,
    )
    options = forms.CharField(
        label='Opciones (una opción por línea; solo si eliges una opción)',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
    )
    answer = forms.CharField(
        label='Respuesta correcta', max_length=255, widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    def to_payload(self):
        data = self.cleaned_data
        options = [line.strip() for line in data['options'].splitlines() if line.strip()]
        return {'question': data['question'], 'kind': data['kind'], 'options': options, 'answer': data['answer']}

    @classmethod
    def initial_from(cls, step):
        payload = step.payload
        return {**payload, 'options': '\n'.join(payload.get('options', []))}


WORD_ONLY = re.compile(r'^[^\W\d_]+$')
PALABRA_MAX_LENGTH = 30


class PalabrasStepForm(StepForm):
    step_type = 'palabras'
    words = forms.CharField(
        label='Una palabra por línea (3 a 6)',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'words' not in self.initial:
            proposed = self._proposed_words()
            if proposed:
                self.initial['words'] = '\n'.join(proposed)

    def _proposed_words(self):
        lectura = self.task.steps.filter(step_type=TaskStep.StepType.LECTURA).select_related('reading').first()
        return propose_hard_words(lectura.text) if lectura is not None else []

    def _lines(self, text):
        return [line.strip() for line in text.splitlines() if line.strip()]

    def clean_words(self):
        lines = self._lines(self.cleaned_data['words'])
        for line in lines:
            if len(line) > PALABRA_MAX_LENGTH or not WORD_ONLY.match(line):
                raise ValidationError(
                    f'Escribe una sola palabra por línea, solo con letras y de {PALABRA_MAX_LENGTH} letras o menos: "{line}".'
                )
        return '\n'.join(lines)

    def to_payload(self):
        return {'words': self._lines(self.cleaned_data['words'])}

    @classmethod
    def initial_from(cls, step):
        return {'words': '\n'.join(step.payload.get('words', []))}


ARMA_UNIT_LABELS = {'letter': 'Letras', 'syllable': 'Sílabas', 'word': 'Palabras'}


class ArmaStepForm(StepForm):
    step_type = 'arma'
    text = forms.CharField(
        label='Palabra u oración (escribe [entre corchetes] lo que el niño debe completar)',
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    unit = forms.ChoiceField(
        label='Fichas de',
        choices=[(unit, ARMA_UNIT_LABELS[unit]) for unit in ARMA_UNITS],
        initial='syllable',
        widget=forms.RadioSelect,
    )

    def to_payload(self):
        return {'text': self.cleaned_data['text'], 'unit': self.cleaned_data['unit']}


DISTRACTORS_MAX = 3


class ExerciseForm(forms.Form):
    prompt = forms.CharField(label='Ejercicio', max_length=255, widget=forms.TextInput(attrs={'class': 'form-control'}))
    answer = forms.CharField(label='Respuesta correcta', max_length=255, widget=forms.TextInput(attrs={'class': 'form-control'}))
    distractors = forms.CharField(
        label='Otras opciones, separadas por coma',
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )

    def clean(self):
        cleaned = super().clean()
        if not self.errors:
            answer = cleaned['answer'].strip()
            others = [o for o in dict.fromkeys(p.strip() for p in cleaned['distractors'].split(',')) if o and o != answer]
            if not 1 <= len(others) <= DISTRACTORS_MAX:
                raise ValidationError(f'Escribe de 1 a {DISTRACTORS_MAX} opciones distintas de la respuesta.')
            cleaned['options'] = [answer, *others]
        return cleaned


ExerciseFormSet = formset_factory(
    ExerciseForm, extra=3, min_num=1, max_num=EXERCISES_MAX, validate_min=True,
)


class EjemploStepForm(StepForm):
    """A worked example (one line per step) followed by exercises, edited together as one form + a formset."""

    step_type = 'ejemplo'
    example_steps = forms.CharField(
        label=f'Un paso del ejemplo por línea (1 a {EXAMPLE_STEPS_MAX})',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
    )
    image = forms.ImageField(
        label='Imagen (opcional)', required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        initial = self.initial.get('exercises') if not self.is_bound else None
        self.exercises = ExerciseFormSet(self.data if self.is_bound else None, prefix='exercises', initial=initial)

    def is_valid(self):
        # Evaluate both so every error shows at once.
        return super().is_valid() & self.exercises.is_valid()

    def clean(self):
        if not self.exercises.is_valid():
            return self.cleaned_data
        return super().clean()

    def _lines(self, text):
        return [line.strip() for line in text.splitlines() if line.strip()]

    def to_payload(self):
        rows = [form.cleaned_data for form in self.exercises if form.cleaned_data]
        return {
            'example_steps': self._lines(self.cleaned_data['example_steps']),
            'exercises': [{'prompt': r['prompt'], 'answer': r['answer'].strip(), 'options': r['options']} for r in rows],
        }

    def extras(self):
        return {'image': self.cleaned_data.get('image')}

    @classmethod
    def initial_from(cls, step):
        payload = step.payload
        return {
            'example_steps': '\n'.join(payload.get('example_steps', [])),
            'exercises': [
                {'prompt': e['prompt'], 'answer': e['answer'], 'distractors': ', '.join(o for o in e['options'] if o != e['answer'])}
                for e in payload.get('exercises', [])
            ],
        }


STEP_FORMS: dict[str, type[StepForm]] = {
    'mira': MiraStepForm,
    'lectura': LecturaStepForm,
    'palabras': PalabrasStepForm,
    'contesta': ContestaStepForm,
    'arma': ArmaStepForm,
    'ejemplo': EjemploStepForm,
}
