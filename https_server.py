import http.server
import ssl
import os

# Configuración
CERT_FILE = "certs/babia_cert.pem"
KEY_FILE = "certs/babia_key.pem"
PORT = 8000
HOST = "0.0.0.0"  # Escucha en TODAS las interfaces

# Verificar que los certificados existan
if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
    print(f"❌ Error: Certificados no encontrados")
    print(f"   - {CERT_FILE}")
    print(f"   - {KEY_FILE}")
    exit(1)

# Crear el servidor
server_address = (HOST, PORT)
handler = http.server.SimpleHTTPRequestHandler
httpd = http.server.HTTPServer(server_address, handler)

# Permitir reutilizar el socket
httpd.allow_reuse_address = True

# Configurar SSL/TLS
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(CERT_FILE, KEY_FILE)
httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

# Mostrar información del servidor
print("\n" + "="*60)
print("🚀 SERVIDOR HTTPS INICIADO")
print("="*60)
print(f"\n📍 URLs para acceder:\n")
print(f"   🖥️  En este ordenador:")
print(f"      https://localhost:{PORT}")
print(f"      https://127.0.0.1:{PORT}")
print(f"      https://192.168.1.136:{PORT}")
print(f"\n   🌐 Desde otra máquina en la red:")
print(f"      https://192.168.1.136:{PORT}")
print(f"\n📜 Certificado: {CERT_FILE}")
print(f"🔑 Clave privada: {KEY_FILE}")
print(f"\n⚠️  El navegador mostrará 'No es seguro' (certificado auto-firmado)")
print(f"💡 Escribe 'thisisunsafe' en Chrome/Chromium para ignorar el aviso")
print(f"\n✅ Presiona Ctrl+C para detener el servidor\n")
print("="*60 + "\n")

try:
    httpd.serve_forever()
except KeyboardInterrupt:
    print("\n⛔ Servidor detenido")
    httpd.server_close()
