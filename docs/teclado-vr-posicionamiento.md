# Posicionamiento del teclado virtual en VR

Documento resumen de la corrección implementada, pensado para incorporarse a la memoria del TFG. Incluye una explicación no técnica del problema y la solución, y el detalle técnico del cambio.

## 1. Problema

La aplicación tiene un teclado virtual en 3D (`#vr-keyboard-panel`) que se abre cada vez que hay que escribir texto dentro de la experiencia VR — por ejemplo, al elegir el nombre de una tabla o una columna en el constructor de consultas. El teclado se posicionaba **en función de hacia dónde estaba mirando la cámara en el instante en que se abría**: se calculaba un punto a una distancia fija delante del usuario, usando el ángulo de giro horizontal (yaw) de la cámara.

Ese enfoque resultó frágil en la práctica:

- Si el usuario estaba mirando hacia arriba o hacia abajo (inclinación vertical) al pulsar la caja de texto, el teclado no quedaba centrado en su vista.
- El tamaño del panel (14 unidades de ancho) no encajaba de forma fiable en el campo de visión a la distancia elegida, según el tamaño/proporción de la ventana del navegador: en unos casos se veía recortado y había que alejarse manualmente (retroceder con las teclas WASD) para verlo entero.

## 2. Explicación no técnica

Antes, el teclado aparecía "donde estuvieras mirando en ese momento" — como si alguien te pusiera un cartel justo delante de los ojos sin comprobar antes si estabas mirando al techo, al suelo, o si el cartel era más ancho de lo que se puede abarcar de un vistazo. El resultado dependía de la postura del usuario en el instante exacto de pulsar el botón, así que unas veces se veía bien y otras no.

La solución fue dejar de intentar adivinar "hacia dónde miras" y, en su lugar, hacer dos cosas fijas y predecibles:

1. **Apartar la mesa antes de sacar el teclado.** El panel del constructor de consultas (título, opciones, vista previa del SQL) se desplaza hacia arriba, dejando un hueco libre justo delante del usuario.
2. **Colocar siempre al usuario en el mismo sitio para mirar ese hueco**, en vez de confiar en dónde estuviera mirando. Es como si, al sacar el teclado, alguien te girase suavemente la silla para dejarte mirando de frente a la pizarra — siempre en el mismo ángulo, así el teclado siempre cae centrado.

Después de validar que funcionaba, se ajustó el tamaño: en vez de acercar el teclado al usuario (lo cual generaba una sensación de estar "demasiado encima"), se mantuvo a la misma distancia de siempre y en su lugar se hizo el panel algo más ancho y alto, y se subió la mesa un poco más arriba para dejarle más hueco.

## 3. Decisiones de diseño

**Por qué anclar a la escena y no seguir intentando calcular a partir de la cámara.** El teclado solo se abre desde dentro de una única escena (`escena-query-builder`), nunca desde otro sitio de la aplicación. Al saberlo, no hace falta ninguna fórmula que dependa de la cámara: basta con una posición fija ya conocida de antemano, igual que sabes de antemano dónde está la pizarra de una clase aunque el alumno mire hacia otro lado un momento.

**Reutilizar el mecanismo de "recentrar vista" ya existente.** La aplicación ya tenía una función `resetVista()` (atajo de teclado `R`) que recoloca al usuario en un punto de partida fijo y nivela la cámara. Se reutilizó exactamente ese mismo mecanismo (recolocar el `rig` y resetear el `pitch`/`yaw` de `look-controls`) al abrir el teclado, en vez de inventar uno nuevo.

**Tamaño: agrandar el panel en vez de acercarlo.** La primera corrección de tamaño acercó el teclado al usuario para que se viera más grande, pero visualmente no gustó (sensación de estar "demasiado encima"/fuera de sitio). Se revirtió, y en su lugar se mantuvo la distancia original y se escaló el propio panel (más ancho y alto), que consigue el mismo efecto de "más grande y más fácil de acertar con el puntero" sin cambiar la distancia percibida.

## 4. Cambios técnicos — `index.html`

En `abrirTecladoVR(titulo, valorInicial, callback)`:

- Constantes nuevas: `QB_BASE_Y` (posición Y original de `#escena-query-builder`), `QB_SHIFT_UP` (desplazamiento hacia arriba mientras el teclado está abierto, `10`), `QB_KEYBOARD_POS` (posición fija del teclado: misma profundidad `z` que el panel del constructor, altura de ojos), `QB_KEYBOARD_SCALE` (escala del panel, `"1.3 1.25 1"` — más ancho y alto, profundidad sin cambios).
- Se posiciona `#vr-keyboard-panel` en `QB_KEYBOARD_POS` con rotación `0 0 0` y la escala anterior, en vez de calcularlo a partir de la rotación de la cámara.
- Se desplaza `#escena-query-builder` hacia arriba (`QB_BASE_Y + QB_SHIFT_UP`) para dejar hueco visualmente donde aparece el teclado.
- Se recoloca el `rig` a `RESET_POS`, actualizando también la variable `rigPos` (para que el bucle de movimiento por WASD/joystick, que corre cada 30 ms, no la sobrescriba en el siguiente tick) y se resetea `pitchObject`/`yawObject` de `look-controls`, igual que hace `resetVista()`.

En `cerrarTecladoVR()`:

- Al confirmar o cancelar, `#escena-query-builder` vuelve a su posición Y original (`QB_BASE_Y`).

## 5. Verificación realizada

Iterativo, guiado por capturas de pantalla del usuario probando en un navegador de escritorio (no se puede probar la escena 3D desde este entorno de desarrollo):

1. Primer intento (distancia/escala fija delante de la cámara): el teclado se recortaba y había que retroceder con WASD para verlo entero.
2. Segundo intento (alejar el panel y reducir su escala): seguía sin verse bien si el usuario miraba hacia arriba/abajo.
3. Tercer intento (recentrar solo la inclinación de la cámara): mejoró el centrado vertical, pero el usuario seguía sin ver el teclado completo en ciertos casos.
4. Cuarto intento — **el que quedó**: anclar el teclado a una posición fija de la escena, apartar el panel del constructor hacia arriba y recentrar `rig` + cámara al abrir. Confirmado por el usuario con captura de pantalla: teclado centrado, panel del constructor fuera de la vista.
5. Ajuste de tamaño: acercar el teclado (descartado, no gustó visualmente) → mantener distancia y agrandar el panel (ancho x1.3, alto x1.25) + subir más el panel del constructor (`QB_SHIFT_UP` de 7 a 10). Confirmado por el usuario como correcto.

## 6. Archivos modificados

- `index.html` — funciones `abrirTecladoVR()` y `cerrarTecladoVR()`.
