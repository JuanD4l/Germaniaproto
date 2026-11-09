-- =====================================================================
--  SENA / Proyecto Germania - Esquema Relacional para PostgreSQL (Render)
--  Base de datos: colegio_rural
-- =====================================================================

-- 1. TABLAS DE SEGURIDAD Y RBAC
CREATE TABLE IF NOT EXISTS rol (
    id_rol SERIAL PRIMARY KEY,
    codigo VARCHAR(30) NOT NULL UNIQUE,
    nombre VARCHAR(60) NOT NULL,
    descripcion VARCHAR(200)
);

CREATE TABLE IF NOT EXISTS usuario (
    id_usuario SERIAL PRIMARY KEY,
    id_rol INT NOT NULL REFERENCES rol(id_rol) ON UPDATE CASCADE ON DELETE RESTRICT,
    tipo_documento VARCHAR(10) NOT NULL,
    documento VARCHAR(20) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE,
    contrasena VARCHAR(255) NOT NULL,
    telefono VARCHAR(15),
    fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(20) NOT NULL DEFAULT 'activo',
    CONSTRAINT uq_usuario_doc UNIQUE (tipo_documento, documento)
);

CREATE TABLE IF NOT EXISTS parametro_sistema (
    clave VARCHAR(50) PRIMARY KEY,
    valor VARCHAR(100) NOT NULL,
    descripcion VARCHAR(200)
);

-- 2. ESTRUCTURA INSTITUCIONAL
CREATE TABLE IF NOT EXISTS sede (
    id_sede SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    codigo_dane VARCHAR(15),
    direccion VARCHAR(200),
    es_principal BOOLEAN NOT NULL DEFAULT FALSE,
    estado VARCHAR(20) NOT NULL DEFAULT 'activa'
);

CREATE TABLE IF NOT EXISTS anio_lectivo (
    id_anio SERIAL PRIMARY KEY,
    anio SMALLINT NOT NULL UNIQUE,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'activo',
    CONSTRAINT ck_anio_fechas CHECK (fecha_fin > fecha_inicio)
);

CREATE TABLE IF NOT EXISTS periodo (
    id_periodo SERIAL PRIMARY KEY,
    id_anio INT NOT NULL REFERENCES anio_lectivo(id_anio) ON UPDATE CASCADE ON DELETE RESTRICT,
    numero SMALLINT NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'abierto',
    CONSTRAINT uq_periodo UNIQUE (id_anio, numero),
    CONSTRAINT ck_periodo_num CHECK (numero BETWEEN 1 AND 4),
    CONSTRAINT ck_periodo_fechas CHECK (fecha_fin > fecha_inicio)
);

CREATE TABLE IF NOT EXISTS curso (
    id_curso SERIAL PRIMARY KEY,
    id_sede INT NOT NULL REFERENCES sede(id_sede) ON UPDATE CASCADE ON DELETE RESTRICT,
    id_anio INT NOT NULL REFERENCES anio_lectivo(id_anio) ON UPDATE CASCADE ON DELETE RESTRICT,
    nombre VARCHAR(50) NOT NULL,
    grado SMALLINT NOT NULL CHECK (grado BETWEEN 0 AND 11),
    jornada VARCHAR(20) NOT NULL,
    CONSTRAINT uq_curso_sede_anio UNIQUE (id_sede, id_anio, nombre)
);

CREATE TABLE IF NOT EXISTS materia (
    id_materia SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE
);

-- 3. PERSONAS
CREATE TABLE IF NOT EXISTS estudiante (
    id_estudiante SERIAL PRIMARY KEY,
    id_usuario INT NOT NULL UNIQUE REFERENCES usuario(id_usuario) ON UPDATE CASCADE ON DELETE RESTRICT,
    direccion VARCHAR(200),
    fecha_nacimiento DATE NOT NULL,
    puntaje_esa DECIMAL(4,2) DEFAULT 0.0 -- Encuesta Socioeconómica de Vulnerabilidad (0.0 a 1.0)
);

CREATE TABLE IF NOT EXISTS profesor (
    id_profesor SERIAL PRIMARY KEY,
    id_usuario INT NOT NULL UNIQUE REFERENCES usuario(id_usuario) ON UPDATE CASCADE ON DELETE RESTRICT,
    especialidad VARCHAR(100) NOT NULL
);

-- 4. MATRÍCULA Y ASIGNACIÓN
CREATE TABLE IF NOT EXISTS matricula (
    id_matricula SERIAL PRIMARY KEY,
    id_estudiante INT NOT NULL REFERENCES estudiante(id_estudiante) ON UPDATE CASCADE ON DELETE RESTRICT,
    id_curso INT NOT NULL REFERENCES curso(id_curso) ON UPDATE CASCADE ON DELETE RESTRICT,
    id_anio INT NOT NULL REFERENCES anio_lectivo(id_anio) ON UPDATE CASCADE ON DELETE RESTRICT,
    fecha DATE NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'activa',
    documentacion_fisica_entregada BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_matricula_est_anio UNIQUE (id_estudiante, id_anio)
);

CREATE TABLE IF NOT EXISTS asignacion (
    id_asignacion SERIAL PRIMARY KEY,
    id_profesor INT NOT NULL REFERENCES profesor(id_profesor) ON UPDATE CASCADE ON DELETE RESTRICT,
    id_materia INT NOT NULL REFERENCES materia(id_materia) ON UPDATE CASCADE ON DELETE RESTRICT,
    id_curso INT NOT NULL REFERENCES curso(id_curso) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT uq_asignacion UNIQUE (id_materia, id_curso)
);

CREATE TABLE IF NOT EXISTS horario (
    id_horario SERIAL PRIMARY KEY,
    id_asignacion INT NOT NULL REFERENCES asignacion(id_asignacion) ON UPDATE CASCADE ON DELETE RESTRICT,
    dia_semana VARCHAR(15) NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    aula VARCHAR(20),
    CONSTRAINT ck_horario_horas CHECK (hora_fin > hora_inicio)
);

CREATE TABLE IF NOT EXISTS actividad (
    id_actividad SERIAL PRIMARY KEY,
    id_asignacion INT NOT NULL REFERENCES asignacion(id_asignacion) ON UPDATE CASCADE ON DELETE CASCADE,
    titulo VARCHAR(150) NOT NULL,
    descripcion TEXT,
    fecha_entrega DATE NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente'
);

CREATE TABLE IF NOT EXISTS asistencia (
    id_asistencia SERIAL PRIMARY KEY,
    id_estudiante INT NOT NULL REFERENCES estudiante(id_estudiante) ON UPDATE CASCADE ON DELETE RESTRICT,
    id_horario INT NOT NULL REFERENCES horario(id_horario) ON UPDATE CASCADE ON DELETE RESTRICT,
    fecha DATE NOT NULL,
    estado VARCHAR(20) NOT NULL CHECK (estado IN ('presente', 'retraso', 'ausente', 'excusa')),
    minutos_retraso INT DEFAULT 0,
    valor_inasistencia DECIMAL(3,2) NOT NULL DEFAULT 0.0,
    observacion VARCHAR(255),
    id_usuario_registro INT NOT NULL REFERENCES usuario(id_usuario),
    fecha_registro TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_asistencia UNIQUE (id_estudiante, id_horario, fecha)
);

CREATE TABLE IF NOT EXISTS calificacion (
    id_calificacion SERIAL PRIMARY KEY,
    id_estudiante INT NOT NULL REFERENCES estudiante(id_estudiante) ON UPDATE CASCADE ON DELETE RESTRICT,
    id_asignacion INT NOT NULL REFERENCES asignacion(id_asignacion) ON UPDATE CASCADE ON DELETE RESTRICT,
    id_periodo INT NOT NULL REFERENCES periodo(id_periodo) ON UPDATE CASCADE ON DELETE RESTRICT,
    nota DECIMAL(3,1) NOT NULL CHECK (nota BETWEEN 0.0 AND 5.0),
    fecha_registro TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    id_usuario_registro INT NOT NULL REFERENCES usuario(id_usuario),
    CONSTRAINT uq_calificacion UNIQUE (id_estudiante, id_asignacion, id_periodo)
);

CREATE TABLE IF NOT EXISTS alerta_ive (
    id_alerta SERIAL PRIMARY KEY,
    id_estudiante INT NOT NULL REFERENCES estudiante(id_estudiante) ON UPDATE CASCADE ON DELETE RESTRICT,
    id_periodo INT REFERENCES periodo(id_periodo) ON UPDATE CASCADE ON DELETE RESTRICT,
    valor_ive DECIMAL(4,3) NOT NULL,
    factor_ausentismo DECIMAL(4,3) NOT NULL,
    factor_rendimiento DECIMAL(4,3) NOT NULL,
    factor_socioeconomico DECIMAL(4,3) NOT NULL,
    nivel_riesgo VARCHAR(20) NOT NULL CHECK (nivel_riesgo IN ('verde', 'naranja', 'rojo')),
    fecha_calculo TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
