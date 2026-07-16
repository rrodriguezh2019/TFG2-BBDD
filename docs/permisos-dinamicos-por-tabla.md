# Sistema de permisos dinámicos por tabla (lectura / escritura)

Documento resumen de la funcionalidad implementada, pensado para incorporarse a la memoria del TFG. Incluye una explicación no técnica del problema y la solución, y el detalle técnico de la implementación en cada capa del sistema.

## 1. Contexto y objetivo

### 1.1 Punto de partida

La aplicación permitía iniciar sesión con una serie de usuarios ya cargados en la base de datos a modo de prueba, cada uno con un **rol fijo** (`admin`, `user`) que determinaba qué acciones podía realizar dentro de la aplicación (crear tablas, borrar estudiantes, etc.). Sin embargo, esa comprobación de permisos ocurría **únicamente en la aplicación web** (Flask): la lectura de datos de las tablas se hacía mediante una segunda vía, PostgREST, que exponía **todas las tablas de la base de datos con lectura pública**, sin ningún tipo de autenticación. Es decir, cualquiera que conociera la URL de PostgREST podía leer todos los datos, independientemente de si había iniciado sesión o no.

Tampoco existía manera de crear usuarios nuevos desde la propia aplicación: los únicos usuarios disponibles eran los que se habían insertado manualmente en la base de datos para hacer pruebas.

### 1.2 Objetivo

Añadir a la aplicación la capacidad de **crear usuarios de forma dinámica**, cada uno con:

- Permisos de **lectura** o **lectura + escritura**, configurables tabla por tabla.
- **Roles** (por ejemplo, "profesor" o "estudiante") que proponen automáticamente un conjunto de tablas por defecto con sentido para ese perfil, pero que el administrador puede ampliar o modificar antes de crear el usuario.

Y, de forma añadida (decisión tomada durante el diseño, ver apartado 3), que esos permisos se hagan cumplir **en la propia base de datos**, no solo en la aplicación — de modo que, aunque alguien se saltase la interfaz web, la base de datos siga rechazando lo que no está autorizado.

## 2. Explicación no técnica

Puede pensarse en una analogía de llaves y habitaciones:

- Cada **tabla** de la base de datos es como una habitación de un edificio (Estudiantes, Profesores, Asignaturas...).
- Cada **usuario** recibe un llavero con las llaves de las habitaciones a las que tiene acceso, y cada llave puede ser "solo para mirar" (lectura) o "para mirar y modificar" (lectura + escritura).
- Antes de este cambio, había un guardia en la puerta principal (la aplicación web) que revisaba las llaves — pero había una puerta trasera (PostgREST) sin ningún guardia, por la que se podía entrar a cualquier habitación sin llave.
- Ahora, es el **propio edificio** (la base de datos PostgreSQL) el que tiene cerraduras reales en cada puerta, y solo abre con la llave correcta. Da igual por qué puerta se entre: si no tienes la llave, no entras.
- Los **roles** ("profesor", "estudiante") son llaveros predefinidos con una selección razonable de llaves ya hecha de antemano, para no tener que elegir una a una cada vez — pero el administrador puede añadir o quitar llaves sueltas a un llavero concreto si ese usuario necesita algo distinto de lo habitual en su perfil.

El resultado práctico: desde un panel dentro de la propia aplicación (visible solo para el administrador), se puede crear un usuario nuevo eligiendo su rol y las tablas a las que debe tener acceso, con casillas independientes de "lectura" y "escritura" por tabla.

## 3. Decisiones de diseño

**¿Por qué hacer cumplir los permisos en la base de datos y no solo en la aplicación?**

La alternativa más simple habría sido comprobar los permisos únicamente dentro de Flask (como ya se hacía con los permisos por acción, tabla `permissions`). Se decidió ir un paso más allá y usar el propio sistema de roles y privilegios de PostgreSQL (`ROLE`, `GRANT`, `REVOKE`) combinado con autenticación JWT en PostgREST, por dos motivos:

1. **Defensa en profundidad**: el control de acceso no depende de que ninguna ruta de la aplicación se le olvide comprobar un permiso — la base de datos rechaza la operación aunque se la pida directamente.
2. Es coherente con el enfoque de un TFG de bases de datos: se aprovecha el propio motor de la BD como mecanismo de seguridad, en lugar de reimplementar ese control solo en la capa de aplicación.

**Separación entre "permisos por defecto de un rol" y "permisos reales de un usuario"**: se crearon dos tablas distintas (`role_default_tables` y `user_table_permissions`) en lugar de una sola, para poder ofrecer una plantilla por rol reutilizable sin atar cada usuario a lo que diga su rol — cada usuario tiene su propia fila de permisos, que se inicializa a partir de la plantilla de su rol pero es completamente editable después.

**Exclusión explícita de las tablas internas** (`users`, `permissions`, `role_default_tables`, `user_table_permissions`): estas tablas nunca aparecen como opción concedible en el panel de administración, porque `users` contiene las contraseñas (en forma de hash) de todos los usuarios — concederle acceso de lectura a alguien por error sería una fuga de seguridad grave.

## 4. Arquitectura

### 4.1 Antes

```
Navegador ──(login, sesión Flask)──> Flask ──> Postgres
Navegador ──(sin autenticar)────────────────> PostgREST ──(rol web_anon: SELECT en todo)──> Postgres
```

### 4.2 Después

```
Navegador ──(login)──> Flask ──> Postgres
   │                      │
   │                      └─ genera un JWT con el rol de Postgres del usuario (claim "role": "app_user_<id>")
   │
   └─(peticiones de datos, con el JWT)──> PostgREST ──(SET ROLE app_user_<id>)──> Postgres
                                                              │
                                                              └─ solo puede hacer lo que se le
                                                                 concedió con GRANT a ese rol
```

Cada usuario de la aplicación tiene ahora un **rol real de PostgreSQL** asociado (`app_user_<id>`), sin capacidad de iniciar sesión por sí mismo (`NOLOGIN`) pero delegable por el usuario técnico `authenticator` que usa PostgREST. El JWT que Flask entrega al hacer login le dice a PostgREST a qué rol cambiar (`SET ROLE`) en cada petición; ese rol solo tiene los privilegios (`SELECT`, y opcionalmente `INSERT`/`UPDATE`/`DELETE`) que se le hayan concedido tabla por tabla.

El acceso anónimo (rol `web_anon`) que antes daba lectura pública a todo se ha revocado por completo.

## 5. Cambios técnicos por capa

### 5.1 Base de datos — `initdb/002-user-table-permissions.sql`

- `role_default_tables(role_name, table_name, can_write)`: plantilla de tablas por defecto para cada rol. Sembrada con `profesor` (lectura+escritura en Asignaturas y Matrículas, lectura en Estudiantes y Profesores) y `estudiante` (lectura en Estudiantes, Asignaturas y Matrículas).
- `user_table_permissions(user_id, table_name, can_read, can_write)`: permisos reales y efectivos de cada usuario, con clave primaria compuesta `(user_id, table_name)`.
- Se añadió el permiso de aplicación `admin_manage_users` al rol `admin` en la tabla `permissions` ya existente, reutilizando el mecanismo de permisos por ruta que ya tenía la aplicación.
- Durante las pruebas se descubrió que la tabla `users` tenía una **clave foránea** (`users_role_fkey`) hacia una tabla `roles` preexistente no documentada: fue necesario dar de alta los roles nuevos (`profesor`, `estudiante`) en esa tabla antes de poder crear usuarios con esos roles.

### 5.2 Roles y privilegios de PostgreSQL

Al crear un usuario o modificar sus permisos, la aplicación ejecuta (con la misma conexión de administrador que ya se usaba para la función de crear tablas):

```sql
CREATE ROLE app_user_<id> NOLOGIN;
GRANT app_user_<id> TO authenticator;
GRANT SELECT ON <tabla> TO app_user_<id>;                       -- si tiene lectura
GRANT INSERT, UPDATE, DELETE ON <tabla> TO app_user_<id>;       -- si tiene escritura
```

Se aplicó también de forma retroactiva a los dos usuarios que ya existían antes de este cambio (`admin`: acceso total; el usuario con rol `user`: solo lectura), para que no perdieran acceso al activar el nuevo sistema.

Por último, se revocó el acceso público:

```sql
REVOKE SELECT ON ALL TABLES IN SCHEMA public FROM web_anon;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT ON TABLES FROM web_anon;
```

### 5.3 PostgREST (`docker-compose.yml`)

Se añadió `PGRST_JWT_SECRET` al servicio `postgrest`, con el mismo secreto que usa Flask para firmar los tokens. Es lo que le permite a PostgREST verificar el JWT recibido y decidir a qué rol de Postgres cambiar en cada petición.

### 5.4 Backend — `https_server.py`

- `generar_jwt(user_id)`: crea un JWT (librería `PyJWT`) con el claim `role: app_user_<id>` y caducidad de 8 horas (igual que la sesión de Flask). Se emite en `/login` y se puede volver a pedir en `GET /api/token` (necesario porque el token vive solo en memoria del navegador y se pierde al recargar la página, mientras que la sesión de Flask sigue siendo válida).
- `GET /api/admin/tables`: lista de tablas disponibles para conceder (excluyendo las internas del sistema).
- `GET /api/admin/roles`: tablas por defecto de cada rol, para precargar el formulario de creación de usuario.
- `GET /api/my-tables`: tablas accesibles del usuario autenticado, con sus permisos de lectura/escritura — sustituye a la lista de tablas que antes estaba fija en el código del frontend.
- `POST /api/admin/users`: crea el usuario, su rol de PostgreSQL y aplica los `GRANT` correspondientes.
- `PUT /api/admin/users/<id>/permissions`: permite modificar más adelante los permisos de un usuario ya creado (aplicando los `GRANT`/`REVOKE` a juego). Implementado pero, de momento, sin botón en la interfaz — solo accesible por API.
- Todos los endpoints de administración están protegidos con el mismo decorador `require_permission('admin_manage_users')` que ya usaba la aplicación para otras acciones restringidas.
- Los nombres de tabla y de rol que llegan del cliente se validan (solo alfanumérico y guión bajo, y comprobación de que la tabla existe realmente en `information_schema.tables`) antes de usarse en sentencias SQL dinámicas (`GRANT`/`REVOKE`/`CREATE ROLE`), para evitar inyección SQL.

### 5.5 Frontend — `index.html`

- La lista de tablas mostrada en el menú ya no es una lista fija en el código: se carga tras el login desde `/api/my-tables`.
- Se centralizaron en una función `postgrestFetch()` todas las llamadas directas a PostgREST, que ahora incluyen la cabecera `Authorization: Bearer <jwt>`.
- Nuevo panel de administración ("👥 Gestionar usuarios"), visible solo para el rol `admin`: formulario con usuario/contraseña, desplegable de rol (que precarga las tablas por defecto de ese rol) y una lista de tablas con casillas independientes de lectura y escritura, editable antes de confirmar la creación.

## 6. Verificación realizada

Se probó cada capa por separado antes de dar por buena la funcionalidad completa:

| Prueba | Usuario / rol | Resultado esperado | Resultado obtenido |
|---|---|---|---|
| Leer tabla concedida | `roberto` (estudiante) → `estudiantes` | Devuelve datos | `200 OK`, datos reales |
| Leer tabla no concedida | `roberto` (estudiante) → `profesores` | Rechazado | `403 Forbidden`, `permission denied for table profesores` |
| Escribir en tabla de solo lectura | `roberto` (estudiante) → `INSERT` en `asignaturas` | Rechazado | `403 Forbidden`, `permission denied for table asignaturas` |
| Acceso sin token (anónimo) | — | Rechazado | `401 Unauthorized`, `permission denied` |
| Acceso de administrador | `admin` | Acceso total, sin regresión | Correcto |
| Acceso de usuario preexistente | `juan` (rol `user`) | Sigue funcionando en modo solo lectura | Correcto |

Estas pruebas se hicieron directamente contra PostgREST con `curl`, sin pasar por la interfaz gráfica, precisamente para comprobar que la restricción la impone la base de datos y no únicamente la interfaz.

## 7. Incidencias encontradas durante el desarrollo

- **Clave foránea no documentada** (`users.role → roles.role_name`): impidió crear el primer usuario con rol `estudiante` hasta dar de alta ese rol en la tabla `roles`.
- **Mixed Content (HTTPS → HTTP)**: la aplicación se sirve por HTTPS pero PostgREST corría por HTTP sin cifrar; el navegador bloqueaba las peticiones por política de contenido mixto. Se solucionó para el entorno de pruebas desactivando esa protección en el navegador (`about:config` → `security.mixed_content.block_active_content`); queda pendiente como mejora una solución definitiva (ver apartado 8).
- **Dirección IP obsoleta**: la URL de PostgREST estaba escrita con una IP local que había cambiado desde que se escribió el código original; se actualizó a la IP actual del equipo.

## 8. Archivos creados o modificados

- `initdb/002-user-table-permissions.sql` — nuevo.
- `docker-compose.yml` — añadido `PGRST_JWT_SECRET` al servicio `postgrest`.
- `https_server.py` — generación de JWT, roles de Postgres dinámicos, nuevos endpoints de administración.
- `index.html` — tablas dinámicas, cabecera JWT en las llamadas a PostgREST, panel de administración de usuarios.

## 9. Trabajo futuro

- Añadir a la interfaz un formulario para editar los permisos de un usuario ya existente (el endpoint `PUT /api/admin/users/<id>/permissions` ya está implementado).
- Hacer que Flask actúe de proxy hacia PostgREST, de modo que todo el tráfico pase por el mismo origen HTTPS y no dependa de la configuración del navegador ni de una IP fija.
