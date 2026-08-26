---
name: debugging-revision-errores
description: Debugging errores tracebacks Django Python templates database migrations tests. Use when diagnosing exceptions, failed commands, broken pages, 404/500 errors, auth bugs, form validation problems, or regressions.
---

# Debugging Y Revision De Errores

Use esta Skill cuando el usuario reporte errores, tracebacks, comandos fallidos, paginas rotas o comportamiento inesperado.

## Flujo De Diagnostico

- Reproducir el error si es viable con el comando o ruta indicada.
- Leer el traceback completo y ubicar el primer frame del proyecto, no solo la ultima linea.
- Identificar si el fallo viene de URL, vista, formulario, modelo, migracion, template, static, permiso o datos locales.
- Buscar cambios relacionados antes de editar.
- Aplicar el arreglo minimo que corrija la causa raiz.

## Django Checks

- Para errores generales: `python manage.py check`.
- Para migraciones: `python manage.py showmigrations` y luego `python manage.py migrate` si corresponde.
- Para rutas: revisar `mysite/urls.py` y `urls.py` de la app.
- Para templates: revisar nombres, extends, includes, context variables y `{% url %}`.
- Para autenticacion/permisos: revisar backend, decoradores/mixins, validaciones en vista y usuario actual.

## Reglas De Seguridad

- No borrar bases SQLite, media, migraciones ni datos para ocultar el error.
- No desactivar CSRF, autenticacion o permisos como solucion rapida.
- No exponer valores de `.env`, secretos o contrasenas en respuestas.
- Si el error depende de datos locales, describir el dato esperado y una correccion segura.

## Al Final

- Explicar causa raiz en una frase clara.
- Indicar archivos tocados si hubo cambios.
- Indicar comandos de verificacion ejecutados y resultado.
