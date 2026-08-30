-- Usuario administrador de arranque (username: admin, password: admin123), igual que el que
-- ya usa la aplicación real, pero que hasta ahora solo existía porque se creó a mano una vez.
-- Sin este script, un volumen de Docker nuevo no tiene con qué usuario iniciar sesión.
-- El hash está generado con bcrypt (ver sección de seguridad de la memoria), no es la contraseña
-- en claro.

INSERT INTO users (username, password_hash, email, role, is_active)
VALUES (
    'admin',
    '$2b$12$qPxiiQMmw7F1vrNprzySMOPcJTZww.H.CLuJ/ZKa4C8rDiTFWx/zS',
    'admin@universidad.es',
    'admin',
    TRUE
)
ON CONFLICT (username) DO NOTHING;

-- Solo el usuario 'admin' llega a tener aquí user_id = 1 en un volumen nuevo (es el primer
-- INSERT en la tabla users). El resto del arranque replica exactamente lo que hace
-- admin_create_user() en https_server.py cuando se crea un usuario desde el panel: rol real de
-- PostgreSQL, delegable por "authenticator" (el usuario con el que se conecta PostgREST), y
-- GRANT explícito tabla por tabla -- sin esto, el usuario existe pero no ve ninguna tabla,
-- porque la app decide qué mostrar consultando user_table_permissions, no por ser "admin".

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user_1') THEN
    CREATE ROLE app_user_1 NOLOGIN;
  END IF;
  GRANT app_user_1 TO authenticator;
END $$;

INSERT INTO user_table_permissions (user_id, table_name, can_read, can_write)
VALUES
    (1, 'estudiantes', TRUE, TRUE),
    (1, 'profesores',  TRUE, TRUE),
    (1, 'asignaturas', TRUE, TRUE),
    (1, 'matriculas',  TRUE, TRUE),
    (1, 'triggers_audit_log', TRUE, FALSE)
ON CONFLICT (user_id, table_name) DO NOTHING;

GRANT SELECT, INSERT, UPDATE, DELETE ON estudiantes, profesores, asignaturas, matriculas TO app_user_1;
GRANT SELECT ON triggers_audit_log TO app_user_1;
