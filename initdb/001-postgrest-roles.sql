-- Se ejecuta SOLO la primera vez si el volumen postgres está vacío

-- 1) Rol anónimo (solo lectura)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'web_anon') THEN
    CREATE ROLE web_anon NOLOGIN;
  END IF;
END $$;

-- 2) Usuario "authenticator" que usará PostgREST para conectarse
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticator') THEN
    CREATE ROLE authenticator LOGIN PASSWORD 'authenticator_password';
  END IF;
END $$;

-- 3) Permisos (ajusta si quieres)
GRANT USAGE ON SCHEMA public TO web_anon;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO web_anon;

-- Para que las tablas futuras también queden con SELECT:
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON TABLES TO web_anon;

-- Permite al authenticator "cambiar" al rol web_anon
GRANT web_anon TO authenticator;
