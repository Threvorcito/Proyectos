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
- SQLite para desarrollo local
- PostgreSQL opcional/recomendado para producción
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

## Base de datos

Por defecto el proyecto usa SQLite con `db_lectura.sqlite3`. Para usar PostgreSQL no es necesario cambiar código; basta con configurar variables de entorno.

El archivo local `.env` se carga automáticamente si existe. Este archivo está ignorado por git y debe usarse para credenciales locales.

Variables principales:

```bash
DB_ENGINE=postgresql
DB_NAME=lectura_sin_limites
DB_USER=lectura_user
DB_PASSWORD=tu_contrasena
DB_HOST=localhost
DB_PORT=5432
```

Migración de prueba desde SQLite a PostgreSQL:

```bash
python manage.py dumpdata --exclude contenttypes --exclude auth.permission > data.json
# Cambiar DB_ENGINE y variables DB_* a PostgreSQL
python manage.py migrate
python manage.py loaddata data.json
python manage.py check
python manage.py test
```

Mantén una copia de `db_lectura.sqlite3` antes de importar datos en PostgreSQL.

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
