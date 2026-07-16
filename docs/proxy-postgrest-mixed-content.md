# Proxy de Flask hacia PostgREST (solución al bloqueo de "Mixed Content")

Documento resumen de este cambio, para incorporar a la memoria del TFG. Complementa a [`permisos-dinamicos-por-tabla.md`](./permisos-dinamicos-por-tabla.md), donde ya se apuntaba este problema como trabajo futuro.

## 1. El problema

La aplicación se sirve por **HTTPS** (`https_server.py` usa un certificado propio, `certs/babia_cert.pem`), pero las llamadas a PostgREST desde el navegador se hacían directamente a `http://<ip-local>:3000`, es decir, **HTTP sin cifrar**. Los navegadores modernos bloquean por defecto que una página cargada por HTTPS haga peticiones activas (como `fetch`) a un destino HTTP — esta protección se llama **"Mixed Content"** — precisamente porque esa mezcla es un punto débil típico: un atacante en la misma red podría interceptar o manipular esa parte del tráfico sin que el candado de "conexión segura" del navegador lo reflejase.

Esto se detectó al probar la aplicación en el navegador: la interfaz cargaba, pero cualquier tabla mostraba 0 resultados, y en las herramientas de desarrollador la petición aparecía marcada como **"Mixed Block"** — bloqueada antes siquiera de intentarse.

Como solución provisional para poder seguir probando el resto de la funcionalidad ese mismo día, se desactivó la protección de contenido mixto en el navegador de pruebas (`about:config` → `security.mixed_content.block_active_content`). Quedó anotado como algo a resolver de raíz, no como solución definitiva: desactivar esa protección no es algo que se le pueda pedir a un usuario real de la aplicación, y dependía además de una IP local escrita a mano en el código, que había quedado desactualizada.

## 2. Explicación no técnica

Puede pensarse en dos ventanillas de un mismo edificio (la aplicación): una es la entrada principal, con cristal blindado (HTTPS) — todo lo que pasa por ahí va protegido. La otra era una ventanilla trasera sin ese cristal (HTTP), por la que se atendían las consultas de datos. El propio edificio de seguridad del navegador, al darse cuenta de que había una ventanilla sin blindar, decidió tapiarla directamente para proteger a quien la usara — y de paso, dejó sin servicio esa parte de la aplicación.

La solución ha sido eliminar la ventanilla trasera: ahora **todo** pasa por la entrada principal blindada. Cuando el navegador necesita datos, se lo pide a la propia aplicación (Flask), y es la aplicación —ya dentro de la "casa", sin exponerse a la calle— quien hace un recado interno a PostgREST y trae la respuesta de vuelta. El navegador nunca llega a hablar directamente con la ventanilla trasera; de hecho, ya ni siquiera necesita saber que existe.

Efecto colateral positivo: como la comunicación con PostgREST ya no depende de que el navegador conozca la dirección de red del ordenador donde corre la aplicación, se ha eliminado también la dirección IP que estaba escrita a mano en el código (y que se había quedado obsoleta al cambiar de red).

## 3. Solución técnica: Flask como proxy inverso hacia PostgREST

### 3.1 Backend — `https_server.py`

Se añadió una ruta que reenvía cualquier petición a PostgREST y devuelve su respuesta tal cual:

```python
POSTGREST_URL = os.environ.get('POSTGREST_URL', 'http://localhost:3000')

@app.route('/pgrest/<path:subpath>', methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE'])
def pgrest_proxy(subpath):
    headers = {}
    if 'Authorization' in request.headers:
        headers['Authorization'] = request.headers['Authorization']
    if 'Content-Type' in request.headers:
        headers['Content-Type'] = request.headers['Content-Type']
    if 'Prefer' in request.headers:
        headers['Prefer'] = request.headers['Prefer']

    pg_response = requests.request(
        method=request.method,
        url=f'{POSTGREST_URL}/{subpath}',
        params=request.args,
        data=request.get_data(),
        headers=headers,
        timeout=15
    )

    response_headers = [
        (k, v) for k, v in pg_response.headers.items()
        if k.lower() not in HOP_BY_HOP_HEADERS
    ]
    return Response(pg_response.content, status=pg_response.status_code, headers=response_headers)
```

Puntos importantes de esta ruta:

- **Es una tubería, no una barrera**: no comprueba sesión de Flask ni permisos — se limita a reenviar la petición (incluida la cabecera `Authorization` con el JWT) y devolver la respuesta de PostgREST sin modificarla. Quien decide de verdad si la operación está permitida sigue siendo PostgREST/PostgreSQL, exactamente igual que antes (ver [`permisos-dinamicos-por-tabla.md`](./permisos-dinamicos-por-tabla.md)) — este cambio solo mueve por dónde viaja la petición, no quién la autoriza.
- **`POSTGREST_URL` apunta a `localhost:3000`**: PostgREST ya no necesita ser alcanzable desde otros equipos de la red, solo desde la propia máquina donde corre Flask.
- Se filtran las **cabeceras "hop-by-hop"** (`Connection`, `Transfer-Encoding`, `Content-Length`, etc.) al devolver la respuesta, porque son específicas de cada tramo de la conexión y reenviarlas tal cual puede provocar respuestas mal formadas.
- Se añadió `threaded=True` al arranque de Flask (`app.run(...)`), necesario para que, mientras se espera la respuesta de PostgREST en una petición, el servidor pueda seguir atendiendo a otros usuarios en paralelo.

Nueva dependencia: librería `requests`, usada para reenviar la petición HTTP a PostgREST.

### 3.2 Frontend — `index.html`

Un único cambio real:

```js
// Antes
const API_URL = "http://192.168.1.144:3000";

// Ahora
const API_URL = "/pgrest";
```

Al ser una ruta **relativa**, el navegador la resuelve automáticamente contra el origen actual de la página (`https://<host>:8000/pgrest/...`), sea cual sea la IP o el dominio desde el que se acceda. El resto del frontend (la función `postgrestFetch`, las llamadas a `estudiantes`, `profesores`, etc.) no necesitó ningún cambio, porque ya usaban `API_URL` como base en vez de tener la URL de PostgREST repetida en cada sitio.

## 4. Verificación

- Se revirtió deliberadamente el cambio de `about:config` (`security.mixed_content.block_active_content` de vuelta a `true`, protección activada) antes de probar, para confirmar que la solución es real y no un side-effect de tener la protección desactivada.
- Con la protección del navegador activada de nuevo, se repitió el flujo completo (login, "ver tablas", consultas guiadas) sin ningún aviso de contenido mixto ni error de red.

## 5. Beneficios de este cambio

- **Elimina el bloqueo de Mixed Content** de forma definitiva, sin pedirle nada al usuario ni a su navegador.
- **Elimina la dependencia de una IP fija** en el código: la aplicación funciona igual si cambia de red, de equipo, o si se accede por `localhost`, por IP local o por un nombre de dominio en el futuro.
- **Reduce la superficie expuesta**: PostgREST deja de necesitar ser alcanzable desde fuera del propio equipo (ver apartado 6).

## 6. Pendiente relacionado (a decidir)

El puerto `3000` de PostgREST sigue publicado en `docker-compose.yml` como `"3000:3000"`, lo que lo mantiene accesible desde cualquier equipo de la red local, aunque ya no lo necesite nadie más que el propio Flask. El cierre natural de este cambio sería restringirlo a `"127.0.0.1:3000:3000"`, para que solo se pueda acceder a PostgREST desde la propia máquina — quedó pendiente de decidir si aplicarlo ahora o más adelante.

## 7. Archivos modificados

- `https_server.py` — nueva ruta `/pgrest/<path:subpath>`, dependencia `requests`, `threaded=True` en `app.run`.
- `index.html` — `API_URL` pasa de una URL absoluta con IP fija a la ruta relativa `/pgrest`.
