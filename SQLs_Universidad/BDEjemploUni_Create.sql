-- Tabla de Estudiantes
CREATE TABLE Estudiantes (
    Matricula INT PRIMARY KEY,
    Nombre VARCHAR(50),
    Apellido VARCHAR(50),
    Telefono VARCHAR(15),
    CorreoElectronico VARCHAR(100),
    Direccion VARCHAR(100),
    Edad INT
);

-- Tabla de Profesores
CREATE TABLE Profesores (
    IDProfesor INT PRIMARY KEY,
    Nombre VARCHAR(50),
    Apellido VARCHAR(50),
    CorreoElectronico VARCHAR(100),
    Departamento VARCHAR(50),
    Salario DECIMAL(10, 2)
);

-- Tabla de Asignaturas
CREATE TABLE Asignaturas (
    IDAsignatura INT PRIMARY KEY,
    Nombre VARCHAR(100),
    Creditos INT,
    Curso INT,
    Semestre INT,
    IDProfesor INT,
    FOREIGN KEY (IDProfesor) REFERENCES Profesores(IDProfesor)
);

-- Tabla de Matriculas
CREATE TABLE Matriculas (
    Matricula INT,
    IDAsignatura INT,
    FechaMatriculacion DATE,
    NotaNumerica DECIMAL(4, 2),
    NotaTexto VARCHAR(50),
    PRIMARY KEY (Matricula, IDAsignatura),
    FOREIGN KEY (Matricula) REFERENCES Estudiantes(Matricula),
    FOREIGN KEY (IDAsignatura) REFERENCES Asignaturas(IDAsignatura)
);
