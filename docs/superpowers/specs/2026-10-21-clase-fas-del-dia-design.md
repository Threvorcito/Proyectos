# Diseño: Clase FAS del día

Fecha: 2026-10-21 · Proyecto: Lectura sin Límites · Segunda pieza de la integración del Método FAS

## 1. Intención y porqué

La maestra consultada explicó que en cada clase se dan los pasos completos del FAS para la letra del día, y que existe un calendario que fija qué letra va cada semana. El calendario todavía no lo tenemos, pero el **Tomo I de Educación Especial del MINED** (MINED/UNICEF, p38 del PDF) da el **orden oficial de presentación de los fonemas**:

i, u, y → a, e, o → m, p, b, v → s, c, z → l, n → f, t, d → r, rr → ñ, ll, y, h, ch → k, c, q, g, j (x y w aparte; h antes de /ch/).

El mismo tomo indica que solo se dictan palabras **ya analizadas fónicamente** (p44–45): una clase de la «m» no debe usar letras que el niño todavía no vio.

Hoy armar una tarea completa le toma a la maestra varios pasos. Esta pieza le da, por cada letra de la secuencia oficial, una **clase lista** con los pasos del FAS que puede revisar, ajustar y asignar en un minuto.

## 2. Metas

- Página **"Secuencia FAS"** para la maestra: las letras en el orden oficial, agrupadas como en el tomo, con el estado de cada una ("sin clase", "clase creada", "asignada").
- Botón **"Crear clase de la «m»"**: genera una tarea normal de "Mi tarea" con los pasos del FAS, usando solo letras ya vistas:
  1. **Presentación del fonema** (paso *Mira y comenta*): escuchar el sonido ("mmm") y pensar palabras que lo tienen.
  2. **Presentación del grafema y análisis** (paso *Palabras*): palabras con la letra en distintas posiciones; al tocarlas, el niño ve las letras, oye cada sonido y la unión en sílabas (decodificación FAS ya existente).
  3. **Formación de sílabas y palabras** (paso *Arma*, fichas de sílabas): armar una palabra de la clase.
  4. **Formación de oraciones** (paso *Arma*, fichas de palabras): armar una oración.
  5. **Lectura** (paso *Lectura*): un texto corto solo con letras vistas.
  6. **Dictado** (paso *Dictado* de la pieza anterior): 5 palabras y 2 oraciones.
- La tarea creada es **editable como cualquier otra** antes de asignarla.
- Un **banco de contenido por letra** (palabras, oraciones, lectura) revisable, guardado en el código.

## 3. No-metas (por ahora)

- Calendario por fechas (se agrega cuando llegue el de la maestra; la maestra marca el ritmo).
- Vocales (etapa inicial): el dictado exige palabras con la letra y con solo vocales casi no hay palabras. La secuencia las muestra como "aprestamiento", sin botón.
- Grafemas x y w, y sílabas trabadas.
- Componedor libre y esquema gráfico (pieza siguiente).
- Rehacer el catálogo `FasStep`.
- Imágenes por palabra.

## 4. Restricciones

- Reusar los tipos de paso existentes; no hay pantallas nuevas para el niño.
- Cada palabra, oración y lectura de una letra usa solo vocales y consonantes **anteriores o iguales** en la secuencia. Un test lo verifica para todo el banco.
- El banco debe pasar la validación de cada tipo de paso (`clean_payload`). Un test lo verifica para todas las letras.
- Textos en español neutral de Nicaragua; nada de "tú" en consignas para el niño.
- Código en inglés; interfaz en español.

## 5. Decidido

- Seguir el orden oficial del Tomo I hasta tener el calendario.
- Se construye sobre "Mi tarea".

## 6. Decisiones del constructor

- **La maestra elige la letra** (no la fecha): cada aula va a su ritmo y el calendario aún no está.
- **Una letra por grafema**: c, y, g se repiten en el tomo con sonidos distintos; en esta pieza cada grafema aparece una vez, en su primera posición (c junto a s, z; y entre las vocales se omite). Ajustable cuando llegue el calendario.
- **El contenido lo propone la app y es editable**: palabras simples y comunes; la maestra corrige lo que no le sirva. Conviene que la profe consultada revise el banco.
- **Contenido para las consonantes hasta la «d»** (m, p, b, v, s, c, z, l, n, f, t, d) en esta pieza; el resto de la secuencia aparece en la página sin botón hasta completar el banco.
