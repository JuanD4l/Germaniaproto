import unittest
from app import create_app
from app.db_init_sqlite import init_sqlite_db


class WebAndRolesTestCase(unittest.TestCase):
    """Pruebas para formularios Web y control RBAC."""

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
            pw = generate_password_hash("Germania2026*", method="scrypt")

            # Sembrar rector
            db.execute("""
                INSERT OR IGNORE INTO usuario (id_usuario, id_rol, tipo_documento, documento, nombre, apellido, email, contrasena)
                VALUES (2, 2, 'CC', '2001', 'María', 'Rectoría', 'rectoria_test@santana.edu.co', ?)
            """, (pw,))

            # Sembrar profesor y asignación
            db.execute("""
                INSERT OR IGNORE INTO usuario (id_usuario, id_rol, tipo_documento, documento, nombre, apellido, email, contrasena)
                VALUES (4, 4, 'CC', '4001', 'Docente', 'Prueba', 'docente_test@santana.edu.co', ?)
            """, (pw,))
            db.execute("INSERT OR IGNORE INTO profesor (id_profesor, id_usuario, especialidad) VALUES (1, 4, 'Matemáticas')")
            db.execute("INSERT OR IGNORE INTO asignacion (id_asignacion, id_profesor, id_materia, id_curso) VALUES (1, 1, 1, 1)")

            db.commit()
            close_db()

    def test_01_web_login_flow(self):
        """Valida el inicio de sesión web con formulario y redirección al Dashboard."""
        res = self.client.post("/login", data={
            "tipo_documento": "CC",
            "identificador": "2001",
            "contrasena": "Germania2026*"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Panel de Control", res.data)

        # Logout
        res_out = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(res_out.status_code, 200)
        self.assertIn(b"Acceso Institucional", res_out.data)

    def test_02_web_crear_matricula_form(self):
        """Valida la creación de matrícula vía formulario web Data-Light."""
        # Loguearse como rector
        self.client.post("/login", data={
            "tipo_documento": "CC",
            "identificador": "2001",
            "contrasena": "Germania2026*"
        })

        res = self.client.post("/matriculas/crear", data={
            "tipo_documento": "TI",
            "documento": "1065849888",
            "nombre": "Diana",
            "apellido": "Castro",
            "fecha_nacimiento": "2013-09-12",
            "id_curso": 1,
            "puntaje_esa": 0.20,
            "documentacion_fisica_entregada": "1"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Diana Castro", res.data)

    def test_03_web_crear_horario_form(self):
        """Valida la creación de horario vía formulario web."""
        # Loguearse como rector
        self.client.post("/login", data={
            "tipo_documento": "CC",
            "identificador": "2001",
            "contrasena": "Germania2026*"
        })

        res = self.client.post("/horarios/crear", data={
            "id_asignacion": 1,
            "dia_semana": "viernes",
            "hora_inicio": "07:00",
            "hora_fin": "08:30",
            "aula": "Aula 201"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Aula 201", res.data)

    def test_04_error_handlers(self):
        """Valida las respuestas JSON de endpoints no encontrados o erróneos."""
        res = self.client.get("/api/v1/ruta_inexistente")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertFalse(data["success"])


if __name__ == "__main__":
    unittest.main()
