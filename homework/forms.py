from django import forms
from django.db.models import Q

from learning.models import LessonPlan, Subject

from .models import Task
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
