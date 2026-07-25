-- Vistas de solo lectura por rol.
-- Se ejecuta automáticamente SOLO si el volumen de postgres está vacío (igual que 001-*.sql
-- y 002-*.sql). Si ya tienes datos, aplícalo a mano una vez desde el Query Tool de pgAdmin.
--
-- Por qué una vista y no solo tablas: una vista se ejecuta en PostgreSQL con los privilegios
-- de quien la CREA (aquí, el usuario que corre este script), no de quien la consulta. Eso
-- permite exponer datos combinados de varias tablas (asignatura + nombre del profesor) a un
-- rol que NUNCA tiene GRANT SELECT sobre la tabla origen (profesores) — así un estudiante
-- puede ver qué profesor da una asignatura sin que se le conceda acceso a `profesores`, y por
-- tanto sin poder ver columnas sensibles como Salario. Con GRANT sobre la tabla real esto no
-- sería posible: o se concede la tabla entera (con Salario incluido) o no se concede nada.

-- 1) Vista para el rol "estudiante": asignaturas con su profesor (sin Salario) y las
--    matrículas/notas asociadas. No filtra por alumno concreto (ver docs/vistas-por-rol.md,
--    apartado de alcance): es la misma vista para todos los usuarios de este rol.
CREATE OR REPLACE VIEW vista_estudiante AS
SELECT
    a.idasignatura,
    a.nombre       AS asignatura,
    a.creditos,
    a.curso,
    a.semestre,
    p.nombre       AS profesor_nombre,
    p.apellido     AS profesor_apellido,
    m.matricula,
    m.fechamatriculacion,
    m.notanumerica,
    m.notatexto
FROM asignaturas a
JOIN profesores p ON p.idprofesor = a.idprofesor
LEFT JOIN matriculas m ON m.idasignatura = a.idasignatura;

-- 2) Vista para el rol "profesor": informe agregado por asignatura (nº de alumnos
--    matriculados y nota media). El profesor ya tiene acceso directo a las tablas base,
--    así que aquí el valor de la vista no es ocultar columnas sino evitar recalcular a
--    mano el mismo agregado cada vez en el constructor de consultas.
CREATE OR REPLACE VIEW vista_profesor AS
SELECT
    a.idasignatura,
    a.nombre       AS asignatura,
    a.creditos,
    a.curso,
    a.semestre,
    p.nombre       AS profesor_nombre,
    p.apellido     AS profesor_apellido,
    COUNT(m.matricula)            AS num_alumnos_matriculados,
    ROUND(AVG(m.notanumerica), 2) AS nota_media
FROM asignaturas a
JOIN profesores p ON p.idprofesor = a.idprofesor
LEFT JOIN matriculas m ON m.idasignatura = a.idasignatura
GROUP BY a.idasignatura, a.nombre, a.creditos, a.curso, a.semestre, p.nombre, p.apellido;

-- 3) Se añaden como "tabla" por defecto del rol correspondiente, mismo mecanismo que las
--    tablas normales (role_default_tables -> precarga el checklist del panel de admin al
--    crear un usuario de ese rol; el GRANT SELECT real se hace en https_server.py igual que
--    para cualquier tabla). can_write siempre FALSE: son vistas de solo lectura.
INSERT INTO role_default_tables (role_name, table_name, can_write) VALUES
    ('estudiante', 'vista_estudiante', FALSE),
    ('profesor',   'vista_profesor',   FALSE)
ON CONFLICT (role_name, table_name) DO NOTHING;
