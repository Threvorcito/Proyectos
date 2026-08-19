from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from activities.models import Activity, ActivityOption
from gamification.models import Achievement
from learning.models import CurriculumCompetency, FasStep, Lesson, Level, MinedReference, MinedStrategy, ParentProfile, StudentProfile, Subject, TeacherProfile, Syllable, Word
from progress.models import StudentDifficulty, StudentProgress
from readings.models import Reading, ReadingAnswer, ReadingQuestion


class Command(BaseCommand):
    help = 'Crea datos demostrativos para Lectura sin Límites.'

    def handle(self, *args, **options):
        User = get_user_model()

        admin_user, _ = User.objects.get_or_create(username='Admin', defaults={
            'first_name': 'Administrador', 'last_name': 'Sistema', 'email': 'admin@example.com', 'role': 'ADMIN',
            'is_staff': True, 'is_superuser': True,
        })
        admin_user.role = 'ADMIN'
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.set_password('admin123')
        admin_user.save()

        levels = [
            Level.objects.get_or_create(number=1, defaults={'name': 'Primeros pasos', 'description': 'Letras, sonidos y sílabas.', 'order': 1})[0],
            Level.objects.get_or_create(number=2, defaults={'name': 'Construyo palabras', 'description': 'Sílabas, palabras y frases.', 'order': 2})[0],
            Level.objects.get_or_create(number=3, defaults={'name': 'Leo y comprendo', 'description': 'Lecturas cortas y comprensión.', 'order': 3})[0],
        ]

        subjects = {}
        for name, description in [
            ('Lengua y Literatura', 'Lectoescritura inicial, comprensión oral y lectura guiada con método FAS.'),
            ('Matemática', 'Pensamiento lógico, conteo, comparación y resolución de problemas con apoyo visual.'),
            ('Ciencias Naturales', 'Observación del entorno, animales, plantas, cuerpo humano y hábitos saludables.'),
            ('Estudios Sociales', 'Familia, escuela, comunidad, convivencia y ubicación en el entorno.'),
            ('English', 'Vocabulario básico mediante escucha, imágenes y repetición.'),
            ('Educación Artística y Cultural', 'Expresión visual, ritmo, trazos y reconocimiento cultural.'),
        ]:
            subjects[name], _ = Subject.objects.get_or_create(name=name, defaults={'description': description, 'is_active': True})

        strategies = {}
        for name, focus, description in [
            ('Continuidad de aprendizajes 1.º a 3.º', 'Lenguaje comunicativo, científico, matemático y social', 'Desarrollo progresivo de competencias tempranas en primero, segundo y tercer grado.'),
            ('Método FAS', 'Lectoescritura inicial', 'Método Fónico Analítico Sintético para trabajar fonemas, sílabas, palabras y lectura.'),
            ('Inglés como segundo idioma', 'Vocabulario y comprensión oral', 'Aprendizaje inicial del inglés con escucha, repetición e imágenes.'),
            ('Planes nacionales de lectura y matemática', 'Lectura comprensiva y pensamiento matemático', 'Refuerzo de lectura, ciencias naturales y matemática en primaria.'),
        ]:
            strategies[name], _ = MinedStrategy.objects.get_or_create(name=name, defaults={'focus': focus, 'description': description, 'is_active': True})

        competencies = {}
        competency_rows = [
            ('1', 'Lengua y Literatura', 'Sonidos iniciales', 'Reconoce sonidos iniciales en palabras familiares.', 'Identifica vocales, consonantes y sílabas simples con apoyo visual.', 'Usar letras grandes, lectura pausada, repetición oral y una instrucción por pantalla.', 'Método FAS'),
            ('1', 'Matemática', 'Conteo inicial', 'Relaciona cantidad, número y palabra numérica en situaciones cercanas.', 'Cuenta objetos del 1 al 5 y selecciona el número correcto.', 'Presentar cantidades con imágenes claras y pocas opciones.', 'Continuidad de aprendizajes 1.º a 3.º'),
            ('2', 'Lengua y Literatura', 'Fluidez de frases', 'Lee frases cortas y ordena palabras para formar oraciones.', 'Responde preguntas literales sobre frases y textos breves.', 'Separar palabras, resaltar sílabas trabadas y permitir relectura.', 'Método FAS'),
            ('2', 'Ciencias Naturales', 'Vocabulario científico básico', 'Reconoce partes de plantas, animales y hábitos saludables.', 'Relaciona palabra, imagen y concepto en textos cortos.', 'Acompañar conceptos con pictogramas y segmentación silábica.', 'Continuidad de aprendizajes 1.º a 3.º'),
            ('3', 'Lengua y Literatura', 'Comprensión de cuento corto', 'Comprende personajes, lugar e idea principal en lecturas infantiles.', 'Elige respuestas literales después de leer por partes.', 'Dividir textos en párrafos cortos y usar preguntas de una idea.', 'Planes nacionales de lectura y matemática'),
            ('3', 'Matemática', 'Lectura de problemas', 'Comprende enunciados matemáticos con datos y operación.', 'Identifica palabras clave como total, quedan, más y menos.', 'Separar visualmente datos, operación y respuesta.', 'Continuidad de aprendizajes 1.º a 3.º'),
        ]
        for grade, subject_name, title, competency, indicator, adaptation, strategy_name in competency_rows:
            unit = 'first' if grade in ('1', '2') else 'second'
            competencies[title], _ = CurriculumCompetency.objects.get_or_create(
                title=title,
                grade=grade,
                subject=subjects[subject_name],
                defaults={
                    'pedagogical_unit': unit,
                    'strategy': strategies[strategy_name],
                    'competency': competency,
                    'achievement_indicator': indicator,
                    'dyslexia_adaptation': adaptation,
                    'is_active': True,
                },
            )

        for order, stage, title, description, grade in [
            (1, 'phoneme', 'Escuchar el sonido', 'Identificar fonemas en palabras familiares.', '1'),
            (2, 'syllable', 'Formar sílabas', 'Unir sonidos para leer sílabas simples.', '1'),
            (3, 'word', 'Construir palabras', 'Ordenar sílabas y reconocer palabras frecuentes.', '2'),
            (4, 'phrase', 'Leer frases', 'Leer oraciones cortas con sentido.', '2'),
            (5, 'reading', 'Comprender textos cortos', 'Leer por partes y responder preguntas literales.', '3'),
        ]:
            FasStep.objects.get_or_create(stage=stage, title=title, grade=grade, defaults={'description': description, 'order': order, 'is_active': True})

        for title, resource_type, grade, subject_name, usage in [
            ('Libros de Primaria MINED', 'book', '1', 'Lengua y Literatura', 'Referencia para organizar lecturas y vocabulario por grado.'),
            ('Cuaderno de Aprestamiento', 'notebook', '1', 'Lengua y Literatura', 'Base para trazos, percepción visual y preparación lectora.'),
            ('Conociendo mi Mundo', 'book', '1', 'Estudios Sociales', 'Referencia para vocabulario de familia, escuela y comunidad.'),
            ('Ciencias Naturales Primaria', 'book', '2', 'Ciencias Naturales', 'Referencia para textos científicos cortos con apoyo visual.'),
            ('Colección de lecturas infantiles', 'reading', '3', 'Lengua y Literatura', 'Inspiración para cuentos breves con preguntas literales.'),
        ]:
            MinedReference.objects.get_or_create(
                title=title,
                defaults={
                    'resource_type': resource_type,
                    'grade': grade,
                    'subject': subjects[subject_name],
                    'official_url': 'https://www.mined.gob.ni/biblioteca/?s=primaria&post_type=product',
                    'app_usage': usage,
                    'is_active': True,
                },
            )

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
        teacher_profile, _ = TeacherProfile.objects.get_or_create(user=teacher_user, defaults={'name': 'Laura Martínez'})
        teacher_profile.first_name = 'Laura'
        teacher_profile.last_name = 'Martínez'
        teacher_profile.email = 'docente_demo@example.com'
        teacher_profile.name = 'Laura Martínez'
        teacher_profile.can_manage_lessons = True
        teacher_profile.can_manage_activities = True
        teacher_profile.can_manage_readings = True
        teacher_profile.save(update_fields=['first_name', 'last_name', 'email', 'name', 'can_manage_lessons', 'can_manage_activities', 'can_manage_readings'])

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
                'subject': subjects['Lengua y Literatura'],
                'competency': competencies['Sonidos iniciales'],
                'grade': '1',
                'difficulty': 'easy',
                'points': 10,
                'stars': 1,
                'is_active': True,
            }
        )
        for option_text, correct in [('CASA', True), ('MASA', False), ('CAMA', False)]:
            ActivityOption.objects.get_or_create(activity=activity, text=option_text, defaults={'is_correct': correct})
        activity.subject = subjects['Lengua y Literatura']
        activity.competency = competencies['Sonidos iniciales']
        activity.grade = '1'
        activity.level = levels[0]
        activity.save(update_fields=['subject', 'competency', 'grade', 'level'])

        curriculum_activities = [
            ('1', 'Lengua y Literatura', levels[0], 'Sonido inicial: m, p, l', 'Reconoce sonidos iniciales y diferencia letras parecidas con apoyo visual.', 'Escucha la palabra, mira la imagen mentalmente y selecciona la letra inicial.', 'LISTEN_SELECT', [('m', True), ('n', False), ('p', False)]),
            ('1', 'Matemática', levels[0], 'Cuenta y lee números del 1 al 5', 'Relaciona cantidad, número y palabra corta.', 'Cuenta despacio, lee el número y elige la cantidad correcta.', 'MATCH_IMAGE_WORD', [('3', True), ('5', False), ('2', False)]),
            ('1', 'Ciencias Naturales', levels[0], 'Animales de mi entorno', 'Lee nombres cortos de animales y asocia sonido-imagen-palabra.', 'Escucha el nombre del animal y selecciona la palabra correcta.', 'LISTEN_SELECT', [('gato', True), ('pato', False), ('dato', False)]),
            ('1', 'Estudios Sociales', levels[0], 'Mi familia y mi escuela', 'Identifica palabras frecuentes del entorno familiar y escolar.', 'Lee con calma y selecciona la palabra que corresponde.', 'READING', [('mamá', True), ('mapa', False), ('masa', False)]),
            ('2', 'Lengua y Literatura', levels[1], 'Sílabas trabadas simples', 'Forma palabras con sílabas y fortalece la ruta fonológica.', 'Ordena las sílabas para formar una palabra conocida.', 'FORM_WORD', [('plato', True), ('palo', False), ('pato', False)]),
            ('2', 'Matemática', levels[1], 'Problemas cortos con suma', 'Lee enunciados breves y reconoce datos importantes.', 'Lee una oración corta, identifica el número y responde.', 'COMPLETE_WORD', [('7', True), ('6', False), ('8', False)]),
            ('2', 'Ciencias Naturales', levels[1], 'Partes de una planta', 'Reconoce vocabulario científico básico con segmentación silábica.', 'Lee la palabra por sílabas y selecciona la parte de la planta.', 'SYLLABLES', [('raíz', True), ('risa', False), ('maíz', False)]),
            ('2', 'Estudios Sociales', levels[1], 'Mi comunidad', 'Lee palabras del barrio y la comunidad con apoyo contextual.', 'Selecciona la palabra que nombra un lugar de la comunidad.', 'LISTEN_SELECT', [('escuela', True), ('estrella', False), ('escoba', False)]),
            ('3', 'Lengua y Literatura', levels[2], 'Comprendo un cuento corto', 'Lee un texto breve y responde una pregunta literal.', 'Lee por partes, subraya mentalmente la idea y elige la respuesta.', 'READING', [('Milo', True), ('Luna', False), ('Sol', False)]),
            ('3', 'Matemática', levels[2], 'Lectura de problemas', 'Comprende enunciados matemáticos con palabras clave.', 'Lee el problema y selecciona la operación necesaria.', 'READING', [('sumar', True), ('borrar', False), ('saltar', False)]),
            ('3', 'Ciencias Naturales', levels[2], 'Cuidado del cuerpo', 'Clasifica hábitos saludables mediante lectura comprensiva.', 'Lee cada opción y selecciona el hábito saludable.', 'LISTEN_SELECT', [('lavarse las manos', True), ('no dormir', False), ('no beber agua', False)]),
            ('3', 'Estudios Sociales', levels[2], 'Normas de convivencia', 'Comprende normas breves para la escuela y comunidad.', 'Lee la norma y elige la acción respetuosa.', 'READING', [('escuchar', True), ('gritar', False), ('empujar', False)]),
        ]
        for grade, subject_name, level, title, description, instructions, activity_type, options in curriculum_activities:
            item, _ = Activity.objects.get_or_create(
                title=title,
                defaults={
                    'description': description,
                    'instructions': instructions,
                    'activity_type': activity_type,
                    'level': level,
                    'subject': subjects[subject_name],
                    'competency': CurriculumCompetency.objects.filter(grade=grade, subject=subjects[subject_name]).first(),
                    'grade': grade,
                    'difficulty': 'easy' if grade == '1' else 'medium',
                    'points': 10,
                    'stars': 1,
                    'is_active': True,
                },
            )
            item.subject = subjects[subject_name]
            item.competency = CurriculumCompetency.objects.filter(grade=grade, subject=subjects[subject_name]).first()
            item.grade = grade
            item.level = level
            item.save(update_fields=['subject', 'competency', 'grade', 'level'])
            for order, (option_text, correct) in enumerate(options, start=1):
                ActivityOption.objects.get_or_create(activity=item, text=option_text, defaults={'is_correct': correct, 'order': order})

        reading, _ = Reading.objects.get_or_create(
            title='Milo y Luna',
            defaults={
                'description': 'Una lectura corta sobre un gato y su amiga Luna.',
                'content': 'Luna tiene un gato. El gato se llama Milo. Milo juega con una pelota. Luna quiere mucho a Milo.',
                'level': levels[2],
                'subject': subjects['Lengua y Literatura'],
                'competency': competencies['Comprensión de cuento corto'],
                'grade': '3',
                'difficulty': 'easy',
                'estimated_time': 3,
                'is_active': True,
            }
        )
        question, _ = ReadingQuestion.objects.get_or_create(reading=reading, question='¿Cómo se llama el gato?', defaults={'question_type': 'multiple_choice'})
        for answer_text, correct in [('Luna', False), ('Milo', True), ('Sol', False)]:
            ReadingAnswer.objects.get_or_create(question=question, answer=answer_text, defaults={'is_correct': correct})
        reading.subject = subjects['Lengua y Literatura']
        reading.competency = competencies['Comprensión de cuento corto']
        reading.grade = '3'
        reading.level = levels[2]
        reading.save(update_fields=['subject', 'competency', 'grade', 'level'])

        reading_plan = [
            ('1', 'Lengua y Literatura', levels[0], 'La mamá lee', 'Lectura con palabras frecuentes.', 'Mamá lee. Memo mira. Memo ama leer.'),
            ('2', 'Ciencias Naturales', levels[1], 'La semilla', 'Lectura corta sobre plantas.', 'La semilla cae en la tierra. Con agua y sol, la semilla crece.'),
            ('3', 'Estudios Sociales', levels[2], 'Mi comunidad ayuda', 'Lectura sobre convivencia.', 'En mi comunidad saludamos, escuchamos y ayudamos. Así vivimos mejor.'),
            ('3', 'Matemática', levels[2], 'Ana cuenta frutas', 'Lectura matemática breve.', 'Ana tiene tres mangos y suma dos más. Ahora puede compartir cinco mangos.'),
        ]
        for grade, subject_name, level, title, description, content in reading_plan:
            Reading.objects.get_or_create(
                title=title,
                defaults={
                    'description': description,
                    'content': content,
                    'level': level,
                    'subject': subjects[subject_name],
                    'competency': CurriculumCompetency.objects.filter(grade=grade, subject=subjects[subject_name]).first(),
                    'grade': grade,
                    'difficulty': 'easy',
                    'estimated_time': 3,
                    'is_active': True,
                },
            )

        StudentProgress.objects.get_or_create(student=student_profile, activity=activity, defaults={'completed': False, 'progress_percentage': 20, 'best_score': 0, 'attempts': 0})
        StudentDifficulty.objects.get_or_create(student=student_profile, difficulty_type='letter_confusion', character_a='b', character_b='d', defaults={'error_count': 3})

        self.stdout.write(self.style.SUCCESS('Datos demo creados correctamente.'))
