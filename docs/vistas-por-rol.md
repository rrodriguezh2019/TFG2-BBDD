# Vistas por rol (vista_estudiante / vista_profesor)

Documento resumen de la funcionalidad implementada, pensado para incorporarse a la memoria del TFG. Incluye una explicación no técnica del problema y la solución, y el detalle técnico de la implementación.

## 1. Contexto y objetivo

### 1.1 Punto de partida

El sistema de [permisos dinámicos por tabla](permisos-dinamicos-por-tabla.md) permite conceder a cada rol (`profesor`, `estudiante`) acceso de lectura y/o escritura tabla por tabla, mediante roles reales de PostgreSQL (`GRANT`/`REVOKE`). Ese modelo funciona bien mientras el permiso que se quiere dar es "toda la tabla o nada": no hay forma de conceder una tabla ocultando alguna columna concreta. Esto es un problema real en el esquema actual: la tabla `profesores` tiene una columna `Salario`, y no existe ninguna forma, con el sistema de permisos por tabla tal cual estaba, de dar acceso de lectura a `profesores` (por ejemplo, para que un estudiante vea qué profesor imparte una asignatura) sin exponer también el salario de ese profesor.

### 1.2 Objetivo

Añadir, junto a las tablas, un segundo tipo de recurso concedible por rol: **vistas** (`CREATE VIEW`), que combinan datos de varias tablas y seleccionan solo las columnas que tienen sentido para ese rol. Cada rol tiene una vista por defecto:

- `vista_estudiante`: asignaturas con el nombre del profesor que las imparte (sin `Salario`) y las matrículas/notas asociadas.
- `vista_profesor`: informe agregado por asignatura (número de alumnos matriculados y nota media), para no tener que recalcular ese agregado a mano cada vez en el constructor de consultas.

## 2. Explicación no técnica

Siguiendo la analogía de llaves y habitaciones del documento de permisos: hasta ahora, una llave de una habitación abría la habitación entera. Una **vista** es como una ventana practicada en la pared entre dos habitaciones: alguien sin llave de la habitación de "Profesores" puede asomarse por esa ventana y ver el nombre del profesor de una asignatura, pero la ventana está tapiada justo donde estaría la información del salario — nunca llega a verla, ni aunque quisiera, porque esa parte de la pared no tiene hueco.

Técnicamente esto es posible porque, en PostgreSQL, una vista "recuerda" quién la construyó y mira las habitaciones originales con las llaves de esa persona, no con las de quien se asoma por la ventana. Así, se le puede dar a un estudiante la llave de la ventana (`GRANT SELECT` sobre la vista) sin darle nunca la llave de la habitación de profesores.

## 3. Decisiones de diseño

### 3.1 Vistas normales, no materializadas

PostgreSQL ofrece dos tipos de vista: las **normales** (una consulta guardada, que se ejecuta entera cada vez que se consulta la vista) y las **materializadas** (el resultado se calcula una vez y se guarda físicamente; hay que pedir explícitamente un `REFRESH` para que se ponga al día).

Se optó por vistas normales por dos motivos:

1. **Los datos deben estar siempre al día.** Notas y matrículas cambian con el uso normal de la aplicación (un profesor pone una nota, se matricula un alumno). Con una vista materializada, esos cambios no se verían reflejados hasta el siguiente `REFRESH`, lo que obligaría a decidir cuándo refrescar (¿cada cambio? ¿con un cron?) — complejidad añadida sin necesidad real.
2. **No hay ganancia de rendimiento que lo justifique.** Con el volumen de datos actual (9 asignaturas, 9 profesores, 32 matrículas), la vista normal se ejecuta en milisegundos; una materializada solo compensa cuando la consulta subyacente es costosa de recalcular (agregados sobre millones de filas, por ejemplo), que no es el caso aquí.

Queda anotado como posible ampliación futura (no implementada): si en algún momento se quisiera mostrar un informe agregado realmente costoso de calcular, ahí sí tendría sentido usar una vista materializada con un `REFRESH` programado.

### 3.2 Vista igual para todos los usuarios del rol (no personalizada por usuario)

Se planteó la alternativa de que cada estudiante viera solo sus propias matrículas/notas (filtrado por fila, no solo por columna). No se implementó porque, en el esquema actual, **la tabla `users` no está enlazada con `estudiantes` ni con `profesores`** — no existe ninguna columna que diga "este usuario logueado es el estudiante con Matrícula=X". Añadir ese vínculo y el filtrado por fila (vía JWT) es una funcionalidad nueva no trivial, fuera del alcance de este cambio. Con el diseño actual, `vista_estudiante` es la misma para todos los estudiantes y sigue mostrando las matrículas de todos los alumnos, no solo las del usuario que consulta — queda anotado como mejora futura.

### 3.3 Vistas registradas en el mismo mecanismo que las tablas

En vez de crear un sistema de permisos aparte para vistas, se reutilizó `role_default_tables` (rol → recurso por defecto) y el `GRANT` genérico que ya existía en `https_server.py`, porque PostgreSQL trata el `GRANT SELECT` sobre una vista exactamente igual que sobre una tabla. La única pieza que faltaba era que el código de la aplicación, al listar "tablas concedibles", solo miraba `information_schema.tables` con `table_type = 'BASE TABLE'` (excluye vistas por definición). Se añadió una función paralela `_get_public_views()` y se sumó a los tres puntos donde se valida o se ofrece la lista (panel de admin, creación de usuario, edición de permisos) — sin tocar la validación de `DROP TABLE`, que debe seguir excluyendo vistas porque `DROP TABLE` no funciona sobre una vista.

## 4. Detalle técnico

- `initdb/004-role-views.sql`: define `vista_estudiante` y `vista_profesor` con `CREATE OR REPLACE VIEW`, e inserta ambas en `role_default_tables` (`can_write = FALSE`, son de solo lectura).
- `https_server.py`: nueva función `_get_public_views()`, sumada a `_get_public_tables()` en `/api/admin/tables`, `admin_create_user` y `admin_update_user_permissions`.
- Al igual que el resto de migraciones sobre una base de datos ya poblada, `004-role-views.sql` no se ejecuta solo (los scripts de `initdb/` solo corren automáticamente en un volumen de Postgres vacío) — se aplicó a mano desde el Query Tool de pgAdmin.

## 5. Incidencia encontrada: caché de esquema de PostgREST

Al probar la vista en la aplicación, no daba error visible pero tampoco mostraba ninguna fila. Dos causas se solaparon:

1. **PostgREST cachea el esquema de la base de datos al arrancar.** Como la vista se creó con una conexión aparte (pgAdmin) después de que el contenedor `postgrest_container` ya llevaba un rato levantado, PostgREST no sabía que `vista_profesor` existía y respondía con un error `404` (`PGRST205: Could not find the table 'public.vista_profesor' in the schema cache`). Se resolvió sin reiniciar el contenedor, simplemente notificando a PostgREST que recargase el esquema:
   ```sql
   NOTIFY pgrst, 'reload schema';
   ```
2. **El frontend capturaba ese error en silencio.** La función `cargarTabla()` de `index.html` envuelve la petición en un `try/catch` que, ante cualquier error, deja la tabla vacía (`datosActuales = []`) y solo registra el error en la consola del navegador (`console.error`), sin mostrar ningún aviso en la escena VR. Esto retrasó el diagnóstico: hubo que abrir las herramientas de desarrollador del navegador para ver el error real. Queda anotado como mejora futura (no implementada): mostrar ese error en la propia escena en vez de tragarlo.
