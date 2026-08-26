---
name: frontend-django-web
description: HTML CSS JavaScript Bootstrap Django templates static responsive UI. Use when editing templates, static CSS/JS, Bootstrap 5 layouts, accessibility, forms, or visual behavior in this Django project.
---

# Frontend Django Web

Use esta Skill para trabajo en templates Django, CSS, JavaScript y UI del proyecto.

## Contexto Frontend

- Templates globales: `templates/`.
- Static global: `static/`.
- Bootstrap 5 esta documentado como tecnologia del proyecto.
- La aplicacion debe favorecer lectura infantil y apoyo a dislexia.

## Principios Visuales

- Mantener instrucciones cortas, jerarquia visual clara y poca carga textual por pantalla.
- Priorizar contraste suficiente, tamanos legibles, separacion generosa y estados de foco visibles.
- Evitar distractores visuales que dificulten lectura a estudiantes con dislexia.
- Mantener consistencia con el diseno existente; no redisenar pantallas completas si la tarea es puntual.
- Verificar escritorio y movil cuando se toque layout o navegacion.

## Django Templates

- Revisar template base y bloques existentes antes de crear estructura nueva.
- Respetar namespaces de URLs con `{% url 'app:name' %}`.
- Mantener CSRF en formularios POST.
- No mostrar acciones a usuarios sin permiso, pero recordar que la autorizacion real debe vivir en backend.
- Evitar duplicar HTML grande si ya existe un partial o patron repetido.

## JavaScript Y CSS

- Preferir JavaScript simple y progresivo; la pagina debe seguir siendo usable si una mejora menor falla.
- No mover logica de seguridad o permisos al cliente.
- Mantener CSS organizado por pantalla/componente si el proyecto ya lo hace asi.
- No introducir frameworks frontend nuevos sin requisito explicito.

## Verificacion

- Ejecutar `python manage.py check` si el cambio toca templates con URLs, formularios o tags Django.
- Probar rutas principales afectadas con `python manage.py runserver` cuando sea necesario.
