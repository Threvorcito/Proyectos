# Contexto del proyecto Lectura sin Limites

Este documento resume el trabajo realizado para que un chat nuevo pueda entender el estado del proyecto sin perder contexto.

## Proyecto

- Ruta local: `C:\Proyectos`
- Framework: Django
- Nombre funcional: `Lectura sin Limites`
- Objetivo: plataforma de apoyo para ensenanza-aprendizaje de lectura en primaria, especialmente para ninos con dislexia.
- Enfoque curricular: alineacion con MINED Nicaragua, usando indicadores de logro, competencias, Metodo FAS, planes de clase y recursos didacticos.

## Idea central del sistema

El sistema debe conectar:

- Administrador: gestiona usuarios, docentes, estudiantes, recursos educativos y permisos.
- Docente: crea estudiantes, planes, actividades, lecturas, juegos y reportes segun permisos.
- Estudiante: recibe una experiencia guiada y simple, con actividades recomendadas y planes asignados.
- Padre/tutor: ve progreso del estudiante.

El sitio debe estar orientado a comprension infantil y apoyo a dislexia:

- pasos cortos
- lectura modelada
- apoyo visual
- segmentacion silabica
- actividades multisensoriales
- menos carga textual por pantalla
- juegos de refuerzo
- reportes de avance/dificultades

## Decisiones importantes

### Autenticacion

- `CustomUser` sigue siendo el modelo principal de autenticacion Django.
- El login ahora usa `Correo electronico` en lugar de `Nombre de usuario`.
- Se creo `accounts/authentication.py` con `EmailOrTeacherBackend`.
- Docentes independientes en `TeacherProfile` pueden iniciar sesion con `email` y `password` propios.
- Al primer login de un docente independiente, se crea/vincula automaticamente un `CustomUser` interno con rol `TEACHER`.
- El login por username se conserva por compatibilidad.

### Docentes

- `TeacherProfile.user` es opcional.
- Crear docente ya no crea inmediatamente un usuario Django.
- `TeacherProfile` ahora tiene `is_active` para desactivar docentes sin borrar historial.
- `TeacherProfile` tiene sus propios datos:
  - nombres
  - apellidos
  - correo
  - password cifrado
  - perfil docente
  - estado activo/inactivo
  - permisos

Regla importante de respaldo academico:

- Al desactivar/eliminar desde `Docentes y permisos`, el docente no se borra fisicamente.
- Se marca `TeacherProfile.is_active=False`.
- Si tiene usuario vinculado, tambien se marca `CustomUser.is_active=False`.
- Sus planes, asignaciones, reportes y evidencias se conservan.
- Un docente inactivo no puede iniciar sesion por correo/password docente.
- Si se reactiva desde `Usuarios y roles`, se restaura/vincula el perfil docente si hace falta.

### Estudiantes

- Los estudiantes no necesitan correo real.
- Al crear estudiante desde docente, el sistema genera:
  - usuario interno
  - PIN seguro
  - correo tecnico tipo `nombre@estudiante.local`
- Se quito del formulario docente la entrada manual de usuario y PIN.
- Se agrego campo `Colegio / centro educativo` con opciones:
  - Por definir
  - Escuela publica
  - Colegio privado
  - Centro subvencionado
  - Escuela rural o multigrado
  - Centro comunitario
  - Otro

## Permisos docentes

Antes existian solo 3 permisos generales. Se ampliaron a permisos especificos:

- `can_create_students`: crear estudiantes
- `can_view_student_reports`: ver reportes de estudiantes
- `can_create_lesson_plans`: crear planes
- `can_edit_lesson_plans`: editar planes
- `can_assign_lesson_plans`: asignar/implementar planes
- `can_manage_lessons`: gestionar clases
- `can_manage_activities`: gestionar actividades
- `can_manage_readings`: gestionar lecturas
- `can_manage_games`: gestionar juegos

Los permisos se validan en backend. No basta con ocultar botones.

Validaciones actuales:

- Sin `can_create_students`, el docente no puede crear alumnos.
- Sin `can_view_student_reports`, no puede ver reportes de estudiantes.
- Sin `can_create_lesson_plans`, no puede crear planes.
- Sin `can_edit_lesson_plans`, no puede editar planes.
- Sin `can_assign_lesson_plans`, no puede implementar/asignar planes.
- Sin permiso del recurso correspondiente, no puede entrar por URL directa a clases, actividades, lecturas o juegos.

La UI tambien oculta acciones no permitidas.

## Planes de clase

Se analizo el documento local:

`C:\Users\admin\Downloads\Documento_unificado_indicadores_logro.docx`

El documento tenia ejemplos de planes diarios por indicador de logro, con esta estructura:

- Fecha
- Periodo
- Unidad
- Disciplina
- Indicador de logro
- Criterios de evaluacion
- Contenido
- Actividades iniciales
- Lectura por la docente
- Actividades de comprension y ortografia

El modelo `LessonPlan` se adapto a esa estructura.

Campos agregados a `LessonPlan`:

- `competency`: competencia/indicador MINED opcional
- `period`
- `unit`
- `achievement_indicator`
- `evaluation_criteria`
- `content`
- `initial_activities`
- `teacher_reading`
- `comprehension_orthography_activities`

El formulario de planes esta organizado en secciones:

- Datos generales
- Indicador MINED y contenido
- Secuencia didactica
- Recursos vinculados

Si se selecciona competencia MINED, el formulario puede completar:

- indicador de logro
- contenido
- metodologia/adaptacion para dislexia

## Implementacion de planes

Se creo una pantalla de implementacion del plan:

Ruta:

`/panel/planes/<id>/implementar/`

Template:

`templates/dashboard/lesson_plan_implementation.html`

Muestra:

- base curricular MINED
- secuencia didactica
- estudiantes asignados
- actividades vinculadas
- lecturas vinculadas
- recursos sugeridos automaticamente por nivel y grado
- guia de apoyo para dislexia

Los recursos sugeridos salen de:

- actividades activas con mismo nivel y grado
- lecturas activas con mismo nivel y grado
- juegos activos con mismo nivel y grado

## Reporte por plan

Se creo reporte academico por plan:

Ruta:

`/panel/planes/<id>/reporte/`

Template:

`templates/dashboard/lesson_plan_report.html`

Muestra:

- estudiantes asignados
- estado por estudiante: asignado, en progreso, completado
- conteo de asignados, en progreso y completados
- porcentaje de avance
- notas del docente por estudiante
- fecha/hora de completado
- dificultades frecuentes detectadas en estudiantes del plan
- recomendaciones de refuerzo

Tambien se agrego accion POST para actualizar seguimiento:

`/panel/planes/<id>/seguimiento/<assignment_id>/`

Reglas:

- Solo admin o docente con `can_assign_lesson_plans` puede actualizar seguimiento.
- Si el estado cambia a `Completado`, se guarda `completed_at` automaticamente.
- Si vuelve a otro estado, se limpia `completed_at`.
- Docentes solo pueden ver/actualizar planes propios.

En la lista de planes se agrego:

- columna `Docente` con nombre y correo del profesor responsable
- boton `Reporte`

## Asignacion de planes a estudiantes

Se agrego modelo:

`LessonPlanAssignment`

Campos:

- plan
- estudiante
- estado
- fecha asignacion
- fecha completado
- notas del docente

Estados:

- Asignado
- En progreso
- Completado

Restriccion:

- un estudiante no puede tener duplicada la misma asignacion del mismo plan.

## Panel del estudiante

El panel del estudiante ahora puede mostrar:

- `Mi clase de hoy`, si tiene un plan asignado.
- Boton `Empezar con ayuda`.

Se creo vista infantil:

`templates/dashboard/student_lesson_plan.html`

Estructura para ninos:

- Escucho
- Comprendo
- Practico palabras
- Juego y refuerzo

La idea es que el estudiante no tenga muchas opciones dispersas, sino una ruta guiada y clara.

## Perfil

Perfil de usuario mejorado:

- campo `Sexo`
- campo `Foto de perfil`
- preview de imagen
- la foto aparece en el perfil y en el panel docente
- el topbar admin tambien muestra la foto si existe

Campos agregados a `CustomUser`:

- `gender`
- `profile_photo`

Las imagenes se guardan en:

`media/profile-photos/`

## Panel docente

Se redisenio el panel docente para hacerlo mas profesional:

- hero con bienvenida y foto
- acciones principales segun permisos
- accesos a planes, actividades, clases, lecturas y juegos segun permisos
- metricas
- tabla de planes recientes
- tabla de seguimiento de estudiantes

El panel oculta opciones cuando el docente no tiene permiso.

## Perfil docente y reportes

El perfil docente muestra un reporte academico solo segun permisos:

- planes creados si tiene permisos de planes
- clases activas si puede gestionar clases
- actividades si puede gestionar actividades
- juegos si puede gestionar juegos
- lecturas si puede gestionar lecturas

Si no tiene ningun permiso academico activo, muestra aviso:

`No tienes permisos de gestion academica activos.`

## Administrador

Se redisenaron pantallas administrativas:

- dashboards
- modales de crear/editar/eliminar
- permisos docentes
- recursos educativos

Actualizacion reciente del panel administrativo:

- El panel de control ahora refleja todos los modulos del menu administrativo.
- Se agregaron tarjetas/resumen para usuarios, docentes, estudiantes, padres, planes, niveles, estrategias MINED, competencias, Metodo FAS, Biblioteca MINED, clases, actividades, juegos, lecturas, palabras y silabas.
- Se agregaron contadores de palabras y silabas al dashboard admin.
- Se agrego una seccion de planes recientes con docente responsable.
- Las pantallas de gestion de recursos usan un diseno tipo tabla administrativa profesional:
  - encabezado con titulo y descripcion
  - boton de agregar
  - buscador local
  - tabla con registro, descripcion, tipo, estado y acciones
  - acciones editar/eliminar y permisos en docentes
- El diseno se aplico desde `templates/dashboard/admin_resource_landing.html` para que afecte a todos los modulos del menu.

El panel admin ya tiene menu de usuario en el topbar con:

- Mi panel
- Mi forma de leer
- Perfil
- Cerrar sesion

Logout usa POST con CSRF.

## Permisos en administrador

La gestion de profesores tiene:

- boton `Permisos`
- modal de permisos agrupado
- formulario `Editar profesor` con permisos agrupados en tarjetas

Grupos:

- Estudiantes
- Planificacion
- Recursos educativos

## Recursos MINED y curriculares

Se agregaron modelos curriculares:

- `MinedStrategy`
- `CurriculumCompetency`
- `FasStep`
- `MinedReference`

Tambien se conectaron recursos a competencias:

- actividades
- lecturas
- juegos

El administrador tiene menu para:

- Estrategias MINED
- Competencias
- Metodo FAS
- Biblioteca MINED

## UI/UX aplicada

Se han hecho multiples mejoras visuales:

- dashboards profesionales
- tablas tipo reporte
- modales amplios y segmentados
- diseno responsive
- botones claros
- tarjetas de metricas
- experiencia infantil para estudiantes
- formularios con secciones

Especial atencion:

- desktop
- tablet
- movil

## Seguridad y correcciones

- Logout por POST + CSRF.
- Eliminaciones por POST + CSRF.
- Admin no puede eliminarse a si mismo.
- Superusuarios ocultos en gestion de usuarios.
- Actividades no confian en `is_correct` del cliente; usan `option_id`.
- Password de docente y usuarios no se renderiza en edicion.
- Campo `Nueva contrasena` queda vacio; si no se escribe nada, conserva la actual.
- Se agrego auditoria minima con `core.AuditLog` para registrar actor, accion, modelo, objeto y metadatos.
- La eliminacion administrativa ahora protege datos con historial academico:
  - docentes con planes se desactivan, no se borran
  - estudiantes con progreso/intentos/asignaciones se desactivan, no se borran
  - actividades con intentos/progreso/planes se archivan mediante `is_active=False`
  - lecturas/juegos vinculados a planes se archivan mediante `is_active=False`
  - cuentas de usuario con historial se desactivan para conservar evidencia
- Si una cuenta docente sin historial se elimina desde usuarios, tambien se elimina su perfil docente para evitar perfiles huerfanos activos.
- La sincronizacion usuario-perfil se reforzo:
  - reactivar una cuenta docente reactiva o restaura `TeacherProfile`
  - desactivar una cuenta docente desactiva tambien `TeacherProfile`
  - editar un docente sincroniza estado, correo, nombres y rol del usuario vinculado

## Estados de planes

`LessonPlan` ahora tiene estado real:

- `draft`: Borrador
- `active`: Activo
- `in_progress`: En implementacion
- `completed`: Completado
- `archived`: Archivado

El campo `is_active` se conserva para visibilidad, pero `status` permite controlar mejor ciclo de vida academico y reportes.

## Migraciones importantes recientes

- `accounts/0002_customuser_gender_customuser_profile_photo.py`
- `learning/0007_studentprofile_school.py`
- `learning/0008_lessonplan_achievement_indicator_and_more.py`
- `learning/0009_lessonplan_competency_lessonplanassignment.py`
- `learning/0010_teacherprofile_can_assign_lesson_plans_and_more.py`
- `learning/0011_teacherprofile_is_active.py`
- `core/0001_initial.py`
- `learning/0012_lessonplan_status.py`

## Commits relevantes

- `7d7175f Mejora gestion docente y acceso por correo`
- `5d799dc Conecta planes con estudiantes y recursos`

Hay cambios posteriores a esos commits que todavia pueden estar pendientes de guardar, especialmente permisos ampliados y ajustes visuales recientes.

## Verificaciones frecuentes

Comandos usados para validar:

```bash
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
```

Ultimas verificaciones realizadas durante el trabajo:

- tests OK
- check OK
- sin migraciones pendientes despues de crearlas/aplicarlas

## Nota sobre la base de datos

`db_lectura.sqlite3` esta versionado y se ha incluido en commits anteriores cuando el usuario pidio guardar todos los cambios.

Suele aparecer modificado despues de ejecutar migraciones.

Se dejo preparada configuracion dual de base de datos:

- SQLite queda como base por defecto para desarrollo local.
- PostgreSQL se activa por variables de entorno sin cambiar codigo.
- `settings.py` carga automaticamente un archivo local `.env` si existe.
- Variables principales:
  - `DB_ENGINE=postgresql`
  - `DB_NAME`
  - `DB_USER`
  - `DB_PASSWORD`
  - `DB_HOST`
  - `DB_PORT`
- Se agrego `.env.example` con configuracion segura de ejemplo.
- Se agrego `psycopg[binary]>=3.1` a `requirements.txt`.
- Se documento en `README.md` el flujo de migracion de prueba:
  - `dumpdata` desde SQLite
  - cambiar variables a PostgreSQL
  - `migrate`
  - `loaddata`
  - `check` y `test`

PostgreSQL ya fue configurado localmente:

- Servicio detectado: `postgresql-x64-18`.
- Base creada: `lectura_sin_limites`.
- Usuario creado: `lectura_user`.
- Contrasena usada localmente: `Admin123`.
- Se cambio la contrasena local del superusuario PostgreSQL `postgres` a `Admin123`.
- Se restauro `pg_hba.conf` a `scram-sha-256` y se recargo configuracion.
- Se creo `.env` local ignorado por git para que Django use PostgreSQL por defecto en esta maquina.
- Datos de SQLite fueron exportados e importados correctamente a PostgreSQL.
- Se eliminaron los archivos temporales de dump.
- Validaciones contra PostgreSQL:
  - `python manage.py check` OK
  - `python manage.py makemigrations --check --dry-run` OK
  - `python manage.py test` OK, 33 tests
  - prueba funcional admin/docente/estudiante/padre OK

## Prioridades recomendadas siguientes

1. Cargar un banco mas completo de indicadores MINED por grado/materia/unidad.
2. Mejorar el formulario dinamico de planes para filtrar competencias por materia y grado sin recargar.
3. Crear reporte por plan: estudiantes asignados, completados, errores frecuentes y progreso promedio.
4. Agregar seguimiento del estado `completado` de un plan asignado.
5. Crear actividades automaticamente desde un plan.
6. Agregar audio/lectura en voz alta para apoyar dislexia.
7. Mejorar panel de padres/tutores.

## Como usar este documento en un chat nuevo

En un chat nuevo, indica:

`Lee C:\Proyectos\CONTEXTO_PROYECTO.md antes de hacer cambios.`

O pega el contenido de este archivo al inicio del nuevo chat.
