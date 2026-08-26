import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.db.models import Q


class Level(models.Model):
    number = models.PositiveSmallIntegerField(unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'Nivel {self.number} - {self.name}'


class Lesson(models.Model):
    class Stage(models.TextChoices):
        LEARN = 'LEARN', 'Aprendo'
        PRACTICE = 'PRACTICE', 'Practico'
        ADVANCE = 'ADVANCE', 'Avanzo'

    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    stage = models.CharField(max_length=20, choices=Stage.choices)
    order = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class Word(models.Model):
    text = models.CharField(max_length=80)
    image = models.ImageField(upload_to='words/', blank=True, null=True)
    level = models.ForeignKey(Level, on_delete=models.SET_NULL, null=True, related_name='words')
    syllables = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return self.text


class Syllable(models.Model):
    text = models.CharField(max_length=20, unique=True)
    level = models.ForeignKey(Level, on_delete=models.SET_NULL, null=True, related_name='syllables')

    def __str__(self):
        return self.text


class StudentProfile(models.Model):
    VISUAL_KEY_CHOICES = (
        ('dog', '🐶', 'perro'),
        ('star', '⭐', 'estrella'),
        ('car', '🚗', 'carro'),
        ('book', '📘', 'libro'),
        ('sun', '☀️', 'sol'),
        ('house', '🏠', 'casa'),
        ('apple', '🍎', 'manzana'),
        ('fish', '🐟', 'pez'),
    )

    class Grade(models.TextChoices):
        FIRST = '1', 'Primer grado'
        SECOND = '2', 'Segundo grado'
        THIRD = '3', 'Tercer grado'

    class Modality(models.TextChoices):
        REGULAR = 'regular', 'Primaria regular'
        MULTIGRADE = 'multigrade', 'Primaria multigrado'
        OVERAGE = 'overage', 'Primaria extraedad'
        DISTANCE_RURAL = 'distance_rural', 'Primaria a distancia en el campo'

    class Zone(models.TextChoices):
        URBAN = 'urban', 'Urbana'
        RURAL = 'rural', 'Rural'

    class School(models.TextChoices):
        TO_DEFINE = 'to_define', 'Por definir'
        PUBLIC = 'public', 'Escuela pública'
        PRIVATE = 'private', 'Colegio privado'
        SUBSIDIZED = 'subsidized', 'Centro subvencionado'
        RURAL_MULTIGRADE = 'rural_multigrade', 'Escuela rural o multigrado'
        COMMUNITY = 'community', 'Centro comunitario'
        OTHER = 'other', 'Otro'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    name = models.CharField(max_length=150)
    alias = models.CharField(max_length=80, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    grade = models.CharField(max_length=1, choices=Grade.choices, default=Grade.FIRST)
    school = models.CharField(max_length=30, choices=School.choices, default=School.TO_DEFINE)
    modality = models.CharField(max_length=20, choices=Modality.choices, default=Modality.REGULAR)
    zone = models.CharField(max_length=10, choices=Zone.choices, default=Zone.URBAN)
    reading_level = models.ForeignKey(Level, on_delete=models.SET_NULL, null=True, related_name='students')
    current_level = models.ForeignKey(Level, on_delete=models.SET_NULL, null=True, related_name='current_students')
    points = models.PositiveIntegerField(default=0)
    stars = models.PositiveIntegerField(default=0)
    experience = models.PositiveIntegerField(default=0)
    learning_streak = models.PositiveIntegerField(default=0)
    last_activity_at = models.DateTimeField(blank=True, null=True)
    visual_key_hash = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def display_name(self):
        return self.alias or self.name

    def __str__(self):
        return self.display_name()

    @classmethod
    def visual_key_codes(cls):
        return [choice[0] for choice in cls.VISUAL_KEY_CHOICES]

    @classmethod
    def visual_key_items(cls):
        return [
            {'code': code, 'icon': icon, 'label': label}
            for code, icon, label in cls.VISUAL_KEY_CHOICES
        ]

    @classmethod
    def visual_key_items_for_codes(cls, codes):
        items = {item['code']: item for item in cls.visual_key_items()}
        return [items[code] for code in codes if code in items]

    @classmethod
    def visual_key_secret(cls, codes):
        return '|'.join(codes)

    def set_visual_key(self, codes):
        self.visual_key_hash = make_password(self.visual_key_secret(codes))

    def check_visual_key(self, codes):
        return bool(self.visual_key_hash and check_password(self.visual_key_secret(codes), self.visual_key_hash))

    def generate_visual_key(self):
        codes = secrets.SystemRandom().sample(self.visual_key_codes(), 3)
        self.set_visual_key(codes)
        self.save(update_fields=['visual_key_hash'])
        return self.visual_key_items_for_codes(codes)


class TeacherProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='teacher_profile')
    first_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    password = models.CharField(max_length=128, blank=True)
    name = models.CharField(max_length=150)
    students = models.ManyToManyField(StudentProfile, blank=True, related_name='teachers')
    bio = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, verbose_name='Docente activo')
    can_create_students = models.BooleanField(default=False, verbose_name='Puede crear estudiantes')
    can_view_student_reports = models.BooleanField(default=False, verbose_name='Puede ver reportes de estudiantes')
    can_create_lesson_plans = models.BooleanField(default=False, verbose_name='Puede crear planes de clase')
    can_edit_lesson_plans = models.BooleanField(default=False, verbose_name='Puede editar planes de clase')
    can_assign_lesson_plans = models.BooleanField(default=False, verbose_name='Puede asignar/implementar planes')
    can_manage_lessons = models.BooleanField(default=False, verbose_name='Puede gestionar clases')
    can_manage_activities = models.BooleanField(default=False, verbose_name='Puede gestionar actividades')
    can_manage_readings = models.BooleanField(default=False, verbose_name='Puede gestionar lecturas')
    can_manage_games = models.BooleanField(default=False, verbose_name='Puede gestionar juegos')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['email'], condition=~Q(email=''), name='unique_teacher_email_when_present'),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        full_name = f'{self.first_name} {self.last_name}'.strip()
        if full_name:
            self.name = full_name
        super().save(*args, **kwargs)

    def set_password(self, raw_password):
        self.password = make_password(raw_password) if raw_password else ''

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)


class Subject(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class MinedStrategy(models.Model):
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    focus = models.CharField(max_length=160, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class CurriculumCompetency(models.Model):
    class PedagogicalUnit(models.TextChoices):
        FIRST = 'first', 'Primera Unidad Pedagógica (1.º y 2.º grado)'
        SECOND = 'second', 'Segunda Unidad Pedagógica (3.º y 4.º grado)'
        THIRD = 'third', 'Tercera Unidad Pedagógica (5.º y 6.º grado)'

    pedagogical_unit = models.CharField(max_length=20, choices=PedagogicalUnit.choices, default=PedagogicalUnit.FIRST)
    grade = models.CharField(max_length=1, choices=StudentProfile.Grade.choices, default=StudentProfile.Grade.FIRST)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='competencies')
    strategy = models.ForeignKey(MinedStrategy, on_delete=models.SET_NULL, blank=True, null=True, related_name='competencies')
    title = models.CharField(max_length=180)
    competency = models.TextField()
    achievement_indicator = models.TextField(verbose_name='Indicador de logro')
    dyslexia_adaptation = models.TextField(blank=True, verbose_name='Adaptación para dislexia')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['grade', 'subject__name', 'title']
        verbose_name_plural = 'Curriculum competencies'

    def __str__(self):
        return f'{self.get_grade_display()} - {self.subject}: {self.title}'


class FasStep(models.Model):
    class Stage(models.TextChoices):
        PHONEME = 'phoneme', 'Fonema'
        SYLLABLE = 'syllable', 'Sílaba'
        WORD = 'word', 'Palabra'
        PHRASE = 'phrase', 'Frase'
        READING = 'reading', 'Lectura corta'

    stage = models.CharField(max_length=20, choices=Stage.choices)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    grade = models.CharField(max_length=1, choices=StudentProfile.Grade.choices, default=StudentProfile.Grade.FIRST)
    order = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['grade', 'order']

    def __str__(self):
        return f'{self.get_stage_display()} - {self.title}'


class MinedReference(models.Model):
    class ResourceType(models.TextChoices):
        BOOK = 'book', 'Libro'
        NOTEBOOK = 'notebook', 'Cuaderno'
        GUIDE = 'guide', 'Guía docente'
        READING = 'reading', 'Lectura'
        STRATEGY = 'strategy', 'Estrategia'

    title = models.CharField(max_length=180)
    resource_type = models.CharField(max_length=20, choices=ResourceType.choices, default=ResourceType.BOOK)
    grade = models.CharField(max_length=1, choices=StudentProfile.Grade.choices, default=StudentProfile.Grade.FIRST)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, blank=True, null=True, related_name='mined_references')
    official_url = models.URLField(blank=True)
    app_usage = models.TextField(blank=True, verbose_name='Uso dentro de la aplicación')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['grade', 'subject__name', 'title']

    def __str__(self):
        return self.title


class LessonPlan(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Borrador'
        ACTIVE = 'active', 'Activo'
        IN_PROGRESS = 'in_progress', 'En implementación'
        COMPLETED = 'completed', 'Completado'
        ARCHIVED = 'archived', 'Archivado'

    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='lesson_plans')
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='lesson_plans')
    competency = models.ForeignKey(CurriculumCompetency, on_delete=models.SET_NULL, blank=True, null=True, related_name='lesson_plans')
    level = models.ForeignKey(Level, on_delete=models.PROTECT, related_name='lesson_plans')
    grade = models.CharField(max_length=1, choices=StudentProfile.Grade.choices, default=StudentProfile.Grade.FIRST)
    period = models.CharField(max_length=80, blank=True, default='45 minutos')
    unit = models.CharField(max_length=40, blank=True)
    title = models.CharField(max_length=160)
    topic = models.CharField(max_length=180)
    achievement_indicator = models.TextField(blank=True, verbose_name='Indicador de logro')
    evaluation_criteria = models.TextField(blank=True, verbose_name='Criterios de evaluación')
    content = models.TextField(blank=True, verbose_name='Contenido')
    objective = models.TextField()
    initial_activities = models.TextField(blank=True, verbose_name='Actividades iniciales')
    teacher_reading = models.TextField(blank=True, verbose_name='Lectura por el docente')
    comprehension_orthography_activities = models.TextField(blank=True, verbose_name='Actividades de comprensión y ortografía')
    methodology = models.TextField(blank=True, verbose_name='Metodología de aplicación')
    planned_date = models.DateField(blank=True, null=True)
    activities = models.ManyToManyField('activities.Activity', blank=True, related_name='lesson_plans')
    readings = models.ManyToManyField('readings.Reading', blank=True, related_name='lesson_plans')
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-planned_date', '-created_at']

    def __str__(self):
        return self.title


class LessonPlanAssignment(models.Model):
    class Status(models.TextChoices):
        ASSIGNED = 'assigned', 'Asignado'
        IN_PROGRESS = 'in_progress', 'En progreso'
        COMPLETED = 'completed', 'Completado'

    plan = models.ForeignKey(LessonPlan, on_delete=models.CASCADE, related_name='assignments')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='lesson_plan_assignments')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ASSIGNED)
    assigned_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    teacher_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-assigned_at']
        constraints = [
            models.UniqueConstraint(fields=['plan', 'student'], name='unique_lesson_plan_assignment'),
        ]

    def __str__(self):
        return f'{self.plan} - {self.student}'


class ParentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='parent_profile')
    name = models.CharField(max_length=150)
    students = models.ManyToManyField(StudentProfile, blank=True, related_name='parents')


class AccessibilityPreference(models.Model):
    student = models.OneToOneField(StudentProfile, on_delete=models.CASCADE, related_name='accessibility')
    font_size = models.PositiveSmallIntegerField(default=18)
    letter_spacing = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    word_spacing = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    line_height = models.DecimalField(max_digits=3, decimal_places=1, default=1.6)
    high_contrast = models.BooleanField(default=False)
    reduce_motion = models.BooleanField(default=False)
    reading_guide = models.BooleanField(default=False)
    text_to_speech_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f'Accesibilidad de {self.student}'
