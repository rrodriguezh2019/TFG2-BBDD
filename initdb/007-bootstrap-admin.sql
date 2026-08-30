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
