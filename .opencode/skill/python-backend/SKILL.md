---
name: python-backend
description: Python backend Django services utils management commands tests. Use when editing Python code, business rules, forms, validation, ORM queries, custom auth, seed data, or tests in this project.
---

# Python Backend

Use esta Skill para trabajo en Python dentro del backend Django de `Lectura sin Limites`.

## Estilo Y Alcance

- Preferir cambios pequenos y directos antes que nuevas abstracciones.
- Mantener la logica cerca de la app responsable salvo que ya exista un patron compartido.
- Usar nombres claros en espanol o ingles segun el archivo existente; no mezclar estilos dentro del mismo modulo.
- Evitar compatibilidad innecesaria si no hay datos persistidos, consumidores externos o requisito explicito.
- No introducir dependencias nuevas sin necesidad clara; el proyecto usa `Django`, `Pillow`, `django-crispy-forms`, `crispy-bootstrap5` y `psycopg`.

## Django Python

- Validar permisos y propiedad de datos en vistas, formularios o queries, no solo en HTML.
- Usar el ORM de Django de forma explicita; revisar `select_related` o `prefetch_related` si se muestran listas con relaciones.
- En formularios, mantener validaciones en `clean()`, `clean_<field>()` o `ModelForm` segun corresponda.
- Para autenticacion, revisar `accounts.CustomUser`, `TeacherProfile` y `accounts/authentication.py` antes de cambiar login o permisos.
- Para datos academicos, conservar historial: planes, reportes, asignaciones y evidencias no deben perderse por cambios simples.

## Verificacion

- Ejecutar `python manage.py check` para cambios backend.
- Ejecutar `python manage.py test` cuando el cambio toque reglas de negocio, permisos, formularios, modelos o autenticacion.
- Si se agregan migraciones, verificar con `python manage.py migrate` en entorno local antes de considerar finalizado.
