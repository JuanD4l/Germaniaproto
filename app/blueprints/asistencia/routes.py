from datetime import date
from flask import request, g
from app.blueprints.asistencia import asistencia_bp
from app.database import query_db, execute_db
from app.utils.responses import success_response, error_response


def calcular_ive_estudiante(id_estudiante: int, id_periodo: int = 1):
    """
    Motor Central de Vulnerabilidad Escolar:
    IVE = (FA * 0.50) + (RA * 0.30) + (ESA * 0.20)
    Semáforo:
      - Verde: < 0.40
      - Naranja: 0.40 - 0.69 o fallas >= 10%
      - Rojo: >= 0.70 o fallas >= 15%
    """
    # 1. Factor de Ausentismo (FA)
    asistencias = query_db("""
        SELECT COUNT(*) AS total_clases,
               SUM(valor_inasistencia) AS inasistencias_ponderadas
        FROM asistencia
        WHERE id_estudiante = %s
    """, (id_estudiante,), one=True)

    total_clases = asistencias["total_clases"] if asistencias and asistencias["total_clases"] else 0
    inasistencias_ponderadas = float(asistencias["inasistencias_ponderadas"] or 0.0) if asistencias else 0.0

    if total_clases > 0:
        porcentaje_fallas = (inasistencias_ponderadas / total_clases) * 100.0
        factor_fa = min(inasistencias_ponderadas / total_clases, 1.0)
    else:
        porcentaje_fallas = 0.0
        factor_fa = 0.0

    # 2. Factor de Rendimiento Académico (RA)
    calificaciones = query_db("""
        SELECT AVG(nota) AS promedio_nota
        FROM calificacion
        WHERE id_estudiante = %s
    """, (id_estudiante,), one=True)

    promedio = float(calificaciones["promedio_nota"]) if calificaciones and calificaciones["promedio_nota"] is not None else 3.8
    factor_ra = max(0.0, min(1.0, (5.0 - promedio) / 5.0))

    # 3. Factor Socioeconómico (ESA)
    est = query_db("SELECT puntaje_esa FROM estudiante WHERE id_estudiante = %s", (id_estudiante,), one=True)
    factor_esa = float(est["puntaje_esa"] or 0.20) if est else 0.20

    # Fórmula ponderada estricta
    ive = (factor_fa * 0.50) + (factor_ra * 0.30) + (factor_esa * 0.20)
    ive = round(ive, 3)

    # Determinar Semáforo
    if ive >= 0.70 or porcentaje_fallas >= 15.0:
        semaforo = "rojo"
        diagnostico = "Riesgo Crítico de Deserción Escolar"
    elif ive >= 0.40 or porcentaje_fallas >= 10.0:
        semaforo = "naranja"
        diagnostico = "Riesgo Moderado - Monitoreo Preventivo"
    else:
        semaforo = "verde"
        diagnostico = "Permanencia Estable"

    return {
        "id_estudiante": id_estudiante,
        "valor_ive": ive,
        "factor_ausentismo": round(factor_fa, 3),
        "factor_rendimiento": round(factor_ra, 3),
        "factor_socioeconomico": round(factor_esa, 3),
        "porcentaje_fallas": round(porcentaje_fallas, 1),
        "promedio_academico": round(promedio, 2),
        "nivel_riesgo": semaforo,
        "diagnostico": diagnostico
    }


@asistencia_bp.route("/asistencia/registrar", methods=["POST"])
def registrar_asistencia():
    """
    Registro diario de asistencia con tiempos de gracia:
    - minutos <= 15: presente (0.0)
    - 16 <= minutos <= 30: retraso (0.5)
    - minutos > 30 o ausente: ausente (1.0)
    - excusa: excusa (0.0)
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("JSON requerido", status_code=400)

    campos = ["id_estudiante", "id_horario", "fecha", "estado"]
    for c in campos:
        if c not in data:
            return error_response(f"El campo '{c}' es obligatorio", status_code=400)

    id_estudiante = int(data["id_estudiante"])
    id_horario = int(data["id_horario"])
    fecha = str(data["fecha"]).strip()
    estado = str(data["estado"]).strip().lower()
    minutos_retraso = int(data.get("minutos_retraso", 0))
    observacion = data.get("observacion", "")

    id_usuario_registro = data.get("id_usuario_registro")
    if not id_usuario_registro:
        usuario_db = query_db("SELECT id_usuario FROM usuario LIMIT 1", one=True)
        id_usuario_registro = usuario_db["id_usuario"] if usuario_db else 1
    else:
        id_usuario_registro = int(id_usuario_registro)

    # Validar que el estudiante exista
    est_val = query_db("SELECT id_estudiante FROM estudiante WHERE id_estudiante = %s", (id_estudiante,), one=True)
    if not est_val:
        return error_response("El estudiante especificado no existe", status_code=404)

    # Validar que el horario exista
    hor_val = query_db("SELECT id_horario FROM horario WHERE id_horario = %s", (id_horario,), one=True)
    if not hor_val:
        return error_response("El horario especificado no existe", status_code=404)

    # Aplicar tiempos de gracia y cálculo normativo
    if estado == "excusa":
        valor_inasistencia = 0.0
    elif estado == "ausente" or minutos_retraso > 30:
        estado = "ausente"
        valor_inasistencia = 1.0
    elif minutos_retraso > 15 or estado == "retraso":
        estado = "retraso"
        valor_inasistencia = 0.5
    else:
        estado = "presente"
        valor_inasistencia = 0.0

    # Insertar o actualizar asistencia
    existente = query_db(
        "SELECT id_asistencia FROM asistencia WHERE id_estudiante = %s AND id_horario = %s AND fecha = %s",
        (id_estudiante, id_horario, fecha),
        one=True
    )

    if existente:
        execute_db("""
            UPDATE asistencia
            SET estado = %s, minutos_retraso = %s, valor_inasistencia = %s, observacion = %s, id_usuario_registro = %s
            WHERE id_asistencia = %s
        """, (estado, minutos_retraso, valor_inasistencia, observacion, id_usuario_registro, existente["id_asistencia"]))
        id_asistencia = existente["id_asistencia"]
    else:
        res = execute_db("""
            INSERT INTO asistencia (id_estudiante, id_horario, fecha, estado, minutos_retraso, valor_inasistencia, observacion, id_usuario_registro)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (id_estudiante, id_horario, fecha, estado, minutos_retraso, valor_inasistencia, observacion, id_usuario_registro))
        id_asistencia = res["lastrowid"]

    # Recalcular IVE para el estudiante
    ive_info = calcular_ive_estudiante(id_estudiante)

    return success_response({
        "id_asistencia": id_asistencia,
        "id_estudiante": id_estudiante,
        "fecha": fecha,
        "estado": estado,
        "minutos_retraso": minutos_retraso,
        "valor_inasistencia": valor_inasistencia,
        "ive": ive_info
    }, message="Asistencia registrada y métricas de permanencia actualizadas", status_code=201)


@asistencia_bp.route("/asistencia/sincronizar", methods=["POST"])
def sincronizar_batch_pwa():
    """
    Recepción de lotes JSON offline provenientes del Service Worker / IndexedDB (RF-10).
    Procesa el array de registros e inserta/actualiza masivamente.
    """
    data = request.get_json(silent=True)
    if not data or "registros_asistencia" not in data:
        return error_response("Estructura de lote offline no válida. Debe contener 'registros_asistencia'", status_code=400)

    registros = data["registros_asistencia"]
    id_docente = data.get("docente_id")

    # Validar existencia de id_docente en BD
    usr = query_db("SELECT id_usuario FROM usuario WHERE id_usuario = %s", (id_docente,), one=True) if id_docente else None
    if not usr:
        primero = query_db("SELECT id_usuario FROM usuario LIMIT 1", one=True)
        id_docente = primero["id_usuario"] if primero else 1

    procesados = 0

    for item in registros:
        tipo_doc = item.get("tipo_documento")
        num_doc = item.get("numero_documento")
        fecha = item.get("fecha")
        id_horario = item.get("id_horario", 1)
        minutos = int(item.get("minutos_retardo", item.get("minutos_retraso", 0)))
        estado = item.get("estado_calculado", item.get("estado", "presente"))
        valor = float(item.get("valor_inasistencia", 0.0))

        est = query_db("""
            SELECT e.id_estudiante
            FROM estudiante e
            JOIN usuario u ON u.id_usuario = e.id_usuario
            WHERE u.tipo_documento = %s AND u.documento = %s
        """, (tipo_doc, num_doc), one=True)

        if est:
            id_est = est["id_estudiante"]
            existente = query_db(
                "SELECT id_asistencia FROM asistencia WHERE id_estudiante = %s AND id_horario = %s AND fecha = %s",
                (id_est, id_horario, fecha),
                one=True
            )
            if existente:
                execute_db("""
                    UPDATE asistencia
                    SET estado = %s, minutos_retraso = %s, valor_inasistencia = %s, id_usuario_registro = %s
                    WHERE id_asistencia = %s
                """, (estado, minutos, valor, id_docente, existente["id_asistencia"]))
            else:
                execute_db("""
                    INSERT INTO asistencia (id_estudiante, id_horario, fecha, estado, minutos_retraso, valor_inasistencia, id_usuario_registro)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (id_est, id_horario, fecha, estado, minutos, valor, id_docente))
            procesados += 1

    return success_response({
        "total_enviados": len(registros),
        "procesados_con_exito": procesados,
        "timestamp_recepcion": date.today().isoformat()
    }, message="Sincronización PWA offline completada con éxito")


@asistencia_bp.route("/ive/estudiante/<int:id_estudiante>", methods=["GET"])
def obtener_ive_estudiante(id_estudiante: int):
    """Retorna el diagnóstico individual del Índice de Vulnerabilidad Escolar."""
    diagnostico = calcular_ive_estudiante(id_estudiante)
    return success_response(diagnostico, "IVE calculado")


@asistencia_bp.route("/ive/resumen", methods=["GET"])
def resumen_institucional_ive():
    """
    Consolidado ejecutivo para Rectoría:
    Distribución de estudiantes en el Semáforo (Verde, Naranja, Rojo) y alertas críticas.
    """
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

    total = len(estudiantes)
    return success_response({
        "total_estudiantes": total,
        "conteo_semaforo": conteo,
        "porcentajes": {
            "verde": round((conteo["verde"] / total) * 100, 1) if total > 0 else 0,
            "naranja": round((conteo["naranja"] / total) * 100, 1) if total > 0 else 0,
            "rojo": round((conteo["rojo"] / total) * 100, 1) if total > 0 else 0,
        },
        "estudiantes_en_riesgo": estudiantes_riesgo
    }, "Resumen ejecutivo de permanencia escolar obtenido")
