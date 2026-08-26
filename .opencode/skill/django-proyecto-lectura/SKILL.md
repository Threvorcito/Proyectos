---
name: django-proyecto-lectura
description: Django manage.py settings.py urls.py models.py views.py forms.py migrations Lectura sin Limites. Use when working on this local Django project, its apps, routes, settings, ORM, auth, templates integration, migrations, or management commands.
---

# Django Proyecto Lectura

Use esta Skill cuando la tarea afecte el comportamiento Django del proyecto `Lectura sin Limites` en `C:\Proyectos`.

## Contexto Del Proyecto

- Proyecto Django: `mysite`.
- Configuracion principal: `mysite/settings.py`.
- URLs principales: `mysite/urls.py`.
- Apps instaladas: `accounts`, `learning`, `activities`, `games`, `readings`, `progress`, `gamification`, `dashboard`, `core`.
- Base de datos local por defecto: SQLite en `db_lectura.sqlite3`.
- PostgreSQL opcional mediante variables `DB_ENGINE` y `DB_*`.
- Idioma y zona horaria: `es-es`, `America/Mexico_City`.
- Usuario personalizado: `accounts.CustomUser`.
- Login principal: `accounts:login`.
- Redirect de login: `dashboard:redirect`.

## Reglas De Trabajo

- Revisar primero `README.md`, `CONTEXTO_PROYECTO.md`, `mysite/settings.py` y las URLs de la app relacionada antes de modificar comportamiento.
- Mantener validaciones criticas en backend; no confiar solo en ocultar botones en templates.
- Respetar el modelo de roles: administrador, docente, estudiante, padre/tutor.
- Respetar el enfoque educativo: primaria, dislexia, instrucciones cortas, apoyo visual, baja carga textual y Metodo FAS.
- No cambiar el modelo `AUTH_USER_MODEL` ni flujos de autenticacion sin revisar `accounts/authentication.py`, modelos, formularios y migraciones.
- Para nuevas vistas, preferir patrones existentes de la app: URLs con namespace, templates bajo `templates/<app>/`, permisos en vista y mensajes Django cuando ya se usen.

## Comandos Utiles

- `python manage.py check`
- `python manage.py test`
- `python manage.py makemigrations`
- `python manage.py migrate`
- `python manage.py runserver`

## Antes De Cambiar Modelos

- Revisar migraciones existentes de la app.
- Confirmar impacto sobre datos locales y demo.
- Crear migracion solo si el cambio modifica esquema o constraints.
- Evitar borrar campos o modelos con datos academicos/historicos sin una razon explicita.
