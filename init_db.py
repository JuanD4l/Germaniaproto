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
    with app.app_context():
        db = get_db()
        config = app.config
        db_type = config.get("DB_TYPE")
        database_url = config.get("DATABASE_URL")

        if db_type == "postgres" and database_url:
            print("[+] Detectado motor PostgreSQL (Render). Ejecutando schema_postgres.sql...")
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
            print("[+] Inicializando esquema SQLite...")
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
                INSERT OR IGNORE INTO asignacion (id_asignacion, id_profesor, id_materia, id_curso)
                VALUES (1, 1, 1, 1)
            """)
            cursor.execute("""
                INSERT OR IGNORE INTO horario (id_horario, id_asignacion, dia_semana, hora_inicio, hora_fin, aula)
                VALUES (1, 1, 'lunes', '07:00', '08:30', 'Aula 101')
            """)
            cursor.execute("""
                INSERT OR IGNORE INTO horario (id_horario, id_asignacion, dia_semana, hora_inicio, hora_fin, aula)
                VALUES (2, 1, 'miercoles', '08:30', '10:00', 'Aula 101')
            """)
            cursor.execute("""
                INSERT OR IGNORE INTO estudiante (id_estudiante, id_usuario, direccion, fecha_nacimiento, puntaje_esa)
                VALUES (1, 6, 'Vereda Germania', '2012-05-10', 0.20)
            """)
            cursor.execute("""
                INSERT OR IGNORE INTO matricula (id_matricula, id_estudiante, id_curso, id_anio, fecha, estado, documentacion_fisica_entregada)
                VALUES (1, 1, 1, 1, '2026-01-25', 'activa', 1)
            """)

            # Actividades y calificaciones de prueba
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


if __name__ == "__main__":
    run_init()
