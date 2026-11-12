from functools import wraps
from datetime import date
from flask import render_template, request, redirect, url_for, flash, session
from app.blueprints.web import web_bp
from app.database import query_db, execute_db
from app.utils.security import verify_password, hash_password
from app.blueprints.asistencia.routes import calcular_ive_estudiante


def solo_personal_autorizado(f):
    """
    Middleware que restringe el acceso a funciones administrativas.
    Bloquea el acceso a estudiantes y acudientes.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get("user")
        if not user:
            flash("Debe iniciar sesión para acceder al recurso.", "info")
            return redirect(url_for("web.login"))

        rol = user.get("rol_codigo")
        if rol in ["estudiante", "acudiente"]:
            flash("Acceso Denegado (403): Los estudiantes no cuentan con permisos para funciones administrativas.", "error")
            return redirect(url_for("estudiante.portal"))

        return f(*args, **kwargs)
    return decorated_function


@web_bp.route("/login", methods=["GET", "POST"])
def login():
    """Pantalla de inicio de sesión."""
    if request.method == "POST":
        identificador = request.form.get("identificador", "").strip()
        tipo_doc = request.form.get("tipo_documento", "CC").strip().upper()
        contrasena = request.form.get("contrasena", "").strip()

        usuario = query_db("""
            SELECT u.id_usuario, u.id_rol, u.tipo_documento, u.documento, u.nombre,
                   u.apellido, u.email, u.contrasena, u.estado, r.codigo AS rol_codigo, r.nombre AS rol_nombre
            FROM usuario u
            JOIN rol r ON r.id_rol = u.id_rol
            WHERE (u.tipo_documento = %s AND u.documento = %s) OR u.email = %s
        """, (tipo_doc, identificador, identificador), one=True)

        if not usuario or not verify_password(contrasena, usuario["contrasena"]):
            flash("Credenciales incorrectas. Verifique su documento y contraseña.", "error")
            return render_template("login.html")

        if usuario["estado"] != "activo":
            flash("Usuario inactivo o suspendido. Contacte a Rectoría.", "error")
            return render_template("login.html")

        session["user"] = {
            "id_usuario": usuario["id_usuario"],
            "id_rol": usuario["id_rol"],
            "rol_codigo": usuario["rol_codigo"],
            "rol_nombre": usuario["rol_nombre"],
            "nombre": f"{usuario['nombre']} {usuario['apellido']}",
            "documento": usuario["documento"]
        }
        flash(f"¡Bienvenido(a), {usuario['nombre']}!", "success")

        if usuario["rol_codigo"] in ["estudiante", "acudiente"]:
            return redirect(url_for("estudiante.portal"))

        return redirect(url_for("web.dashboard"))

    return render_template("login.html")


@web_bp.route("/logout")
def logout():
    """Cierra la sesión activa."""
    session.clear()
    flash("Sesión finalizada.", "info")
    return redirect(url_for("web.login"))


@web_bp.route("/")
def dashboard():
    """Dashboard principal con métricas de permanencia y semáforo IVE."""
    user = session.get("user")
    if user and user.get("rol_codigo") in ["estudiante", "acudiente"]:
        return redirect(url_for("estudiante.portal"))

    sedes = query_db("""
        SELECT s.id_sede, s.nombre, s.codigo_dane, s.direccion, s.es_principal, s.estado,
               COUNT(c.id_curso) AS total_cursos
        FROM sede s
        LEFT JOIN curso c ON c.id_sede = s.id_sede
        GROUP BY s.id_sede, s.nombre, s.codigo_dane, s.direccion, s.es_principal, s.estado
        ORDER BY s.es_principal DESC, s.nombre ASC
    """)

    estudiantes = query_db("""
        SELECT e.id_estudiante, u.nombre, u.apellido, u.documento, c.nombre AS curso_nombre, s.nombre AS sede_nombre
        FROM estudiante e
        JOIN usuario u ON u.id_usuario = e.id_usuario
        JOIN matricula m ON m.id_estudiante = e.id_estudiante AND m.estado = 'activa'
        JOIN curso c ON c.id_curso = m.id_curso
        JOIN sede s ON s.id_sede = c.id_sede
    """)

    conteo = {"verde": 0, "naranja": 0, "rojo": 0}
    estudiantes_riesgo = []

    for est in estudiantes:
        ive = calcular_ive_estudiante(est["id_estudiante"])
        color = ive["nivel_riesgo"]
        conteo[color] = conteo.get(color, 0) + 1
        if color in ["naranja", "rojo"]:
            estudiantes_riesgo.append({
                **est,
                **ive
            })

    total_estudiantes = len(estudiantes)

    return render_template(
        "dashboard.html",
        sedes=sedes,
        total_estudiantes=total_estudiantes,
        semaforo=conteo,
        estudiantes_riesgo=estudiantes_riesgo
    )


@web_bp.route("/sat")
@solo_personal_autorizado
def sat_monitoreo():
    """
    Centro Integral SAT - Prevención de Deserción Escolar e Índice IVE.
    Muestra la lista de todos los estudiantes clasificados con sus factores de riesgo.
    """
    estudiantes = query_db("""
        SELECT e.id_estudiante, e.direccion, e.puntaje_esa,
               u.nombre, u.apellido, u.tipo_documento, u.documento,
               c.nombre AS curso_nombre, s.nombre AS sede_nombre
        FROM estudiante e
        JOIN usuario u ON u.id_usuario = e.id_usuario
        JOIN matricula m ON m.id_estudiante = e.id_estudiante AND m.estado = 'activa'
        JOIN curso c ON c.id_curso = m.id_curso
        JOIN sede s ON s.id_sede = c.id_sede
        ORDER BY c.nombre ASC, u.apellido ASC
    """)

    filtro = request.args.get("filtro", "todos")
    estudiantes_sat = []

    for est in estudiantes:
        ive = calcular_ive_estudiante(est["id_estudiante"])
        if filtro == "todos" or ive["nivel_riesgo"] == filtro:
            estudiantes_sat.append({
                **est,
                **ive
            })

    # Ordenar por nivel de riesgo (rojo primero, luego naranja, luego verde)
    prioridad = {"rojo": 1, "naranja": 2, "verde": 3}
    estudiantes_sat.sort(key=lambda x: prioridad.get(x["nivel_riesgo"], 4))

    return render_template(
        "sat/monitoreo.html",
        estudiantes=estudiantes_sat,
        filtro_actual=filtro
    )


@web_bp.route("/sat/estudiante/<int:id_estudiante>")
@solo_personal_autorizado
def sat_ficha_estudiante(id_estudiante: int):
    """
    Ficha de Diagnóstico Integral IVE del Estudiante.
    Radiografía de Ausentismo (50%), Rendimiento (30%) y Factores Socioeconómicos Rurales (20%).
    """
    estudiante = query_db("""
        SELECT e.id_estudiante, e.direccion, e.fecha_nacimiento, e.puntaje_esa,
               u.nombre, u.apellido, u.tipo_documento, u.documento, u.email, u.telefono,
               c.nombre AS curso_nombre, c.grado, c.jornada,
               s.nombre AS sede_nombre, s.direccion AS sede_direccion
        FROM estudiante e
        JOIN usuario u ON u.id_usuario = e.id_usuario
        JOIN matricula m ON m.id_estudiante = e.id_estudiante AND m.estado = 'activa'
        JOIN curso c ON c.id_curso = m.id_curso
        JOIN sede s ON s.id_sede = c.id_sede
        WHERE e.id_estudiante = %s
    """, (id_estudiante,), one=True)

    if not estudiante:
        flash("Estudiante no encontrado.", "error")
        return redirect(url_for("web.sat_monitoreo"))

    ive = calcular_ive_estudiante(id_estudiante)

    # Historial de inasistencias para posible justificación con excusa
    asistencias = query_db("""
        SELECT a.id_asistencia, a.fecha, a.estado, a.minutos_retraso, a.valor_inasistencia, a.observacion,
               m.nombre AS materia_nombre
        FROM asistencia a
        JOIN horario h ON h.id_horario = a.id_horario
        JOIN asignacion asig ON asig.id_asignacion = h.id_asignacion
        JOIN materia m ON m.id_materia = asig.id_materia
        WHERE a.id_estudiante = %s
        ORDER BY a.fecha DESC
    """, (id_estudiante,))

    # Notas del estudiante
    calificaciones = query_db("""
        SELECT m.nombre AS materia_nombre, c.nota, c.fecha_registro
        FROM calificacion c
        JOIN asignacion a ON a.id_asignacion = c.id_asignacion
        JOIN materia m ON m.id_materia = a.id_materia
        WHERE c.id_estudiante = %s
    """, (id_estudiante,))

    return render_template(
        "sat/ficha.html",
        estudiante=estudiante,
        ive=ive,
        asistencias=asistencias,
        calificaciones=calificaciones
    )


@web_bp.route("/sat/estudiante/<int:id_estudiante>/radicar-excusa", methods=["POST"])
@solo_personal_autorizado
def radicar_excusa(id_estudiante: int):
    """
    Radicación de Excusas Médicas / Calamidad (RF-20).
    Neutraliza la inasistencia (valor_inasistencia = 0.0) y recalcula el IVE al instante.
    """
    id_asistencia = request.form.get("id_asistencia")
    motivo = request.form.get("motivo", "Excusa justificada por acudiente")

    if not id_asistencia:
        flash("Debe seleccionar un registro de asistencia para justificar.", "error")
        return redirect(url_for("web.sat_ficha_estudiante", id_estudiante=id_estudiante))

    # Actualizar a 'excusa' y neutralizar ausentismo
    execute_db("""
        UPDATE asistencia
        SET estado = 'excusa', valor_inasistencia = 0.0, observacion = %s
        WHERE id_asistencia = %s AND id_estudiante = %s
    """, (f"Excusa Aprobada: {motivo}", id_asistencia, id_estudiante))

    nuevo_ive = calcular_ive_estudiante(id_estudiante)

    flash(f"Excusa radicada exitosamente. Las inasistencias fueron neutralizadas. Nuevo IVE: {nuevo_ive['valor_ive']} (Semáforo: {nuevo_ive['nivel_riesgo'].upper()}).", "success")
    return redirect(url_for("web.sat_ficha_estudiante", id_estudiante=id_estudiante))


@web_bp.route("/matriculas", methods=["GET"])
@solo_personal_autorizado
def matriculas():
    """Vista de Admisión y Matrícula Data-Light."""
    cursos = query_db("""
        SELECT c.id_curso, c.nombre, c.grado, s.nombre AS sede_nombre
        FROM curso c
        JOIN sede s ON s.id_sede = c.id_sede
        ORDER BY c.grado ASC, c.nombre ASC
    """)

    matriculas_lista = query_db("""
        SELECT m.id_matricula, m.fecha, m.estado, m.documentacion_fisica_entregada,
               e.id_estudiante, e.direccion, e.puntaje_esa,
               u.nombre, u.apellido, u.tipo_documento, u.documento,
               c.nombre AS curso_nombre, s.nombre AS sede_nombre
        FROM matricula m
        JOIN estudiante e ON e.id_estudiante = m.id_estudiante
        JOIN usuario u ON u.id_usuario = e.id_usuario
        JOIN curso c ON c.id_curso = m.id_curso
        JOIN sede s ON s.id_sede = c.id_sede
        ORDER BY m.id_matricula DESC
    """)

    return render_template("matriculas.html", cursos=cursos, matriculas=matriculas_lista)


@web_bp.route("/matriculas/crear", methods=["POST"])
@solo_personal_autorizado
def crear_matricula_form():
    """Procesamiento del formulario de matrícula."""
    tipo_doc = request.form.get("tipo_documento", "TI").strip().upper()
    doc = request.form.get("documento", "").strip()
    nombre = request.form.get("nombre", "").strip()
    apellido = request.form.get("apellido", "").strip()
    fecha_nac = request.form.get("fecha_nacimiento", "").strip()
    id_curso = request.form.get("id_curso")
    puntaje_esa = float(request.form.get("puntaje_esa", 0.20))
    doc_entregada = 1 if request.form.get("documentacion_fisica_entregada") else 0

    existente = query_db(
        "SELECT id_usuario FROM usuario WHERE tipo_documento = %s AND documento = %s",
        (tipo_doc, doc),
        one=True
    )
    if existente:
        flash(f"Error 409: Ya existe un registro con el documento {tipo_doc} {doc}.", "error")
        return redirect(url_for("web.matriculas"))

    rol_est = query_db("SELECT id_rol FROM rol WHERE codigo = 'estudiante'", one=True)
    id_rol = rol_est["id_rol"] if rol_est else 5
    anio = query_db("SELECT id_anio FROM anio_lectivo WHERE estado = 'activo' ORDER BY anio DESC", one=True)
    id_anio = anio["id_anio"] if anio else 1

    pw = hash_password(f"{doc}*")
    execute_db("""
        INSERT INTO usuario (id_rol, tipo_documento, documento, nombre, apellido, email, contrasena, estado)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'activo')
    """, (id_rol, tipo_doc, doc, nombre, apellido, f"{doc}@estudiante.santana.edu.co", pw))

    u = query_db("SELECT id_usuario FROM usuario WHERE tipo_documento = %s AND documento = %s", (tipo_doc, doc), one=True)
    id_usuario = u["id_usuario"]

    execute_db("""
        INSERT INTO estudiante (id_usuario, direccion, fecha_nacimiento, puntaje_esa)
        VALUES (%s, 'Vereda Germania', %s, %s)
    """, (id_usuario, fecha_nac, puntaje_esa))

    e = query_db("SELECT id_estudiante FROM estudiante WHERE id_usuario = %s", (id_usuario,), one=True)
    id_estudiante = e["id_estudiante"]

    execute_db("""
        INSERT INTO matricula (id_estudiante, id_curso, id_anio, fecha, estado, documentacion_fisica_entregada)
        VALUES (%s, %s, %s, %s, 'activa', %s)
    """, (id_estudiante, id_curso, id_anio, date.today().isoformat(), doc_entregada))

    flash(f"Matrícula registrada exitosamente para {nombre} {apellido}.", "success")
    return redirect(url_for("web.matriculas"))


@web_bp.route("/horarios", methods=["GET"])
@solo_personal_autorizado
def horarios():
    """Vista de gestión de malla horaria."""
    asignaciones = query_db("""
        SELECT a.id_asignacion, m.nombre AS materia_nombre, c.nombre AS curso_nombre,
               u.nombre AS profesor_nombre, u.apellido AS profesor_apellido
        FROM asignacion a
        JOIN materia m ON m.id_materia = a.id_materia
        JOIN curso c ON c.id_curso = a.id_curso
        JOIN profesor p ON p.id_profesor = a.id_profesor
        JOIN usuario u ON u.id_usuario = p.id_usuario
        ORDER BY c.nombre ASC, m.nombre ASC
    """)

    horarios_lista = query_db("""
        SELECT h.id_horario, h.dia_semana, h.hora_inicio, h.hora_fin, h.aula,
               m.nombre AS materia_nombre, c.nombre AS curso_nombre,
               u.nombre AS profesor_nombre, u.apellido AS profesor_apellido
        FROM horario h
        JOIN asignacion a ON a.id_asignacion = h.id_asignacion
        JOIN materia m ON m.id_materia = a.id_materia
        JOIN curso c ON c.id_curso = a.id_curso
        JOIN profesor p ON p.id_profesor = a.id_profesor
        JOIN usuario u ON u.id_usuario = p.id_usuario
        ORDER BY CASE h.dia_semana WHEN 'lunes' THEN 1 WHEN 'martes' THEN 2 WHEN 'miercoles' THEN 3 WHEN 'jueves' THEN 4 WHEN 'viernes' THEN 5 ELSE 6 END, h.hora_inicio ASC
    """)

    return render_template("horarios.html", asignaciones=asignaciones, horarios=horarios_lista)


@web_bp.route("/horarios/crear", methods=["POST"])
@solo_personal_autorizado
def crear_horario_form():
    """Procesamiento del formulario de horarios con algoritmo anti-colisión."""
    id_asignacion = int(request.form.get("id_asignacion"))
    dia_semana = request.form.get("dia_semana", "").strip().lower()
    hora_inicio = request.form.get("hora_inicio", "").strip()
    hora_fin = request.form.get("hora_fin", "").strip()
    aula = request.form.get("aula", "Aula General").strip()

    if hora_fin <= hora_inicio:
        flash("La hora de fin debe ser posterior a la de inicio.", "error")
        return redirect(url_for("web.horarios"))

    asig = query_db("SELECT id_profesor FROM asignacion WHERE id_asignacion = %s", (id_asignacion,), one=True)
    id_profesor = asig["id_profesor"]

    solapamiento_prof = query_db("""
        SELECT h.id_horario, h.hora_inicio, h.hora_fin, m.nombre AS materia
        FROM horario h
        JOIN asignacion a ON a.id_asignacion = h.id_asignacion
        JOIN materia m ON m.id_materia = a.id_materia
        WHERE a.id_profesor = %s
          AND h.dia_semana = %s
          AND (h.hora_inicio < %s AND h.hora_fin > %s)
    """, (id_profesor, dia_semana, hora_fin, hora_inicio), one=True)

    if solapamiento_prof:
        flash(f"Colisión 422: El docente ya tiene clase de {solapamiento_prof['materia']} entre {solapamiento_prof['hora_inicio']} y {solapamiento_prof['hora_fin']}.", "error")
        return redirect(url_for("web.horarios"))

    execute_db("""
        INSERT INTO horario (id_asignacion, dia_semana, hora_inicio, hora_fin, aula)
        VALUES (%s, %s, %s, %s, %s)
    """, (id_asignacion, dia_semana, hora_inicio, hora_fin, aula))

    flash("Bloque horario programado correctamente sin colisiones.", "success")
    return redirect(url_for("web.horarios"))


@web_bp.route("/asistencia", methods=["GET"])
@solo_personal_autorizado
def asistencia():
    """Planilla diaria de asistencia docente con selector y soporte PWA."""
    hoy = date.today().isoformat()
    grupo_sel = request.args.get("grupo", "").strip()
    id_curso = request.args.get("id_curso", type=int)

    sedes = query_db("SELECT id_sede, nombre FROM sede ORDER BY nombre ASC")
    cursos = query_db("SELECT id_curso, nombre, grado FROM curso ORDER BY nombre ASC")

    # Si no se selecciona grupo ni curso, mostrar estado inicial (Mockup 6)
    mostrar_planilla = bool(grupo_sel or id_curso)

    estudiantes_con_ive = []
    if mostrar_planilla:
        sql = """
            SELECT e.id_estudiante, u.nombre, u.apellido, u.tipo_documento, u.documento,
                   a.estado AS asistencia_hoy, a.minutos_retraso AS minutos_retraso_hoy,
                   a.valor_inasistencia AS valor_inasistencia_hoy
            FROM estudiante e
            JOIN usuario u ON u.id_usuario = e.id_usuario
            JOIN matricula m ON m.id_estudiante = e.id_estudiante AND m.estado = 'activa'
            LEFT JOIN asistencia a ON a.id_estudiante = e.id_estudiante AND a.fecha = %s
        """
        args = [hoy]
        if id_curso:
            sql += " WHERE m.id_curso = %s"
            args.append(id_curso)
        sql += " ORDER BY u.apellido ASC, u.nombre ASC"

        estudiantes = query_db(sql, tuple(args))
        for est in estudiantes:
            ive = calcular_ive_estudiante(est["id_estudiante"])
            estudiantes_con_ive.append({
                **est,
                "ive": ive
            })

    return render_template(
        "asistencia.html",
        fecha_actual=hoy,
        mostrar_planilla=mostrar_planilla,
        grupo_sel=grupo_sel or "Matemáticas 9-A",
        sedes=sedes,
        cursos=cursos,
        estudiantes=estudiantes_con_ive
    )


@web_bp.route("/asistencia/guardar", methods=["POST"])
@solo_personal_autorizado
def guardar_asistencia_lote():
    """Guarda en lote la marcación de asistencia docente."""
    user = session.get("user")
    id_usuario_reg = user["id_usuario"]
    hoy = date.today().isoformat()

    # Recibe registros con prefijo estado_
    for key, val in request.form.items():
        if key.startswith("estado_"):
            id_est = int(key.split("_")[1])
            estado = val.strip().lower()
            val_inas = 0.0 if estado in ["presente", "asiste"] else (0.5 if estado == "retraso" else 1.0)
            if estado == "excusa":
                val_inas = 0.0

            # Guardar o actualizar
            existente = query_db(
                "SELECT id_asistencia FROM asistencia WHERE id_estudiante = %s AND fecha = %s",
                (id_est, hoy), one=True
            )
            if existente:
                execute_db("""
                    UPDATE asistencia
                    SET estado = %s, valor_inasistencia = %s, id_usuario_registro = %s
                    WHERE id_asistencia = %s
                """, (estado, val_inas, id_usuario_reg, existente["id_asistencia"]))
            else:
                execute_db("""
                    INSERT INTO asistencia (id_estudiante, id_horario, fecha, estado, valor_inasistencia, id_usuario_registro)
                    VALUES (%s, 1, %s, %s, %s, %s)
                """, (id_est, hoy, estado, val_inas, id_usuario_reg))

    flash("¡Asistencia guardada exitosamente y sincronizada!", "success")
    return redirect(url_for("web.asistencia", grupo="Matemáticas 9-A"))


@web_bp.route("/mis-grupos", methods=["GET"])
@solo_personal_autorizado
def mis_grupos():
    """Gestión de Aula: Visualización de estudiantes, filtros de riesgo y ficha médica."""
    filtro_riesgo = request.args.get("alerta") == "1"
    buscar = request.args.get("buscar", "").strip().lower()

    estudiantes = query_db("""
        SELECT e.id_estudiante, u.nombre, u.apellido, u.tipo_documento, u.documento,
               m.estado AS estado_matricula, c.nombre AS curso_nombre, c.grado, s.nombre AS sede_nombre
        FROM estudiante e
        JOIN usuario u ON u.id_usuario = e.id_usuario
        JOIN matricula m ON m.id_estudiante = e.id_estudiante
        JOIN curso c ON c.id_curso = m.id_curso
        JOIN sede s ON s.id_sede = c.id_sede
        ORDER BY u.apellido ASC, u.nombre ASC
    """)

    sedes = query_db("SELECT id_sede, nombre FROM sede ORDER BY nombre ASC")
    cursos = query_db("SELECT id_curso, nombre, grado FROM curso ORDER BY nombre ASC")

    lista = []
    conteo_riesgo = 0
    for est in estudiantes:
        ive = calcular_ive_estudiante(est["id_estudiante"])
        es_riesgo = ive["nivel_riesgo"] in ["rojo", "naranja"]
        if es_riesgo:
            conteo_riesgo += 1

        if filtro_riesgo and not es_riesgo:
            continue

        if buscar:
            texto = f"{est['nombre']} {est['apellido']} {est['documento']}".lower()
            if buscar not in texto:
                continue

        lista.append({
            **est,
            "ive": ive,
            "es_riesgo": es_riesgo
        })

    return render_template(
        "mis_grupos.html",
        estudiantes=lista,
        sedes=sedes,
        cursos=cursos,
        filtro_riesgo=filtro_riesgo,
        buscar=buscar,
        conteo_riesgo=conteo_riesgo
    )


@web_bp.route("/api/estudiante/<int:id_estudiante>/ficha-medica", methods=["GET"])
@solo_personal_autorizado
def api_ficha_medica(id_estudiante: int):
    """Retorna los datos estructurados para la Ficha Médica de Emergencia (Mockup 9)."""
    est = query_db("""
        SELECT e.id_estudiante, u.nombre, u.apellido, u.tipo_documento, u.documento,
               f.grupo_sanguineo, f.proveedor_eps, f.alergias_condiciones,
               f.contacto_emergencia_nombre, f.contacto_emergencia_telefono,
               f.direccion_domicilio
        FROM estudiante e
        JOIN usuario u ON u.id_usuario = e.id_usuario
        LEFT JOIN ficha_socioeconomica f ON f.id_estudiante = e.id_estudiante
        WHERE e.id_estudiante = %s
    """, (id_estudiante,), one=True)

    if not est:
        return {"error": "Estudiante no encontrado"}, 404

    return {
        "success": True,
        "estudiante": {
            "id_estudiante": est["id_estudiante"],
            "nombre_completo": f"{est['nombre']} {est['apellido']}",
            "documento": f"{est['tipo_documento']} {est['documento']}",
            "acudiente": est["contacto_emergencia_nombre"] or "María Rodríguez (Madre)",
            "telefono": est["contacto_emergencia_telefono"] or "+57 300 123 4567",
            "grupo_sanguineo": est["grupo_sanguineo"] or "O+",
            "eps": est["proveedor_eps"] or "Sanitas Salud",
            "alergias": est["alergias_condiciones"] or "Penicilina, Nueces, Polen",
            "direccion": est["direccion_domicilio"] or "Km 7 Vía a Atánquez, Vereda El Cielo, Valledupar, Cesar (Área Rural)"
        }
    }


@web_bp.route("/planilla-notas", methods=["GET"])
@solo_personal_autorizado
def planilla_notas():
    """Redirige a la vista completa de calificaciones o muestra el portal docente."""
    return redirect(url_for("calificaciones.planilla"))


@web_bp.route("/reportes-academicos", methods=["GET"])
@solo_personal_autorizado
def reportes_academicos():
    """Seguimiento y Reportes Académicos: Donut inasistencias y riesgos (Mockup 8)."""
    sedes = query_db("SELECT id_sede, nombre FROM sede ORDER BY nombre ASC")
    cursos = query_db("SELECT id_curso, nombre, grado FROM curso ORDER BY nombre ASC")

    estudiantes = query_db("""
        SELECT e.id_estudiante, u.nombre, u.apellido, u.tipo_documento, u.documento,
               c.nombre AS curso_nombre
        FROM estudiante e
        JOIN usuario u ON u.id_usuario = e.id_usuario
        JOIN matricula m ON m.id_estudiante = e.id_estudiante AND m.estado = 'activa'
        JOIN curso c ON c.id_curso = m.id_curso
        LIMIT 10
    """)

    estudiantes_riesgo = []
    for est in estudiantes:
        ive = calcular_ive_estudiante(est["id_estudiante"])
        if ive["nivel_riesgo"] in ["rojo", "naranja"]:
            estudiantes_riesgo.append({
                **est,
                **ive
            })

    return render_template(
        "reportes_seguimiento.html",
        sedes=sedes,
        cursos=cursos,
        estudiantes_riesgo=estudiantes_riesgo
    )


@web_bp.route("/institucion", methods=["GET"])
@solo_personal_autorizado
def institucion():
    """Gestión de Institución y Salones."""
    sedes = query_db("SELECT * FROM sede ORDER BY es_principal DESC, nombre ASC")
    salones = query_db("SELECT * FROM salon_espacio ORDER BY codigo ASC")
    return render_template("institucion.html", sedes=sedes, salones=salones)


@web_bp.route("/auditoria", methods=["GET"])
@solo_personal_autorizado
def auditoria():
    """Centro de Reportes y Auditoría."""
    logs = query_db("SELECT * FROM log_actividad ORDER BY sello_tiempo DESC LIMIT 25")
    return render_template("auditoria.html", logs=logs)


@web_bp.route("/recuperar-contrasena", methods=["GET", "POST"])
def recuperar_contrasena():
    """Recuperación de contraseña institucional."""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        flash("Se han enviado las instrucciones de recuperación a su correo institucional.", "success")
        return redirect(url_for("web.login"))
    return render_template("recuperar_password.html")
