import unittest
from datetime import date
from app import create_app
from app.db_init_sqlite import init_sqlite_db


class GermaniaCoreTestCase(unittest.TestCase):
    """Suite de pruebas para la lógica central de Germania (Hitos 1, 2 y 3)."""

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

            from werkzeug.security import generate_password_hash
            pw = generate_password_hash("Docente123*", method="scrypt")
            db.execute("""
                INSERT INTO usuario (id_usuario, id_rol, tipo_documento, documento, nombre, apellido, email, contrasena)
                VALUES (10, 4, 'CC', '5001', 'Profesor', 'Prueba', 'profesor@santana.edu.co', ?)
            """, (pw,))
            db.execute("INSERT INTO profesor (id_profesor, id_usuario, especialidad) VALUES (1, 10, 'Matemáticas')")
            db.execute("INSERT INTO asignacion (id_asignacion, id_profesor, id_materia, id_curso) VALUES (1, 1, 1, 1)")
            db.commit()
            close_db()

    def test_01_matricula_data_light_y_prevencion_duplicados(self):
        """Valida inscripción Data-Light y control de colisión 409 por documento."""
        payload = {
            "tipo_documento": "TI",
            "documento": "1065999001",
            "nombre": "Estudiante",
            "apellido": "Uno",
            "fecha_nacimiento": "2013-05-10",
            "id_curso": 1,
            "documentacion_fisica_entregada": True,
            "puntaje_esa": 0.20
        }
        res1 = self.client.post("/api/v1/matriculas", json=payload)
        self.assertEqual(res1.status_code, 201)
        data1 = res1.get_json()
        self.assertTrue(data1["success"])
        self.assertTrue(data1["data"]["documentacion_fisica_entregada"])

        res2 = self.client.post("/api/v1/matriculas", json=payload)
        self.assertEqual(res2.status_code, 409)
        data2 = res2.get_json()
        self.assertFalse(data2["success"])
        self.assertIn("Conflicto", data2["error"])

    def test_02_algoritmo_anti_cruce_horarios_422(self):
        """Valida que un cruce en el horario de un docente o aula sea bloqueado con 422."""
        h1 = {
            "id_asignacion": 1,
            "dia_semana": "lunes",
            "hora_inicio": "07:00",
            "hora_fin": "08:30",
            "aula": "Aula 101"
        }
        res1 = self.client.post("/api/v1/horarios", json=h1)
        self.assertEqual(res1.status_code, 201)

        h_solapado = {
            "id_asignacion": 1,
            "dia_semana": "lunes",
            "hora_inicio": "08:00",
            "hora_fin": "09:30",
            "aula": "Aula 102"
        }
        res2 = self.client.post("/api/v1/horarios", json=h_solapado)
        self.assertEqual(res2.status_code, 422)
        data2 = res2.get_json()
        self.assertFalse(data2["success"])
        self.assertIn("Colisión de Horario", data2["error"])

    def test_03_asistencia_tiempos_de_gracia(self):
        """Valida cálculo normativo: presente (0.0), retraso (0.5), ausente (1.0)."""
        mat_res = self.client.post("/api/v1/matriculas", json={
            "tipo_documento": "TI",
            "documento": "1065999002",
            "nombre": "Carlos",
            "apellido": "Ruiz",
            "fecha_nacimiento": "2013-02-15",
            "id_curso": 1
        })
        id_estudiante = mat_res.get_json()["data"]["id_estudiante"]

        hor_res = self.client.post("/api/v1/horarios", json={
            "id_asignacion": 1,
            "dia_semana": "martes",
            "hora_inicio": "07:00",
            "hora_fin": "08:30",
            "aula": "Aula 101"
        })
        id_horario = hor_res.get_json()["data"]["id_horario"]

        res = self.client.post("/api/v1/asistencia/registrar", json={
            "id_estudiante": id_estudiante,
            "id_horario": id_horario,
            "fecha": "2026-02-03",
            "estado": "retraso",
            "minutos_retraso": 20
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["data"]["valor_inasistencia"], 0.5)
        self.assertEqual(data["data"]["estado"], "retraso")

    def test_04_motor_ive_y_semaforo(self):
        """Valida que el Índice de Vulnerabilidad Escolar se calcule correctamente."""
        mat_res = self.client.post("/api/v1/matriculas", json={
            "tipo_documento": "TI",
            "documento": "1065999005",
            "nombre": "Estudiante",
            "apellido": "Prueba",
            "fecha_nacimiento": "2013-01-01",
            "id_curso": 1,
            "puntaje_esa": 0.30
        })
        id_estudiante = mat_res.get_json()["data"]["id_estudiante"]

        res = self.client.get(f"/api/v1/ive/estudiante/{id_estudiante}")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("valor_ive", data["data"])
        self.assertIn(data["data"]["nivel_riesgo"], ["verde", "naranja", "rojo"])

    def test_05_sincronizacion_batch_pwa(self):
        """Valida recepción masiva de registros offline generados por la PWA."""
        self.client.post("/api/v1/matriculas", json={
            "tipo_documento": "TI",
            "documento": "1065999003",
            "nombre": "Ana",
            "apellido": "Torres",
            "fecha_nacimiento": "2013-08-20",
            "id_curso": 1
        })

        hor_res = self.client.post("/api/v1/horarios", json={
            "id_asignacion": 1,
            "dia_semana": "miercoles",
            "hora_inicio": "10:00",
            "hora_fin": "11:30",
            "aula": "Aula 102"
        })
        id_horario = hor_res.get_json()["data"]["id_horario"]

        batch_payload = {
            "sede_id": 1,
            "docente_id": 10,
            "registros_asistencia": [
                {
                    "tipo_documento": "TI",
                    "numero_documento": "1065999003",
                    "fecha": "2026-02-04",
                    "id_horario": id_horario,
                    "minutos_retardo": 10,
                    "estado_calculado": "presente",
                    "valor_inasistencia": 0.0
                }
            ]
        }
        res = self.client.post("/api/v1/asistencia/sincronizar", json=batch_payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["procesados_con_exito"], 1)

    def test_06_vistas_web_render(self):
        """Valida que las páginas principales carguen con código HTTP 200."""
        # Loguearse como docente para tener permisos administrativos de vista
        self.client.post("/login", data={
            "tipo_documento": "CC",
            "identificador": "5001",
            "contrasena": "Docente123*"
        })

        rutas = ["/", "/matriculas", "/horarios", "/asistencia"]
        for r in rutas:
            res = self.client.get(r)
            self.assertEqual(res.status_code, 200, f"Fallo al cargar ruta {r}")


if __name__ == "__main__":
    unittest.main()
