from django.conf import settings
from django.db import models


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

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    name = models.CharField(max_length=150)
    alias = models.CharField(max_length=80, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    grade = models.CharField(max_length=1, choices=Grade.choices, default=Grade.FIRST)
    modality = models.CharField(max_length=20, choices=Modality.choices, default=Modality.REGULAR)
    zone = models.CharField(max_length=10, choices=Zone.choices, default=Zone.URBAN)
    reading_level = models.ForeignKey(Level, on_delete=models.SET_NULL, null=True, related_name='students')
    current_level = models.ForeignKey(Level, on_delete=models.SET_NULL, null=True, related_name='current_students')
    points = models.PositiveIntegerField(default=0)
    stars = models.PositiveIntegerField(default=0)
    experience = models.PositiveIntegerField(default=0)
    learning_streak = models.PositiveIntegerField(default=0)
    last_activity_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def display_name(self):
        return self.alias or self.name

    def __str__(self):
        return self.display_name()


class TeacherProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='teacher_profile')
    name = models.CharField(max_length=150)
    bio = models.TextField(blank=True)
    can_manage_lessons = models.BooleanField(default=False, verbose_name='Puede gestionar clases')
    can_manage_activities = models.BooleanField(default=False, verbose_name='Puede gestionar actividades')
    can_manage_readings = models.BooleanField(default=False, verbose_name='Puede gestionar lecturas')

    def __str__(self):
        return self.name


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
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='lesson_plans')
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='lesson_plans')
    level = models.ForeignKey(Level, on_delete=models.PROTECT, related_name='lesson_plans')
    grade = models.CharField(max_length=1, choices=StudentProfile.Grade.choices, default=StudentProfile.Grade.FIRST)
    title = models.CharField(max_length=160)
    topic = models.CharField(max_length=180)
    objective = models.TextField()
    methodology = models.TextField(blank=True, verbose_name='Metodología de aplicación')
    planned_date = models.DateField(blank=True, null=True)
    activities = models.ManyToManyField('activities.Activity', blank=True, related_name='lesson_plans')
    readings = models.ManyToManyField('readings.Reading', blank=True, related_name='lesson_plans')
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-planned_date', '-created_at']

    def __str__(self):
        return self.title


class ParentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='parent_profile')
    name = models.CharField(max_length=150)


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
