# 🏫 Proyecto Germania — Sistema de Gestión Escolar y SAT Rural

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask 3.0](https://img.shields.io/badge/Framework-Flask%203.0-green.svg)](https://flask.palletsprojects.com/)
[![Render Deploy](https://img.shields.io/badge/Deploy-Render-46E3B7.svg)](https://render.com/)
[![Tests & Coverage](https://img.shields.io/badge/Coverage-85%25-brightgreen.svg)]()
[![License: SENA ADSO](https://img.shields.io/badge/Academic-SENA%20ADSO%202026-orange.svg)]()

> Prototipo funcional del **Sistema de Información Educativa (SIE)** y **Sistema de Alertas Tempranas (SAT)** para la Institución Educativa Santa Ana (corregimiento de Germania, Valledupar, Cesar) y sus sedes rurales veredales. Optimizado bajo arquitectura **Data-Light** para baja conectividad (2G/3G) con cálculo automatizado del **Índice de Vulnerabilidad Escolar (IVE)**.

---

## 📌 1. Supuestos de Diseño e Implementación

1. **Alcance del MVP Institucional**: Modela la **Sede Principal Santa Ana** y dos sedes rurales veredales (*El Prado* y *Las Flores*), implementando los roles esenciales del RBAC: **Rector/Directivo**, **Docente**, **Secretaría Académica** y **Estudiante/Acudiente**.
2. **Motor de Base de Datos en Render**: Se utiliza **Managed PostgreSQL** nativo de Render como base de datos en la nube (proporcionada mediante `DATABASE_URL`). Para ejecución local y testing automatizado sin dependencias externas pesadas, la aplicación incluye fallback transparente a **SQLite** (y soporte para **MariaDB/MySQL**).
3. **Matrícula Data-Light**: Para prevenir el colapso de red en zonas rurales, la entrega de documentos no requiere la subida de archivos PDF/imágenes pesadas, sino una verificación física mediante el indicador `documentacion_fisica_entregada` (RNF-02).
4. **Prevención de Duplicados**: La unicidad del estudiante se garantiza mediante la llave compuesta obligatoria `(tipo_documento, documento)`. Cualquier intento de reinscripción retorna un código HTTP `409 Conflict`.
5. **Algoritmo Anti-Cruce de Horarios**: Un bloque de clase no puede solaparse para el mismo docente ni para la misma aula en el mismo tramo horario. Condición estricta: $\text{Choque} = (A.\text{hora\_inicio} < B.\text{hora\_fin}) \land (A.\text{hora\_fin} > B.\text{hora\_inicio})$. Un conflicto retorna `422 Unprocessable Entity`.
6. **Motor IVE & Prevención de Deserción Escolar**:
   $$\text{IVE} = (\text{FA} \times 0.50) + (\text{RA} \times 0.30) + (\text{ESA} \times 0.20)$$
   - **FA (Factor Ausentismo - 50%)**: Conteo exacto de inasistencias ponderadas (Presente $0.0$, Retraso $0.5$, Ausente $1.0$). Excusas médicas o calamidad aprobadas neutralizan la falta a $0.0$.
   - **RA (Rendimiento Académico - 30%)**: Promedio ponderado y asignaturas en riesgo de reprobación ($< 3.0$).
   - **ESA (Encuesta Socioeconómica de Vulnerabilidad Rural - 20%)**: Tiempo de desplazamiento por trocha, estrato, conectividad y apoyo laboral en cosecha.
   - **Semáforo SAT**:
     * 🟢 **Verde (Permanencia Estable)**: $\text{IVE} < 0.40$ y fallas $< 10\%$.
     * 🟠 **Naranja (Riesgo Moderado / Alerta Temprana)**: $\text{IVE}$ entre $0.40 - 0.69$ o fallas $\ge 10\%$.
     * 🔴 **Rojo (Riesgo Crítico de Abandono)**: $\text{IVE} \ge 0.70$ o fallas $\ge 15\%$.

---

## 🏛️ 2. Arquitectura de la Solución

```mermaid
flowchart TD
    subgraph Cliente_DataLight ["Cliente Web & PWA"]
        UI_Admin["Portal Directivo & Docente"]
        UI_Estudiante["Portal Estudiantil (Solo Lectura)"]
        SW["Service Worker & IndexedDB (Offline)"]
    end

    subgraph Backend_Flask ["Servidor Web en Render (Flask Application Factory)"]
        WSGI["Gunicorn (wsgi:app)"]
        AuthBP["Blueprint Auth (JWT / Sesiones RBAC)"]
        AcadBP["Blueprint Académico (Matrículas y Horarios)"]
        AsisBP["Blueprint Asistencia & Motor IVE"]
        EstBP["Blueprint Estudiante (Solo Lectura)"]
        RepBP["Blueprint Reportes SIMAT & SAT"]
        WebBP["Blueprint Web (Vistas Jinja2)"]
    end

    subgraph Persistencia ["Base de Datos en Render"]
        PG[("Render Managed PostgreSQL")]
        SQLite[("SQLite Local / Testing")]
    end

    UI_Admin --> WSGI
    UI_Estudiante --> WSGI
    SW -.->|Lotes JSON Offline| AsisBP
    WSGI --> WebBP
    WSGI --> AuthBP
    WSGI --> AcadBP
    WSGI --> AsisBP
    WSGI --> EstBP
    WSGI --> RepBP

    AuthBP --> PG
    AcadBP --> PG
    AsisBP --> PG
    EstBP --> PG
    RepBP --> PG

    AuthBP -.-> SQLite
    AcadBP -.-> SQLite
    AsisBP -.-> SQLite
```

---

## 💻 3. Módulos y Portales del Sistema

### 1. Centro SAT - Monitoreo Anti-Deserción (`/sat`)
- Filtros por nivel del semáforo (🔴 Crítico, 🟠 Medio, 🟢 Estable).
- Desglose clínico de cada estudiante en riesgo: inasistencias exactas, materias reprobadas y factores socioeconómicos.
- **Ficha Clínica SAT (`/sat/estudiante/<id>`)**: Radiografía matemática del IVE ($50\%$ Ausentismo, $30\%$ Académico, $20\%$ ESA).
- **Radicación de Excusas (RF-20)**: Formulario administrativo para aprobar excusas médicas o de calamidad, neutralizando las faltas a $0.0$ y recalculando el IVE en tiempo real.

### 2. Portal Estudiantil en Solo Lectura (`/estudiante/portal`)
- Vista exclusiva y protegida para estudiantes y acudientes.
- Acceso a calificaciones, horario semanal, tareas vigentes e historial de asistencia con diagnóstico de permanencia.
- **Aislamiento RBAC estricto**: Bloqueo automático `403 Forbidden` si un estudiante intenta acceder a `/matriculas`, `/horarios` o `/asistencia`.

### 3. Exportador Oficial SIMAT (`/api/v1/reportes/simat`)
- Descarga en 1 clic de archivos planos CSV estructurados según la plantilla ministerial del Ministerio de Educación Nacional.

---

## 🧪 4. Pruebas Automatizadas (Gate 2: 85% Cobertura)

```bash
# Ejecutar todas las pruebas unitarias
python -m unittest discover tests

# Reporte con coverage.py
python -m coverage run -m unittest discover tests
python -m coverage report
```

```text
----------------------------------------------------------------------
Ran 23 tests in 19.064s

OK
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
app\__init__.py                            46      6    87%
app\blueprints\academico\routes.py        110     36    67%
app\blueprints\asistencia\routes.py       136     31    77%
app\blueprints\auth\routes.py              80     14    82%
app\blueprints\estudiante\routes.py        27      5    81%
app\blueprints\reportes\routes.py          27      0   100%
app\blueprints\web\routes.py              168     43    74%
app\config.py                              35      2    94%
app\database.py                            62     11    82%
tests\test_auth.py                         91      1    99%
tests\test_estudiante_portal.py            64      1    98%
tests\test_germania_core.py                95      1    99%
tests\test_reportes.py                     44      1    98%
tests\test_web_and_roles.py                50      1    98%
-----------------------------------------------------------
TOTAL                                    1139    171    85%
```

---

## ☁️ 5. Despliegue en Render

El repositorio incluye el archivo Blueprint [`render.yaml`](file:///c:/Users/LEMUS/OneDrive/Desktop/ADSO/prototipo%20germania/render.yaml):
1. Sube tu código a GitHub:
   ```bash
   git push -u origin main
   ```
2. En [Render Dashboard](https://dashboard.render.com/), haz clic en **New +** -> **Blueprint**.
3. Selecciona tu repositorio `germania`.
4. Render creará automáticamente la base de datos PostgreSQL (`germania-db`), el servicio web Python (`germania-web`), ejecutará `python init_db.py` y desplegará la aplicación con HTTPS gratuito.
