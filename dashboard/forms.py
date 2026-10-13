from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.forms import modelform_factory
from django.utils.crypto import get_random_string
from django.utils.text import slugify

from accounts.models import CustomUser
from activities.models import Activity
from games.models import Game
from learning.models import CurriculumCompetency, LessonPlan, LessonPlanAssignment, Level, ParentProfile, StudentProfile, Subject, TeacherProfile
from readings.models import Reading


class AdminUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        restrict_staff_field(self, actor)
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
        widget=forms.PasswordInput,
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active', 'password')

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_password = self.instance.password if self.instance and self.instance.pk else ''
        self.fields['password'].initial = ''
        self.fields['username'].label = 'Usuario de acceso'
        self.fields['email'].label = 'Correo electrónico'
        self.fields['first_name'].label = 'Nombres'
        self.fields['last_name'].label = 'Apellidos'
        self.fields['role'].label = 'Rol del sistema'
        self.fields['is_staff'].label = 'Acceso al administrador Django'
        self.fields['is_active'].label = 'Cuenta activa'
        self.fields['is_active'].help_text = 'Activa o suspende el acceso sin borrar el historial de la cuenta.'
        self.fields['is_staff'].help_text = 'Úsalo solo para administradores que deban entrar al administrador avanzado de Django.'
        restrict_staff_field(self, actor)
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
            if password:
                clear_legacy_teacher_password(user)
            full_name = user.get_full_name() or user.username
            if user.is_active and user.role == CustomUser.Role.TEACHER:
                teacher, _ = TeacherProfile.objects.get_or_create(user=user, defaults={
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'name': full_name,
                })
                update_fields = []
                if not teacher.is_active:
                    teacher.is_active = True
                    update_fields.append('is_active')
                if not teacher.email and user.email:
                    teacher.email = user.email
                    update_fields.append('email')
                if update_fields:
                    teacher.save(update_fields=update_fields)
            elif not user.is_active and user.role == CustomUser.Role.TEACHER:
                teacher = getattr(user, 'teacher_profile', None)
                if teacher and teacher.is_active:
                    teacher.is_active = False
                    teacher.save(update_fields=['is_active'])
            elif user.is_active and user.role == CustomUser.Role.PARENT:
                ParentProfile.objects.get_or_create(user=user, defaults={'name': full_name})
            elif user.is_active and user.role == CustomUser.Role.STUDENT:
                level = Level.objects.filter(is_active=True).order_by('order').first()
                StudentProfile.objects.get_or_create(
                    user=user,
                    defaults={'name': full_name, 'reading_level': level, 'current_level': level},
                )
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
    can_create_students = forms.BooleanField(label='Puede crear estudiantes', required=False, initial=True)
    can_view_student_reports = forms.BooleanField(label='Puede ver reportes de estudiantes', required=False, initial=True)
    can_create_lesson_plans = forms.BooleanField(label='Puede crear planes de clase', required=False, initial=True)
    can_edit_lesson_plans = forms.BooleanField(label='Puede editar planes de clase', required=False, initial=True)
    can_assign_lesson_plans = forms.BooleanField(label='Puede asignar/implementar planes', required=False, initial=True)
    can_manage_lessons = forms.BooleanField(label='Puede gestionar clases', required=False, initial=True)
    can_manage_activities = forms.BooleanField(label='Puede gestionar actividades', required=False, initial=True)
    can_manage_readings = forms.BooleanField(label='Puede gestionar lecturas', required=False, initial=True)
    can_manage_games = forms.BooleanField(label='Puede gestionar juegos', required=False, initial=True)

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
            can_create_students=self.cleaned_data.get('can_create_students', False),
            can_view_student_reports=self.cleaned_data.get('can_view_student_reports', False),
            can_create_lesson_plans=self.cleaned_data.get('can_create_lesson_plans', False),
            can_edit_lesson_plans=self.cleaned_data.get('can_edit_lesson_plans', False),
            can_assign_lesson_plans=self.cleaned_data.get('can_assign_lesson_plans', False),
            can_manage_lessons=self.cleaned_data.get('can_manage_lessons', False),
            can_manage_activities=self.cleaned_data.get('can_manage_activities', False),
            can_manage_readings=self.cleaned_data.get('can_manage_readings', False),
            can_manage_games=self.cleaned_data.get('can_manage_games', False),
        )
        teacher.set_password(self.cleaned_data['password'])
        teacher.save()
        return teacher


class TeacherUpdateForm(forms.ModelForm):
    password = forms.CharField(
        label='Nueva contraseña',
        required=False,
        help_text='Opcional. Déjalo vacío para mantener la contraseña actual.',
        widget=forms.PasswordInput,
    )

    class Meta:
        model = TeacherProfile
        fields = (
            'first_name', 'last_name', 'email', 'password', 'students', 'bio', 'is_active',
            'can_create_students', 'can_view_student_reports',
            'can_create_lesson_plans', 'can_edit_lesson_plans', 'can_assign_lesson_plans',
            'can_manage_lessons', 'can_manage_activities', 'can_manage_readings', 'can_manage_games',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_password = self.instance.password if self.instance and self.instance.pk else ''
        self.fields['password'].initial = ''
        self.fields['first_name'].label = 'Nombres'
        self.fields['last_name'].label = 'Apellidos'
        self.fields['email'].label = 'Correo institucional'
        self.fields['students'].label = 'Estudiantes vinculados'
        self.fields['students'].queryset = StudentProfile.objects.select_related('current_level').order_by('name')
        self.fields['bio'].label = 'Perfil docente'
        self.fields['is_active'].label = 'Docente activo'
        self.fields['is_active'].help_text = 'Desactivar conserva sus planes, reportes y evidencias, pero bloquea su acceso docente.'
        self.fields['can_create_students'].label = 'Puede crear estudiantes'
        self.fields['can_view_student_reports'].label = 'Puede ver reportes de estudiantes'
        self.fields['can_create_lesson_plans'].label = 'Puede crear planes de clase'
        self.fields['can_edit_lesson_plans'].label = 'Puede editar planes de clase'
        self.fields['can_assign_lesson_plans'].label = 'Puede asignar/implementar planes'
        self.fields['can_manage_lessons'].label = 'Puede gestionar clases'
        self.fields['can_manage_activities'].label = 'Puede gestionar actividades'
        self.fields['can_manage_readings'].label = 'Puede gestionar lecturas'
        self.fields['can_manage_games'].label = 'Puede gestionar juegos'
        style_admin_form(self)

    def save(self, commit=True):
        password = self.cleaned_data.get('password', '')
        teacher = super().save(commit=False)
        teacher.password = self._original_password
        if password and teacher.user_id:
            # The linked account is the single source of truth for the password.
            teacher.user.set_password(password)
            teacher.password = ''
        elif password:
            # No account yet: keep a pending password that the first login moves to the user.
            teacher.set_password(password)
        if commit:
            teacher.save()
            if teacher.user_id:
                user = teacher.user
                user.is_active = teacher.is_active
                user.email = teacher.email
                user.first_name = teacher.first_name
                user.last_name = teacher.last_name
                user.role = CustomUser.Role.TEACHER
                update_fields = ['is_active', 'email', 'first_name', 'last_name', 'role']
                if password:
                    update_fields.append('password')
                user.save(update_fields=update_fields)
            self.save_m2m()
        return teacher


class QuickStudentCreationForm(forms.Form):
    name = forms.CharField(label='Nombre completo', max_length=150)
    alias = forms.CharField(label='Nombre corto o alias', max_length=80, required=False)
    grade = forms.ChoiceField(label='Grado', choices=StudentProfile.Grade.choices)
    school = forms.ChoiceField(label='Colegio / centro educativo', choices=StudentProfile.School.choices, initial=StudentProfile.School.TO_DEFINE)
    modality = forms.ChoiceField(label='Modalidad educativa', choices=StudentProfile.Modality.choices, initial=StudentProfile.Modality.REGULAR)
    zone = forms.ChoiceField(label='Zona', choices=StudentProfile.Zone.choices, initial=StudentProfile.Zone.URBAN)
    reading_level = forms.ModelChoiceField(label='Nivel lector inicial', queryset=Level.objects.none())
    parents = forms.ModelMultipleChoiceField(
        label='Tutores existentes',
        queryset=ParentProfile.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    new_parent_first_name = forms.CharField(label='Nombre del nuevo tutor', max_length=80, required=False)
    new_parent_last_name = forms.CharField(label='Apellido del nuevo tutor', max_length=100, required=False)
    new_parent_email = forms.EmailField(label='Correo del nuevo tutor', required=False)
    new_parent_username = forms.CharField(label='Usuario del nuevo tutor', max_length=150, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reading_level'].queryset = Level.objects.filter(is_active=True).order_by('order')
        self.fields['parents'].queryset = ParentProfile.objects.select_related('user').order_by('name')
        self.fields['parents'].label_from_instance = lambda parent: str(parent)
        style_admin_form(self)

    def clean(self):
        cleaned_data = super().clean()
        first_name = (cleaned_data.get('new_parent_first_name') or '').strip()
        last_name = (cleaned_data.get('new_parent_last_name') or '').strip()
        email = (cleaned_data.get('new_parent_email') or '').strip().lower()
        username = (cleaned_data.get('new_parent_username') or '').strip()
        wants_new_parent = bool(first_name or last_name or email or username)
        if wants_new_parent:
            if not first_name:
                self.add_error('new_parent_first_name', 'Escribe el nombre del tutor.')
            if not last_name:
                self.add_error('new_parent_last_name', 'Escribe el apellido del tutor.')
            if not email:
                self.add_error('new_parent_email', 'Escribe el correo del tutor.')
            if email and CustomUser.objects.filter(email__iexact=email).exists():
                self.add_error('new_parent_email', 'Ya existe un usuario con este correo.')
            if username and CustomUser.objects.filter(username__iexact=username).exists():
                self.add_error('new_parent_username', 'Ya existe un usuario con este nombre.')
        cleaned_data['new_parent_email'] = email
        cleaned_data['new_parent_username'] = username
        return cleaned_data

    def _build_username(self):
        base_source = self.cleaned_data['name']
        base = slugify(base_source).replace('-', '_') or 'estudiante'
        candidate = base[:140]
        counter = 1
        while CustomUser.objects.filter(username=candidate).exists():
            counter += 1
            candidate = f'{base[:135]}_{counter}'
        return candidate

    def _build_parent_username(self):
        if self.cleaned_data.get('new_parent_username'):
            return self.cleaned_data['new_parent_username']
        email_base = (self.cleaned_data.get('new_parent_email') or '').split('@', 1)[0]
        name_base = f"{self.cleaned_data.get('new_parent_first_name', '')} {self.cleaned_data.get('new_parent_last_name', '')}"
        base = slugify(email_base or name_base).replace('-', '_') or 'tutor'
        candidate = base[:140]
        counter = 1
        while CustomUser.objects.filter(username__iexact=candidate).exists():
            counter += 1
            candidate = f'{base[:135]}_{counter}'
        return candidate

    def save_parent_links(self, student):
        parents = list(self.cleaned_data.get('parents') or [])
        if self.cleaned_data.get('new_parent_first_name') and self.cleaned_data.get('new_parent_last_name') and self.cleaned_data.get('new_parent_email'):
            username = self._build_parent_username()
            parent_user = CustomUser.objects.create_user(
                username=username,
                email=self.cleaned_data['new_parent_email'],
                password=get_random_string(10),
                first_name=self.cleaned_data['new_parent_first_name'],
                last_name=self.cleaned_data['new_parent_last_name'],
                role=CustomUser.Role.PARENT,
            )
            parent = ParentProfile.objects.create(
                user=parent_user,
                name=f"{parent_user.first_name} {parent_user.last_name}".strip(),
            )
            parents.append(parent)
        for parent in parents:
            parent.students.add(student)

    def save(self, teacher=None):
        username = self._build_username()
        password = get_random_string(4, allowed_chars='23456789')
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
        student = StudentProfile.objects.create(
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
        visual_items = student.generate_visual_key()
        if teacher is not None:
            teacher.students.add(student)
        self.save_parent_links(student)
        self.created_credentials = {'username': user.username, 'password': password, 'visual_key': visual_items}
        return user, password


class TeacherStudentUpdateForm(forms.ModelForm):
    parents = forms.ModelMultipleChoiceField(
        label='Tutores vinculados',
        queryset=ParentProfile.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    new_parent_first_name = forms.CharField(label='Nombre del nuevo tutor', max_length=80, required=False)
    new_parent_last_name = forms.CharField(label='Apellido del nuevo tutor', max_length=100, required=False)
    new_parent_email = forms.EmailField(label='Correo del nuevo tutor', required=False)
    new_parent_username = forms.CharField(label='Usuario del nuevo tutor', max_length=150, required=False)

    class Meta:
        model = StudentProfile
        fields = ('name', 'alias', 'birth_date', 'grade', 'school', 'modality', 'zone', 'reading_level', 'current_level')
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = 'Nombre completo'
        self.fields['alias'].label = 'Nombre corto o alias'
        self.fields['birth_date'].label = 'Fecha de nacimiento'
        self.fields['grade'].label = 'Grado'
        self.fields['school'].label = 'Colegio / centro educativo'
        self.fields['modality'].label = 'Modalidad educativa'
        self.fields['zone'].label = 'Zona'
        self.fields['reading_level'].label = 'Nivel lector inicial'
        self.fields['current_level'].label = 'Nivel actual'
        self.fields['reading_level'].queryset = Level.objects.filter(is_active=True).order_by('order')
        self.fields['current_level'].queryset = Level.objects.filter(is_active=True).order_by('order')
        self.fields['parents'].queryset = ParentProfile.objects.select_related('user').order_by('name')
        if self.instance and self.instance.pk:
            self.fields['parents'].initial = self.instance.parents.values_list('pk', flat=True)
        style_admin_form(self)

    def clean(self):
        cleaned_data = super().clean()
        first_name = (cleaned_data.get('new_parent_first_name') or '').strip()
        last_name = (cleaned_data.get('new_parent_last_name') or '').strip()
        email = (cleaned_data.get('new_parent_email') or '').strip().lower()
        username = (cleaned_data.get('new_parent_username') or '').strip()
        wants_new_parent = bool(first_name or last_name or email or username)
        if wants_new_parent:
            if not first_name:
                self.add_error('new_parent_first_name', 'Escribe el nombre del tutor.')
            if not last_name:
                self.add_error('new_parent_last_name', 'Escribe el apellido del tutor.')
            if not email:
                self.add_error('new_parent_email', 'Escribe el correo del tutor.')
            if email and CustomUser.objects.filter(email__iexact=email).exists():
                self.add_error('new_parent_email', 'Ya existe un usuario con este correo.')
            if username and CustomUser.objects.filter(username__iexact=username).exists():
                self.add_error('new_parent_username', 'Ya existe un usuario con este nombre.')
        cleaned_data['new_parent_email'] = email
        cleaned_data['new_parent_username'] = username
        return cleaned_data

    def _build_parent_username(self):
        if self.cleaned_data.get('new_parent_username'):
            return self.cleaned_data['new_parent_username']
        email_base = (self.cleaned_data.get('new_parent_email') or '').split('@', 1)[0]
        name_base = f"{self.cleaned_data.get('new_parent_first_name', '')} {self.cleaned_data.get('new_parent_last_name', '')}"
        base = slugify(email_base or name_base).replace('-', '_') or 'tutor'
        candidate = base[:140]
        counter = 1
        while CustomUser.objects.filter(username__iexact=candidate).exists():
            counter += 1
            candidate = f'{base[:135]}_{counter}'
        return candidate

    def save(self, commit=True):
        student = super().save(commit=commit)
        if commit:
            parents = list(self.cleaned_data.get('parents') or [])
            if self.cleaned_data.get('new_parent_first_name') and self.cleaned_data.get('new_parent_last_name') and self.cleaned_data.get('new_parent_email'):
                parent_user = CustomUser.objects.create_user(
                    username=self._build_parent_username(),
                    email=self.cleaned_data['new_parent_email'],
                    password=get_random_string(10),
                    first_name=self.cleaned_data['new_parent_first_name'],
                    last_name=self.cleaned_data['new_parent_last_name'],
                    role=CustomUser.Role.PARENT,
                )
                parents.append(ParentProfile.objects.create(
                    user=parent_user,
                    name=f"{parent_user.first_name} {parent_user.last_name}".strip(),
                ))
            student.parents.set(parents)
        return student


class TeacherStudentModalForm(forms.ModelForm):
    parents = forms.ModelMultipleChoiceField(
        label='Seleccionar tutor',
        queryset=ParentProfile.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = StudentProfile
        fields = ('name', 'alias', 'birth_date', 'grade', 'school', 'modality', 'zone', 'reading_level', 'current_level')
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = 'Nombre completo'
        self.fields['alias'].label = 'Nombre corto o alias'
        self.fields['birth_date'].label = 'Fecha de nacimiento'
        self.fields['grade'].label = 'Grado'
        self.fields['school'].label = 'Colegio / centro educativo'
        self.fields['modality'].label = 'Modalidad educativa'
        self.fields['zone'].label = 'Zona'
        self.fields['reading_level'].label = 'Nivel lector inicial'
        self.fields['current_level'].label = 'Nivel actual'
        self.fields['reading_level'].queryset = Level.objects.filter(is_active=True).order_by('order')
        self.fields['current_level'].queryset = Level.objects.filter(is_active=True).order_by('order')
        self.fields['parents'].queryset = ParentProfile.objects.select_related('user').order_by('name')
        self.fields['parents'].label_from_instance = lambda parent: parent.name or parent.user.get_full_name() or parent.user.username
        if self.instance and self.instance.pk:
            self.fields['parents'].initial = self.instance.parents.values_list('pk', flat=True)
        style_admin_form(self)

    def save(self, commit=True):
        student = super().save(commit=commit)
        if commit:
            student.parents.set(self.cleaned_data.get('parents') or [])
        return student


class LessonPlanForm(forms.ModelForm):
    assigned_students = forms.ModelMultipleChoiceField(
        label='Asignar a estudiantes',
        queryset=StudentProfile.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = LessonPlan
        fields = (
            'subject', 'competency', 'level', 'grade', 'planned_date', 'period', 'unit', 'title', 'topic',
            'achievement_indicator', 'evaluation_criteria', 'content', 'objective',
            'initial_activities', 'teacher_reading', 'comprehension_orthography_activities',
            'closing_activities', 'methodology', 'activities', 'readings', 'games', 'notes', 'status', 'is_active',
        )
        widgets = {
            'planned_date': forms.DateInput(attrs={'type': 'date'}),
            'activities': forms.CheckboxSelectMultiple(),
            'readings': forms.CheckboxSelectMultiple(),
            'games': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, teacher=None, **kwargs):
        self.teacher = teacher
        super().__init__(*args, **kwargs)
        level = self.data.get('level') or getattr(self.instance, 'level_id', None)
        subject = self.data.get('subject') or getattr(self.instance, 'subject_id', None)
        grade = self.data.get('grade') or getattr(self.instance, 'grade', None)
        self.fields['subject'].label = 'Materia'
        self.fields['competency'].label = 'Indicador MINED / competencia'
        self.fields['level'].label = 'Nivel lector'
        self.fields['grade'].label = 'Grado'
        self.fields['period'].label = 'Período'
        self.fields['unit'].label = 'Unidad'
        self.fields['title'].label = 'Título del plan'
        self.fields['topic'].label = 'Tema'
        self.fields['achievement_indicator'].label = 'Indicador de logro'
        self.fields['evaluation_criteria'].label = 'Criterios de evaluación'
        self.fields['content'].label = 'Contenido'
        self.fields['objective'].label = 'Objetivo de aprendizaje'
        self.fields['initial_activities'].label = 'Actividades iniciales'
        self.fields['teacher_reading'].label = 'Lectura por el docente'
        self.fields['comprehension_orthography_activities'].label = 'Actividades de comprensión y ortografía'
        self.fields['closing_activities'].label = 'Actividades de cierre/evaluación'
        self.fields['methodology'].label = 'Metodología de aplicación'
        self.fields['planned_date'].label = 'Fecha planificada'
        self.fields['activities'].label = 'Actividades sugeridas'
        self.fields['readings'].label = 'Lecturas sugeridas'
        self.fields['games'].label = 'Juegos sugeridos'
        self.fields['notes'].label = 'Notas internas'
        self.fields['status'].label = 'Estado del plan'
        self.fields['status'].required = False
        self.fields['status'].initial = LessonPlan.Status.ACTIVE
        self.fields['is_active'].label = 'Plan activo'
        self.fields['subject'].queryset = Subject.objects.filter(is_active=True).order_by('name')
        self.fields['competency'].queryset = CurriculumCompetency.objects.filter(is_active=True).select_related('subject').order_by('grade', 'subject__name', 'title')
        if subject:
            self.fields['competency'].queryset = self.fields['competency'].queryset.filter(subject_id=subject)
        if grade:
            self.fields['competency'].queryset = self.fields['competency'].queryset.filter(grade=grade)
        self.fields['assigned_students'].queryset = StudentProfile.objects.select_related('current_level').order_by('name')
        if self.teacher is not None:
            self.fields['assigned_students'].queryset = self.teacher.students.select_related('current_level').order_by('name')
        if grade:
            self.fields['assigned_students'].queryset = self.fields['assigned_students'].queryset.filter(grade=grade)
        if self.instance and self.instance.pk:
            self.fields['assigned_students'].initial = self.instance.assignments.filter(is_active=True).values_list('student_id', flat=True)
        self.fields['activities'].queryset = Activity.objects.filter(is_active=True).select_related('level', 'subject')
        self.fields['readings'].queryset = Reading.objects.filter(is_active=True).select_related('level', 'subject')
        self.fields['games'].queryset = Game.objects.filter(is_active=True).select_related('level', 'subject')
        if level:
            self.fields['activities'].queryset = self.fields['activities'].queryset.filter(level_id=level)
            self.fields['readings'].queryset = self.fields['readings'].queryset.filter(level_id=level)
            self.fields['games'].queryset = self.fields['games'].queryset.filter(level_id=level)
        if subject:
            self.fields['activities'].queryset = self.fields['activities'].queryset.filter(subject_id=subject)
            self.fields['readings'].queryset = self.fields['readings'].queryset.filter(subject_id=subject)
            self.fields['games'].queryset = self.fields['games'].queryset.filter(subject_id=subject)
        if grade:
            self.fields['activities'].queryset = self.fields['activities'].queryset.filter(grade=grade)
            self.fields['readings'].queryset = self.fields['readings'].queryset.filter(grade=grade)
            self.fields['games'].queryset = self.fields['games'].queryset.filter(grade__in=('', grade))
        style_admin_form(self)

    def clean(self):
        cleaned_data = super().clean()
        competency = cleaned_data.get('competency')
        if competency:
            cleaned_data['achievement_indicator'] = cleaned_data.get('achievement_indicator') or competency.achievement_indicator
            cleaned_data['content'] = cleaned_data.get('content') or competency.competency
            cleaned_data['methodology'] = cleaned_data.get('methodology') or competency.dyslexia_adaptation
        selected_students = cleaned_data.get('assigned_students')
        if self.teacher is not None and selected_students is not None:
            allowed_ids = set(self.teacher.students.values_list('id', flat=True))
            invalid_students = [student for student in selected_students if student.id not in allowed_ids]
            if invalid_students:
                self.add_error('assigned_students', 'Solo puedes asignar estudiantes vinculados a tu perfil docente.')
        cleaned_data['status'] = cleaned_data.get('status') or LessonPlan.Status.ACTIVE
        return cleaned_data

    def save_assignments(self, plan):
        selected_students = self.cleaned_data.get('assigned_students')
        if selected_students is None:
            return
        removable_assignments = plan.assignments.exclude(student__in=selected_students)
        removable_assignments.filter(
            status=LessonPlanAssignment.Status.ASSIGNED,
            completed_at__isnull=True,
            teacher_notes='',
        ).delete()
        removable_assignments.update(is_active=False)
        for student in selected_students:
            assignment, _ = plan.assignments.get_or_create(student=student)
            if not assignment.is_active:
                assignment.is_active = True
                assignment.save(update_fields=['is_active'])


def build_admin_model_form(model, fields):
    form_class = modelform_factory(model, fields=fields)

    class AdminModelForm(form_class):
        pass

    return AdminModelForm


def restrict_staff_field(form, actor):
    """Only superusers may grant Django admin access; superuser status is never editable here."""
    if actor is None or not actor.is_superuser:
        form.fields.pop('is_staff', None)


def clear_legacy_teacher_password(user):
    teacher = TeacherProfile.objects.filter(user=user).exclude(password='').first()
    if teacher:
        teacher.password = ''
        teacher.save(update_fields=['password'])


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
