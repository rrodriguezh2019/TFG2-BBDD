-- Insertar estudiantes
INSERT INTO Estudiantes (Matricula, Nombre, Apellido, Telefono, CorreoElectronico, Direccion, Edad)
VALUES
    (1001, 'Juan', 'Perez', '555-1234', 'juan.perez@dominio1.com', 'Calle Flores 14', '25'),
    (1002, 'Maria', 'Lopez', '555-5678', 'maria.lopez@dominio2.com', 'Avenida Sol 9', '23'),
    (1003, 'Luis', 'Gonzalez', '555-9876', 'luis.gonzalez@ejemplo.com', 'Calle Luna 22', '18'),
    (1004, 'Ana', 'Martinez', '555-4321', 'ana.martinez@correo.com', 'Avenida Rio 7', '20'),
    (1005, 'Carlos', 'Rodriguez', '555-8765', 'carlos.rodriguez@dominio1.com', 'Calle Estrella 3', '25'),
    (1006, 'Laura', 'Fernandez', '555-2345', 'laura.fernandez@dominio2.com', 'Avenida Mar 15', '21'),
    (1007, 'Miguel', 'Sanchez', '555-3456', 'miguel.sanchez@ejemplo.com', 'Calle Monte 10', '21'),
    (1008, 'Isabel', 'Luna', '555-6543', 'isabel.luna@correo.com', 'Avenida Sol 5', '22'),
    (1009, 'Javier', 'Diaz', '555-7890', 'javier.diaz@dominio1.com', 'Calle Rio 18', '19'),
    (1010, 'Sofia', 'Ortega', '555-8765', 'sofia.ortega@dominio2.com', 'Avenida Estrella 12', '20');

-- Insertar profesores
INSERT INTO Profesores (IDProfesor, Nombre, Apellido, CorreoElectronico, Departamento, Salario)
VALUES
    (2001, 'Juan', 'Lopez', 'juan.lopez@ing.com', 'Ingenieria', 30000.00),
    (2002, 'Maria', 'Garcia', 'maria.garcia@ccss.com', 'Ciencias Sociales', 35000.00),
    (2003, 'Luis', 'Martinez', 'luis.martinez@csalud.com', 'Ciencias Salud', 37000.00),
    (2004, 'Ana', 'Rodriguez', 'ana.rodriguez@ing.com', 'Ingenieria', 32000.00),
    (2005, 'Carlos', 'Fernandez', 'carlos.fernandez@ccss.com', 'Ciencias Sociales', 38000.00),
    (2006, 'Laura', 'Gomez', 'laura.gomez@csalud.com', 'Ciencias Salud', 29000.00),
    (2007, 'Miguel', 'Perez', 'miguel.perez@ing.com', 'Ingenieria', 31000.00),
    (2008, 'Isabel', 'Sanchez', 'isabel.sanchez@ccss.com', 'Ciencias Sociales', 34000.00),
    (2009, 'Javier', 'Diaz', 'javier.diaz@csalud.com', 'Ciencias Salud', 36000.00);
	
	-- Insertar asignaturas
INSERT INTO Asignaturas (IDAsignatura, Nombre, Creditos, Curso, Semestre, IDProfesor)
VALUES
    (3001, 'Biologia', 4, 1, 2, 2006),
    (3002, 'Quimica', 3, 1, 2, 2005),
    (3003, 'Biomecanica', 2, 1, 1, 2009),
    (3004, 'Derecho', 5, 2, 2, 2008),
    (3005, 'Historia', 3, 2, 1, 2007),
    (3006, 'Economia', 6, 2, 2, 2002),
    (3007, 'Matematicas', 4, 3, 1, 2001),
    (3008, 'Programacion', 6, 3, 1, 2004),
    (3009, 'Fisica', 3, 3, 1, 2003);

-- Insertar matriculas aleatorias
-- Cada estudiante puede tener entre 1 y 5 asignaturas matriculadas
INSERT INTO Matriculas (Matricula, IDAsignatura, FechaMatriculacion, NotaNumerica, NotaTexto)
VALUES
    -- Matriculas para el estudiante 1001
    (1001, 3002, '2022-02-20', 3.8, 'SUSPENSO'),
    (1001, 3001, '2021-01-15', 5.3, 'SUFICIENTE'),
    (1001, 3004, '2022-01-16', 9.2, 'SOBRESALIENTE'),
    (1001, 3007, '2023-01-17', 6.8, 'BIEN'),
    -- Matriculas para el estudiante 1002
    (1002, 3003, '2023-02-10', 6.0, 'BIEN'),
    (1002, 3005, '2022-02-11', 7.7, 'NOTABLE'),
    (1002, 3008, '2022-02-12', 9.5, 'SOBRESALIENTE'),
-- Matrículas adicionales para el estudiante 1003
    (1003, 3006, '2023-03-05', 9.0, 'SOBRESALIENTE'),
    (1003, 3009, '2021-03-06', 9.3, 'SOBRESALIENTE'),
    (1003, 3001, '2020-03-07', 2.1, 'SUSPENSO'),
    (1003, 3005, '2022-03-08', 7.6, 'NOTABLE'),
-- Matrículas adicionales para el estudiante 1004
    (1004, 3003, '2021-04-10', 6.8, 'BIEN'),
    (1004, 3007, '2022-04-11', 5.3, 'SUFICIENTE'),
    (1004, 3008, '2020-04-12', 7.9, 'NOTABLE'),
-- Matrículas adicionales para el estudiante 1005
    (1005, 3002, '2023-05-15', 6.5, 'BIEN'),
    (1005, 3006, '2023-05-16', 9.2, 'SOBRESALIENTE'),
-- Matrículas adicionales para el estudiante 1006
    (1006, 3003, '2023-06-20', 7.9, 'NOTABLE'),
    (1006, 3005, '2022-06-21', 8.2, 'NOTABLE'),
    (1006, 3009, '2021-01-22', 7.1, 'NOTABLE'),
-- Matrícula adicional para el estudiante 1007
    (1007, 3006, '2023-07-05', 6.8, 'BIEN'),
-- Matrículas adicionales para el estudiante 1008
    (1008, 3001, '2023-01-10', 7.5, 'NOTABLE'),
    (1008, 3002, '2022-01-11', 5.6, 'SUFICIENTE'),
    (1008, 3004, '2023-06-12', 8.7, 'NOTABLE'),
    (1008, 3007, '2021-06-13', 6.3, 'BIEN'),
    (1008, 3009, '2022-06-14', 10.0, 'MATRICULA'),
-- Matrículas adicionales para el estudiante 1009
    (1009, 3002, '2023-09-15', 5.7, 'SUFICIENTE'),
    (1009, 3005, '2023-09-16', 3.9, 'SUSPENSO'),
    (1009, 3008, '2023-09-17', 6.6, 'BIEN'),
    (1009, 3009, '2023-09-18', 7.8, 'NOTABLE'),
-- Matrículas adicionales para el estudiante 1010
    (1010, 3001, '2023-01-20', 9.3, 'SOBRESALIENTE'),
    (1010, 3004, '2023-09-21', 8.8, 'NOTABLE'),
    (1010, 3008, '2023-10-22', 7.2, 'NOTABLE');


