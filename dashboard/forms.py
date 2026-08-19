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
        self._original_password = self.instance.password if self.instance and self.instance.pk else ''
        self.fields['role'].choices = (
            (CustomUser.Role.ADMIN, 'Administrador'),
            (CustomUser.Role.TEACHER, 'Docente'),
            (CustomUser.Role.PARENT, 'Padre o tutor'),
        )
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''
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


class AdminUserUpdateForm(forms.ModelForm):
    password = forms.CharField(
        label='Nueva contraseña',
        required=False,
        help_text='Opcional. Déjalo vacío para mantener la contraseña actual.',
        widget=forms.PasswordInput(render_value=True),
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active', 'password')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_password = self.instance.password if self.instance and self.instance.pk else ''
        self.fields['role'].choices = (
            (CustomUser.Role.ADMIN, 'Administrador'),
            (CustomUser.Role.TEACHER, 'Docente'),
            (CustomUser.Role.PARENT, 'Padre o tutor'),
        )
        style_admin_form(self)

    def save(self, commit=True):
        password = self.cleaned_data.get('password', '')
        user = super().save(commit=False)
        if password:
            user.set_password(password)
        else:
            user.password = self._original_password
        if commit:
            user.save()
        return user


class TeacherCreationForm(forms.Form):
    first_name = forms.CharField(label='Nombres', max_length=80)
    last_name = forms.CharField(label='Apellidos', max_length=100)
    email = forms.EmailField(label='Correo institucional')
    password = forms.CharField(
        label='Contraseña',
        max_length=32,
        help_text='Contraseña inicial del docente.',
        widget=forms.PasswordInput(render_value=True),
    )
    bio = forms.CharField(label='Perfil docente', required=False, widget=forms.Textarea(attrs={'rows': 3}))
    can_manage_lessons = forms.BooleanField(label='Puede gestionar clases', required=False, initial=True)
    can_manage_activities = forms.BooleanField(label='Puede gestionar actividades', required=False, initial=True)
    can_manage_readings = forms.BooleanField(label='Puede gestionar lecturas', required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_admin_form(self)
        self.fields['first_name'].widget.attrs.setdefault('placeholder', 'Ej. María')
        self.fields['last_name'].widget.attrs.setdefault('placeholder', 'Ej. López Pérez')
        self.fields['email'].widget.attrs.setdefault('placeholder', 'docente@correo.com')
        self.fields['email'].widget.attrs['data-teacher-email'] = '1'
        self.fields['password'].widget.attrs.setdefault('placeholder', 'Crea una contraseña')
        self.fields['bio'].widget.attrs.setdefault('placeholder', 'Área que atiende, grado asignado o notas internas.')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if TeacherProfile.objects.filter(email=email).exists():
            raise forms.ValidationError('Ya existe un docente con este correo.')
        return email

    def save(self):
        full_name = f"{self.cleaned_data['first_name']} {self.cleaned_data['last_name']}".strip()
        teacher = TeacherProfile(
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            email=self.cleaned_data['email'],
            name=full_name,
            bio=self.cleaned_data.get('bio', ''),
            can_manage_lessons=self.cleaned_data.get('can_manage_lessons', False),
            can_manage_activities=self.cleaned_data.get('can_manage_activities', False),
            can_manage_readings=self.cleaned_data.get('can_manage_readings', False),
        )
        teacher.set_password(self.cleaned_data['password'])
        teacher.save()
        return teacher


class TeacherUpdateForm(forms.ModelForm):
    password = forms.CharField(
        label='Nueva contraseña',
        required=False,
        help_text='Opcional. Déjalo vacío para mantener la contraseña actual.',
        widget=forms.PasswordInput(render_value=True),
    )

    class Meta:
        model = TeacherProfile
        fields = ('first_name', 'last_name', 'email', 'password', 'bio', 'can_manage_lessons', 'can_manage_activities', 'can_manage_readings')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_password = self.instance.password if self.instance and self.instance.pk else ''
        self.fields['first_name'].label = 'Nombres'
        self.fields['last_name'].label = 'Apellidos'
        self.fields['email'].label = 'Correo institucional'
        self.fields['bio'].label = 'Perfil docente'
        self.fields['can_manage_lessons'].label = 'Puede gestionar planes de clase'
        self.fields['can_manage_activities'].label = 'Puede gestionar actividades'
        self.fields['can_manage_readings'].label = 'Puede gestionar lecturas'
        style_admin_form(self)

    def save(self, commit=True):
        password = self.cleaned_data.get('password', '')
        teacher = super().save(commit=False)
        if password:
            teacher.set_password(password)
        else:
            teacher.password = self._original_password
        if commit:
            teacher.save()
        return teacher


class QuickStudentCreationForm(forms.Form):
    name = forms.CharField(label='Nombre completo', max_length=150)
    alias = forms.CharField(label='Nombre corto o alias', max_length=80, required=False)
    grade = forms.ChoiceField(label='Grado', choices=StudentProfile.Grade.choices)
    school = forms.ChoiceField(label='Colegio / centro educativo', choices=StudentProfile.School.choices, initial=StudentProfile.School.TO_DEFINE)
    modality = forms.ChoiceField(label='Modalidad educativa', choices=StudentProfile.Modality.choices, initial=StudentProfile.Modality.REGULAR)
    zone = forms.ChoiceField(label='Zona', choices=StudentProfile.Zone.choices, initial=StudentProfile.Zone.URBAN)
    reading_level = forms.ModelChoiceField(label='Nivel lector inicial', queryset=Level.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reading_level'].queryset = Level.objects.filter(is_active=True).order_by('order')
        style_admin_form(self)

    def _build_username(self):
        base_source = self.cleaned_data['name']
        base = slugify(base_source).replace('-', '_') or 'estudiante'
        candidate = base[:140]
        counter = 1
        while CustomUser.objects.filter(username=candidate).exists():
            counter += 1
            candidate = f'{base[:135]}_{counter}'
        return candidate

    def save(self):
        username = self._build_username()
        password = get_random_string(8, allowed_chars='23456789ABCDEFGHJKLMNPQRSTUVWXYZ')
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
            school=self.cleaned_data['school'],
            modality=self.cleaned_data['modality'],
            zone=self.cleaned_data['zone'],
            reading_level=level,
            current_level=level,
        )
        self.created_credentials = {'username': user.username, 'password': password}
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
        self.fields['subject'].label = 'Materia'
        self.fields['level'].label = 'Nivel lector'
        self.fields['grade'].label = 'Grado'
        self.fields['title'].label = 'Título del plan'
        self.fields['topic'].label = 'Tema'
        self.fields['objective'].label = 'Objetivo de aprendizaje'
        self.fields['methodology'].label = 'Metodología de aplicación'
        self.fields['planned_date'].label = 'Fecha planificada'
        self.fields['activities'].label = 'Actividades sugeridas'
        self.fields['readings'].label = 'Lecturas sugeridas'
        self.fields['notes'].label = 'Notas internas'
        self.fields['is_active'].label = 'Plan activo'
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
