import os
from werkzeug.security import generate_password_hash


def get_seed_sql_statements():
    """Genera las sentencias SQL parametrizadas para sembrar datos en cualquier motor."""
    default_pw = generate_password_hash("Germania2026*", method="scrypt")

    roles = [
        ('administrador', 'Super Administrador', 'Control global del sistema y sedes'),
        ('rector', 'Rector / Directivo', 'Supervisión multi-sede, cierre de periodos y alertas rojas'),
        ('administrativo', 'Secretaría Académica', 'Matrículas Data-Light y gestión de excusas'),
        ('docente', 'Docente de Aula', 'Planillas y pase de lista diario'),
        ('estudiante', 'Estudiante', 'Consulta de calificaciones y horarios'),
        ('acudiente', 'Padre / Acudiente', 'Seguimiento de permanencia escolar')
    ]

    parametros = [
        ('peso_retraso', '0.50', 'Ponderación de retraso frente a inasistencia total'),
        ('tiempo_gracia_retraso_min', '15', 'Minutos antes de contar como retraso'),
        ('tiempo_gracia_ausente_min', '30', 'Minutos tras los cuales cuenta como ausencia'),
        ('ive_umbral_naranja', '0.40', 'Umbral de riesgo medio'),
        ('ive_umbral_rojo', '0.70', 'Umbral de riesgo crítico de deserción')
    ]

    sedes = [
        ('Sede Principal Santa Ana', '120001001234', 'Corregimiento Germania, Valledupar', 1),
        ('Sede Rural El Prado', '120001001235', 'Vereda El Prado', 0),
        ('Sede Rural Las Flores', '120001001236', 'Vereda Las Flores', 0)
    ]

    materias = [
        ('Matemáticas',),
        ('Lengua Castellana',),
        ('Ciencias Naturales',),
        ('Ciencias Sociales',),
        ('Inglés',)
    ]

    usuarios = [
        (1, 'CC', '1001', 'Admin', 'Germania', 'admin@germania.edu.co', default_pw, '3000000001'),
        (2, 'CC', '2001', 'María', 'Rectoría', 'rectoria@germania.edu.co', default_pw, '3000000002'),
        (3, 'CC', '3001', 'Alberto', 'Secretaría', 'secretaria@germania.edu.co', default_pw, '3000000003'),
        (4, 'CC', '4001', 'Carlos', 'Mendoza', 'carlos.mendoza@germania.edu.co', default_pw, '3000000004'),
        (4, 'CC', '4002', 'Elena', 'Morales', 'elena.morales@germania.edu.co', default_pw, '3000000005'),
        (5, 'TI', '1065849201', 'Juan', 'Pérez', 'juan.perez@germania.edu.co', default_pw, '3000000006'),
        (5, 'TI', '1065849202', 'Laura', 'Díaz', 'laura.diaz@germania.edu.co', default_pw, '3000000007'),
        (5, 'TI', '1065849203', 'Mateo', 'Gómez', 'mateo.gomez@germania.edu.co', default_pw, '3000000008')
    ]

    return {
        "roles": roles,
        "parametros": parametros,
        "sedes": sedes,
        "materias": materias,
        "usuarios": usuarios
    }

