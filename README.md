# Lectura sin Límites

Aplicación web que facilita el proceso de enseñanza-aprendizaje en estudiantes con dislexia de educación primaria, enfocada en primero, segundo y tercer grado.

## Roles del sistema
- Administrador: gestiona docentes, permisos y recursos educativos como niveles, actividades, juegos, cuentos y lecturas.
- Docente: registra estudiantes, crea planes de clase y da seguimiento al avance lector.
- Estudiante: practica actividades, juegos y lecturas adaptadas.
- Padre o tutor: consulta información de acompañamiento familiar.

## Base curricular
El contenido se organiza tomando como referencia la información pública del MINED para Educación Primaria:
- Primera Unidad Pedagógica: 1.° y 2.° grado.
- Segunda Unidad Pedagógica: 3.° y 4.° grado.
- Enfoque de 1.° a 3.° grado: continuidad de aprendizajes mediante lenguaje comunicativo, científico, matemático y social.
- Lectoescritura inicial: método FAS, Fónico Analítico Sintético.

Para esta aplicación se trabaja únicamente con 1.°, 2.° y 3.° grado, clasificando actividades, juegos y lecturas por asignatura. Las asignaturas iniciales se tomaron de las categorías de la Biblioteca Digital del MINED: Lengua y Literatura, Matemática, Ciencias Naturales, Estudios Sociales, English y Educación Artística y Cultural.

Todo recurso debe mantener adaptaciones para dislexia: instrucciones cortas, lectura pausada, apoyo visual, contraste adecuado, repetición, segmentación silábica y reducción de distractores confusos.

## Tecnologías
- Python 3
- Django
- SQLite
- HTML5, CSS3, JavaScript
- Bootstrap 5

## Instalación
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver
```

## Cuentas demo
- `Admin` / `admin123`
- `estudiante_demo` / `Demo12345!`
- `docente_demo` / `Demo12345!`
- `padre_demo` / `Demo12345!`

## Rutas principales
- `/`
- `/cuentas/registro/`
- `/cuentas/login/`
- `/panel/estudiante/`
- `/panel/docente/`
- `/panel/padres/`
- `/actividades/`
- `/lecturas/`
