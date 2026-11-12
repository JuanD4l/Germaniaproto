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
        (4, 'CC', '4002', 'Elena', 'Rivas', 'elena.rivas@germania.edu.co', default_pw, '3000000005'),
        (5, 'TI', '1065849201', 'Juan', 'Pérez', 'juan.perez@germania.edu.co', default_pw, '3000000006'),
        (5, 'TI', '1065849202', 'Laura', 'Díaz', 'laura.diaz@germania.edu.co', default_pw, '3000000007'),
        (5, 'TI', '1065849203', 'Mateo', 'Gómez', 'mateo.gomez@germania.edu.co', default_pw, '3000000008'),
        (5, 'TI', '1065123456', 'Juan', 'Pérez', 'juan.perez2@germania.edu.co', default_pw, '3000000009'),
        (5, 'TI', '1065987654', 'María', 'García', 'maria.garcia@germania.edu.co', default_pw, '3000000010'),
        (5, 'TI', '1065112233', 'Carlos', 'Rodríguez', 'carlos.rodriguez@germania.edu.co', default_pw, '3000000011'),
        (5, 'TI', '1065112234', 'Ana', 'Beltrán', 'ana.beltran@germania.edu.co', default_pw, '3000000012'),
        (5, 'TI', '1065112235', 'Pedro', 'Gómez', 'pedro.gomez@germania.edu.co', default_pw, '3000000013'),
        (5, 'TI', '1065112236', 'Sofía', 'Vargas', 'sofia.vargas@germania.edu.co', default_pw, '3000000014'),
        (5, 'TI', '1065112237', 'Luis', 'Martínez', 'luis.martinez@germania.edu.co', default_pw, '3000000015'),
        (5, 'TI', '1065112238', 'Laura', 'Castro', 'laura.castro@germania.edu.co', default_pw, '3000000016'),
        (5, 'TI', '1065112239', 'Mateo', 'Jiménez', 'mateo.jimenez@germania.edu.co', default_pw, '3000000017'),
        (5, 'TI', '1065112240', 'Valentina', 'Ortiz', 'valentina.ortiz@germania.edu.co', default_pw, '3000000018'),
        (5, 'TI', '1065112241', 'Daniel', 'Quintero', 'daniel.quintero@germania.edu.co', default_pw, '3000000019'),
        (5, 'TI', '1065112242', 'Isabela', 'Salazar', 'isabela.salazar@germania.edu.co', default_pw, '3000000020'),
        (5, 'TI', '20240012', 'Juan', 'Alvarado Montenegro', 'juan.alvarado@germania.edu.co', default_pw, '3000000021'),
        (5, 'TI', '20240015', 'Lucía', 'Bermúdez Estrada', 'lucia.bermudez@germania.edu.co', default_pw, '3000000022'),
        (5, 'TI', '20240018', 'Roberto', 'Calderón Vega', 'roberto.calderon@germania.edu.co', default_pw, '3000000023'),
        (5, 'TI', '1092348', 'Mateo', 'Rodríguez', 'mateo.rodriguez@germania.edu.co', default_pw, '3000000024'),
        (5, 'TI', '1092551', 'Isabella', 'López', 'isabella.lopez@germania.edu.co', default_pw, '3000000025'),
        (5, 'TI', '1092882', 'Lucas', 'Garzón', 'lucas.garzon@germania.edu.co', default_pw, '3000000026'),
        (5, 'TI', '1092889', 'Mateo', 'Alemán', 'mateo.aleman@germania.edu.co', default_pw, '3000000027')
    ]

    return {
        "roles": roles,
        "parametros": parametros,
        "sedes": sedes,
        "materias": materias,
        "usuarios": usuarios
    }

