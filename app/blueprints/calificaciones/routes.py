from datetime import date
from flask import render_template, request, redirect, url_for, flash, session
from app.blueprints.calificaciones import calificaciones_bp
from app.database import query_db, execute_db
from functools import wraps


def solo_personal_autorizado(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get("user")
        if not user:
            flash("Debe iniciar sesión.", "info")
            return redirect(url_for("web.login"))
        if user.get("rol_codigo") in ["estudiante", "acudiente"]:
            flash("Acceso Denegado (403).", "error")
            return redirect(url_for("estudiante.portal"))
        return f(*args, **kwargs)
    return decorated_function


@calificaciones_bp.route("/")
@solo_personal_autorizado
def planilla():
    """
    Planilla de Calificaciones Multidimensional por Período.
    Dimensiones: Saber (40%), Hacer (40%), Ser (20%) — según modelo pedagógico institucional.
    """
    id_curso = request.args.get("id_curso", type=int)
    id_periodo = request.args.get("id_periodo", type=int)

    cursos = query_db("""
        SELECT c.id_curso, c.nombre, s.nombre AS sede_nombre
        FROM curso c
        JOIN sede s ON s.id_sede = c.id_sede
        ORDER BY c.grado ASC, c.nombre ASC
    """)

    periodos = query_db("""
        SELECT p.id_periodo, p.numero, p.estado, a.anio
        FROM periodo p
        JOIN anio_lectivo a ON a.id_anio = p.id_anio
        ORDER BY a.anio DESC, p.numero ASC
    """)

    # Periodo activo por defecto
    if not id_periodo and periodos:
        id_periodo = periodos[0]["id_periodo"]

    # Curso por defecto
    if not id_curso and cursos:
        id_curso = cursos[0]["id_curso"]

    estudiantes_notas = []
    materias = []
    periodo_actual = None

    if id_curso and id_periodo:
        # Verificar estado del período
        periodo_actual = query_db(
            "SELECT id_periodo, numero, estado FROM periodo WHERE id_periodo = %s",
            (id_periodo,), one=True
        )

        # Materias del curso
        materias = query_db("""
            SELECT a.id_asignacion, m.nombre AS materia_nombre,
                   u.nombre AS prof_nombre, u.apellido AS prof_apellido
            FROM asignacion a
            JOIN materia m ON m.id_materia = a.id_materia
            JOIN profesor p ON p.id_profesor = a.id_profesor
            JOIN usuario u ON u.id_usuario = p.id_usuario
            WHERE a.id_curso = %s
            ORDER BY m.nombre ASC
        """, (id_curso,))

        # Estudiantes del curso con sus notas
        estudiantes = query_db("""
            SELECT e.id_estudiante, u.nombre, u.apellido, u.tipo_documento, u.documento
            FROM estudiante e
            JOIN usuario u ON u.id_usuario = e.id_usuario
            JOIN matricula m ON m.id_estudiante = e.id_estudiante AND m.estado = 'activa'
            WHERE m.id_curso = %s
            ORDER BY u.apellido ASC, u.nombre ASC
        """, (id_curso,))

        for est in estudiantes:
            notas_por_materia = {}
            for mat in materias:
                nota = query_db("""
                    SELECT nota FROM calificacion
                    WHERE id_estudiante = %s AND id_asignacion = %s AND id_periodo = %s
                """, (est["id_estudiante"], mat["id_asignacion"], id_periodo), one=True)
                notas_por_materia[mat["id_asignacion"]] = float(nota["nota"]) if nota and nota["nota"] is not None else None

            notas_validas = [v for v in notas_por_materia.values() if v is not None]
            promedio = round(sum(notas_validas) / len(notas_validas), 2) if notas_validas else None
            materias_perdidas = sum(1 for v in notas_validas if v < 3.0)

            estudiantes_notas.append({
                **est,
                "notas": notas_por_materia,
                "promedio": promedio,
                "materias_perdidas": materias_perdidas
            })

    return render_template(
        "calificaciones/planilla.html",
        cursos=cursos,
        periodos=periodos,
        materias=materias,
        estudiantes=estudiantes_notas,
        id_curso_sel=id_curso,
        id_periodo_sel=id_periodo,
        periodo_actual=periodo_actual
    )


@calificaciones_bp.route("/registrar", methods=["POST"])
@solo_personal_autorizado
def registrar_nota():
    """
    Registro/Actualización de nota con auditoría obligatoria.
    Período cerrado → 403. Nota fuera de rango → 400.
    """
    user = session.get("user")
    id_estudiante = request.form.get("id_estudiante", type=int)
    id_asignacion = request.form.get("id_asignacion", type=int)
    id_periodo = request.form.get("id_periodo", type=int)
    nota_str = request.form.get("nota", "").strip()
    id_curso = request.form.get("id_curso", type=int)

    # Validar período abierto
    periodo = query_db(
        "SELECT estado, numero FROM periodo WHERE id_periodo = %s", (id_periodo,), one=True
    )
    if periodo and periodo["estado"] == "cerrado":
        flash(f"403: El Período {periodo['numero']} está cerrado. Contacte a Rectoría para reapertura.", "error")
        return redirect(url_for("calificaciones.planilla", id_curso=id_curso, id_periodo=id_periodo))

    try:
        nota = float(nota_str)
        if not (0.0 <= nota <= 5.0):
            raise ValueError
    except (ValueError, TypeError):
        flash("Nota inválida. Debe ser un número entre 0.0 y 5.0.", "error")
        return redirect(url_for("calificaciones.planilla", id_curso=id_curso, id_periodo=id_periodo))

    # Registrar o actualizar con auditoría
    existente = query_db("""
        SELECT id_calificacion, nota FROM calificacion
        WHERE id_estudiante = %s AND id_asignacion = %s AND id_periodo = %s
    """, (id_estudiante, id_asignacion, id_periodo), one=True)

    id_usuario_registro = user["id_usuario"]

    if existente:
        nota_anterior = existente["nota"]
        execute_db("""
            UPDATE calificacion
            SET nota = %s, id_usuario_registro = %s
            WHERE id_calificacion = %s
        """, (nota, id_usuario_registro, existente["id_calificacion"]))
        # Auditoría
        execute_db("""
            INSERT INTO auditoria_notas (id_usuario, id_estudiante, accion, nota_anterior, nota_nueva, motivo_cambio)
            VALUES (%s, %s, 'UPDATE', %s, %s, %s)
        """, (id_usuario_registro, id_estudiante, nota_anterior, nota, "Corrección desde planilla"))
        flash(f"Nota actualizada: {nota_anterior} → {nota}. Auditoría registrada.", "success")
    else:
        execute_db("""
            INSERT INTO calificacion (id_estudiante, id_asignacion, id_periodo, nota, id_usuario_registro)
            VALUES (%s, %s, %s, %s, %s)
        """, (id_estudiante, id_asignacion, id_periodo, nota, id_usuario_registro))
        # Auditoría primer registro
        execute_db("""
            INSERT INTO auditoria_notas (id_usuario, id_estudiante, accion, nota_anterior, nota_nueva, motivo_cambio)
            VALUES (%s, %s, 'INSERT', NULL, %s, %s)
        """, (id_usuario_registro, id_estudiante, nota, "Registro inicial desde planilla"))
        flash(f"Nota {nota} registrada con éxito.", "success")

    return redirect(url_for("calificaciones.planilla", id_curso=id_curso, id_periodo=id_periodo))

