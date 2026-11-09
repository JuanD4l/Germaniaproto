import unittest
from app import create_app
from app.db_init_sqlite import init_sqlite_db


class ReportesTestCase(unittest.TestCase):
    """Suite de pruebas para el Exportador SIMAT (RF-18) y Matriz IVE."""

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
            pw = generate_password_hash("Docente123*", method="scrypt")

            # Sembrar estudiante para reporte
            db.execute("""
                INSERT OR IGNORE INTO usuario (id_usuario, id_rol, tipo_documento, documento, nombre, apellido, email, contrasena)
                VALUES (70, 5, 'TI', '1065849777', 'Simat', 'Prueba', 'simat@santana.edu.co', ?)
            """, (pw,))

            db.execute("""
                INSERT OR IGNORE INTO estudiante (id_estudiante, id_usuario, direccion, fecha_nacimiento, puntaje_esa)
                VALUES (70, 70, 'Vereda Las Flores', '2012-08-11', 0.20)
            """)

            db.execute("""
                INSERT OR IGNORE INTO matricula (id_matricula, id_estudiante, id_curso, id_anio, fecha, estado, documentacion_fisica_entregada)
                VALUES (70, 70, 1, 1, '2026-01-22', 'activa', 1)
            """)

            db.commit()
            close_db()

    def test_01_exportar_simat_csv(self):
        """Valida que el archivo CSV SIMAT se descargue con la cabecera estándar y contenido."""
        res = self.client.get("/api/v1/reportes/simat")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "text/csv")
        self.assertIn("attachment; filename=SIMAT_matricula_germania_2026.csv", res.headers.get("Content-Disposition", ""))

        data = res.data.decode("utf-8")
        self.assertIn("CODIGO_DANE_SEDE", data)
        self.assertIn("NUMERO_DOCUMENTO", data)
        self.assertIn("1065849777", data)

    def test_02_exportar_ive_consolidado_csv(self):
        """Valida que el reporte IVE descargue la matriz de riesgo de permanencia."""
        res = self.client.get("/api/v1/reportes/ive-consolidado")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "text/csv")
        self.assertIn("attachment; filename=SAT_consolidado_IVE_germania_2026.csv", res.headers.get("Content-Disposition", ""))

        data = res.data.decode("utf-8")
        self.assertIn("VALOR_IVE", data)
        self.assertIn("SEMAFORO_RIESGO", data)


if __name__ == "__main__":
    unittest.main()

