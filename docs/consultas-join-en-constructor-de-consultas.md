# Soporte de JOIN en el constructor de consultas

Documento resumen de la funcionalidad implementada, pensado para incorporarse a la memoria del TFG. Incluye una explicación no técnica del problema y la solución, y el detalle técnico de la implementación en cada capa del sistema.

## 1. Contexto y objetivo

### 1.1 Punto de partida

El constructor de consultas (menú "SELECCIONA UNA TABLA" → constructor guiado) solo permitía construir un `SELECT` sobre **una única tabla**: elegir tabla, columnas, un filtro `WHERE` y un `ORDER BY`. La consulta no se ejecutaba como SQL de verdad: el asistente traducía las elecciones a parámetros de PostgREST (`?select=...&columna=eq.valor&order=...`), que es quien construye el SQL final internamente.

En una base de datos relacional real, la operación más representativa — y la que casi no se estaba usando en la aplicación — es el `JOIN` entre tablas relacionadas (por ejemplo, `Estudiantes` con `Matriculas`). PostgREST permite algo parecido ("resource embedding"), pero solo cuando hay una clave foránea real declarada, siempre como una igualdad implícita, y sin posibilidad de subconsultas.

### 1.2 Objetivo

Añadir al constructor de consultas la posibilidad de combinar dos tablas ("cajas") en un `JOIN` real:

- Elegir una segunda tabla tras la principal.
- Que el sistema sugiera automáticamente la condición de unión cuando existe una clave foránea real entre ambas, pero permitiendo cambiarla a mano.
- Elegir tipo de `JOIN` (`INNER` / `LEFT` / `RIGHT`), columnas de ambas tablas, filtro y orden.
- Ejecutar la consulta como SQL real contra PostgreSQL (no una simulación vía REST), respetando los mismos permisos de lectura por tabla que ya existían.

Quedó fuera de esta primera fase el soporte de subconsultas (`WHERE col IN (SELECT ...)`), pensado como ampliación futura sobre la misma base.

## 2. Explicación no técnica

Hasta ahora, el constructor de consultas era como pedir datos de un único archivador. La idea nueva es poder coger **dos archivadores** (dos tablas) y decirle al sistema "júntalos por esta columna que tienen en común" — por ejemplo, unir la ficha de cada estudiante con sus matrículas, usando el número de matrícula como punto de unión. El resultado es una única tabla combinada con columnas de ambos archivadores.

Para que sea sencillo de construir sin saber SQL, el asistente:

1. Detecta solo si hay una relación ya definida en la base de datos entre las dos tablas elegidas (una clave foránea) y propone esa columna de unión automáticamente.
2. Deja cambiarla a mano si se quiere explorar una unión distinta, con fines didácticos.
3. Va enseñando en todo momento el SQL real equivalente a lo que se está construyendo, para relacionar la interacción visual con la sintaxis SQL que representa.

## 3. Decisiones de diseño

**Ejecución como SQL real en vez de seguir usando PostgREST.** PostgREST no soporta `JOIN` con condición arbitraria ni subconsultas por API REST — solo "resource embedding" ligado a una clave foránea existente y con igualdad implícita. Como el objetivo del constructor es justamente enseñar cómo se forma un `JOIN`, se optó por añadir un endpoint propio en Flask (`POST /api/query/join`) que construye y ejecuta el `SELECT ... JOIN ...` de verdad contra PostgreSQL.

**No perder el control de permisos por tabla al saltarse PostgREST.** El resto de la aplicación (ver `permisos-dinamicos-por-tabla.md`) hace cumplir los permisos de lectura/escritura por tabla mediante roles reales de PostgreSQL, comprobados por PostgREST vía JWT. Como este nuevo endpoint ejecuta SQL directamente con `psycopg2` (sin pasar por PostgREST), se detectó que la conexión de Flask a la base de datos (`get_db_connection()`) usa el superusuario `postgres` — si el `JOIN` se ejecutara tal cual con esa conexión, cualquier usuario podría leer una tabla para la que no tiene permiso, saltándose todo el sistema construido previamente. Se resolvió haciendo `SET ROLE app_user_<id>` justo antes de ejecutar la consulta, de modo que PostgreSQL aplica exactamente los mismos `GRANT`/`REVOKE` que ya existían — si el usuario no tiene `SELECT` concedido sobre alguna de las dos tablas, la consulta falla con un `403`, igual que le pasaría a través de PostgREST.

**Validación de identificadores contra el catálogo real, no contra lo que envía el navegador.** Todo nombre de tabla o columna que llega desde el frontend (tablas, columnas, columna de unión, columna del `WHERE`/`ORDER BY`) se comprueba contra `information_schema` antes de usarse para construir SQL, y se ensambla con `psycopg2.sql.Identifier` (nunca concatenando texto). Los valores de filtro (`WHERE ... = valor`) van siempre parametrizados. Es el mismo patrón de seguridad que ya se usaba en `admin_create_table`.

**Alias de columnas cortos salvo colisión de nombres.** La primera versión etiquetaba siempre cada columna del resultado como `tabla.columna` para evitar ambigüedad cuando dos tablas comparten un nombre de columna. En la práctica, la mayoría de columnas no colisionan, y esos alias largos desbordaban las celdas de la tabla de resultados (pensada para nombres cortos), solapando el texto de columnas contiguas. Se cambió a anteponer el nombre de tabla **solo cuando dos columnas seleccionadas comparten el mismo nombre**; en el resto de casos se usa el nombre corto de siempre.

**Wizard dividido por tabla en cada paso, no combinado.** Un primer intento mostraba en una sola pantalla las columnas de ambas tablas juntas (hasta 12 botones). Con listas tan largas, las filas inferiores quedaban fuera del área visible del constructor (pensado para listas cortas de una sola tabla, como el resto de la aplicación). Se resolvió separando cada paso por tabla (columnas de la tabla principal → columnas de la segunda tabla), manteniendo listas siempre cortas, y reduciendo el ancho de los botones de `WHERE`/`ORDER BY` por el mismo motivo.

**Tabla de resultados anclada por la izquierda si hay muchas columnas.** El panel fijo de "CONTROLES" (paginación) y el gráfico 3D rotatorio de la escena de resultados están en posiciones fijas, pensadas para una tabla de pocas columnas centrada en su sitio. Un resultado de `JOIN` con muchas columnas seleccionadas hacía que el borde izquierdo de la tabla invadiera esos paneles. Se cambió el cálculo de posición para que, a partir de cierto ancho, la tabla deje de centrarse y se ancle por la izquierda, creciendo solo hacia la derecha (sin paneles fijos en esa zona).

## 4. Arquitectura

```
Navegador (constructor de consultas)
   │  1. elige tabla A
   │  2. ¿segunda tabla? → elige tabla B
   │       GET /api/schema/relations  (¿hay FK real entre A y B?)
   │  3. confirma condición de unión y tipo de JOIN
   │  4. columnas de A, columnas de B, WHERE, ORDER BY opcionales
   │  5. ejecutar
   ▼
POST /api/query/join  (Flask)
   │  - valida tablas/columnas contra information_schema
   │  - construye SQL con psycopg2.sql (identificadores) + parámetros (valores)
   │  - SET ROLE app_user_<id>   ←── mismo rol de Postgres que usa PostgREST
   ▼
PostgreSQL  (aplica los GRANT/REVOKE ya existentes sobre app_user_<id>)
```

Para las consultas de una sola tabla (sin `JOIN`) no cambia nada: se sigue usando PostgREST tal cual, como hasta ahora.

## 5. Cambios técnicos por capa

### 5.1 Backend — `https_server.py`

- `_get_table_columns(cur, table_name)`: columnas reales de una tabla desde `information_schema.columns`.
- `_get_foreign_keys(cur)`: relaciones de clave foránea entre tablas públicas (`information_schema.table_constraints` + `key_column_usage` + `constraint_column_usage`), excluyendo las tablas internas del sistema.
- `GET /api/schema/relations`: expone esas relaciones al frontend para sugerir la columna de unión.
- `POST /api/query/join`: recibe `{tableA, tableB, joinType, onA, onB, columns, where, orderBy}`, valida cada identificador contra el catálogo real, construye el `SELECT ... JOIN ... ON ...` con `psycopg2.sql`, ejecuta con `SET ROLE app_user_<id>` y devuelve `{sql, data}`. Los alias de columna solo incluyen el nombre de tabla cuando hay colisión de nombres entre las columnas seleccionadas. Errores de permiso de PostgreSQL (`psycopg2.errors.InsufficientPrivilege`) se traducen a `403` con un mensaje claro.

### 5.2 Frontend — `index.html`

- `queryState` ampliado con `join` (`{table, type, onA, onB, auto}` o `null`) y `joinColumns`.
- Nuevos pasos del wizard: 2.5 (¿segunda tabla?), 2.6/2.7 (columna de unión manual, solo si no se detectó FK), 2.8 (confirmar tipo de `JOIN` y condición), 3 y 3.5 (columnas de cada tabla, una pantalla por tabla), y variantes de los pasos 4 (`WHERE`) y 5 (`ORDER BY`) con selector de tabla.
- `getForeignKeys()` / `findJoinColumns()`: caché en memoria de `GET /api/schema/relations` y búsqueda de la relación entre las dos tablas elegidas, en cualquier dirección.
- `actualizarDisplaySQL()`: genera el texto SQL de vista previa (`SELECT ... FROM a JOIN b ON ... WHERE ... ORDER BY ...`) cuando hay un `JOIN` activo.
- `qb_ejecutar()`: si `queryState.join` está activo, hace `POST /api/query/join`; si no, sigue usando PostgREST exactamente igual que antes.
- `offsetXTabla()`: nueva función compartida por `renderizarTabla2D`/`renderizarTabla3D` para anclar la tabla de resultados por la izquierda cuando el número de columnas no cabe centrado sin invadir los paneles fijos de la escena.

## 6. Verificación realizada

Probado de forma guiada, en el navegador, sobre datos reales (`Estudiantes` / `Matriculas`, con clave foránea `Matriculas.Matricula → Estudiantes.Matricula`):

| Prueba | Resultado esperado | Resultado obtenido |
|---|---|---|
| `Estudiantes` + `Matriculas`, condición sugerida automáticamente | Salta directo a "confirmar JOIN" con `estudiantes.matricula = matriculas.matricula` | Correcto |
| Cambiar la condición de unión a mano ("CAMBIAR COLUMNAS") | Permite re-elegir columna de cada tabla | Correcto |
| Ciclar tipo de JOIN (`INNER` → `LEFT` → `RIGHT`) | El botón de control cambia de etiqueta y de tipo | Corregido tras un primer intento en el que el botón quedaba fuera de la fila de controles (ver incidencias) |
| Ejecutar sin filtros | Devuelve varias filas combinadas | Correcto |
| Seleccionar "TODAS LAS COLUMNAS" (12 columnas de ambas tablas) | Tabla de resultados legible, sin solapar el panel de controles | Corregido tras el primer intento (ver incidencias) |
| Selección manual de columnas de la segunda tabla | Deben aparecer las columnas de `Matriculas`, no solo las de `Estudiantes` | Corregido tras el primer intento (ver incidencias) |

## 7. Incidencias encontradas durante el desarrollo

- **Conexión de Flask como superusuario de Postgres**: de no corregirse, el nuevo endpoint habría podido leer cualquier tabla sin respetar los permisos por usuario ya implementados. Resuelto con `SET ROLE app_user_<id>` antes de ejecutar la consulta (ver apartado 3).
- **Botón de tipo de JOIN inalcanzable**: el paso de confirmación llegó a tener 4 botones de control (tipo, cambiar columnas, continuar, cancelar) cuando el resto de la aplicación nunca pasa de 3; el conjunto se salía del ancho previsto para esa fila. Se movió "cambiar columnas" al área de opciones grandes, dejando 3 controles como en el resto del wizard.
- **Cabeceras de columna solapadas**: los alias `tabla.columna` en todas las columnas del resultado eran más anchos que las celdas de la tabla (pensada para nombres cortos). Resuelto acotando el alias con tabla solo a los casos de colisión real de nombres (apartado 3).
- **Selector de columnas mostrando solo la tabla principal**: al combinar las columnas de ambas tablas en una única pantalla (hasta 12 botones), las filas correspondientes a la segunda tabla quedaban fuera del área visible del constructor. Resuelto separando el paso en dos pantallas, una por tabla.
- **Tabla de resultados invadiendo el panel de controles**: con muchas columnas seleccionadas, el borde izquierdo de la tabla (centrada por defecto) llegaba a solaparse con el panel fijo de paginación y el gráfico 3D de la escena. Resuelto anclando la tabla por la izquierda a partir de cierto ancho (apartado 3).

## 8. Archivos creados o modificados

- `https_server.py` — helpers de catálogo (`_get_table_columns`, `_get_foreign_keys`), endpoints `GET /api/schema/relations` y `POST /api/query/join`.
- `index.html` — nuevos pasos del wizard para JOIN, lógica de ejecución contra el nuevo endpoint, ajuste del renderizado de la tabla de resultados para anchos grandes.

## 9. Trabajo futuro

- **Subconsultas** (`WHERE columna IN (SELECT ...)`): construir la subconsulta anidando el mismo asistente, reutilizando `POST /api/query/join` como base.
- **Interacción por gestos en VR**: en vez de (o además de) el asistente por pasos actual, permitir con los mandos de las gafas "arrastrar" el bloque de una tabla sobre el de otra para generar el JOIN, con una animación de las dos cajas uniéndose en un cubo — idea propuesta por el usuario tras ver funcionando la versión por pasos, pendiente de diseñar y valorar cómo determinar la condición de unión en una interacción de arrastre (¿FK automática igual que ahora? ¿un segundo gesto para elegir columnas?).
- Formulario en la interfaz para editar permisos de un usuario ya existente (heredado de la funcionalidad de permisos dinámicos, sigue pendiente).
