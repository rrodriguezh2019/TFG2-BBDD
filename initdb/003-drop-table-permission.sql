-- Permiso de aplicación para poder eliminar tablas (DROP TABLE) desde el constructor
-- de consultas. Solo se concede al rol 'admin': tener permiso de escritura sobre los
-- datos de una tabla (user_table_permissions.can_write) no implica poder borrar la
-- tabla en sí, que es una operación de esquema (DDL), no de datos (DML).
-- Se ejecuta automáticamente SOLO si el volumen de postgres está vacío (igual que 001/002-*.sql).
-- Si ya tienes datos, aplícalo a mano una vez desde el Query Tool de pgAdmin.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM permissions
    WHERE role_name = 'admin' AND permission_name = 'admin_drop_table'
  ) THEN
    INSERT INTO permissions (role_name, permission_name, description)
    VALUES ('admin', 'admin_drop_table', 'Eliminar tablas (DROP TABLE) desde el constructor de consultas');
  END IF;
END $$;
