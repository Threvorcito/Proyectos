---
name: estructura-buenas-practicas
description: Buenas practicas estructura proyecto arquitectura Django apps responsabilidades permisos seguridad dislexia MINED. Use when planning features, refactoring, organizing files, reviewing architecture, or deciding where code should live.
---

# Estructura Y Buenas Practicas

Use esta Skill para decisiones de arquitectura, estructura de apps, refactors y revision general del proyecto.

## Responsabilidades Del Proyecto

- `accounts`: usuarios, roles, login, perfiles docentes/estudiantes/padres y autenticacion.
- `dashboard`: paneles por rol, gestion docente/admin y vistas operativas.
- `learning`: contenido curricular, planes o recursos de aprendizaje si aplica al patron existente.
- `activities`, `games`, `readings`: recursos didacticos por tipo.
- `progress`: avance, reportes, evidencias y seguimiento.
- `gamification`: logros, puntos o refuerzos motivacionales.
- `core`: home, paginas comunes, contexto global y errores como 404.

## Criterios De Diseno

- Ubicar codigo por dominio, no por conveniencia temporal.
- Mantener reglas de negocio criticas en backend.
- Mantener datos academicos historicos siempre que sea posible.
- Evitar duplicacion entre actividades, juegos y lecturas si se puede resolver con patrones existentes simples.
- No crear servicios, helpers o capas nuevas si una vista/form/model bien organizado basta.
- Documentar decisiones relevantes en archivos de contexto solo si el usuario lo pide o si el cambio requiere continuidad.

## Seguridad Y Datos

- Proteger rutas por rol y permiso.
- Evitar exponer informacion de estudiantes a usuarios no autorizados.
- No registrar secretos ni credenciales.
- Tratar `.env`, SQLite local y `media/` como datos locales no versionables.

## Calidad Educativa

- Preservar el objetivo: apoyo a ensenanza-aprendizaje de lectura en primaria, especialmente dislexia.
- Mantener alineacion con MINED Nicaragua cuando la tarea afecte planes, indicadores, competencias o contenidos.
- Favorecer progresion por grado, asignatura, dificultad y seguimiento claro.

## Revision De Cambios

- Comprobar que el cambio respeta roles y permisos.
- Comprobar que no rompe rutas principales documentadas en `README.md`.
- Comprobar que el flujo sigue siendo comprensible para docentes, estudiantes y padres/tutores.
