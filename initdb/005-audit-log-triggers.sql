-- Log de cambios (auditoría) sobre las tablas de datos académicos, vía triggers.
-- Se ejecuta automáticamente SOLO si el volumen de postgres está vacío (igual que los
-- scripts anteriores). Si ya tienes datos, aplícalo a mano una vez desde el Query Tool
-- de pgAdmin.

-- 1) Tabla donde queda el rastro de cada cambio. Se guarda el nombre de la tabla, el tipo
--    de operación, quién lo hizo y el estado de la fila antes/después (como JSON, para no
--    tener que definir una tabla de log distinta por cada tabla auditada).
CREATE TABLE IF NOT EXISTS audit_log (
    log_id      BIGSERIAL PRIMARY KEY,
    table_name  VARCHAR(100) NOT NULL,
    operation   VARCHAR(10)  NOT NULL,
    changed_by  VARCHAR(100) NOT NULL,
    changed_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    old_data    JSONB,
    new_data    JSONB
);

-- Nadie (ni web_anon ni ningún app_user_<id>) tiene GRANT sobre audit_log: no se concede
-- explícitamente en ningún sitio, así que por defecto nadie puede leerla ni escribirla
-- salvo el superusuario desde pgAdmin. Esta línea lo deja explícito además de implícito,
-- para que quede documentado que es intencional y no un descuido.
REVOKE ALL ON audit_log FROM PUBLIC;

-- 2) Función de trigger genérica: una sola función sirve para cualquier tabla, usando las
--    variables TG_TABLE_NAME/TG_OP/OLD/NEW que Postgres rellena automáticamente. SECURITY
--    DEFINER hace que se ejecute con los privilegios de quien la CREÓ (no de quien dispara
--    el trigger), porque los roles app_user_<id> no tienen (ni deben tener) permiso para
--    escribir en audit_log directamente: si pudieran, un usuario podría manipular su propio
--    rastro de auditoría.
CREATE OR REPLACE FUNCTION fn_audit_log() RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, operation, changed_by, old_data, new_data)
        VALUES (TG_TABLE_NAME, TG_OP, current_user, to_jsonb(OLD), NULL);
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, operation, changed_by, old_data, new_data)
        VALUES (TG_TABLE_NAME, TG_OP, current_user, to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    ELSE -- INSERT
        INSERT INTO audit_log (table_name, operation, changed_by, old_data, new_data)
        VALUES (TG_TABLE_NAME, TG_OP, current_user, NULL, to_jsonb(NEW));
        RETURN NEW;
    END IF;
END;
$$;

-- 3) Enganchar la función a las 4 tablas de datos académicos. DROP TRIGGER IF EXISTS hace
--    el bloque re-ejecutable (por si se corre este script más de una vez a mano).
DROP TRIGGER IF EXISTS trg_audit_asignaturas ON asignaturas;
CREATE TRIGGER trg_audit_asignaturas
    AFTER INSERT OR UPDATE OR DELETE ON asignaturas
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

DROP TRIGGER IF EXISTS trg_audit_estudiantes ON estudiantes;
CREATE TRIGGER trg_audit_estudiantes
    AFTER INSERT OR UPDATE OR DELETE ON estudiantes
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

DROP TRIGGER IF EXISTS trg_audit_profesores ON profesores;
CREATE TRIGGER trg_audit_profesores
    AFTER INSERT OR UPDATE OR DELETE ON profesores
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

DROP TRIGGER IF EXISTS trg_audit_matriculas ON matriculas;
CREATE TRIGGER trg_audit_matriculas
    AFTER INSERT OR UPDATE OR DELETE ON matriculas
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

-- 4) Vista para visualizar el log (pedido por el tutor: los triggers no valen de nada si
--    nadie puede ver lo que registran). Se llama "triggers_..._log" y no "vista_..." para
--    distinguirla de vista_estudiante/vista_profesor: aquella son vistas de datos, esta es
--    la ventana de administración sobre lo que han hecho los triggers de auditoría. Reutiliza
--    el mismo truco de propietario que las vistas de rol (ver docs/vistas-por-rol.md): se
--    ejecuta con los privilegios de quien la crea, así que "admin" puede tener SELECT solo
--    sobre esta vista sin necesitar GRANT directo sobre audit_log. Solo estas 5 columnas (sin
--    old_data/new_data): el renderizador de tablas de la escena VR no sabe pintar JSON (sale
--    "[object Object]"), así que para ver el detalle completo de un cambio se sigue consultando
--    audit_log desde pgAdmin; esta vista es el "qué pasó, quién y cuándo" de un vistazo en la app.
--    DROP + CREATE (no CREATE OR REPLACE) porque esta vista ya tuvo más columnas antes en
--    algún entorno donde se probó, y CREATE OR REPLACE VIEW no permite quitar columnas.
DROP VIEW IF EXISTS vista_admin_audit_log;
DROP VIEW IF EXISTS triggers_audit_log;
CREATE VIEW triggers_audit_log AS
SELECT
    log_id,
    table_name,
    operation,
    changed_by,
    changed_at
FROM audit_log
ORDER BY changed_at DESC;

-- Se registra como tabla-por-defecto del rol "admin", mismo mecanismo que las vistas de
-- profesor/estudiante: precarga el checklist del panel de admin al crear un usuario admin.
DELETE FROM role_default_tables WHERE role_name = 'admin' AND table_name = 'vista_admin_audit_log';
INSERT INTO role_default_tables (role_name, table_name, can_write) VALUES
    ('admin', 'triggers_audit_log', FALSE)
ON CONFLICT (role_name, table_name) DO NOTHING;
