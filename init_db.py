import os
import sys
from app import create_app
from app.database import get_db, close_db
from app.db_init_sqlite import init_sqlite_db
from database.seed_data import get_seed_sql_statements


def run_init():
    """Inicializa tablas y datos semilla según el motor activo (PostgreSQL, MariaDB, SQLite)."""
    env = os.getenv("FLASK_ENV", "development")
    app = create_app(env)

    print(f"[*] Inicializando base de datos para entorno: {env}...")
    try:
        with app.app_context():
            db = get_db()
            config = app.config
            db_type = config.get("DB_TYPE")
            database_url = config.get("DATABASE_URL")

            if db_type == "postgres" and database_url:
                print("[+] Detectado motor PostgreSQL. Ejecutando schema_postgres.sql...")
                schema_path = os.path.join(os.path.dirname(__file__), "database", "schema_postgres.sql")
                with open(schema_path, "r", encoding="utf-8") as f:
                    ddl = f.read()

                cursor = db.cursor()
                cursor.execute(ddl)
                db.commit()

                print("[+] Sembrando datos iniciales en PostgreSQL...")
                seed = get_seed_sql_statements()

                for rol in seed["roles"]:
                    cursor.execute("""
                        INSERT INTO rol (codigo, nombre, descripcion)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (codigo) DO NOTHING;
                    """, rol)

                for param in seed["parametros"]:
                    cursor.execute("""
                        INSERT INTO parametro_sistema (clave, valor, descripcion)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (clave) DO NOTHING;
                    """, param)

                for sede in seed["sedes"]:
                    cursor.execute("""
                        INSERT INTO sede (nombre, codigo_dane, direccion, es_principal)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (nombre) DO NOTHING;
                    """, (sede[0], sede[1], sede[2], bool(sede[3])))

                for mat in seed["materias"]:
                    cursor.execute("""
                        INSERT INTO materia (nombre)
                        VALUES (%s)
                        ON CONFLICT (nombre) DO NOTHING;
                    """, mat)

                cursor.execute("""
                    INSERT INTO anio_lectivo (anio, fecha_inicio, fecha_fin, estado)
                    VALUES (2026, '2026-01-20', '2026-11-30', 'activo')
                    ON CONFLICT (anio) DO NOTHING;
                """)
                cursor.execute("""
                    INSERT INTO periodo (id_anio, numero, fecha_inicio, fecha_fin, estado)
                    VALUES (1, 1, '2026-01-20', '2026-04-10', 'abierto')
                    ON CONFLICT (id_anio, numero) DO NOTHING;
                """)
                cursor.execute("""
                    INSERT INTO curso (id_sede, id_anio, nombre, grado, jornada)
                    VALUES (1, 1, 'Grado 6° A', 6, 'manana')
                    ON CONFLICT (id_sede, id_anio, nombre) DO NOTHING;
                """)

                for usr in seed["usuarios"]:
                    cursor.execute("""
                        INSERT INTO usuario (id_rol, tipo_documento, documento, nombre, apellido, email, contrasena, telefono)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (tipo_documento, documento) DO NOTHING;
                    """, usr)

                cursor.execute("""
                    INSERT INTO profesor (id_usuario, especialidad)
                    SELECT id_usuario, 'Matemáticas y Ciencias' FROM usuario WHERE documento = '4001'
                    ON CONFLICT (id_usuario) DO NOTHING;
                """)
                cursor.execute("""
                    INSERT INTO asignacion (id_profesor, id_materia, id_curso)
                    VALUES (1, 1, 1)
                    ON CONFLICT (id_materia, id_curso) DO NOTHING;
                """)
                cursor.execute("""
                    INSERT INTO horario (id_asignacion, dia_semana, hora_inicio, hora_fin, aula)
                    VALUES (1, 'lunes', '07:00:00', '08:30:00', 'Aula 101')
                    ON CONFLICT DO NOTHING;
                """)

                # Estudiante de prueba Juan Pérez
                cursor.execute("""
                    INSERT INTO estudiante (id_usuario, direccion, fecha_nacimiento, puntaje_esa)
                    SELECT id_usuario, 'Corregimiento Germania', '2012-05-14', 0.20 FROM usuario WHERE documento = '1065849201'
                    ON CONFLICT (id_usuario) DO NOTHING;
                """)
                cursor.execute("""
                    INSERT INTO matricula (id_estudiante, id_curso, id_anio, fecha, estado, documentacion_fisica_entregada)
                    SELECT e.id_estudiante, 1, 1, '2026-01-25', 'activa', TRUE
                    FROM estudiante e
                    JOIN usuario u ON u.id_usuario = e.id_usuario
                    WHERE u.documento = '1065849201'
                    ON CONFLICT (id_estudiante, id_anio) DO NOTHING;
                """)

                # Sembrar Actividades y Notas
                cursor.execute("""
                    INSERT INTO actividad (id_asignacion, titulo, descripcion, fecha_entrega, estado)
                    VALUES (1, 'Taller 1: Fracciones y Operaciones Básicas', 'Resolver ejercicios 1 al 15 de la guía pedagógica', '2026-03-15', 'pendiente')
                    ON CONFLICT DO NOTHING;
                """)
                cursor.execute("""
                    INSERT INTO calificacion (id_estudiante, id_asignacion, id_periodo, nota, id_usuario_registro)
                    SELECT e.id_estudiante, 1, 1, 4.2, 4
                    FROM estudiante e
                    JOIN usuario u ON u.id_usuario = e.id_usuario
                    WHERE u.documento = '1065849201'
                    ON CONFLICT (id_estudiante, id_asignacion, id_periodo) DO NOTHING;
                """)

                db.commit()
                cursor.close()
                print("[✓] Base de datos PostgreSQL inicializada y sembrada con éxito.")

            else:
                # SQLite / Local
                print("[+] Inicializando esquema SQLite local...")
                init_sqlite_db(db)
                cursor = db.cursor()
                seed = get_seed_sql_statements()
                for usr in seed["usuarios"]:
                    cursor.execute("""
                        INSERT OR IGNORE INTO usuario (id_rol, tipo_documento, documento, nombre, apellido, email, contrasena, telefono)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, usr)

                cursor.execute("""
                    INSERT OR IGNORE INTO profesor (id_profesor, id_usuario, especialidad)
                    VALUES (1, 4, 'Matemáticas')
                """)
                cursor.execute("""
                    INSERT OR IGNORE INTO profesor (id_profesor, id_usuario, especialidad)
                    VALUES (2, 5, 'Matemáticas y Cálculo')
                """)
                cursor.execute("""
                    INSERT OR IGNORE INTO asignacion (id_asignacion, id_profesor, id_materia, id_curso)
                    VALUES (1, 1, 1, 1)
                """)
                cursor.execute("""
                    INSERT OR IGNORE INTO asignacion (id_asignacion, id_profesor, id_materia, id_curso)
                    VALUES (2, 2, 1, 1)
                """)
                cursor.execute("""
                    INSERT OR IGNORE INTO horario (id_horario, id_asignacion, dia_semana, hora_inicio, hora_fin, aula)
                    VALUES (1, 1, 'lunes', '07:00', '08:30', 'Pabellón B - 204')
                """)
                cursor.execute("""
                    INSERT OR IGNORE INTO horario (id_horario, id_asignacion, dia_semana, hora_inicio, hora_fin, aula)
                    VALUES (2, 1, 'miercoles', '08:30', '10:00', 'Pabellón B - 204')
                """)

                # Sembrar todos los estudiantes
                estudiantes_meta = [
                    ('1065849201', 'Vereda Germania', '2012-05-10', 0.20, 'O+', 'Sanitas Salud', 'Penicilina, Nueces, Polen', 'María Rodríguez', '+57 300 123 4567', 'Km 7 Vía a Atánquez, Vereda El Cielo, Valledupar, Cesar (Área Rural)'),
                    ('1065123456', 'Km 7 Vía a Atánquez, Vereda El Cielo', '2011-04-12', 0.45, 'O+', 'Sanitas Salud', 'Penicilina, Nueces, Polen', 'María Rodríguez', '+57 300 123 4567', 'Km 7 Vía a Atánquez, Vereda El Cielo, Valledupar, Cesar (Área Rural)'),
                    ('1065987654', 'Vereda Las Flores', '2011-09-20', 0.15, 'A+', 'Nueva EPS', 'Ninguna', 'Carlos García', '+57 310 987 6543', 'Vereda Las Flores, Finca La Esperanza'),
                    ('1065112233', 'Vereda El Jabo', '2010-11-15', 0.60, 'B+', 'Coosalud', 'Rinitis', 'Rosa Rodríguez', '+57 312 345 6789', 'Vereda El Jabo, Sector El Puente'),
                    ('1065112234', 'Vereda Patillal', '2011-02-14', 0.10, 'O+', 'Famisanar', 'Ninguna', 'Jorge Beltrán', '+57 314 567 8901', 'Corregimiento de Patillal'),
                    ('1065112235', 'Vereda Guacoche', '2011-06-18', 0.25, 'O-', 'Salud Total', 'Polen', 'Martha Gómez', '+57 315 678 9012', 'Corregimiento de Guacoche'),
                    ('1065112236', 'Vereda Atánquez', '2011-08-30', 0.30, 'A-', 'Sura', 'Ninguna', 'David Vargas', '+57 316 789 0123', 'Corregimiento de Atánquez'),
                    ('1065112237', 'Vereda Badillo', '2011-03-22', 0.20, 'AB+', 'Sanitas', 'Ninguna', 'Lucía Martínez', '+57 317 890 1234', 'Corregimiento de Badillo'),
                    ('1065112238', 'Vereda La Vega', '2011-12-05', 0.15, 'O+', 'Compensar', 'Asma leve', 'Fernando Castro', '+57 318 901 2345', 'Vereda La Vega'),
                    ('1065112239', 'Vereda Los Corazones', '2011-07-11', 0.22, 'B-', 'Sanitas', 'Ninguna', 'Gloria Jiménez', '+57 319 012 3456', 'Corregimiento Los Corazones'),
                    ('1065112240', 'Vereda Las Raíces', '2011-01-29', 0.18, 'O+', 'Nueva EPS', 'Ninguna', 'Andrés Ortiz', '+57 320 123 4567', 'Corregimiento Las Raíces'),
                    ('1065112241', 'Vereda El Alto', '2011-05-19', 0.28, 'A+', 'Salud Total', 'Ninguna', 'Paola Quintero', '+57 321 234 5678', 'Vereda El Alto de la Vuelta'),
                    ('1065112242', 'Vereda El Jabo', '2011-10-08', 0.12, 'O+', 'Coosalud', 'Ninguna', 'Roberto Salazar', '+57 322 345 6789', 'Vereda El Jabo'),
                    ('20240012', 'Sede Principal Urbana', '2009-03-15', 0.10, 'O+', 'Sanitas Salud', 'Ninguna', 'Carmen Montenegro', '+57 301 234 5678', 'Calle 14 # 8-22, Valledupar'),
                    ('20240015', 'Km 3 Vía a La Paz', '2009-07-20', 0.55, 'B+', 'Nueva EPS', 'Rinitis alérgica', 'Héctor Bermúdez', '+57 302 345 6789', 'Vereda San Lorenzo, Finca El Recuerdo'),
                    ('20240018', 'Barrio Los Fundadores', '2008-11-02', 0.05, 'A+', 'Sura', 'Ninguna', 'Patricia Vega', '+57 303 456 7890', 'Carrera 23 # 12-40, Valledupar'),
                    ('1092348', 'Vereda Atánquez', '2011-04-10', 0.65, 'O+', 'Coosalud', 'Ninguna', 'Clara Rodríguez', '+57 304 567 8901', 'Sector Resguardo Indígena Kankuamo'),
                    ('1092551', 'Vereda Guacochito', '2011-08-14', 0.40, 'AB+', 'Sanitas', 'Polen', 'Javier López', '+57 305 678 9012', 'Vereda Guacochito Km 2'),
                    ('1092882', 'Vereda El Alto', '2010-12-25', 0.70, 'O-', 'Nueva EPS', 'Asma', 'Silvia Garzón', '+57 306 789 0123', 'Vereda El Alto'),
                    ('1092889', 'Sede Principal', '2009-02-18', 0.10, 'O+', 'Sanitas', 'Ninguna', 'Martín Alemán', '+57 307 890 1234', 'Calle Real # 4-50')
                ]

                for doc, dir_dom, fnac, pesa, gsang, eps, alerg, acud, tel_acud, dir_comp in estudiantes_meta:
                    u = cursor.execute("SELECT id_usuario FROM usuario WHERE documento = ?", (doc,)).fetchone()
                    if u:
                        uid = u["id_usuario"] if isinstance(u, dict) else u[0]
                        cursor.execute("""
                            INSERT OR IGNORE INTO estudiante (id_usuario, direccion, fecha_nacimiento, puntaje_esa)
                            VALUES (?, ?, ?, ?)
                        """, (uid, dir_dom, fnac, pesa))
                        e = cursor.execute("SELECT id_estudiante FROM estudiante WHERE id_usuario = ?", (uid,)).fetchone()
                        if e:
                            eid = e["id_estudiante"] if isinstance(e, dict) else e[0]
                            # Estado de matrícula: Carlos Rodríguez como 'retirada', los demás 'activa'
                            est_mat = 'retirada' if doc == '1065112233' else 'activa'
                            cursor.execute("""
                                INSERT OR IGNORE INTO matricula (id_estudiante, id_curso, id_anio, fecha, estado, documentacion_fisica_entregada)
                                VALUES (?, 1, 1, '2026-01-25', ?, 1)
                            """, (eid, est_mat))

                            cursor.execute("""
                                INSERT OR IGNORE INTO ficha_socioeconomica
                                (id_estudiante, distancia_kms, tiempo_desplazamiento_min, medio_transporte, grupo_sanguineo, proveedor_eps, alergias_condiciones, contacto_emergencia_nombre, contacto_emergencia_telefono, direccion_domicilio, vulnerabilidad_score)
                                VALUES (?, 7.0, 40, 'Caminata', ?, ?, ?, ?, ?, ?, ?)
                            """, (eid, gsang, eps, alerg, acud, tel_acud, dir_comp, pesa))

                # Configuración de usuario por defecto para Elena Rivas (id_usuario=5)
                cursor.execute("""
                    INSERT OR IGNORE INTO configuracion_usuario (id_usuario, umbral_inasistencia_critica, umbral_rendimiento_bajo, notificar_alertas_automaticas)
                    VALUES (5, 15.0, 3.0, 1)
                """)

                cursor.execute("""
                    INSERT OR IGNORE INTO actividad (id_actividad, id_asignacion, titulo, descripcion, fecha_entrega, estado)
                    VALUES (1, 1, 'Taller 1: Fracciones y Operaciones Básicas', 'Resolver ejercicios 1 al 15 de la guía pedagógica institucional', '2026-03-15', 'pendiente')
                """)
                cursor.execute("""
                    INSERT OR IGNORE INTO actividad (id_actividad, id_asignacion, titulo, descripcion, fecha_entrega, estado)
                    VALUES (2, 1, 'Guía 2: Geometría Plana y Áreas', 'Dibujar y calcular área de 5 figuras poligonales en papel milimetrado', '2026-03-22', 'pendiente')
                """)
                cursor.execute("""
                    INSERT OR IGNORE INTO calificacion (id_calificacion, id_estudiante, id_asignacion, id_periodo, nota, id_usuario_registro)
                    VALUES (1, 1, 1, 1, 4.2, 4)
                """)

                db.commit()
                cursor.close()
                print("[✓] Base de datos SQLite inicializada y sembrada con éxito.")

            close_db()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[!] Advertencia durante la inicialización de BD: {e}")
        print("[!] El despliegue continuará con normalidad.")



if __name__ == "__main__":
    run_init()
