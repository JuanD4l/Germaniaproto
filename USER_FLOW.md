# User Flow - Flujo de Navegación y Experiencia de Usuario (v2)
## Sistema de Gestión Escolar - Proyecto Germania

---

### 1. Caminos Críticos por Rol ("Happy Paths")

#### 1.1 Flujo del Administrador / Rector
1. **Inicio de Sesión**: Ingresa credenciales -> Validación de token/sesión y rol (`Rector` o `Administrativo`).
2. **Dashboard Multi-Sede**: Muestra estadísticas globales y semáforo de riesgo IVE por sedes.
3. **Módulo de Matrícula**: Formulario `tipo_documento` + `documento`. Checkbox `documentacion_fisica_entregada`.
4. **Malla Horaria**: Selección de curso y docente. Sistema valida traslapes antes de guardar.
5. **Cierre de Periodo**: Ejecuta `UPDATE periodo SET estado = 'cerrado'`. Requiere definición previa de `@id_usuario_actual` y `@justificacion_periodo`.

#### 1.2 Flujo del Docente (PWA Offline)
1. **Inicio de Sesión & Carga de Caché**: La PWA descarga grupos y estudiantes asignados.
2. **Toma de Asistencia Daily**:
   - Selecciona clase y marca: Presente (0-15 min), Retraso (16-30 min), Ausente (>30 min).
   - En caso de desconexión: La PWA guarda en **IndexedDB** y muestra indicador *"Guardado Local"*.
3. **Sincronización**: Al detectar red, el Service Worker dispara el envío batch JSON y actualiza el semáforo UI.

#### 1.3 Flujo del Estudiante / Acudiente
1. **Inicio de Sesión**: Ingresa credenciales -> Redirección a `/estudiante/dashboard`.
2. **Consulta de Horario y Calificaciones**: Vista de solo lectura. Inmutabilidad estricta (sin botones de edición).

---

### 2. Manejo de Excepciones y Casos Borde

#### 2.1 Registro Duplicado (`HTTP 409 Conflict`)
- **Escenario**: Se intenta matricular un estudiante con un documento ya existente.
- **Respuesta**: El backend o trigger aborta la inserción y retorna error `409 Conflict`. La UI despliega banner rojo: *"El documento ya se encuentra registrado"*.

#### 2.2 Cruce de Horario (`HTTP 422 Unprocessable Entity`)
- **Escenario**: Se intenta asignar a un profesor o aula una clase que se solapa con otra existente.
- **Respuesta**: El procedimiento `sp_validar_horario` detiene la acción y retorna error `422`. Banner UI: *"El profesor/aula ya tiene otra clase asignada en ese bloque"*.

#### 2.3 Edición de Nota en Periodo Cerrado (`HTTP 403 Forbidden`)
- **Escenario**: Un docente intenta modificar una calificación cuando el periodo está en estado `'cerrado'`.
- **Respuesta**: Trigger `trg_calificacion_bu` cancela la edición con error `403`. Banner UI: *"Periodo cerrado: se requiere reapertura autorizada por Rectoría"*.
