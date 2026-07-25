# Eliminar tablas (DROP TABLE) desde el constructor de consultas

Documento resumen de la funcionalidad implementada, pensado para incorporarse a la memoria del TFG. Incluye una explicación no técnica del problema y la solución, y el detalle técnico de la implementación en cada capa del sistema.

## 1. Contexto y objetivo

### 1.1 Punto de partida

El constructor de consultas guiadas (VR) ya permitía, para el rol `admin`, crear tablas nuevas (`CREATE TABLE`) desde dentro de la aplicación. No existía ninguna forma de eliminarlas: si se creaba una tabla de más o por error, había que entrar a pgAdmin y borrarla a mano.

### 1.2 Objetivo

Añadir una operación `DROP TABLE` al constructor de consultas, pero **solo accesible para quien deba tener ese poder** — no para cualquiera que tenga permiso de escritura sobre los datos de una tabla.

## 2. Explicación no técnica

Siguiendo la misma analogía de llaves y habitaciones ya usada en el documento de permisos por tabla:

- Tener la llave de "lectura y escritura" de una habitación (una tabla) te deja **entrar, mirar y reorganizar los muebles** — es decir, leer y modificar los datos que hay dentro.
- Eso **no** es lo mismo que tener la llave para **derribar la habitación entera**. Un profesor con permiso de escritura sobre "matrículas" puede insertar y editar matrículas, pero eso no debería darle poder para hacer desaparecer la tabla "matrículas" del edificio entero, con las consecuencias que tendría para todos los demás usuarios.
- Por eso se creó un permiso nuevo y distinto, "poder derribar habitaciones" (`admin_drop_table`), que solo se le entrega al rol `admin` — nunca se deriva automáticamente de tener escritura sobre los datos.

En la práctica: en el constructor de consultas VR aparece una nueva opción "DROP TABLE" (solo si el usuario tiene ese permiso), se elige la tabla de una lista, y aparece una pantalla de confirmación en rojo avisando de que la acción es irreversible antes de ejecutarla.

## 3. Decisiones de diseño

**Separación entre permiso de esquema y permiso de datos.** El sistema de permisos por tabla (`user_table_permissions`, ver [[tfg-progreso-permisos-dinamicos]]) controla operaciones de **datos** (`SELECT`/`INSERT`/`UPDATE`/`DELETE` sobre filas, vía PostgREST). Eliminar una tabla es una operación de **esquema** (DDL), conceptualmente distinta: se decidió modelarla como un permiso de aplicación aparte (`admin_drop_table` en la tabla `permissions`, el mismo mecanismo que ya protegía `admin_create_table`), en vez de derivarla del flag `can_write` de una tabla. Así, ampliar la escritura de datos de un profesor nunca le concede, como efecto colateral, la capacidad de borrar tablas.

**Restricción a un único rol.** A diferencia de `can_read`/`can_write`, que se conceden tabla por tabla y usuario por usuario, `admin_drop_table` es binario y solo lo tiene `admin`. No se contempló (de momento) un modelo más granular tipo "este profesor puede borrar solo sus propias tablas", por no ser necesario para el alcance actual del TFG.

**Protección de las tablas internas.** Se reutilizó la misma lista `EXCLUDED_TABLES` (`users`, `permissions`, `role_default_tables`, `user_table_permissions`) que ya impedía conceder acceso a esas tablas desde el panel de administración, esta vez para impedir también que se puedan eliminar — evitando que un fallo de la propia interfaz pueda destruir el sistema de login y permisos.

**Validación contra el catálogo real antes de borrar**: igual que en el constructor de JOINs (ver [[tfg-progreso-joins-constructor]]), el nombre de tabla recibido del cliente se comprueba contra `information_schema.tables` antes de ejecutar el `DROP`, y se ensambla con `psycopg2.sql.Identifier` en vez de concatenar texto.

## 4. Cambios técnicos por capa

### 4.1 Base de datos — `initdb/003-drop-table-permission.sql`

Inserta el permiso `admin_drop_table` para el rol `admin` en la tabla `permissions` ya existente (mismo patrón que `admin_manage_users` en la migración anterior). Idempotente (`DO $$ ... IF NOT EXISTS`), y aplicado ya a mano contra la base de datos actual (los `initdb/*.sql` solo se ejecutan automáticamente en un volumen de Postgres vacío).

### 4.2 Backend — `https_server.py`

`POST /api/admin/drop_table`, protegido con `@require_auth` + `@require_permission('admin_drop_table')`:

1. Valida que `table_name` es un identificador seguro (alfanumérico + guión bajo).
2. Rechaza con `403` si la tabla está en `EXCLUDED_TABLES`.
3. Comprueba que la tabla existe realmente en `information_schema` (vía `_get_public_tables`, ya usada por `/api/admin/tables`); si no, `404`.
4. Ejecuta `DROP TABLE` con el nombre de tabla ensamblado vía `psycopg2.sql.Identifier` (no concatenación de strings) y hace `commit()`.

### 4.3 Frontend — `index.html`

- Nueva opción "DROP TABLE" en el paso 1 del constructor de consultas, visible solo si `tienePermiso("admin_drop_table")`.
- Paso 2: selector de tabla, cargado en vivo desde `/api/admin/tables` (todas las tablas del sistema, no solo las que el usuario tiene concedidas para datos — es un permiso de esquema, no de datos).
- Paso 3: pantalla de confirmación en rojo ("⚠ CONFIRMAR ELIMINACIÓN") con aviso de que la acción es irreversible, antes de ejecutar.
- `qb_drop_exec()`: hace `POST` a `/api/admin/drop_table` con el nombre de tabla elegido.

## 5. Verificación realizada

Se probó con el cliente de pruebas de Flask (`test_client`, sesión simulada, sin depender de contraseñas reales):

| Prueba | Usuario / rol | Resultado esperado | Resultado obtenido |
|---|---|---|---|
| Crear tabla de prueba | `admin` | Se crea | `200 OK` |
| Listar tablas tras crear | `admin` | Aparece la tabla nueva | Correcto |
| Borrar tabla del sistema (`users`) | `admin` | Rechazado | `403`, "tabla interna del sistema" |
| Borrar tabla de prueba real | `admin` | Se elimina | `200 OK` |
| Listar tablas tras borrar | `admin` | Ya no aparece | Correcto |
| Intentar borrar tabla | `estudiante` (sin el permiso) | Rechazado | `403`, `PERMISSION_DENIED` |

Adicionalmente se reprodujo el flujo completo desde la interfaz VR real (capturas de pantalla): se creó una tabla `rober` desde "CREATE TABLE" y se confirmó, comprobando con `psql` directamente contra el contenedor de Postgres (sin pasar por pgAdmin, para descartar caché de su árbol de objetos) que la tabla existía realmente y aparecía correctamente ordenada alfabéticamente en el selector de "DROP TABLE".

## 6. Archivos creados o modificados

- `initdb/003-drop-table-permission.sql` — nuevo.
- `https_server.py` — nuevo endpoint `POST /api/admin/drop_table`.
- `index.html` — nueva operación "DROP TABLE" en el constructor de consultas (pasos 1-3), acciones `qb_drop_tabla` / `qb_drop_exec`.

## 7. Trabajo futuro

- Si en algún momento se quisiera un modelo más granular (por ejemplo, que un profesor pueda borrar solo tablas que él mismo creó), haría falta registrar qué usuario creó cada tabla — no existe ese dato hoy.
