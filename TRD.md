# TRD - Documento de Requisitos Técnicos (v2)
## Sistema de Gestión Escolar y SAT - Institución Educativa Santa Ana / Germania

---

### 1. Stack Tecnológico y Arquitectura

* **Backend**: Python 3.10+ con **Flask** (patrón Blueprints, MVC, Application Factory).
* **Base de Datos Principal**: **MariaDB 10.5+ / MySQL 8.0+** con motor `InnoDB` y codificación `utf8mb4`.
* **Base de Datos de Pruebas**: SQLite (para ejecución rápida de pruebas unitarias).
* **Frontend & PWA**: HTML5, JS Vanilla / React con Tailwind CSS, Service Workers e IndexedDB.
* **Pruebas Automatizadas**: `unittest` y `coverage.py` con una cobertura $\ge 80\%$.

---

### 2. Esquema Relacional de Base de Datos

#### 2.1 Tablas Núcleo y Estructura
1. `rol`: Catálogo de roles RBAC (`administrador`, `rector`, `administrativo`, `docente`, `estudiante`, `acudiente`).
2. `usuario`: Credenciales, hash de contraseña (bcrypt/Argon2), documento y rol asociado.
3. `sede`: Aislamiento multi-sede con `codigo_dane` y bandera `es_principal`.
4. `anio_lectivo` & `periodo`: Fechas de vigencia y control de apertura/cierre de periodos lectivos.
5. `estudiante`: Vinculado a `usuario`, dirección y fecha de nacimiento.
6. `matricula`: Relación estudiante-curso-año lectivo con indicador `documentacion_fisica_entregada`.
7. `asignacion`: Vínculo único `UNIQUE(id_materia, id_curso)` asignando un profesor.
8. `horario`: Bloques de clase con horario inicio/fin, aula y día de la semana.
9. `calificacion` & `calificacion_auditoria`: Registro de notas (0.0 a 5.0) con auditoría inalterable de ediciones.
10. `asistencia`: Marcación por fecha, estado ('presente', 'retraso', 'ausente', 'excusa') e `id_horario`.
11. `alerta`: Alertas automáticas o manuales del semáforo IVE ('verde', 'amarillo', 'naranja', 'rojo').
12. `periodo_auditoria`: Bitácora inalterable de cierre y reapertura de periodos con justificación.

---

### 3. Integración PWA y Sincronización Batch JSON

El Service Worker intercepta la toma de asistencia sin conexión y persiste los registros en **IndexedDB**. Al reconectar, envía una solicitud `POST /api/v1/asistencia/sincronizar`:

```json
{
  "sede_id": 1,
  "docente_id": 14,
  "timestamp_envio": "2026-11-07T17:45:00Z",
  "registros_asistencia": [
    {
      "tipo_documento": "TI",
      "numero_documento": "1065849201",
      "fecha": "2026-11-07",
      "minutos_retardo": 12,
      "estado_calculado": "presente",
      "valor_inasistencia": 0.0
    },
    {
      "tipo_documento": "TI",
      "numero_documento": "1065849202",
      "fecha": "2026-11-07",
      "minutos_retardo": 25,
      "estado_calculado": "retraso",
      "valor_inasistencia": 0.5
    }
  ]
}
```
