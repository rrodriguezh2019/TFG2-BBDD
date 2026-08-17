-- Tabla de roles: convierte "users.role" y "permissions.role_name" (antes texto libre que solo
-- coincidia por valor) en claves foraneas reales contra un catalogo de roles.
-- Se ejecuta SOLO la primera vez si el volumen postgres esta vacio (igual que el resto de
-- initdb/*.sql). Si ya tienes datos, aplicalo a mano una vez desde el Query Tool de pgAdmin.

CREATE TABLE IF NOT EXISTS roles (
    role_id      SERIAL PRIMARY KEY,
    role_name    VARCHAR(50) NOT NULL UNIQUE,
    description  VARCHAR(255)
);

INSERT INTO roles (role_name, description) VALUES
    ('admin',      'Administrador - Acceso total a todo'),
    ('user',       'Usuario normal - Acceso limitado'),
    ('guest',      'Invitado - Solo lectura'),
    ('profesor',   'Profesor - Lectura y escritura en sus tablas asignadas'),
    ('estudiante', 'Estudiante - Acceso de solo lectura a sus tablas asignadas')
ON CONFLICT (role_name) DO NOTHING;

-- FK real desde permissions.role_name y users.role hacia roles.role_name. Los 5 valores de
-- arriba cubren todos los roles usados hasta ahora en la aplicacion, asi que la restriccion
-- se puede anadir sin dejar ninguna fila existente con un valor huerfano.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'permissions_role_name_fkey'
  ) THEN
    ALTER TABLE permissions
      ADD CONSTRAINT permissions_role_name_fkey FOREIGN KEY (role_name) REFERENCES roles(role_name);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'users_role_fkey'
  ) THEN
    ALTER TABLE users
      ADD CONSTRAINT users_role_fkey FOREIGN KEY (role) REFERENCES roles(role_name);
  END IF;
END $$;
