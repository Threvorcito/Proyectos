from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.forms import modelform_factory
from django.utils.crypto import get_random_string
from django.utils.text import slugify

from accounts.models import CustomUser
from activities.models import Activity
from learning.models import LessonPlan, Level, ParentProfile, StudentProfile, Subject, TeacherProfile
from readings.models import Reading


class AdminUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_superuser')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = (
            (CustomUser.Role.ADMIN, 'Administrador'),
            (CustomUser.Role.TEACHER, 'Docente'),
            (CustomUser.Role.PARENT, 'Padre o tutor'),
        )
        style_admin_form(self)

    def save(self, commit=True):
        user = super().save(commit=False)
        if user.role == CustomUser.Role.ADMIN:
            user.is_staff = True
        if commit:
            user.save()
            full_name = user.get_full_name() or user.username
            if user.role == CustomUser.Role.TEACHER:
                TeacherProfile.objects.get_or_create(user=user, defaults={'name': full_name})
            elif user.role == CustomUser.Role.PARENT:
                ParentProfile.objects.get_or_create(user=user, defaults={'name': full_name})
            elif user.role == CustomUser.Role.STUDENT:
                level = Level.objects.filter(is_active=True).order_by('order').first()
                StudentProfile.objects.get_or_create(
                    user=user,
                    defaults={'name': full_name, 'reading_level': level, 'current_level': level},
                )
        return user


class QuickStudentCreationForm(forms.Form):
    name = forms.CharField(label='Nombre completo', max_length=150)
    alias = forms.CharField(label='Nombre corto o alias', max_length=80, required=False)
    grade = forms.ChoiceField(label='Grado', choices=StudentProfile.Grade.choices)
    reading_level = forms.ModelChoiceField(label='Nivel lector inicial', queryset=Level.objects.none())
    username = forms.CharField(label='Usuario', max_length=150, required=False, help_text='Opcional. Si se deja vacío, el sistema lo genera automáticamente.')
    password = forms.CharField(label='Contraseña o PIN', max_length=32, required=False, help_text='Opcional. Si se deja vacío, el sistema genera un PIN seguro.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reading_level'].queryset = Level.objects.filter(is_active=True).order_by('order')
        style_admin_form(self)

    def _build_username(self):
        username = self.cleaned_data.get('username')
        base_source = username or self.cleaned_data['name']
        base = slugify(base_source).replace('-', '_') or 'estudiante'
        candidate = base[:140]
        counter = 1
        while CustomUser.objects.filter(username=candidate).exists():
            counter += 1
            candidate = f'{base[:135]}_{counter}'
        return candidate

    def save(self):
        username = self._build_username()
        password = self.cleaned_data.get('password') or get_random_string(8, allowed_chars='23456789ABCDEFGHJKLMNPQRSTUVWXYZ')
        name_parts = self.cleaned_data['name'].split(' ', 1)
        user = CustomUser.objects.create(
            username=username,
            email=f'{username}@estudiante.local',
            first_name=name_parts[0],
            last_name=name_parts[1] if len(name_parts) > 1 else '',
            role=CustomUser.Role.STUDENT,
        )
        user.set_password(password)
        user.save(update_fields=['password'])
        level = self.cleaned_data['reading_level']
        StudentProfile.objects.create(
            user=user,
            name=self.cleaned_data['name'],
            alias=self.cleaned_data.get('alias', ''),
            grade=self.cleaned_data['grade'],
            reading_level=level,
            current_level=level,
        )
        return user, password


class LessonPlanForm(forms.ModelForm):
    class Meta:
        model = LessonPlan
        fields = ('subject', 'level', 'grade', 'title', 'topic', 'objective', 'methodology', 'planned_date', 'activities', 'readings', 'notes', 'is_active')
        widgets = {
            'planned_date': forms.DateInput(attrs={'type': 'date'}),
            'activities': forms.CheckboxSelectMultiple(),
            'readings': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        level = self.data.get('level') or getattr(self.instance, 'level_id', None)
        self.fields['subject'].queryset = Subject.objects.filter(is_active=True).order_by('name')
        self.fields['activities'].queryset = Activity.objects.filter(is_active=True).select_related('level', 'subject')
        self.fields['readings'].queryset = Reading.objects.filter(is_active=True).select_related('level', 'subject')
        if level:
            self.fields['activities'].queryset = self.fields['activities'].queryset.filter(level_id=level)
            self.fields['readings'].queryset = self.fields['readings'].queryset.filter(level_id=level)
        style_admin_form(self)


def build_admin_model_form(model, fields):
    form_class = modelform_factory(model, fields=fields)

    class AdminModelForm(form_class):
        pass

    return AdminModelForm


def style_admin_form(form):
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs.setdefault('class', 'form-check-input')
        elif isinstance(widget, forms.Select):
            widget.attrs.setdefault('class', 'form-select')
        elif isinstance(widget, forms.CheckboxSelectMultiple):
            widget.attrs.setdefault('class', 'form-check')
        else:
            widget.attrs.setdefault('class', 'form-control')
    return form
