# Lectura sin Límites

Plataforma educativa web para apoyar el aprendizaje de la lectura en niños de primaria con enfoque accesible y progresivo.

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
