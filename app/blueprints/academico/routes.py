from datetime import date
from flask import request, g
from app.blueprints.academico import academico_bp
from app.database import query_db, execute_db
from app.utils.decorators import jwt_requerido, requiere_rol
from app.utils.responses import success_response, error_response
from app.utils.security import hash_password


@academico_bp.route("/sedes", methods=["GET"])
def listar_sedes():
    """Retorna el catálogo de sedes y conteo de matriculados."""
    sedes = query_db("""
        SELECT s.id_sede, s.nombre, s.codigo_dane, s.direccion, s.es_principal, s.estado,
               COUNT(c.id_curso) AS total_cursos
        FROM sede s
        LEFT JOIN curso c ON c.id_sede = s.id_sede
        GROUP BY s.id_sede, s.nombre, s.codigo_dane, s.direccion, s.es_principal, s.estado
        ORDER BY s.es_principal DESC, s.nombre ASC
    """)
    return success_response(sedes, "Sedes obtenidas")


@academico_bp.route("/cursos", methods=["GET"])
def listar_cursos():
    """Retorna los cursos activos con su sede y año lectivo."""
    cursos = query_db("""
        SELECT c.id_curso, c.nombre, c.grado, c.jornada, s.nombre AS sede_nombre, a.anio
        FROM curso c
        JOIN sede s ON s.id_sede = c.id_sede
        JOIN anio_lectivo a ON a.id_anio = c.id_anio
        ORDER BY c.grado ASC, c.nombre ASC
    """)
    return success_response(cursos, "Cursos obtenidos")


@academico_bp.route("/materias", methods=["GET"])
def listar_materias():
    """Catálogo de materias institucionales."""
    materias = query_db("SELECT id_materia, nombre FROM materia ORDER BY nombre ASC")
    return success_response(materias, "Materias obtenidas")


@academico_bp.route("/matriculas", methods=["GET"])
def listar_matriculas():
    """Listado de estudiantes matriculados Data-Light."""
    id_curso = request.args.get("id_curso")
    sql = """
        SELECT m.id_matricula, m.fecha, m.estado, m.documentacion_fisica_entregada,
               e.id_estudiante, e.direccion, e.fecha_nacimiento, e.puntaje_esa,
               u.nombre, u.apellido, u.tipo_documento, u.documento, u.email,
               c.nombre AS curso_nombre, c.grado, s.nombre AS sede_nombre
        FROM matricula m
        JOIN estudiante e ON e.id_estudiante = m.id_estudiante
        JOIN usuario u ON u.id_usuario = e.id_usuario
        JOIN curso c ON c.id_curso = m.id_curso
        JOIN sede s ON s.id_sede = c.id_sede
    """
    args = []
    if id_curso:
        sql += " WHERE m.id_curso = %s"
        args.append(id_curso)
    sql += " ORDER BY c.grado ASC, u.apellido ASC, u.nombre ASC"

    registros = query_db(sql, tuple(args))
    return success_response(registros, "Matrículas obtenidas")


@academico_bp.route("/matriculas", methods=["POST"])
def crear_matricula():
    """
    Matriculación Data-Light:
    1. Valida unicidad estricta (tipo_documento + documento) -> 409 Conflict si existe.
    2. Crea usuario con rol 'estudiante' (id_rol=5) y contraseña por defecto.
    3. Crea registro en tabla 'estudiante'.
    4. Vincula al curso y año lectivo activo con bandera documentacion_fisica_entregada.
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("El cuerpo de la solicitud debe ser JSON válido", status_code=400)

    campos = ["tipo_documento", "documento", "nombre", "apellido", "id_curso", "fecha_nacimiento"]
    for c in campos:
        if not data.get(c):
            return error_response(f"El campo '{c}' es obligatorio", status_code=400)

    tipo_doc = str(data["tipo_documento"]).strip().upper()
    documento = str(data["documento"]).strip()
    nombre = str(data["nombre"]).strip()
    apellido = str(data["apellido"]).strip()
    fecha_nacimiento = str(data["fecha_nacimiento"]).strip()
    id_curso = int(data["id_curso"])
    direccion = data.get("direccion", "Zona Rural")
    puntaje_esa = float(data.get("puntaje_esa", 0.20))
    doc_entregada = 1 if data.get("documentacion_fisica_entregada") in [True, 1, "1", "true"] else 0

    # 1. Validar duplicado de documento
    existente = query_db(
        "SELECT id_usuario FROM usuario WHERE tipo_documento = %s AND documento = %s",
        (tipo_doc, documento),
        one=True
    )
    if existente:
        return error_response(
            "Conflicto: Ya existe un estudiante o usuario registrado con este tipo y número de documento",
            status_code=409
        )

    # 2. Obtener rol de estudiante (codigo 'estudiante')
    rol_estudiante = query_db("SELECT id_rol FROM rol WHERE codigo = 'estudiante'", one=True)
    id_rol = rol_estudiante["id_rol"] if rol_estudiante else 5

    # 3. Obtener año lectivo activo
    anio_activo = query_db("SELECT id_anio FROM anio_lectivo WHERE estado = 'activo' ORDER BY anio DESC", one=True)
    if not anio_activo:
        return error_response("No se encontró un año lectivo activo en el sistema", status_code=422)
    id_anio = anio_activo["id_anio"]

    # Crear usuario
    contrasena_hasheada = hash_password(f"{documento}*")
    usr_res = execute_db(
        """
        INSERT INTO usuario (id_rol, tipo_documento, documento, nombre, apellido, email, contrasena, estado)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'activo')
        """,
        (id_rol, tipo_doc, documento, nombre, apellido, f"{documento}@estudiante.santana.edu.co", contrasena_hasheada)
    )

    # Si es SQLite podemos obtener id_usuario
    id_usuario = usr_res["lastrowid"]
    if not id_usuario:
        u = query_db("SELECT id_usuario FROM usuario WHERE tipo_documento = %s AND documento = %s", (tipo_doc, documento), one=True)
        id_usuario = u["id_usuario"]

    # Crear estudiante
    est_res = execute_db(
        """
        INSERT INTO estudiante (id_usuario, direccion, fecha_nacimiento, puntaje_esa)
        VALUES (%s, %s, %s, %s)
        """,
        (id_usuario, direccion, fecha_nacimiento, puntaje_esa)
    )
    id_estudiante = est_res["lastrowid"]
    if not id_estudiante:
        e = query_db("SELECT id_estudiante FROM estudiante WHERE id_usuario = %s", (id_usuario,), one=True)
        id_estudiante = e["id_estudiante"]

    # Crear matrícula
    mat_res = execute_db(
        """
        INSERT INTO matricula (id_estudiante, id_curso, id_anio, fecha, estado, documentacion_fisica_entregada)
        VALUES (%s, %s, %s, %s, 'activa', %s)
        """,
        (id_estudiante, id_curso, id_anio, date.today().isoformat(), doc_entregada)
    )

    return success_response({
        "id_matricula": mat_res["lastrowid"],
        "id_estudiante": id_estudiante,
        "estudiante": f"{nombre} {apellido}",
        "documento": f"{tipo_doc} {documento}",
        "id_curso": id_curso,
        "documentacion_fisica_entregada": bool(doc_entregada)
    }, message="Matrícula Data-Light registrada exitosamente", status_code=201)


@academico_bp.route("/horarios", methods=["GET"])
def listar_horarios():
    """Lista la programación horaria con detalles del docente, curso y aula."""
    id_curso = request.args.get("id_curso")
    sql = """
        SELECT h.id_horario, h.dia_semana, h.hora_inicio, h.hora_fin, h.aula,
               m.nombre AS materia_nombre, c.nombre AS curso_nombre,
               u.nombre AS profesor_nombre, u.apellido AS profesor_apellido,
               a.id_profesor, a.id_curso
        FROM horario h
        JOIN asignacion a ON a.id_asignacion = h.id_asignacion
        JOIN materia m ON m.id_materia = a.id_materia
        JOIN curso c ON c.id_curso = a.id_curso
        JOIN profesor p ON p.id_profesor = a.id_profesor
        JOIN usuario u ON u.id_usuario = p.id_usuario
    """
    args = []
    if id_curso:
        sql += " WHERE a.id_curso = %s"
        args.append(id_curso)
    sql += " ORDER BY CASE h.dia_semana WHEN 'lunes' THEN 1 WHEN 'martes' THEN 2 WHEN 'miercoles' THEN 3 WHEN 'jueves' THEN 4 WHEN 'viernes' THEN 5 ELSE 6 END, h.hora_inicio ASC"

    horarios = query_db(sql, tuple(args))
    return success_response(horarios, "Horarios obtenidos")


@academico_bp.route("/horarios", methods=["POST"])
def crear_horario():
    """
    Asignación de bloque horario con algoritmo estricto de prevención de choques:
    Choque = (A.hora_inicio < B.hora_fin) AND (A.hora_fin > B.hora_inicio)
    Valida cruces de profesor o aula en el mismo día. Retorna 422 si hay solapamiento.
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("JSON requerido", status_code=400)

    campos = ["id_asignacion", "dia_semana", "hora_inicio", "hora_fin"]
    for c in campos:
        if not data.get(c):
            return error_response(f"El campo '{c}' es obligatorio", status_code=400)

    id_asignacion = int(data["id_asignacion"])
    dia_semana = str(data["dia_semana"]).strip().lower()
    hora_inicio = str(data["hora_inicio"]).strip()
    hora_fin = str(data["hora_fin"]).strip()
    aula = data.get("aula", "Aula General")

    if hora_fin <= hora_inicio:
        return error_response("La hora de fin debe ser posterior a la hora de inicio", status_code=400)

    # Obtener el profesor y curso de la asignación
    asignacion = query_db(
        "SELECT id_profesor, id_curso, id_materia FROM asignacion WHERE id_asignacion = %s",
        (id_asignacion,),
        one=True
    )
    if not asignacion:
        return error_response("La asignación académica no existe", status_code=404)

    id_profesor = asignacion["id_profesor"]

    # ALGORITMO ANTI-COLISIÓN (Choque horario):
    # 1. Validar que el profesor no tenga otra clase en ese tramo horario
    solapamiento_profesor = query_db("""
        SELECT h.id_horario, h.hora_inicio, h.hora_fin, m.nombre AS materia, c.nombre AS curso
        FROM horario h
        JOIN asignacion a ON a.id_asignacion = h.id_asignacion
        JOIN materia m ON m.id_materia = a.id_materia
        JOIN curso c ON c.id_curso = a.id_curso
        WHERE a.id_profesor = %s
          AND h.dia_semana = %s
          AND (h.hora_inicio < %s AND h.hora_fin > %s)
    """, (id_profesor, dia_semana, hora_fin, hora_inicio), one=True)

    if solapamiento_profesor:
        return error_response(
            f"Colisión de Horario: El docente ya tiene asignada la materia '{solapamiento_profesor['materia']}' "
            f"en '{solapamiento_profesor['curso']}' de {solapamiento_profesor['hora_inicio']} a {solapamiento_profesor['hora_fin']}",
            status_code=422
        )

    # 2. Validar que el aula no esté ocupada en ese tramo horario
    if aula:
        solapamiento_aula = query_db("""
            SELECT h.id_horario, h.hora_inicio, h.hora_fin, c.nombre AS curso
            FROM horario h
            JOIN asignacion a ON a.id_asignacion = h.id_asignacion
            JOIN curso c ON c.id_curso = a.id_curso
            WHERE h.aula = %s
              AND h.dia_semana = %s
              AND (h.hora_inicio < %s AND h.hora_fin > %s)
        """, (aula, dia_semana, hora_fin, hora_inicio), one=True)

        if solapamiento_aula:
            return error_response(
                f"Colisión de Aula: El aula '{aula}' ya se encuentra ocupada por '{solapamiento_aula['curso']}' "
                f"de {solapamiento_aula['hora_inicio']} a {solapamiento_aula['hora_fin']}",
                status_code=422
            )

    # Inserción segura del bloque horario
    resultado = execute_db("""
        INSERT INTO horario (id_asignacion, dia_semana, hora_inicio, hora_fin, aula)
        VALUES (%s, %s, %s, %s, %s)
    """, (id_asignacion, dia_semana, hora_inicio, hora_fin, aula))

    return success_response({
        "id_horario": resultado["lastrowid"],
        "id_asignacion": id_asignacion,
        "dia_semana": dia_semana,
        "hora_inicio": hora_inicio,
        "hora_fin": hora_fin,
        "aula": aula
    }, message="Horario asignado exitosamente sin colisiones", status_code=201)

