import unittest
import os
import sqlite3
from app import create_app
from app.db_init_sqlite import init_sqlite_db


class AuthTestCase(unittest.TestCase):
    """Suite de pruebas unitarias para Autenticación y RBAC (Gate 2)."""

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
            db = get_db()
            # Limpieza en orden relacional estricto (hijas -> padres)
            db.execute("DELETE FROM asistencia;")
            db.execute("DELETE FROM calificacion;")
            db.execute("DELETE FROM actividad;")
            db.execute("DELETE FROM matricula;")
            db.execute("DELETE FROM horario;")
            db.execute("DELETE FROM asignacion;")
            db.execute("DELETE FROM estudiante;")
            db.execute("DELETE FROM profesor;")
            db.execute("DELETE FROM usuario;")
            db.commit()
            close_db()

    def test_01_health_check(self):
        """Valida que el servicio API esté en línea."""
        res = self.client.get("/api/v1/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "online")

    def test_02_catalogo_roles(self):
        """Valida que los 6 roles base estén sembrados en la base de datos."""
        res = self.client.get("/api/v1/auth/roles")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        codigos = [r["codigo"] for r in data["data"]]
        self.assertIn("administrador", codigos)
        self.assertIn("docente", codigos)
        self.assertIn("estudiante", codigos)

    def test_03_registro_usuario_exitoso(self):
        """Valida el registro de un nuevo docente con credenciales reales."""
        payload = {
            "id_rol": 4,  # docente
            "tipo_documento": "CC",
            "documento": "1065849201",
            "nombre": "Carlos",
            "apellido": "Mendoza",
            "email": "carlos.mendoza@santana.edu.co",
            "contrasena": "Docente2026*",
            "telefono": "3001234567"
        }
        res = self.client.post("/api/v1/auth/registro", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["documento"], "1065849201")
        self.assertEqual(data["data"]["rol_codigo"], "docente")

    def test_04_prevencion_duplicados_documento_409(self):
        """Valida que intentar registrar el mismo documento retorne 409 Conflict."""
        payload = {
            "id_rol": 4,
            "tipo_documento": "CC",
            "documento": "1065849201",
            "nombre": "Carlos",
            "apellido": "Mendoza",
            "email": "carlos.mendoza@santana.edu.co",
            "contrasena": "Docente2026*"
        }
        res1 = self.client.post("/api/v1/auth/registro", json=payload)
        self.assertEqual(res1.status_code, 201)

        payload_dup = payload.copy()
        payload_dup["email"] = "otro.email@santana.edu.co"
        res2 = self.client.post("/api/v1/auth/registro", json=payload_dup)
        self.assertEqual(res2.status_code, 409)
        data = res2.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Conflicto", data["error"])

    def test_05_login_exitoso_y_obtencion_jwt(self):
        """Valida autenticación correcta y generación de token JWT."""
        payload_reg = {
            "id_rol": 2,  # rector
            "tipo_documento": "CC",
            "documento": "77123456",
            "nombre": "Ana",
            "apellido": "Gómez",
            "email": "rectoria@santana.edu.co",
            "contrasena": "Rector2026*"
        }
        self.client.post("/api/v1/auth/registro", json=payload_reg)

        login_payload = {
            "tipo_documento": "CC",
            "identificador": "77123456",
            "contrasena": "Rector2026*"
        }
        res = self.client.post("/api/v1/auth/login", json=login_payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("token", data["data"])
        self.assertEqual(data["data"]["usuario"]["rol_codigo"], "rector")

        token = data["data"]["token"]

        res_me = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res_me.status_code, 200)
        me_data = res_me.get_json()
        self.assertTrue(me_data["success"])
        self.assertEqual(me_data["data"]["documento"], "77123456")

    def test_06_login_credenciales_invalidas_401(self):
        """Valida que una contraseña incorrecta sea rechazada con 401 Unauthorized."""
        payload_reg = {
            "id_rol": 3,
            "tipo_documento": "CC",
            "documento": "88123456",
            "nombre": "Secretaria",
            "apellido": "Academica",
            "email": "secretaria@santana.edu.co",
            "contrasena": "Correcta123"
        }
        self.client.post("/api/v1/auth/registro", json=payload_reg)

        login_fail = {
            "tipo_documento": "CC",
            "identificador": "88123456",
            "contrasena": "Erronea999"
        }
        res = self.client.post("/api/v1/auth/login", json=login_fail)
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertFalse(data["success"])


if __name__ == "__main__":
    unittest.main()
