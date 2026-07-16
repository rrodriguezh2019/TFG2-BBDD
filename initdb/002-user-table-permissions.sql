-- Permisos de lectura/escritura por tabla, por usuario, con defaults por rol.
-- Se ejecuta automáticamente SOLO si el volumen de postgres está vacío (igual que 001-*.sql).
-- Si ya tienes datos, aplícalo a mano una vez desde el Query Tool de pgAdmin.

-- 0) Reconstrucción de las tablas ya existentes (creadas a mano), para que el esquema
--    quede versionado y reproducible en un volumen nuevo. IF NOT EXISTS => no toca datos actuales.
CREATE TABLE IF NOT EXISTS users (
    user_id       SERIAL PRIMARY KEY,
    username      VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR NOT NULL,
    email         VARCHAR(100),
    role          VARCHAR(50) NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active     BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS permissions (
    permission_id   SERIAL PRIMARY KEY,
    role_name       VARCHAR(50) NOT NULL,
    permission_name VARCHAR(100) NOT NULL,
    description     VARCHAR
);

-- 1) Tablas por defecto según rol: al crear un usuario con ese rol, se le conceden
--    automáticamente estas tablas (editable después por usuario).
CREATE TABLE IF NOT EXISTS role_default_tables (
    role_name  VARCHAR(50) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    can_write  BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (role_name, table_name)
);

-- 2) Permisos efectivos por usuario y tabla. Se inicializan a partir de role_default_tables
--    al crear el usuario, y se pueden ampliar o modificar después desde el panel de admin.
CREATE TABLE IF NOT EXISTS user_table_permissions (
    user_id    INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    table_name VARCHAR(100) NOT NULL,
    can_read   BOOLEAN NOT NULL DEFAULT TRUE,
    can_write  BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (user_id, table_name)
);

-- 3) Seed: tablas por defecto para los roles "profesor" y "estudiante" (roles nuevos,
--    se usarán al crear usuarios dinámicamente; no tocan los roles admin/user/guest existentes).
INSERT INTO role_default_tables (role_name, table_name, can_write) VALUES
    ('profesor',   'asignaturas',  TRUE),
    ('profesor',   'matriculas',   TRUE),
    ('profesor',   'estudiantes',  FALSE),
    ('profesor',   'profesores',   FALSE),
    ('estudiante', 'estudiantes',  FALSE),
    ('estudiante', 'asignaturas',  FALSE),
    ('estudiante', 'matriculas',   FALSE)
ON CONFLICT (role_name, table_name) DO NOTHING;

-- 4) Nuevo permiso de ruta para el panel de administración de usuarios (mismo patrón que
--    los permisos ya existentes en la tabla `permissions`).
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM permissions
    WHERE role_name = 'admin' AND permission_name = 'admin_manage_users'
  ) THEN
    INSERT INTO permissions (role_name, permission_name, description)
    VALUES ('admin', 'admin_manage_users', 'Crear usuarios y gestionar sus permisos por tabla');
  END IF;
END $$;
