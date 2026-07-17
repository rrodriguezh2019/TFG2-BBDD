from flask import Flask, render_template, request, jsonify, session, Response
from flask_cors import CORS
import ssl
import os
import psycopg2
import psycopg2.extras
from psycopg2 import sql as pgsql
import bcrypt
import jwt
import requests
from functools import wraps
from collections import Counter
from datetime import datetime, timedelta

import socket

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# ============ CONFIGURACIÓN ============

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = 'tfg-super-secret-key-cambiar-en-produccion'
CORS(app)

CERT_FILE = "certs/babia_cert.pem"
KEY_FILE = "certs/babia_key.pem"
PORT = 8000
HOST = "0.0.0.0"

# Configuración de sesión
app.permanent_session_lifetime = timedelta(hours=8)

# Base de datos - VERIFICA ESTOS VALORES
DB_CONFIG = {
    'host': 'localhost',
    'database': 'Universidad',
    'user': 'postgres',
    'password': 'changeme',
    'port': 5432
}

# Secreto para firmar los JWT que usará PostgREST (debe coincidir con
# PGRST_JWT_SECRET en docker-compose.yml)
JWT_SECRET = os.environ.get('JWT_SECRET', 'cambia-esto-en-produccion-tfg-jwt-secret-2026')
JWT_ALGORITHM = 'HS256'

# PostgREST solo escucha en localhost:3000 (no expuesto directamente al navegador);
# Flask hace de proxy para que todo el tráfico vaya por el mismo origen HTTPS.
POSTGREST_URL = os.environ.get('POSTGREST_URL', 'http://localhost:3000')

# ============ FUNCIONES AUXILIARES ============

def get_db_connection():
    """Conecta a PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Error conectando a BD: {e}")
        return None

def hash_password(password):
    """Hashea una contraseña con bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password, hash_password):
    """Verifica si una contraseña coincide con su hash"""
    try:
        return bcrypt.checkpw(password.encode(), hash_password.encode())
    except:
        return False

def pg_role_for_user(user_id):
    """Nombre del rol de PostgreSQL asociado a este usuario (mismo criterio usado al crear el rol en Postgres)"""
    return f"app_user_{user_id}"

def generar_jwt(user_id):
    """Genera el JWT que el frontend enviará a PostgREST para que use el rol de Postgres de este usuario"""
    payload = {
        'role': pg_role_for_user(user_id),
        'exp': datetime.utcnow() + timedelta(hours=8)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

# ============ DECORADORES DE PROTECCIÓN ============

def require_auth(f):
    """Decorator: Requiere que el usuario esté autenticado"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'No autenticado', 'code': 'NO_AUTH'}), 401
        return f(*args, **kwargs)
    return decorated

def require_permission(permission_name):
    """Decorator: Requiere un permiso específico"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Primero verificar autenticación
            if 'user_id' not in session:
                return jsonify({'error': 'No autenticado', 'code': 'NO_AUTH'}), 401
            
            # Luego verificar permiso
            user_role = session.get('role')
            conn = get_db_connection()
            
            if not conn:
                return jsonify({'error': 'Error de conexión a BD'}), 500
            
            cur = conn.cursor()
            try:
                cur.execute(
                    '''SELECT 1 FROM permissions 
                       WHERE role_name = %s AND permission_name = %s''',
                    (user_role, permission_name)
                )
                has_perm = cur.fetchone() is not None
                cur.close()
                conn.close()
                
                if not has_perm:
                    return jsonify({
                        'error': f'Permiso denegado: {permission_name}',
                        'code': 'PERMISSION_DENIED'
                    }), 403
                
                return f(*args, **kwargs)
            except Exception as e:
                cur.close()
                conn.close()
                return jsonify({'error': str(e)}), 500
        
        return decorated
    return decorator

# ============ RUTAS DE AUTENTICACIÓN ============

@app.route('/login', methods=['POST'])
def login():
    """Login del usuario"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Usuario y contraseña requeridos'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a BD'}), 500
    
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    try:
        # Buscar usuario
        cur.execute(
            '''SELECT user_id, username, password_hash, role, email 
               FROM users 
               WHERE username = %s AND is_active = TRUE''',
            (username,)
        )
        
        user = cur.fetchone()
        
        if not user:
            return jsonify({'error': 'Usuario no encontrado'}), 401
        
        # Verificar contraseña
        if not verify_password(password, user['password_hash']):
            return jsonify({'error': 'Contraseña incorrecta'}), 401
        
        # Crear sesión
        session.permanent = True
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['role'] = user['role']
        session['email'] = user['email']
        
        return jsonify({
            'message': '✅ Login exitoso',
            'user_id': user['user_id'],
            'username': user['username'],
            'role': user['role'],
            'email': user['email'],
            'token': generar_jwt(user['user_id'])
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/token', methods=['GET'])
@require_auth
def get_token():
    """Reemite un JWT para el usuario de la sesión actual (se usa al recargar la página, ya que el
    token solo viaja en la respuesta de /login y se pierde en memoria al refrescar el navegador)"""
    return jsonify({'token': generar_jwt(session['user_id'])}), 200

@app.route('/logout', methods=['POST'])
def logout():
    """Logout del usuario"""
    session.clear()
    return jsonify({'message': '✅ Sesión cerrada'}), 200

@app.route('/profile', methods=['GET'])
@require_auth
def profile():
    """Obtener perfil del usuario autenticado"""
    return jsonify({
        'user_id': session.get('user_id'),
        'username': session.get('username'),
        'role': session.get('role'),
        'email': session.get('email')
    }), 200

@app.route('/permissions', methods=['GET'])
@require_auth
def get_permissions():
    """Obtener permisos del usuario actual"""
    role = session.get('role')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a BD'}), 500
    
    cur = conn.cursor()
    
    try:
        cur.execute(
            '''SELECT permission_name FROM permissions 
               WHERE role_name = %s''',
            (role,)
        )
        
        permissions = [row[0] for row in cur.fetchall()]
        
        return jsonify({
            'role': role,
            'permissions': permissions
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# ============ PROXY HACIA POSTGREST ============

# Cabeceras que no se deben reenviar tal cual entre proxy y cliente (son específicas
# de cada salto de la conexión, no del contenido de la respuesta).
HOP_BY_HOP_HEADERS = {
    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailers', 'transfer-encoding', 'upgrade', 'content-encoding', 'content-length'
}

@app.route('/pgrest/<path:subpath>', methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE'])
def pgrest_proxy(subpath):
    """Reenvía la petición a PostgREST (solo accesible en localhost:3000) para que el
    navegador hable siempre con el mismo origen HTTPS. No comprueba sesión ni permisos
    aquí: quien autoriza de verdad es PostgREST/Postgres a partir del JWT reenviado."""
    headers = {}
    if 'Authorization' in request.headers:
        headers['Authorization'] = request.headers['Authorization']
    if 'Content-Type' in request.headers:
        headers['Content-Type'] = request.headers['Content-Type']
    if 'Prefer' in request.headers:
        headers['Prefer'] = request.headers['Prefer']

    try:
        pg_response = requests.request(
            method=request.method,
            url=f'{POSTGREST_URL}/{subpath}',
            params=request.args,
            data=request.get_data(),
            headers=headers,
            timeout=15
        )
    except requests.RequestException as e:
        return jsonify({'error': f'No se pudo contactar con PostgREST: {e}'}), 502

    response_headers = [
        (k, v) for k, v in pg_response.headers.items()
        if k.lower() not in HOP_BY_HOP_HEADERS
    ]
    return Response(pg_response.content, status=pg_response.status_code, headers=response_headers)

# ============ RUTAS ESTÁTICAS ============

@app.route('/')
def index():
    """Sirve el archivo index.html"""
    return app.send_static_file('index.html')

@app.route('/<path:filename>')
def send_static(filename):
    """Sirve archivos estáticos"""
    if os.path.isfile(filename):
        return app.send_static_file(filename)
    return jsonify({'error': 'Archivo no encontrado'}), 404

# ============ RUTAS DE API (EJEMPLOS CON PERMISOS) ============

@app.route('/api/estudiantes', methods=['GET'])
@require_auth
@require_permission('view_estudiantes')
def get_estudiantes():
    """Obtener estudiantes (requiere permiso)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a BD'}), 500
    
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    try:
        cur.execute('SELECT * FROM estudiantes LIMIT 100')
        estudiantes = cur.fetchall()
        return jsonify({'data': estudiantes}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/estudiantes/<int:id>', methods=['DELETE'])
@require_auth
@require_permission('delete_estudiante')
def delete_estudiante(id):
    """Borrar estudiante (solo admins)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a BD'}), 500
    
    cur = conn.cursor()
    
    try:
        cur.execute('DELETE FROM estudiantes WHERE id = %s', (id,))
        conn.commit()
        
        if cur.rowcount == 0:
            return jsonify({'error': 'Estudiante no encontrado'}), 404
        
        return jsonify({'message': f'✅ Estudiante {id} eliminado'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# ============ NUEVA RUTA: CREAR TABLA (solo admin) ============

@app.route('/api/admin/create_table', methods=['POST'])
@require_auth
@require_permission('admin_create_table')
def admin_create_table():
    data = request.get_json()
    table_name = data.get('table_name')
    columns = data.get('columns')  # [{'name': 'nombrecol', 'type': 'TEXT'}, ...]

    # Validar inputs
    if not table_name or not columns or not isinstance(columns, list):
        return jsonify({'error': 'Datos de tabla/columnas inválidos'}), 400

    # Validar nombre tabla seguro (solo letras, números y guión bajo)
    if not table_name.replace('_', '').isalnum():
        return jsonify({'error': 'Nombre de tabla no válido'}), 400

    # Tipos permitidos (amplía si lo deseas)
    allowed_types = {'TEXT', 'INTEGER', 'SERIAL', 'BOOLEAN', 'DATE', 'REAL'}
    col_defs = []
    for col in columns:
        name = col.get('name')
        col_type = col.get('type', '').upper()
        if not name or not name.replace('_', '').isalnum():
            return jsonify({'error': f'Nombre de columna no válido: {name}'}), 400
        if col_type not in allowed_types:
            return jsonify({'error': f'Tipo de columna no permitido: {col_type}'}), 400
        col_defs.append(f"{name} {col_type}")

    sql = f'CREATE TABLE IF NOT EXISTS {table_name} ({", ".join(col_defs)});'

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500
    try:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True, 'sql': sql}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500

# ============ GESTIÓN DINÁMICA DE USUARIOS Y PERMISOS POR TABLA ============

# Tablas internas del propio sistema de login/permisos: nunca se ofrecen en el
# desplegable ni se pueden conceder, para no exponer password_hash de `users`.
EXCLUDED_TABLES = {'users', 'permissions', 'role_default_tables', 'user_table_permissions'}

def _valid_identifier(name):
    """Nombre seguro para usar en SQL dinámico (GRANT/REVOKE/CREATE ROLE): solo alfanumérico y guión bajo"""
    return bool(name) and name.replace('_', '').isalnum()

def _get_public_tables(cur):
    """Tablas de datos disponibles para conceder permisos (excluye las tablas internas del sistema)"""
    cur.execute('''
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    ''')
    return [row[0] for row in cur.fetchall() if row[0] not in EXCLUDED_TABLES]

def _get_table_columns(cur, table_name):
    """Columnas reales de una tabla (para validar identificadores antes de meterlos en SQL dinámico)"""
    cur.execute('''
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
    ''', (table_name,))
    return [row[0] for row in cur.fetchall()]

def _get_foreign_keys(cur):
    """Relaciones FK entre tablas públicas (tabla_origen.columna -> tabla_destino.columna),
    usadas para sugerir automáticamente la condición de un JOIN."""
    cur.execute('''
        SELECT tc.table_name, kcu.column_name, ccu.table_name AS foreign_table_name,
               ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
        ORDER BY tc.table_name
    ''')
    return [
        {'table': t, 'column': c, 'foreign_table': ft, 'foreign_column': fc}
        for t, c, ft, fc in cur.fetchall()
        if t not in EXCLUDED_TABLES and ft not in EXCLUDED_TABLES
    ]

@app.route('/api/schema/relations', methods=['GET'])
@require_auth
def schema_relations():
    """FKs entre tablas públicas, para que el constructor de consultas sugiera la
    columna de unión al elegir una segunda tabla para un JOIN."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a BD'}), 500
    try:
        cur = conn.cursor()
        return jsonify({'relations': _get_foreign_keys(cur)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/query/join', methods=['POST'])
@require_auth
def query_join():
    """Ejecuta un SELECT ... JOIN construido por el usuario en el constructor de consultas.
    Todo identificador (tabla/columna) se valida contra el catálogo real antes de entrar
    en el SQL; los valores de WHERE van siempre parametrizados. La consulta se ejecuta
    con SET ROLE al rol de Postgres del usuario para que se respeten sus permisos de
    lectura por tabla, igual que hace PostgREST vía JWT — así este endpoint no puede
    usarse para leer una tabla a la que el usuario no tiene acceso."""
    data = request.get_json() or {}
    table_a = data.get('tableA')
    table_b = data.get('tableB')
    join_type = (data.get('joinType') or 'INNER').upper()
    on_a = data.get('onA')
    on_b = data.get('onB')
    columns = data.get('columns') or []
    where = data.get('where')
    order_by = data.get('orderBy')

    if join_type not in {'INNER', 'LEFT', 'RIGHT'}:
        return jsonify({'error': 'Tipo de JOIN no válido'}), 400
    if not table_a or not table_b or table_a == table_b:
        return jsonify({'error': 'Se necesitan dos tablas distintas'}), 400
    for name in [table_a, table_b, on_a, on_b]:
        if not _valid_identifier(name):
            return jsonify({'error': f'Identificador no válido: {name}'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a BD'}), 500

    try:
        cur = conn.cursor()

        public_tables = _get_public_tables(cur)
        if table_a not in public_tables or table_b not in public_tables:
            return jsonify({'error': 'Tabla no válida'}), 400

        cols_a = set(_get_table_columns(cur, table_a))
        cols_b = set(_get_table_columns(cur, table_b))
        table_cols = {table_a: cols_a, table_b: cols_b}

        if on_a not in cols_a or on_b not in cols_b:
            return jsonify({'error': 'Columna de unión no válida'}), 400

        def resolve_col(entry, label):
            t, c = entry.get('table'), entry.get('col')
            if t not in (table_a, table_b) or not _valid_identifier(c) or c not in table_cols.get(t, ()):
                raise ValueError(f'{label} no válido: {t}.{c}')
            return t, c

        if not columns:
            select_cols = [(table_a, c) for c in cols_a] + [(table_b, c) for c in cols_b]
        else:
            select_cols = [resolve_col(c, 'columna') for c in columns]

        # Alias corto (solo el nombre de columna) salvo que dos tablas compartan el mismo
        # nombre de columna, en cuyo caso se antepone la tabla para desambiguar. Mantiene
        # las cabeceras de la tabla de resultados legibles en el caso común (sin colisión).
        name_counts = Counter(c for _, c in select_cols)
        select_parts = [
            pgsql.SQL('{}.{} AS {}').format(
                pgsql.Identifier(t), pgsql.Identifier(c),
                pgsql.Identifier(c if name_counts[c] == 1 else f'{t}.{c}')
            ) for t, c in select_cols
        ]

        query = pgsql.SQL('SELECT {select} FROM {ta} {jt} JOIN {tb} ON {ta}.{oa} = {tb}.{ob}').format(
            select=pgsql.SQL(', ').join(select_parts),
            ta=pgsql.Identifier(table_a),
            jt=pgsql.SQL(join_type),
            tb=pgsql.Identifier(table_b),
            oa=pgsql.Identifier(on_a),
            ob=pgsql.Identifier(on_b),
        )
        params = []

        if where and where.get('col'):
            wt, wc = resolve_col(where, 'WHERE')
            query += pgsql.SQL(' WHERE {}.{} = %s').format(pgsql.Identifier(wt), pgsql.Identifier(wc))
            params.append(where.get('val'))

        if order_by and order_by.get('col'):
            ot, oc = resolve_col(order_by, 'ORDER BY')
            direction = 'DESC' if (order_by.get('dir') or '').upper() == 'DESC' else 'ASC'
            query += pgsql.SQL(' ORDER BY {}.{} {}').format(
                pgsql.Identifier(ot), pgsql.Identifier(oc), pgsql.SQL(direction)
            )

        query += pgsql.SQL(' LIMIT 500')

        cur.execute(pgsql.SQL('SET ROLE {}').format(pgsql.Identifier(pg_role_for_user(session['user_id']))))
        cur2 = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur2.execute(query, params)
        rows = cur2.fetchall()
        cur2.close()

        return jsonify({
            'success': True,
            'sql': query.as_string(conn),
            'data': [dict(r) for r in rows]
        }), 200
    except ValueError as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    except psycopg2.errors.InsufficientPrivilege:
        conn.rollback()
        return jsonify({'error': 'No tienes permiso de lectura sobre una de las tablas'}), 403
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/admin/tables', methods=['GET'])
@require_auth
@require_permission('admin_manage_users')
def admin_list_tables():
    """Lista de tablas disponibles para asignar permisos (desplegable del panel de admin)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a BD'}), 500
    try:
        cur = conn.cursor()
        return jsonify({'tables': _get_public_tables(cur)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/admin/roles', methods=['GET'])
@require_auth
@require_permission('admin_manage_users')
def admin_list_roles():
    """Roles conocidos y sus tablas por defecto (role_default_tables), para precargar el formulario"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a BD'}), 500
    try:
        cur = conn.cursor()
        cur.execute('SELECT role_name, table_name, can_write FROM role_default_tables ORDER BY role_name, table_name')
        roles = {}
        for role_name, table_name, can_write in cur.fetchall():
            roles.setdefault(role_name, []).append({'table': table_name, 'can_write': can_write})
        return jsonify({'roles': roles}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/my-tables', methods=['GET'])
@require_auth
def my_tables():
    """Tablas accesibles para el usuario autenticado, con su permiso de lectura/escritura (para el menú dinámico)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a BD'}), 500
    try:
        cur = conn.cursor()
        cur.execute(
            'SELECT table_name, can_read, can_write FROM user_table_permissions WHERE user_id = %s ORDER BY table_name',
            (session['user_id'],)
        )
        tablas = [{'table': t, 'can_read': r, 'can_write': w} for t, r, w in cur.fetchall()]
        return jsonify({'tables': tablas}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/admin/users', methods=['POST'])
@require_auth
@require_permission('admin_manage_users')
def admin_create_user():
    """Crea un usuario nuevo con permisos de lectura/escritura por tabla (rol real de Postgres + GRANTs)"""
    data = request.get_json()
    username = (data.get('username') or '').strip()
    password = data.get('password')
    role = (data.get('role') or '').strip()
    table_permissions = data.get('table_permissions')  # [{table, can_read, can_write}, ...]

    if not username or not password or not role:
        return jsonify({'error': 'username, password y role son obligatorios'}), 400
    if not isinstance(table_permissions, list) or not table_permissions:
        return jsonify({'error': 'Selecciona al menos una tabla'}), 400
    if not _valid_identifier(role):
        return jsonify({'error': 'Rol no válido'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a BD'}), 500

    try:
        cur = conn.cursor()

        cur.execute('SELECT 1 FROM users WHERE username = %s', (username,))
        if cur.fetchone():
            return jsonify({'error': 'Ese nombre de usuario ya existe'}), 409

        tablas_validas = set(_get_public_tables(cur))
        permisos_limpios = []
        for tp in table_permissions:
            tabla = tp.get('table')
            if not _valid_identifier(tabla) or tabla not in tablas_validas:
                return jsonify({'error': f'Tabla no válida: {tabla}'}), 400
            permisos_limpios.append({
                'table': tabla,
                'can_read': bool(tp.get('can_read', True)),
                'can_write': bool(tp.get('can_write', False))
            })

        # 1) Crear usuario
        cur.execute(
            '''INSERT INTO users (username, password_hash, email, role)
               VALUES (%s, %s, %s, %s) RETURNING user_id''',
            (username, hash_password(password), data.get('email'), role)
        )
        user_id = cur.fetchone()[0]
        pg_role = pg_role_for_user(user_id)

        # 2) Rol de Postgres para este usuario, delegable por "authenticator" (PostgREST)
        cur.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', (pg_role,))
        if not cur.fetchone():
            cur.execute(f'CREATE ROLE {pg_role} NOLOGIN')
        cur.execute(f'GRANT {pg_role} TO authenticator')

        # 3) Permisos por tabla: bookkeeping en nuestra tabla + GRANT real en Postgres
        for p in permisos_limpios:
            cur.execute(
                '''INSERT INTO user_table_permissions (user_id, table_name, can_read, can_write)
                   VALUES (%s, %s, %s, %s)''',
                (user_id, p['table'], p['can_read'], p['can_write'])
            )
            if p['can_read']:
                cur.execute(f'GRANT SELECT ON {p["table"]} TO {pg_role}')
            if p['can_write']:
                cur.execute(f'GRANT INSERT, UPDATE, DELETE ON {p["table"]} TO {pg_role}')

        conn.commit()
        return jsonify({
            'success': True,
            'user_id': user_id,
            'username': username,
            'role': role,
            'table_permissions': permisos_limpios
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/admin/users/<int:user_id>/permissions', methods=['PUT'])
@require_auth
@require_permission('admin_manage_users')
def admin_update_user_permissions(user_id):
    """Sustituye los permisos por tabla de un usuario ya existente (añade/quita tablas, cambia lectura/escritura)"""
    data = request.get_json()
    table_permissions = data.get('table_permissions')
    if not isinstance(table_permissions, list) or not table_permissions:
        return jsonify({'error': 'Selecciona al menos una tabla'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a BD'}), 500

    try:
        cur = conn.cursor()
        cur.execute('SELECT 1 FROM users WHERE user_id = %s', (user_id,))
        if not cur.fetchone():
            return jsonify({'error': 'Usuario no encontrado'}), 404

        pg_role = pg_role_for_user(user_id)
        tablas_validas = set(_get_public_tables(cur))

        cur.execute('SELECT table_name FROM user_table_permissions WHERE user_id = %s', (user_id,))
        actuales = {row[0] for row in cur.fetchall()}

        nuevos = {}
        for tp in table_permissions:
            tabla = tp.get('table')
            if not _valid_identifier(tabla) or tabla not in tablas_validas:
                return jsonify({'error': f'Tabla no válida: {tabla}'}), 400
            nuevos[tabla] = (bool(tp.get('can_read', True)), bool(tp.get('can_write', False)))

        # Revocar tablas que ya no están en la lista nueva
        for tabla in actuales - set(nuevos.keys()):
            cur.execute(f'REVOKE ALL PRIVILEGES ON {tabla} FROM {pg_role}')
            cur.execute('DELETE FROM user_table_permissions WHERE user_id = %s AND table_name = %s', (user_id, tabla))

        # Aplicar el estado nuevo (upsert + grant/revoke real)
        for tabla, (can_read, can_write) in nuevos.items():
            cur.execute(
                '''INSERT INTO user_table_permissions (user_id, table_name, can_read, can_write)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (user_id, table_name) DO UPDATE
                   SET can_read = EXCLUDED.can_read, can_write = EXCLUDED.can_write''',
                (user_id, tabla, can_read, can_write)
            )
            cur.execute(f'REVOKE ALL PRIVILEGES ON {tabla} FROM {pg_role}')
            if can_read:
                cur.execute(f'GRANT SELECT ON {tabla} TO {pg_role}')
            if can_write:
                cur.execute(f'GRANT INSERT, UPDATE, DELETE ON {tabla} TO {pg_role}')

        conn.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# ============ MANEJO DE ERRORES ============

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Ruta no encontrada'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Error interno del servidor'}), 500

# ============ INICIAR SERVIDOR ============

if __name__ == '__main__':
    # Verificar certificados
    if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
        print(f"❌ Error: Certificados no encontrados")
        print(f"   - {CERT_FILE}")
        print(f"   - {KEY_FILE}")
        exit(1)
    
    # Configurar SSL/TLS
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(CERT_FILE, KEY_FILE)
    
    # Mostrar información
    server_ip = get_local_ip()

    print("\n" + "="*60)
    print("🚀 SERVIDOR HTTPS INICIADO")
    print("="*60)
    print(f"\n📍 URLs para acceder:\n")
    print(f"   🖥️  En este ordenador:")
    print(f"      https://localhost:{PORT}")
    print(f"      https://127.0.0.1:{PORT}")
    print(f"      https://{server_ip}:{PORT}")
    print(f"\n   🌐 Desde otra máquina en la red:")
    print(f"      https://{server_ip}:{PORT}")
    print(f"\n📜 Certificado: {CERT_FILE}")
    print(f"🔑 Clave privada: {KEY_FILE}")
    print(f"\n⚠️  El navegador mostrará 'No es seguro' (certificado auto-firmado)")
    print(f"💡 Escribe 'thisisunsafe' en Chrome/Chromium para ignorar el aviso")
    print(f"\n✅ Presiona Ctrl+C para detener el servidor\n")
    print("="*60 + "\n")
    
    # Iniciar servidor
    app.run(
        host=HOST,
        port=PORT,
        ssl_context=context,
        debug=False,
        threaded=True  # necesario para no bloquear otras peticiones mientras se hace de proxy hacia PostgREST
    )
