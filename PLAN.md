# PLAN - Roadmap de Desarrollo (v2)
## Sistema de Gestión Escolar y SAT - Proyecto Germania

---

### 1. Alcance del MVP vs. Fases Futuras

#### 1.1 MVP (Fase 1 - Piloto Sede Principal)
* **Autenticación RBAC**: Inicio de sesión seguro y restricción por rol.
* **Admisión y Matrícula Data-Light**: Registro de estudiantes sin duplicados.
* **Malla Horaria**: Asignación de materias y horarios con algoritmo de prevención de cruces.
* **Planilla y Asistencia PWA**: Marcación diaria offline y registro por dimensiones.
* **Motor IVE y Semáforo**: Cálculo automatizado y alertas de permanencia escolar.
* **Exportador SIMAT**: Descarga de reportes planos estructurados.

#### 1.2 Fases Futuras (Fases 2 y 3)
* **Fase 2**: Escalado multi-tenant a las 10 sedes veredales restantes.
* **Fase 3**: Notificaciones automáticas vía WhatsApp SMS a acudientes.

---

### 2. Hitos Secuenciales (Milestones)

* **Hito 1: Infraestructura y BD**: Configuración de Flask, MariaDB y scripts de migración.
* **Hito 2: Motor Backend y Validaciones**: Algoritmo de horarios, triggers y reglas del IVE.
* **Hito 3: Interfaz PWA e Inscripción**: Desarrollo de vistas responsivas Data-Light e IndexedDB.
* **Hito 4: Auditoría y Sincronización**: Pruebas de carga offline-online y manejo de errores HTTP.
* **Hito 5: Despliegue y Validación SENA**: Despliegue en servidor VPS y ejecución de casos de prueba.

---

### 3. Validation Gates (Puertas de Calidad)

1. **Gate 1 (Estructura)**: Aprobación de linter PEP 8 y tipos de datos.
2. **Gate 2 (Pruebas Automatizadas)**: 100% de éxito en la suite `unittest` (cruces de horarios, inmutabilidad de notas y duplicidad).
3. **Gate 3 (Revisión Humana - Maker-Checker)**: Aprobación por directivos institucionales e instructores SENA.
