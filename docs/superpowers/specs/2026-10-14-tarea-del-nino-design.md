# Diseño: "Mi tarea de hoy" — tareas de la maestra guiadas para niños con dislexia

Fecha: 2026-10-14 · Proyecto: Lectura sin Límites (monografía BICU, Bluefields, Nicaragua)

## 1. Intención y porqué

La maestra prepara su clase con un **Plan Diario** en su cuaderno (MINED Nicaragua): datos generales, indicador de logros, criterios, contenido, actividades iniciales, **actividades de desarrollo** y culminación. Según la maestra consultada, los niños con dislexia se traban en el **desarrollo**:

1. **Decodificar**: no logran convertir las letras en sonidos y unirlos; por eso no terminan de aprender a leer.
2. **Escribir completo**: escriben, pero omiten letras o sílabas y no completan la palabra u oración.

La app debe convertir la parte del plan que hace el niño en una **tarea de pasos cortos** que el niño pueda hacer solo en la tableta o el celular, con ayudas para la dislexia en cada paso, siguiendo el **Método FAS** (fónico: primero el **sonido** de la letra, sobre todo de las consonantes; luego la sílaba; luego la palabra).

Esto responde al objetivo general de la monografía y a los específicos 1 (necesidades), 2 (requerimientos) y 3 (interfaz accesible).

## 2. Metas

- La maestra crea una tarea en pocos minutos cargando **solo lo que hace el niño** (no su plan completo; el plan completo sigue en su cuaderno).
- Sirve para **todas las materias de 1.º, 2.º y 3.º grado** (Lengua y Literatura, Matemática, Ciencias Naturales, Estudios Sociales y las demás que existan en el sistema).
- El niño ve **"Mi tarea de hoy"** como un camino de pasos: un paso a la vez, audio en todo, Lumi acompaña, sin cronómetro, sin castigo por equivocarse, puede repetir.
- **Decodificación FAS en cualquier texto de cualquier materia**: el niño toca una palabra y la app muestra sus letras, hace sonar el **fonema** de cada letra, une sonidos en sílabas y sílabas en la palabra.
- **Escritura asistida**: el niño arma palabras con fichas de letras/sílabas (componedor) u oraciones con fichas de palabras; si falta algo, la app marca el hueco y hace sonar el sonido que falta, sin decir "está mal".
- La maestra ve por niño: si terminó, **qué palabras le costó decodificar**, **qué omite al escribir**, y un nivel con la escala MINED SNEPA (Aprendizaje Inicial / Fundamental / Satisfactorio / Avanzado). El niño nunca ve números ni etiquetas.

## 3. No-metas (por ahora)

- Cargar el Plan Diario completo (indicador de logros, criterios, contenido, culminación). Puede venir después.
- Grabaciones reales de fonemas (se usa la voz automática; ver §6).
- Reconocimiento de voz del niño o grabar su voz.
- Modo sin conexión (PWA). Se diseña para no impedirlo después.
- Generar tareas automáticamente con IA.

## 4. Anti-metas (sería un fracaso aunque funcione)

- Que el niño tenga que **leer instrucciones** para saber qué hacer.
- Que la decodificación diga el **nombre** de la letra ("eme") en vez de su **sonido** ("mmm") — contradice el FAS.
- Que la maestra tarde más en cargar la tarea en la app que en escribirla en su cuaderno.
- Mostrar al niño comparaciones con otros, rankings, cronómetros o la palabra "error".
- Que los datos de dificultad del niño (dato sensible, Ley 787) los vea alguien más que sus maestras con permiso de reportes y el admin. El tutor no ve el detalle de dificultades (ver §5.5).

## 5. Experiencia

### 5.1 Maestra: crear una tarea
- Elige **materia**, **grado** y **alumnos** (o su grupo completo).
- Agrega **pasos en orden** desde una lista corta de tipos:

| Tipo de paso | Qué carga la maestra | Qué hace el niño |
|---|---|---|
| 🖼️ Mira y comenta | Imagen + 1 pregunta | Escucha la pregunta, mira la imagen, toca "Listo" (es oral en clase; la app no evalúa) |
| 🔊📖 Lectura | Texto (o elige una Lectura existente) | Escucha la lectura modelo con resaltado → la lee él → la lee en silencio (reutiliza "Practicar lectura") |
| 🔤 Palabras difíciles | 3–6 palabras (o la app propone las más largas del texto) | Practica decodificación FAS de cada una antes de leer |
| ❓ Contesta | Pregunta + opciones (o respuesta corta) y cuál es la correcta | Escucha la pregunta, elige o arma la respuesta con fichas; una pregunta por pantalla |
| ✏️ Arma / completa | Palabra u oración objetivo | Arma con fichas (letras/sílabas o palabras); la app marca huecos |
| 🔢 Ejemplo y práctica | Ejemplo resuelto en pasos (texto + imagen opcional) + ejercicios con respuesta | Ve el ejemplo paso a paso (cada paso con audio), luego resuelve ejercicios parecidos |

- Vista previa "como la ve el niño" antes de asignar.
- Puede reutilizar/duplicar una tarea anterior.

### 5.2 Niño: "Mi tarea de hoy"
- Al entrar, si tiene tarea, la ve primero en su panel: Lumi lo saluda y le dice qué toca.
- Camino de pasos (boceto A aprobado): el paso actual brilla, los hechos tienen ⭐; botón grande "¡Vamos!".
- Cada paso: instrucción **en audio** (🔊), poco texto, botones de 48–64 px, sin tiempo límite.
- Puede salir y volver; retoma donde quedó.
- Al terminar: celebración de Lumi; la tarea queda como terminada para la maestra.

### 5.3 Decodificación FAS (disponible en todo texto que lea el niño)
1. El niño toca una palabra (ej. "leyeron").
2. Se muestran sus letras grandes: l · e · y · e · r · o · n.
3. Al tocar cada letra suena su **fonema**.
4. La app une en voz alta y visualmente: "lll-e → **le**", "yyy-e → **ye**", "rrr-o-nnn → **ron**".
5. Dice la palabra completa: **leyeron**.
- La segmentación en sílabas debe respetar las reglas del español (incluye dígrafos ch, ll, rr, qu, gu y grupos como bl, br, tr).
- Cada vez que el niño pide ayuda en una palabra, se registra (para el reporte de la maestra).

### 5.4 Escritura asistida
- Fichas arrastrables o tocables (letras, sílabas o palabras según el paso).
- Si la respuesta está incompleta: se marca el lugar del hueco con 👀 y suena el fonema/sílaba faltante; el niño vuelve a intentar.
- Se registran las omisiones (qué letra/sílaba faltó y en qué palabra).

### 5.5 Lo que ve la maestra
- Lista de tareas con avance por alumno (sin empezar / en curso / terminada).
- Por alumno y tarea: respuestas, **palabras que pidió decodificar**, **omisiones al escribir**, y nivel SNEPA sugerido (la maestra puede ajustarlo).
- El tutor ve solo "terminó la tarea" y mensajes de ánimo, en lenguaje simple.

## 6. Restricciones

- Stack existente: Django + plantillas + CSS/JS sin frameworks; diseño infantil `kid.css` (body.kid-ui) para el niño; diseño Bodega (tablas/diálogos) para la maestra; Lumi y `AppSpeech` ya existen.
- **Voz**: por ahora la voz automática del navegador (`AppSpeech`, voz femenina preferida). Fonemas: consonantes continuas como sonido alargado ("mmm", "sss", "lll", "nnn", "fff", "rrr", "yyy", "jjj"); consonantes oclusivas (p, t, c/k, b/v, d, g) se pronuncian como su sílaba con la vocal siguiente. **Diseñar una tabla de fonemas reemplazable** para poder cambiar cada sonido por un archivo de audio grabado sin tocar el resto.
- Tablets/celulares de baja gama y conexión débil: páginas livianas, sin dependencias pesadas.
- **Ley 787 (Nicaragua)**: los indicadores de dificultad son datos sensibles; solo los ven las maestras vinculadas al alumno que tengan permiso de ver reportes (`can_view_student_reports`) y el admin; no se ceden a terceros. El tutor solo ve avance general.
- Accesibilidad: contraste AA, sin cursivas, letra Lexend, respeta tamaño/espaciado del panel "Aa" y "reducir movimiento".
- Todo lo existente debe seguir funcionando (Planes de clase, Practicar lectura, actividades, reportes).

## 7. Decisiones tomadas por la persona usuaria
- La maestra carga **solo la parte del niño**.
- Todas las materias de **1.º a 3.º**.
- Método **FAS fónico** (sonido de la letra, no su nombre).
- Por ahora **voz automática**; grabaciones después.
- Pantalla del niño: **camino de pasos** (boceto A).

## 8. Decisiones del diseñador (revisables)
- La tarea se modela como algo nuevo y separado del "Plan de clase" existente, pero puede vincularse opcionalmente a un plan (reutilizando su materia/grado). Los planes actuales no se tocan.
- Tipos de paso cerrados (los 6 de §5.1); no un editor libre.
- Nivel SNEPA **sugerido** por la app a partir de aciertos y ayudas, **siempre editable** por la maestra.
- Una tarea puede asignarse con fecha; el niño ve primero la más próxima.
- **Quién ve los datos**: maestras vinculadas al alumno (`TeacherProfile.students`) con permiso de reportes, y admin. El tutor ve solo "terminó la tarea" y mensajes de ánimo, sin detalle de dificultades (minimización de datos, Ley 787).
- **"Su grupo completo"** = todos los alumnos de la maestra que crea la tarea, filtrados por el grado de la tarea. No se crea un modelo de grupo/sección.
- **Fichas en "Arma / completa"**: las fichas de la palabra u oración objetivo **más 2–3 distractores** (letras o sílabas parecidas: b/d, p/q, m/n, sílabas vecinas). "Completa" = la maestra escribe la oración y marca qué palabra o sílaba queda en blanco. **Omisión** = el niño envía la palabra con letras/sílabas faltantes respecto del objetivo (se registra cuál faltó).
- **Convivencia con Planes de clase**: "Mi tarea de hoy" aparece **arriba** en el panel del niño; el bloque actual de planes asignados se mantiene igual debajo.
- **Editar una tarea**: se puede editar libremente hasta que el primer alumno la empieza; después los pasos quedan bloqueados y la maestra puede **duplicarla** para hacer cambios (solo se pueden agregar alumnos o cambiar la fecha).
- **Respuestas incorrectas**: el niño recibe una pista (audio + resaltado) y reintenta; tras el 2.º intento la app le **modela la respuesta** (Lumi la dice y la muestra) y sigue, sin decir "error". Para el nivel SNEPA sugerido cuenta el **primer intento** y la **cantidad de ayudas** usadas.

## 9. Lo que queda al constructor
- Modelos y migraciones concretos, URLs y vistas.
- Algoritmo de silabeo en español y tabla de fonemas.
- Cómo se reutiliza "Practicar lectura" dentro del paso de lectura.
- Cálculo exacto del nivel SNEPA sugerido.
- Orden de entrega en fases (se recomienda: 1) crear/asignar tarea + camino del niño con pasos Mira, Lectura y Contesta; 2) decodificación FAS; 3) escritura asistida; 4) Ejemplo y práctica; 5) reportes de dificultades).
