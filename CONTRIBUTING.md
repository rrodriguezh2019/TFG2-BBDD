# Guía de desarrollo

Esta guía explica cómo preparar un entorno de desarrollo y las convenciones que sigue el proyecto, para quien quiera modificarlo o entender cómo está organizado.

## Entorno de desarrollo

Sigue primero los pasos de puesta en marcha del [README](README.md#puesta-en-marcha). Para desarrollo, arranca solo los contenedores de base de datos y deja el servidor Flask corriendo en local (así los cambios en `https_server.py` o `index.html` se ven recargando el navegador, sin reconstruir nada):

```bash
docker compose up -d          # PostgreSQL + PostgREST + pgAdmin
source venv/bin/activate
python3 https_server.py       # sirve la app y hace de proxy hacia PostgREST
```

pgAdmin queda disponible en `http://localhost:5050` para inspeccionar la base de datos directamente (usuario/contraseña en las variables de entorno `PGADMIN_DEFAULT_*` de `docker-compose.yml`).

Para partir de una base de datos limpia durante el desarrollo:

```bash
docker compose down -v        # borra también el volumen de datos
docker compose up -d          # vuelve a ejecutar todo initdb/ desde cero
```

## Arquitectura, en resumen

```
navegador ── HTTPS ── https_server.py (Flask) ── HTTP ── PostgREST ── PostgreSQL
```

- **`index.html`** es todo el frontend: la escena A-Frame, la UI 2D y VR, y la lógica de cliente (fetch a la API, construcción de la escena 3D). No hay build step ni bundler: es un único fichero servido tal cual.
- **`https_server.py`** hace tres cosas: sirve `index.html` y los estáticos, gestiona login/sesión/JWT, y expone endpoints propios (administración de usuarios, JOIN entre tablas) que no puede resolver PostgREST directamente.
- **PostgREST** resuelve directamente las consultas simples sobre una sola tabla, autenticando cada petición mediante el JWT que genera Flask.
- **`initdb/`** son los scripts SQL que arrancan la base de datos desde cero (ver más abajo) — es la única fuente de verdad del esquema; no hay migraciones a mano contra un entorno en marcha.

Si quieres más detalle de cómo funciona una pieza concreta antes de tocarla, mira si ya existe una nota en `docs/` (ver el README) o la sección correspondiente de la [memoria](https://github.com/rrodriguezh2019/MemoriaTFG-RobertoRodriguez).

## Convenciones del proyecto

- **Nombres en español**: funciones, variables y comentarios están en español en todo el proyecto (`crearBoton`, `aplicarEntorno`, `hash_password`...). Mantén el mismo idioma al añadir código nuevo.
- **Sin dependencias de build en el frontend**: `index.html` no pasa por ningún compilador ni bundler. Evita introducir uno salvo que sea imprescindible.
- **Todo cambio de esquema va en `initdb/`**, nunca a mano contra una base de datos en marcha. Los scripts se numeran por orden de ejecución (`000-`, `001-`...) y deben ser **idempotentes**: usa `CREATE TABLE IF NOT EXISTS`, `ON CONFLICT DO NOTHING` o bloques `DO $$ IF NOT EXISTS (...) THEN ... END IF; END $$;`, de forma que se puedan volver a ejecutar sobre una base de datos que ya tiene los datos sin duplicar nada ni fallar. Añade un script nuevo con el siguiente número si necesitas cambiar el esquema; no edites uno ya aplicado si ya hay entornos usándolo.
- **Nombres de tabla en las peticiones dinámicas** (permisos, JOIN) deben validarse siempre contra `information_schema` antes de usarse en una consulta -nunca insertes directamente en SQL algo que venga del cliente sin pasar por esa validación.
- **Cualquier endpoint nuevo que devuelva datos de una tabla debe respetar el sistema de permisos**: si no pasa por PostgREST (como el JOIN), haz `SET ROLE` al rol de PostgreSQL del usuario (`pg_role_for_user`) antes de ejecutar la consulta, para que los `GRANT`/`REVOKE` reales se apliquen igual que en cualquier otra petición.

## Pruebas

No hay una suite de tests automatizados formal; la validación funcional se hace con un navegador Chrome en modo *headless* simulando login y acciones reales (ver la sección de metodología de pruebas en la memoria). Antes de dar por buen un cambio:

1. Prueba el flujo afectado en un navegador de escritorio.
2. Si el cambio toca la escena 3D, el teclado virtual o cualquier interacción por rayo, pruébalo también en un dispositivo real (Meta Quest o móvil en AR) si tienes acceso a uno -varios bugs de este proyecto solo se manifestaron en dispositivo real, nunca en escritorio.
3. Si el cambio toca permisos, compruébalo con al menos dos usuarios de rol distinto.

## Cómo proponer un cambio

1. Crea una rama a partir de `main` (`git checkout -b nombre-descriptivo`).
2. Haz commits pequeños y descriptivos.
3. Abre un Pull Request describiendo qué cambia y por qué, y qué has probado.

## Reportar un problema

Abre un [Issue](https://github.com/rrodriguezh2019/TFG2-BBDD/issues) describiendo qué esperabas que pasara, qué pasó en realidad, y los pasos para reproducirlo (incluyendo si ocurre en escritorio, VR o AR).
