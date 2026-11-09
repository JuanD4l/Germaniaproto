from flask import render_template, session, redirect, url_for, flash, request
from app.blueprints.estudiante import estudiante_bp
from app.database import query_db
from app.blueprints.asistencia.routes import calcular_ive_estudiante


@estudiante_bp.route("/portal")
def portal():
    """
    Portal de Consulta para Estudiantes y Acudientes (Modo Solo Lectura).
    Muestra:
    1. Resumen de Matrícula (Curso, Sede, Jornada).
    2. Calificaciones por Materia y Promedio.
    3. Malla Horaria Semanal del Curso.
    4. Historial de Asistencia y Semáforo de Permanencia (IVE).
    5. Actividades y Tareas Académicas Pendientes.
    """
    user = session.get("user")
    if not user:
        flash("Debe iniciar sesión para acceder al portal estudiantil.", "info")
        return redirect(url_for("web.login"))

    id_usuario = user.get("id_usuario")

    # Obtener el registro de estudiante vinculado
    estudiante = query_db("""
        SELECT e.id_estudiante, e.direccion, e.fecha_nacimiento, e.puntaje_esa,
               u.nombre, u.apellido, u.tipo_documento, u.documento, u.email,
               m.id_matricula, m.fecha AS fecha_matricula, m.estado AS estado_matricula,
               c.id_curso, c.nombre AS curso_nombre, c.grado, c.jornada,
               s.nombre AS sede_nombre, s.direccion AS sede_direccion,
               a.anio
        FROM estudiante e
        JOIN usuario u ON u.id_usuario = e.id_usuario
        JOIN matricula m ON m.id_estudiante = e.id_estudiante AND m.estado = 'activa'
        JOIN curso c ON c.id_curso = m.id_curso
        JOIN sede s ON s.id_sede = c.id_sede
        JOIN anio_lectivo a ON a.id_anio = m.id_anio
        WHERE u.id_usuario = %s
    """, (id_usuario,), one=True)

    # Si quien consulta es un directivo/docente probando la vista o si no tiene registro de estudiante
    if not estudiante:
        # Fallback para pruebas: buscar el primer estudiante disponible
        estudiante = query_db("""
            SELECT e.id_estudiante, e.direccion, e.fecha_nacimiento, e.puntaje_esa,
                   u.nombre, u.apellido, u.tipo_documento, u.documento, u.email,
                   m.id_matricula, m.fecha AS fecha_matricula, m.estado AS estado_matricula,
                   c.id_curso, c.nombre AS curso_nombre, c.grado, c.jornada,
                   s.nombre AS sede_nombre, s.direccion AS sede_direccion,
                   a.anio
            FROM estudiante e
            JOIN usuario u ON u.id_usuario = e.id_usuario
            JOIN matricula m ON m.id_estudiante = e.id_estudiante AND m.estado = 'activa'
            JOIN curso c ON c.id_curso = m.id_curso
            JOIN sede s ON s.id_sede = c.id_sede
            JOIN anio_lectivo a ON a.id_anio = m.id_anio
            LIMIT 1
        """, one=True)

    if not estudiante:
        flash("No se encontró una matrícula activa para el estudiante.", "error")
        return redirect(url_for("web.dashboard"))

    id_est = estudiante["id_estudiante"]
    id_cur = estudiante["id_curso"]

    # 1. Calificaciones del Periodo
    calificaciones = query_db("""
        SELECT mat.nombre AS materia_nombre,
               c.nota,
               c.fecha_registro,
               u.nombre AS profesor_nombre,
               u.apellido AS profesor_apellido
        FROM asignacion a
        JOIN materia mat ON mat.id_materia = a.id_materia
        JOIN profesor p ON p.id_profesor = a.id_profesor
        JOIN usuario u ON u.id_usuario = p.id_usuario
        LEFT JOIN calificacion c ON c.id_asignacion = a.id_asignacion AND c.id_estudiante = %s
        WHERE a.id_curso = %s
        ORDER BY mat.nombre ASC
    """, (id_est, id_cur))

    # Promedio
    notas_validas = [float(c["nota"]) for c in calificaciones if c.get("nota") is not None]
    promedio = round(sum(notas_validas) / len(notas_validas), 2) if notas_validas else 0.0

    # 2. Horario Semanal de Clases
    horarios = query_db("""
        SELECT h.dia_semana, h.hora_inicio, h.hora_fin, h.aula,
               m.nombre AS materia_nombre,
               u.nombre AS profesor_nombre, u.apellido AS profesor_apellido
        FROM horario h
        JOIN asignacion a ON a.id_asignacion = h.id_asignacion
        JOIN materia m ON m.id_materia = a.id_materia
        JOIN profesor p ON p.id_profesor = a.id_profesor
        JOIN usuario u ON u.id_usuario = p.id_usuario
        WHERE a.id_curso = %s
        ORDER BY CASE h.dia_semana WHEN 'lunes' THEN 1 WHEN 'martes' THEN 2 WHEN 'miercoles' THEN 3 WHEN 'jueves' THEN 4 WHEN 'viernes' THEN 5 ELSE 6 END, h.hora_inicio ASC
    """, (id_cur,))

    # 3. Asistencia e Índice de Vulnerabilidad Escolar (IVE)
    ive = calcular_ive_estudiante(id_est)

    historial_asistencia = query_db("""
        SELECT a.fecha, a.estado, a.minutos_retraso, a.valor_inasistencia, a.observacion,
               m.nombre AS materia_nombre
        FROM asistencia a
        JOIN horario h ON h.id_horario = a.id_horario
        JOIN asignacion asig ON asig.id_asignacion = h.id_asignacion
        JOIN materia m ON m.id_materia = asig.id_materia
        WHERE a.id_estudiante = %s
        ORDER BY a.fecha DESC
        LIMIT 10
    """, (id_est,))

    # 4. Actividades y Tareas del Curso
    actividades = query_db("""
        SELECT act.id_actividad, act.titulo, act.descripcion, act.fecha_entrega, act.estado,
               m.nombre AS materia_nombre,
               u.nombre AS profesor_nombre, u.apellido AS profesor_apellido
        FROM actividad act
        JOIN asignacion a ON a.id_asignacion = act.id_asignacion
        JOIN materia m ON m.id_materia = a.id_materia
        JOIN profesor p ON p.id_profesor = a.id_profesor
        JOIN usuario u ON u.id_usuario = p.id_usuario
        WHERE a.id_curso = %s
        ORDER BY act.fecha_entrega ASC
    """, (id_cur,))

    return render_template(
        "estudiante/portal.html",
        estudiante=estudiante,
        calificaciones=calificaciones,
        promedio=promedio,
        horarios=horarios,
        ive=ive,
        historial_asistencia=historial_asistencia,
        actividades=actividades
    )

