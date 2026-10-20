# Diseño: Dictado FAS con punto de quiebre

Fecha: 2026-10-20 · Proyecto: Lectura sin Límites · Primera pieza de la integración del Método FAS

## 1. Intención y porqué

El MINED orienta desde 2015 el Método Fónico Analítico Sintético (FAS) a nivel nacional, "con la condición de que los docentes lo enriquezcan con otras estrategias creativas e innovadoras" (Cuadernillo FAS, p. 4). La app es ese enriquecimiento.

La maestra consultada explicó que:

- En cada clase se dan los pasos completos del FAS: sonido, formación de sílabas, sílabas en palabras y palabras en oraciones (coincide con los "Pasos de la Lectura", Cuadernillo p. 14).
- No se sabe en qué paso se traba cada niño hasta la lectura en el libro y, sobre todo, **el dictado**: unos no dominan el sonido-letra, otros escriben sílabas pero no palabras, otros palabras pero no oraciones.
- Ella dicta **5 palabras y 2 oraciones**, y **no existe un instrumento de evaluación** para eso.
- En la escuela no hay internet; el niño practica en casa con el celular del padre.

Esta pieza le da a la maestra un dictado que el niño hace en casa, corregido con un instrumento por pasos FAS, y le muestra el **punto de quiebre** de cada niño.

## 2. Metas

- La maestra agrega a una tarea un paso **Dictado**: la letra o fonema en estudio, 5 palabras y 2 oraciones.
- El niño escucha cada palabra u oración (voz automática, puede repetir) y la escribe con fichas (componedor digital) de letras para palabras y de palabras para oraciones, con distractores confusables (b/d, p/q, m/n) ya existentes en `homework/writing.py`.
- Cada ítem se corrige con el flujo actual de dos intentos, sin decir "está mal".
- Al terminar, la app calcula el **punto de quiebre** del niño según el instrumento (§4).
- La maestra ve en el reporte de la tarea el punto de quiebre por niño y al grupo **agrupado por quiebre**, para reforzar juntos.
- La maestra puede **imprimir el instrumento** (las 5 palabras, las 2 oraciones y la tabla de cotejo por niño) para usarlo también en papel en el aula.

## 3. No-metas (por ahora)

- Componedor libre, esquema gráfico y "Clase FAS del día" (segunda pieza).
- Rehacer `FasStep` según las etapas oficiales (aprestamiento, adquisición, afianzamiento).
- Calendario de fonemas MINED (pendiente de conseguir).
- Cargar en la app los resultados del dictado hecho en papel.
- Escritura a mano o reconocimiento de voz.

## 4. Instrumento de evaluación (lista de cotejo por pasos FAS)

Se evalúan tres criterios, en el orden del método:

| Criterio | Qué mide | Logrado si |
|---|---|---|
| 1. Sonido-letra | Correspondencia fonema-grafema de la letra en estudio | la letra en estudio está bien escrita en al menos 4 de 5 palabras |
| 2. Palabras | Síntesis de sílabas en palabras completas | al menos 4 de 5 palabras completas al primer intento |
| 3. Oraciones | Unir palabras en oraciones completas | las 2 oraciones completas, con hasta un intento extra |

**Punto de quiebre** = el primer criterio no logrado, en ese orden. Si los tres están logrados, el resultado es "Sin quiebre". Si el niño no terminó, se muestra "Incompleto".

Los umbrales son decisión del constructor (§7) y viven en una sola función para poder ajustarlos con la maestra.

## 5. Restricciones

- Mismo flujo de tareas actual: `Task` → `TaskStep` → `TaskAssignment` → `StepResult`. Una fila de `StepResult` por ítem (7 ítems).
- Payload validado en `homework/payloads.py`, corrección en `homework/evaluation.py`, dos intentos en `homework/services.py`.
- Celular primero, pantallas cortas, una consigna por pantalla, nada de números para el niño.
- Ley 787: hoy la familia no ve respuestas, dificultades ni niveles (`dashboard/views.py:1163`, `homework/permissions.py:20`). Esta pieza **no cambia eso**: el punto de quiebre lo ve solo la maestra.
- Código y nombres en inglés; textos de interfaz en español, siguiendo el proyecto.

## 6. Decidido

- El dictado es un tipo de paso nuevo dentro de "Mi tarea" (no una app aparte).
- 5 palabras y 2 oraciones, como dicta la maestra.
- Se empieza por el dictado; componedor libre y esquema gráfico van después.

## 7. Decisiones del constructor

- Escritura con fichas, no con teclado: un niño de primer grado en celular no puede teclear con fluidez.
- Los umbrales del §4.
- Tres criterios en vez de cuatro: los quiebres que describió la maestra son sonido-letra, sílabas→palabras y palabras→oraciones.
- El punto de quiebre se calcula al leer el reporte (no se guarda en la base), así un cambio de umbral corrige todo el historial.
