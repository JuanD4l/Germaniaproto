# AGENTS.md - Fuente Única de Verdad (PIC 2026)
<!-- Estado de Certificación: CERTIFICADO CONSOLIDADO (100% Madurez) -->

## System Brief
- **Propósito del Sistema**: Sistema de Información Educativa (SIE) bajo modelo SaaS Multi-tenant y Aplicación Web Progresiva (PWA) "Germania", para la gestión escolar rural y prevención de la deserción escolar mediante el cálculo del Índice de Vulnerabilidad Escolar (IVE).
- **Público Objetivo & Permisos (RBAC)**:
  1. **Rector / SuperAdmin**: Control multi-sede, cierre/reapertura de periodos lectivos, recepción de alertas críticas (Rojo) y exportación de datos SIMAT.
  2. **Docente**: Planilla de calificaciones multidimensionales (Saber, Hacer, Ser), pase de lista diario offline (PWA) con tiempos de gracia y semáforo pedagógico.
  3. **Administrativo**: Matrícula 'Data-Light', ficha socioeconómica (ESA), asignación de carga académica y radicación de excusas.
  4. **Estudiante / Acudiente**: Consulta en modo solo lectura de boletines, historial de asistencia y seguimiento académico.
- **KPIs Críticos**:
  - **0% Registros Duplicados**: Cero duplicidad en matriculación de estudiantes (llave compuesta `tipo_documento` + `numero_documento`).
  - **0 Colisiones de Horario**: Validación estricta que previene cruces de profesor o aula en el mismo tramo horario.
  - **Latencia < 1.5s**: Respuesta en carga de planillas y formularios.
  - **Sincronización PWA < 3.0s**: Lotes JSON de asistencia offline hacia el backend central.
- **Modelo Emocional / Tone & Vibe**: Quirúrgico, estructurado, determinista y sin respuestas ambiguas ni sesgadas.

## Operational Rules
- **Stack Tecnológico**:
  - **Backend**: Python 3.10+ / Flask (Patrón Blueprints, MVC, Application Factory).
  - **Base de Datos Principal**: MariaDB 10.5+ / MySQL 8.0+ (ENGINE=InnoDB, UTF8MB4).
  - **Base de Datos de Pruebas**: SQLite (Pruebas unitarias `unittest`).
  - **Frontend / PWA**: HTML5, JS Vanilla / React, Service Workers + IndexedDB para almacenamiento offline.
- **Estándares de Código**: Código modular bajo PEP 8. Cobertura de pruebas unitarias $\ge 80\%$ (`unittest` / `coverage.py`).
- **Manejo de Errores & Logging**: Trace ID en logs JSON. Mapeo normativo de excepciones HTTP (`409 Conflict` para duplicados, `422 Unprocessable Entity` para cruce de horarios, `403 Forbidden` para accesos no autorizados o periodos cerrados).

## Harness Config
- **Hooks Obligatorios (`PreToolUse`)**: Validar tipos de datos y esquemas Pydantic/JSON antes de invocar operaciones de escritura o modificación.
- **Comandos Permitidos**: Formateo Markdown/JSON, consultas SQL parametrizadas en MariaDB/SQLite.
- **Límites de Contexto**: Máximo 8,000 tokens por loop activo. Purgar memoria efímera mediante ventana deslizante (sliding window).

## Architectural Rules & Business Logic
- **Prevención de Cruces de Horario**: Condición estricta $\text{Choque} = (A.\text{hora\_inicio} < B.\text{hora\_fin}) \land (A.\text{hora\_fin} > B.\text{hora\_inicio})$.
- **Cálculo del IVE**: $\text{IVE} = (\text{FA} \times 0.50) + (\text{RA} \times 0.30) + (\text{ESA} \times 0.20)$. Excusas aprobadas neutralizan el ausentismo ($\text{FA} = 0.0$).
- **Semáforo IVE**: Verde ($< 0.40$), Naranja ($0.40 - 0.69$ o fallas $\ge 10\%$), Rojo ($\ge 0.70$ o fallas $\ge 15\%$).

## Persistence Loop
- **Protocolo de Memoria y Auditoría**: Auditoría obligatoria para modificaciones de notas (`calificacion_auditoria`) y cierres/reaperturas de periodos (`periodo_auditoria`).
- **Condiciones de Parada (`/goal`)**: Detener la iteración tras cumplir el objetivo de la tarea o tras 5 intentos infructuosos.
- **Mecanismo Maker-Checker**: Requerir aprobación explícita del usuario para acciones destructivas (`DROP`, `TRUNCATE`) o pases a producción.
