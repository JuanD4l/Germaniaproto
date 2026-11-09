import csv
import io
from flask import Response, request, session, redirect, url_for, flash
from app.blueprints.reportes import reportes_bp
from app.database import query_db
from app.blueprints.asistencia.routes import calcular_ive_estudiante


@reportes_bp.route("/simat", methods=["GET"])
def exportar_simat():
    """
    Exportador Oficial SIMAT (RF-18).
    Genera un archivo plano CSV estructurado compatible con los requerimientos
    del Sistema Integrado de Matrícula (SIMAT) del Ministerio de Educación Nacional.
    """
    registros = query_db("""
        SELECT s.codigo_dane AS dane_sede,
               s.nombre AS nombre_sede,
               u.tipo_documento,
               u.documento,
               u.apellido AS primer_apellido,
               '' AS segundo_apellido,
               u.nombre AS nombres,
               e.fecha_nacimiento,
               c.grado,
               c.nombre AS curso_nombre,
               c.jornada,
               m.fecha AS fecha_matricula,
               m.estado AS estado_matricula,
               CASE WHEN m.documentacion_fisica_entregada = 1 THEN 'SI' ELSE 'NO' END AS docs_completos
        FROM matricula m
        JOIN estudiante e ON e.id_estudiante = m.id_estudiante
        JOIN usuario u ON u.id_usuario = e.id_usuario
        JOIN curso c ON c.id_curso = m.id_curso
        JOIN sede s ON s.id_sede = c.id_sede
        WHERE m.estado = 'activa'
        ORDER BY s.codigo_dane ASC, c.grado ASC, u.apellido ASC
    """)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        "CODIGO_DANE_SEDE",
        "NOMBRE_SEDE",
        "TIPO_DOCUMENTO",
        "NUMERO_DOCUMENTO",
        "PRIMER_APELLIDO",
        "SEGUNDO_APELLIDO",
        "NOMBRES",
        "FECHA_NACIMIENTO",
        "GRADO",
        "CURSO",
        "JORNADA",
        "FECHA_MATRICULA",
        "ESTADO_MATRICULA",
        "DOCS_VERIFICADOS"
    ])

    for r in registros:
        writer.writerow([
            r.get("dane_sede", "120001001234"),
            r.get("nombre_sede", "Sede Principal"),
            r.get("tipo_documento", "TI"),
            r.get("documento", ""),
            r.get("primer_apellido", ""),
            r.get("segundo_apellido", ""),
            r.get("nombres", ""),
            r.get("fecha_nacimiento", ""),
            r.get("grado", 0),
            r.get("curso_nombre", ""),
            r.get("jornada", "manana"),
            r.get("fecha_matricula", ""),
            r.get("estado_matricula", "activa"),
            r.get("docs_completos", "SI")
        ])

    csv_data = "\ufeff" + output.getvalue()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=SIMAT_matricula_germania_2026.csv",
            "Content-Type": "text/csv; charset=utf-8"
        }
    )


@reportes_bp.route("/ive-consolidado", methods=["GET"])
def exportar_ive_consolidado():
    """
    Exporta la matriz de permanencia escolar y riesgo de deserción (IVE)
    para el Comité Directivo de Permanencia Escolar.
    """
    estudiantes = query_db("""
        SELECT e.id_estudiante, u.tipo_documento, u.documento, u.nombre, u.apellido,
               c.nombre AS curso_nombre, s.nombre AS sede_nombre
        FROM estudiante e
        JOIN usuario u ON u.id_usuario = e.id_usuario
        JOIN matricula m ON m.id_estudiante = e.id_estudiante AND m.estado = 'activa'
        JOIN curso c ON c.id_curso = m.id_curso
        JOIN sede s ON s.id_sede = c.id_sede
        ORDER BY c.nombre ASC, u.apellido ASC
    """)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        "ID_ESTUDIANTE",
        "TIPO_DOC",
        "DOCUMENTO",
        "ESTUDIANTE",
        "CURSO",
        "SEDE",
        "VALOR_IVE",
        "FACTOR_AUSENTISMO_FA",
        "FACTOR_RENDIMIENTO_RA",
        "FACTOR_SOCIOECONOMICO_ESA",
        "PORCENTAJE_FALLAS",
        "PROMEDIO_ACADEMICO",
        "SEMAFORO_RIESGO",
        "DIAGNOSTICO"
    ])

    for est in estudiantes:
        ive = calcular_ive_estudiante(est["id_estudiante"])
        writer.writerow([
            est["id_estudiante"],
            est["tipo_documento"],
            est["documento"],
            f"{est['nombre']} {est['apellido']}",
            est["curso_nombre"],
            est["sede_nombre"],
            ive["valor_ive"],
            ive["factor_ausentismo"],
            ive["factor_rendimiento"],
            ive["factor_socioeconomico"],
            f"{ive['porcentaje_fallas']}%",
            ive["promedio_academico"],
            ive["nivel_riesgo"].upper(),
            ive["diagnostico"]
        ])

    csv_data = "\ufeff" + output.getvalue()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=SAT_consolidado_IVE_germania_2026.csv",
            "Content-Type": "text/csv; charset=utf-8"
        }
    )
