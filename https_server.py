from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import ssl
import os
import psycopg2
import psycopg2.extras
import bcrypt
from functools import wraps
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
            'email': user['email']
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

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
        debug=False
    )
