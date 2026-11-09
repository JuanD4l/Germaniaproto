import unittest
from app import create_app
from app.db_init_sqlite import init_sqlite_db


class EstudiantePortalTestCase(unittest.TestCase):
    """Suite de pruebas para el Portal de Estudiante (Solo Lectura) y RBAC estricto."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app("testing")
        with cls.app.app_context():
            from app.database import get_db, close_db
            db = get_db()
            init_sqlite_db(db)
            close_db()

    def setUp(self):
        self.app = self.__class__.app
        self.client = self.app.test_client()

        with self.app.app_context():
            from app.database import get_db, close_db
            from werkzeug.security import generate_password_hash
            db = get_db()
            pw = generate_password_hash("Estudiante2026*", method="scrypt")

            # Sembrar profesor y asignación requeridos por las FKs
            db.execute("""
                INSERT OR IGNORE INTO usuario (id_usuario, id_rol, tipo_documento, documento, nombre, apellido, email, contrasena)
                VALUES (1, 4, 'CC', '4001', 'Carlos', 'Mendoza', 'carlos@santana.edu.co', ?)
            """, (pw,))
            db.execute("INSERT OR IGNORE INTO profesor (id_profesor, id_usuario, especialidad) VALUES (1, 1, 'Matemáticas')")
            db.execute("INSERT OR IGNORE INTO asignacion (id_asignacion, id_profesor, id_materia, id_curso) VALUES (1, 1, 1, 1)")

            # Sembrar estudiante
            db.execute("""
                INSERT OR IGNORE INTO usuario (id_usuario, id_rol, tipo_documento, documento, nombre, apellido, email, contrasena)
                VALUES (50, 5, 'TI', '1065849999', 'Mateo', 'Estudiante', 'mateo@santana.edu.co', ?)
            """, (pw,))

            db.execute("""
                INSERT OR IGNORE INTO estudiante (id_estudiante, id_usuario, direccion, fecha_nacimiento, puntaje_esa)
                VALUES (50, 50, 'Vereda Germania', '2012-07-20', 0.25)
            """)

            db.execute("""
                INSERT OR IGNORE INTO matricula (id_matricula, id_estudiante, id_curso, id_anio, fecha, estado, documentacion_fisica_entregada)
                VALUES (50, 50, 1, 1, '2026-01-20', 'activa', 1)
            """)

            db.execute("""
                INSERT OR IGNORE INTO actividad (id_actividad, id_asignacion, titulo, descripcion, fecha_entrega, estado)
                VALUES (50, 1, 'Taller de Comprensión Lectora', 'Guía pedagógica mensual', '2026-03-30', 'pendiente')
            """)

            db.execute("""
                INSERT OR IGNORE INTO calificacion (id_calificacion, id_estudiante, id_asignacion, id_periodo, nota, id_usuario_registro)
                VALUES (50, 50, 1, 1, 4.5, 1)
            """)

            db.commit()
            close_db()

    def test_01_login_estudiante_redirige_a_portal(self):
        """Valida que el login de un estudiante redirija automáticamente a su portal."""
        res = self.client.post("/login", data={
            "tipo_documento": "TI",
            "identificador": "1065849999",
            "contrasena": "Estudiante2026*"
        }, follow_redirects=False)

        self.assertEqual(res.status_code, 302)
        self.assertIn("/estudiante/portal", res.location)

    def test_02_portal_estudiante_contenido_solo_lectura(self):
        """Valida que el portal cargue notas, horario, actividades e IVE en solo lectura."""
        self.client.post("/login", data={
            "tipo_documento": "TI",
            "identificador": "1065849999",
            "contrasena": "Estudiante2026*"
        })

        res = self.client.get("/estudiante/portal")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        self.assertIn("Mateo Estudiante", html)
        self.assertIn("Modo Consulta • Solo Lectura", html)
        self.assertIn("Mis Calificaciones", html)
        self.assertIn("Taller de Comprensión Lectora", html)
        self.assertIn("4.5", html)
        self.assertIn("Permanencia (IVE)", html)

    def test_03_rbac_estudiante_bloqueado_de_matriculas(self):
        """Valida que un estudiante logueado NO pueda acceder al módulo administrativo de matrículas."""
        self.client.post("/login", data={
            "tipo_documento": "TI",
            "identificador": "1065849999",
            "contrasena": "Estudiante2026*"
        })

        res = self.client.get("/matriculas", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn("Acceso Denegado (403)", html)
        self.assertIn("Portal del Estudiante", html)

    def test_04_rbac_estudiante_bloqueado_de_crear_matricula(self):
        """Valida que un estudiante no pueda enviar formularios de matrícula."""
        self.client.post("/login", data={
            "tipo_documento": "TI",
            "identificador": "1065849999",
            "contrasena": "Estudiante2026*"
        })

        res = self.client.post("/matriculas/crear", data={
            "tipo_documento": "TI",
            "documento": "99999999",
            "nombre": "Infiltrado",
            "apellido": "Test",
            "id_curso": 1
        }, follow_redirects=True)

        html = res.data.decode("utf-8")
        self.assertIn("Acceso Denegado (403)", html)

    def test_05_rbac_estudiante_bloqueado_de_asistencia_docente(self):
        """Valida que un estudiante no pueda acceder al pase de lista docente."""
        self.client.post("/login", data={
            "tipo_documento": "TI",
            "identificador": "1065849999",
            "contrasena": "Estudiante2026*"
        })

        res = self.client.get("/asistencia", follow_redirects=True)
        html = res.data.decode("utf-8")
        self.assertIn("Acceso Denegado (403)", html)


if __name__ == "__main__":
    unittest.main()
