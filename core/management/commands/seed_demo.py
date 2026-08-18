from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from activities.models import Activity, ActivityOption
from gamification.models import Achievement
from learning.models import Lesson, Level, ParentProfile, StudentProfile, TeacherProfile, Syllable, Word
from progress.models import StudentDifficulty, StudentProgress
from readings.models import Reading, ReadingAnswer, ReadingQuestion


class Command(BaseCommand):
    help = 'Crea datos demostrativos para Lectura sin Límites.'

    def handle(self, *args, **options):
        User = get_user_model()

        levels = [
            Level.objects.get_or_create(number=1, defaults={'name': 'Primeros pasos', 'description': 'Letras, sonidos y sílabas.', 'order': 1})[0],
            Level.objects.get_or_create(number=2, defaults={'name': 'Construyo palabras', 'description': 'Sílabas, palabras y frases.', 'order': 2})[0],
            Level.objects.get_or_create(number=3, defaults={'name': 'Leo y comprendo', 'description': 'Lecturas cortas y comprensión.', 'order': 3})[0],
        ]

        for text in ['MA', 'ME', 'MI', 'MO', 'MU', 'PA', 'PE', 'PI', 'PO', 'PU', 'LA', 'LE', 'LI', 'LO', 'LU', 'CA', 'CO', 'CU']:
            Syllable.objects.get_or_create(text=text, defaults={'level': levels[0]})

        for text in ['CASA', 'MESA', 'LUNA', 'GATO', 'PERRO', 'MAMÁ', 'PAPÁ', 'MANO', 'SOL', 'FLOR', 'LIBRO', 'AGUA']:
            Word.objects.get_or_create(text=text, defaults={'level': levels[0], 'syllables': text})

        student_user, _ = User.objects.get_or_create(username='estudiante_demo', defaults={
            'first_name': 'Sofía', 'last_name': 'Luna', 'email': 'estudiante_demo@example.com', 'role': 'STUDENT',
        })
        student_user.set_password('Demo12345!')
        student_user.save()
        student_profile, _ = StudentProfile.objects.get_or_create(user=student_user, defaults={
            'name': 'Sofía Luna', 'alias': 'Sofi', 'grade': '1', 'reading_level': levels[0], 'current_level': levels[0],
        })

        teacher_user, _ = User.objects.get_or_create(username='docente_demo', defaults={
            'first_name': 'Laura', 'last_name': 'Martínez', 'email': 'docente_demo@example.com', 'role': 'TEACHER',
        })
        teacher_user.set_password('Demo12345!')
        teacher_user.save()
        TeacherProfile.objects.get_or_create(user=teacher_user, defaults={'name': 'Laura Martínez'})

        parent_user, _ = User.objects.get_or_create(username='padre_demo', defaults={
            'first_name': 'Carlos', 'last_name': 'Pérez', 'email': 'padre_demo@example.com', 'role': 'PARENT',
        })
        parent_user.set_password('Demo12345!')
        parent_user.save()
        ParentProfile.objects.get_or_create(user=parent_user, defaults={'name': 'Carlos Pérez'})

        if not Achievement.objects.exists():
            Achievement.objects.bulk_create([
                Achievement(name='Primer paso', description='Completa tu primera actividad.', icon='⭐', requirement_type='activities', requirement_value=1),
                Achievement(name='Gran lector', description='Completa 10 lecturas.', icon='📚', requirement_type='readings', requirement_value=10),
                Achievement(name='Semana increíble', description='Practica durante 7 días.', icon='🔥', requirement_type='streak', requirement_value=7),
            ])

        for level in levels:
            Lesson.objects.get_or_create(level=level, title=f'Explorando nivel {level.number}', defaults={'description': level.description, 'stage': 'LEARN', 'order': 1})

        activity, _ = Activity.objects.get_or_create(
            title='Escucha y selecciona',
            defaults={
                'description': 'Escucha una palabra y elige la opción correcta.',
                'instructions': 'Presiona el sonido y selecciona la respuesta.',
                'activity_type': 'LISTEN_SELECT',
                'level': levels[0],
                'difficulty': 'easy',
                'points': 10,
                'stars': 1,
                'is_active': True,
            }
        )
        for option_text, correct in [('CASA', True), ('MASA', False), ('CAMA', False)]:
            ActivityOption.objects.get_or_create(activity=activity, text=option_text, defaults={'is_correct': correct})

        reading, _ = Reading.objects.get_or_create(
            title='Milo y Luna',
            defaults={
                'description': 'Una lectura corta sobre un gato y su amiga Luna.',
                'content': 'Luna tiene un gato. El gato se llama Milo. Milo juega con una pelota. Luna quiere mucho a Milo.',
                'level': levels[2],
                'difficulty': 'easy',
                'estimated_time': 3,
                'is_active': True,
            }
        )
        question, _ = ReadingQuestion.objects.get_or_create(reading=reading, question='¿Cómo se llama el gato?', defaults={'question_type': 'multiple_choice'})
        for answer_text, correct in [('Luna', False), ('Milo', True), ('Sol', False)]:
            ReadingAnswer.objects.get_or_create(question=question, answer=answer_text, defaults={'is_correct': correct})

        StudentProgress.objects.get_or_create(student=student_profile, activity=activity, defaults={'completed': False, 'progress_percentage': 20, 'best_score': 0, 'attempts': 0})
        StudentDifficulty.objects.get_or_create(student=student_profile, difficulty_type='letter_confusion', character_a='b', character_b='d', defaults={'error_count': 3})

        self.stdout.write(self.style.SUCCESS('Datos demo creados correctamente.'))
