import sqlite3
from werkzeug.security import generate_password_hash


def init_sqlite_db(connection: sqlite3.Connection):
    """
    Inicializa el esquema relacional completo en SQLite para pruebas unitarias
    y ejecuciones locales offline Data-Light.
    """
    cursor = connection.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS rol (
        id_rol INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,
        descripcion TEXT
    );

    CREATE TABLE IF NOT EXISTS usuario (
        id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
        id_rol INTEGER NOT NULL,
        tipo_documento TEXT NOT NULL,
        documento TEXT NOT NULL,
        nombre TEXT NOT NULL,
        apellido TEXT NOT NULL,
        email TEXT UNIQUE,
        contrasena TEXT NOT NULL,
        telefono TEXT,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        estado TEXT NOT NULL DEFAULT 'activo',
        UNIQUE(tipo_documento, documento),
        FOREIGN KEY (id_rol) REFERENCES rol(id_rol)
    );

    CREATE TABLE IF NOT EXISTS parametro_sistema (
        clave TEXT PRIMARY KEY,
        valor TEXT NOT NULL,
        descripcion TEXT
    );

    CREATE TABLE IF NOT EXISTS sede (
        id_sede INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        codigo_dane TEXT,
        direccion TEXT,
        es_principal INTEGER NOT NULL DEFAULT 0,
        estado TEXT NOT NULL DEFAULT 'activa'
    );

    CREATE TABLE IF NOT EXISTS anio_lectivo (
        id_anio INTEGER PRIMARY KEY AUTOINCREMENT,
        anio INTEGER NOT NULL UNIQUE,
        fecha_inicio TEXT NOT NULL,
        fecha_fin TEXT NOT NULL,
        estado TEXT NOT NULL DEFAULT 'activo'
    );

    CREATE TABLE IF NOT EXISTS periodo (
        id_periodo INTEGER PRIMARY KEY AUTOINCREMENT,
        id_anio INTEGER NOT NULL,
        numero INTEGER NOT NULL,
        fecha_inicio TEXT NOT NULL,
        fecha_fin TEXT NOT NULL,
        estado TEXT NOT NULL DEFAULT 'abierto',
        UNIQUE(id_anio, numero),
        FOREIGN KEY (id_anio) REFERENCES anio_lectivo(id_anio)
    );

    CREATE TABLE IF NOT EXISTS curso (
        id_curso INTEGER PRIMARY KEY AUTOINCREMENT,
        id_sede INTEGER NOT NULL,
        id_anio INTEGER NOT NULL,
        nombre TEXT NOT NULL,
        grado INTEGER NOT NULL,
        jornada TEXT NOT NULL,
        UNIQUE(id_sede, id_anio, nombre),
        FOREIGN KEY (id_sede) REFERENCES sede(id_sede),
        FOREIGN KEY (id_anio) REFERENCES anio_lectivo(id_anio)
    );

    CREATE TABLE IF NOT EXISTS materia (
        id_materia INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS estudiante (
        id_estudiante INTEGER PRIMARY KEY AUTOINCREMENT,
        id_usuario INTEGER NOT NULL UNIQUE,
        direccion TEXT,
        fecha_nacimiento TEXT NOT NULL,
        puntaje_esa REAL DEFAULT 0.0,
        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
    );

    CREATE TABLE IF NOT EXISTS profesor (
        id_profesor INTEGER PRIMARY KEY AUTOINCREMENT,
        id_usuario INTEGER NOT NULL UNIQUE,
        especialidad TEXT NOT NULL,
        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
    );

    CREATE TABLE IF NOT EXISTS matricula (
        id_matricula INTEGER PRIMARY KEY AUTOINCREMENT,
        id_estudiante INTEGER NOT NULL,
        id_curso INTEGER NOT NULL,
        id_anio INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        estado TEXT NOT NULL DEFAULT 'activa',
        documentacion_fisica_entregada INTEGER NOT NULL DEFAULT 0,
        UNIQUE(id_estudiante, id_anio),
        FOREIGN KEY (id_estudiante) REFERENCES estudiante(id_estudiante),
        FOREIGN KEY (id_curso) REFERENCES curso(id_curso),
        FOREIGN KEY (id_anio) REFERENCES anio_lectivo(id_anio)
    );

    CREATE TABLE IF NOT EXISTS asignacion (
        id_asignacion INTEGER PRIMARY KEY AUTOINCREMENT,
        id_profesor INTEGER NOT NULL,
        id_materia INTEGER NOT NULL,
        id_curso INTEGER NOT NULL,
        UNIQUE(id_materia, id_curso),
        FOREIGN KEY (id_profesor) REFERENCES profesor(id_profesor),
        FOREIGN KEY (id_materia) REFERENCES materia(id_materia),
        FOREIGN KEY (id_curso) REFERENCES curso(id_curso)
    );

    CREATE TABLE IF NOT EXISTS horario (
        id_horario INTEGER PRIMARY KEY AUTOINCREMENT,
        id_asignacion INTEGER NOT NULL,
        dia_semana TEXT NOT NULL,
        hora_inicio TEXT NOT NULL,
        hora_fin TEXT NOT NULL,
        aula TEXT,
        FOREIGN KEY (id_asignacion) REFERENCES asignacion(id_asignacion)
    );

    CREATE TABLE IF NOT EXISTS actividad (
        id_actividad INTEGER PRIMARY KEY AUTOINCREMENT,
        id_asignacion INTEGER NOT NULL,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        fecha_entrega TEXT NOT NULL,
        estado TEXT NOT NULL DEFAULT 'pendiente',
        FOREIGN KEY (id_asignacion) REFERENCES asignacion(id_asignacion)
    );

    CREATE TABLE IF NOT EXISTS asistencia (
        id_asistencia INTEGER PRIMARY KEY AUTOINCREMENT,
        id_estudiante INTEGER NOT NULL,
        id_horario INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        estado TEXT NOT NULL,
        minutos_retraso INTEGER DEFAULT 0,
        valor_inasistencia REAL NOT NULL DEFAULT 0.0,
        observacion TEXT,
        id_usuario_registro INTEGER NOT NULL,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(id_estudiante, id_horario, fecha),
        FOREIGN KEY (id_estudiante) REFERENCES estudiante(id_estudiante),
        FOREIGN KEY (id_horario) REFERENCES horario(id_horario),
        FOREIGN KEY (id_usuario_registro) REFERENCES usuario(id_usuario)
    );

    CREATE TABLE IF NOT EXISTS calificacion (
        id_calificacion INTEGER PRIMARY KEY AUTOINCREMENT,
        id_estudiante INTEGER NOT NULL,
        id_asignacion INTEGER NOT NULL,
        id_periodo INTEGER NOT NULL,
        nota REAL NOT NULL,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        id_usuario_registro INTEGER NOT NULL,
        UNIQUE(id_estudiante, id_asignacion, id_periodo),
        FOREIGN KEY (id_estudiante) REFERENCES estudiante(id_estudiante),
        FOREIGN KEY (id_asignacion) REFERENCES asignacion(id_asignacion),
        FOREIGN KEY (id_periodo) REFERENCES periodo(id_periodo),
        FOREIGN KEY (id_usuario_registro) REFERENCES usuario(id_usuario)
    );

    CREATE TABLE IF NOT EXISTS alerta_ive (
        id_alerta INTEGER PRIMARY KEY AUTOINCREMENT,
        id_estudiante INTEGER NOT NULL,
        id_periodo INTEGER,
        valor_ive REAL NOT NULL,
        factor_ausentismo REAL NOT NULL,
        factor_rendimiento REAL NOT NULL,
        factor_socioeconomico REAL NOT NULL,
        nivel_riesgo TEXT NOT NULL,
        fecha_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_estudiante) REFERENCES estudiante(id_estudiante),
        FOREIGN KEY (id_periodo) REFERENCES periodo(id_periodo)
    );

    CREATE TABLE IF NOT EXISTS ficha_socioeconomica (
        id_ficha INTEGER PRIMARY KEY AUTOINCREMENT,
        id_estudiante INTEGER NOT NULL UNIQUE,
        distancia_kms REAL DEFAULT 0.0,
        tiempo_desplazamiento_min INTEGER DEFAULT 0,
        medio_transporte TEXT DEFAULT 'Caminata',
        acceso_transporte_escolar INTEGER DEFAULT 0,
        subsidio_alimentacion_pae INTEGER DEFAULT 1,
        grupo_sanguineo TEXT DEFAULT 'O+',
        proveedor_eps TEXT DEFAULT 'Sanitas Salud',
        alergias_condiciones TEXT DEFAULT 'Ninguna',
        contacto_emergencia_nombre TEXT,
        contacto_emergencia_telefono TEXT,
        direccion_domicilio TEXT,
        vulnerabilidad_score REAL DEFAULT 0.10,
        FOREIGN KEY (id_estudiante) REFERENCES estudiante(id_estudiante)
    );

    CREATE TABLE IF NOT EXISTS excusas (
        id_excusa INTEGER PRIMARY KEY AUTOINCREMENT,
        id_estudiante INTEGER NOT NULL,
        fecha_inicio TEXT NOT NULL,
        fecha_fin TEXT NOT NULL,
        motivo TEXT NOT NULL,
        descripcion TEXT,
        estado TEXT DEFAULT 'Pendiente',
        id_usuario_aprobador INTEGER,
        fecha_solicitud TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_estudiante) REFERENCES estudiante(id_estudiante),
        FOREIGN KEY (id_usuario_aprobador) REFERENCES usuario(id_usuario)
    );

    CREATE TABLE IF NOT EXISTS auditoria_notas (
        id_log INTEGER PRIMARY KEY AUTOINCREMENT,
        id_usuario INTEGER NOT NULL,
        id_estudiante INTEGER NOT NULL,
        accion TEXT NOT NULL,
        nota_anterior REAL,
        nota_nueva REAL,
        motivo_cambio TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario),
        FOREIGN KEY (id_estudiante) REFERENCES estudiante(id_estudiante)
    );

    CREATE TABLE IF NOT EXISTS log_actividad (
        id_log INTEGER PRIMARY KEY AUTOINCREMENT,
        sello_tiempo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        administrador TEXT NOT NULL,
        modulo TEXT NOT NULL,
        accion TEXT NOT NULL,
        estado TEXT NOT NULL DEFAULT 'AUDITADO'
    );

    CREATE TABLE IF NOT EXISTS configuracion_usuario (
        id_config INTEGER PRIMARY KEY AUTOINCREMENT,
        id_usuario INTEGER NOT NULL UNIQUE,
        umbral_inasistencia_critica REAL DEFAULT 15.0,
        umbral_rendimiento_bajo REAL DEFAULT 3.0,
        notificar_alertas_automaticas INTEGER DEFAULT 1,
        firma_digital_url TEXT,
        FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
    );

    CREATE TABLE IF NOT EXISTS salon_espacio (
        id_salon INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL,
        nombre TEXT NOT NULL,
        sede_bloque TEXT NOT NULL,
        capacidad INTEGER NOT NULL DEFAULT 35,
        equipamiento TEXT,
        estado TEXT NOT NULL DEFAULT 'Disponible'
    );
    """)

    # Sembrar Catálogos Base
    roles_base = [
        ('administrador', 'Super Administrador', 'Control global del sistema y sedes'),
        ('rector', 'Rector / Directivo', 'Supervisión multi-sede, cierre de periodos y alertas rojas'),
        ('administrativo', 'Secretaría Académica', 'Matrículas Data-Light y gestión de excusas'),
        ('docente', 'Docente de Aula', 'Planillas y pase de lista diario'),
        ('estudiante', 'Estudiante', 'Consulta de calificaciones y horarios'),
        ('acudiente', 'Padre / Acudiente', 'Seguimiento de permanencia escolar')
    ]
    for codigo, nombre, desc in roles_base:
        cursor.execute("INSERT OR IGNORE INTO rol (codigo, nombre, descripcion) VALUES (?, ?, ?)", (codigo, nombre, desc))

    parametros = [
        ('peso_retraso', '0.50', 'Ponderación de retraso frente a inasistencia total'),
        ('tiempo_gracia_retraso_min', '15', 'Minutos antes de contar como retraso'),
        ('tiempo_gracia_ausente_min', '30', 'Minutos tras los cuales cuenta como ausencia'),
        ('ive_umbral_naranja', '0.40', 'Umbral de riesgo medio'),
        ('ive_umbral_rojo', '0.70', 'Umbral de riesgo crítico de deserción')
    ]
    for clave, val, desc in parametros:
        cursor.execute("INSERT OR IGNORE INTO parametro_sistema (clave, valor, descripcion) VALUES (?, ?, ?)", (clave, val, desc))

    sedes = [
        ('Sede Principal Santa Ana', '120001001001', 'Km 5 Vía Corregimiento Santa Ana', 1),
        ('Sede Rural La Vega', '120001001002', 'Vereda La Vega', 0),
        ('Sede Rural El Jabo', '120001001003', 'Vereda El Jabo', 0),
        ('Sede Rural Guacoche', '120001001004', 'Corregimiento de Guacoche', 0),
        ('Sede Rural Guacochito', '120001001005', 'Corregimiento de Guacochito', 0),
        ('Sede Rural Los Corazones', '120001001006', 'Corregimiento Los Corazones', 0),
        ('Sede Rural Las Raíces', '120001001007', 'Corregimiento Las Raíces', 0),
        ('Sede Rural El Alto de la Vuelta', '120001001008', 'Vereda El Alto', 0),
        ('Sede Rural Badillo', '120001001009', 'Corregimiento de Badillo', 0),
        ('Sede Rural Patillal', '120001001010', 'Corregimiento de Patillal', 0),
        ('Sede Rural Atánquez', '120001001011', 'Corregimiento de Atánquez', 0)
    ]
    for nom, dane, dir_, princ in sedes:
        cursor.execute("INSERT OR IGNORE INTO sede (nombre, codigo_dane, direccion, es_principal) VALUES (?, ?, ?, ?)", (nom, dane, dir_, princ))

    materias = [
        'Matemáticas', 'Lengua Castellana', 'Ciencias Naturales', 'Ciencias Sociales', 'Inglés',
        'Cálculo Integral', 'Química Orgánica', 'Filosofía y Ética', 'Biología Celular', 'Economía Política'
    ]
    for m in materias:
        cursor.execute("INSERT OR IGNORE INTO materia (nombre) VALUES (?)", (m,))

    cursor.execute("INSERT OR IGNORE INTO anio_lectivo (anio, fecha_inicio, fecha_fin, estado) VALUES (2026, '2026-01-20', '2026-11-30', 'activo')")
    cursor.execute("INSERT OR IGNORE INTO periodo (id_anio, numero, fecha_inicio, fecha_fin, estado) VALUES (1, 1, '2026-01-20', '2026-04-10', 'abierto')")
    cursor.execute("INSERT OR IGNORE INTO periodo (id_anio, numero, fecha_inicio, fecha_fin, estado) VALUES (1, 2, '2026-04-11', '2026-06-20', 'abierto')")

    cursor.execute("INSERT OR IGNORE INTO curso (id_sede, id_anio, nombre, grado, jornada) VALUES (1, 1, 'Matemáticas 9-A', 9, 'manana')")
    cursor.execute("INSERT OR IGNORE INTO curso (id_sede, id_anio, nombre, grado, jornada) VALUES (1, 1, 'Grado 6° A', 6, 'manana')")
    cursor.execute("INSERT OR IGNORE INTO curso (id_sede, id_anio, nombre, grado, jornada) VALUES (1, 1, 'Grado 7° A', 7, 'manana')")
    cursor.execute("INSERT OR IGNORE INTO curso (id_sede, id_anio, nombre, grado, jornada) VALUES (1, 1, 'Undécimo Grado (11º) - Grupo A', 11, 'manana')")

    salones = [
        ('A-101', 'Laboratorio de Ciencias', 'Urbana Bloque Norte Piso 1', 35, 'Proyector, 12 Mesas', 'Disponible'),
        ('B-204', 'Aula General', 'Urbana Bloque Sur Piso 2', 40, 'Pupitres, Smart TV', 'Ocupado'),
        ('R-02', 'Biblioteca Rural', 'Rural Módulo Principal', 20, 'Estantería, 4 Computadores', 'Mantenimiento'),
        ('C-305', 'Sala de Sistemas', 'Urbana Bloque Norte Piso 3', 30, '30 PCs, Fibra Óptica', 'Disponible')
    ]
    for cod, nom, blq, cap, eq, est in salones:
        cursor.execute("INSERT OR IGNORE INTO salon_espacio (codigo, nombre, sede_bloque, capacidad, equipamiento, estado) VALUES (?, ?, ?, ?, ?, ?)", (cod, nom, blq, cap, eq, est))

    logs_actividad = [
        ('2026-11-09 14:22:10', 'Juan Delgado', 'Matrículas', 'Modificación de estatus: Alumno #99281 a "Activo"', 'AUDITADO'),
        ('2026-11-09 13:45:02', 'María Rojas', 'Docentes', 'Carga masiva de calificaciones 3er Lapso - Curso 4-B', 'AUDITADO'),
        ('2026-11-09 11:10:55', 'System Admin', 'Seguridad', 'Intento de acceso fallido desde IP 192.168.1.104', 'ALERTA'),
        ('2026-11-09 09:30:15', 'Juan Delgado', 'Reportes', 'Generación de Certificado Legal PDF Alumno #10223', 'AUDITADO')
    ]
    for st, adm, mod, acc, est in logs_actividad:
        cursor.execute("INSERT OR IGNORE INTO log_actividad (sello_tiempo, administrador, modulo, accion, estado) VALUES (?, ?, ?, ?, ?)", (st, adm, mod, acc, est))

    connection.commit()
    cursor.close()
