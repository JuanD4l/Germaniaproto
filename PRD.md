# PRD - Documento de Requisitos de Producto (v2)
## Sistema de Gestión Escolar y SAT - Institución Educativa Santa Ana / Germania

---

### 1. Visión General del Producto y Objetivos de Negocio

#### 1.1 Problema
En la Institución Educativa Santa Ana (Valledupar, Cesar) y sus 10 sedes rurales, la gestión de matrículas, asistencia, planillas y control de deserciones se realiza manualmente en papel. Esto provoca errores en datos, duplicidad de matriculados, colisiones en horarios docentes y falta de alertas oportunas frente a la deserción escolar en zonas rurales con conectividad inestable.

#### 1.2 Propuesta de Valor
Plataforma web centralizada bajo arquitectura SaaS Multi-tenant y Aplicación Web Progresiva (PWA) "Data-Light". Digitaliza la gestión escolar, opera offline en pases de lista y planillas, calcula automáticamente el Índice de Vulnerabilidad Escolar (IVE) y consolida reportes ejecutivos para Rectoría y exportaciones oficiales compatibles con el SIMAT.

#### 1.3 Métricas y KPIs de Éxito
* **0% Registros Duplicados**: Cero incidencias de duplicación por tipo y número de documento.
* **0 Colisiones de Horario**: Bloqueo total de cruces de profesores o salones en un mismo bloque horario.
* **Operatividad Offline**: 100% de persistencia en toma de asistencia sin conexión vía Service Workers e IndexedDB.
* **Reducción de Tiempos**: 80% de ahorro de tiempo en generación de boletines y matrices SIMAT.

---

### 2. Usuarios, Roles y Permisos (RBAC)

| Rol | Descripción / Perfil | Permisos Principales |
| :--- | :--- | :--- |
| **Rector / SuperAdmin** | Directivos y Rectoría | • Supervisión multi-sede global.<br>• Apertura extemporánea y cierre de periodos lectivos.<br>• Recepción de Alertas Críticas (Semáforo Rojo IVE).<br>• Exportador estructurado de reportes SIMAT. |
| **Docente** | Personal docente de aula | • Registro diario de asistencia con tiempos de gracia (PWA offline).<br>• Carga de planillas por dimensiones (Saber, Hacer, Ser).<br>• Visualización de alertas de su grupo (Semáforo Verde/Naranja). |
| **Administrativo** | Secretaría académica | • Matriculación 'Data-Light' y verificación física de documentos.<br>• Diligenciamiento de Ficha Socioeconómica (ESA).<br>• Asignación de carga académica y radicación de excusas. |
| **Estudiante / Acudiente** | Estudiantes y padres de familia | • Consulta en solo lectura de boletines académicos.<br>• Historial de asistencia y citaciones por alertas de permanencia. |

---

### 3. Requerimientos Funcionales Clave

* **RF-01 (Autenticación RBAC)**: Inicio de sesión con credenciales y restricción de endpoints por rol.
* **RF-02 (Arquitectura Multi-Sede)**: Aislamiento lógico de datos entre la Sede Principal y las 10 sedes veredales.
* **RF-05 (Inscripción Llave Compuesta)**: Validación contra duplicados mediante `tipo_documento` + `numero_documento`.
* **RF-06 (Matrícula Data-Light)**: Verificación mediante checkbox 'Documentación Física Entregada', evitando subir archivos pesados.
* **RF-09 (Asistencia Tiempos de Gracia)**: 0-15 min (Presente: 0.0), 16-30 min (Retraso: 0.5), >30 min (Ausente: 1.0).
* **RF-10 (Captura Offline PWA)**: Guardado en IndexedDB con sincronización batch JSON al detectar red.
* **RF-13 (Cálculo del IVE)**: Algoritmo continuo en segundo plano ($\text{IVE} = 0.50\text{FA} + 0.30\text{RA} + 0.20\text{ESA}$).
* **RF-18 (Exportador SIMAT)**: Generación de archivos planos CSV/Excel estructurados para el Ministerio de Educación.
* **RF-20 (Gestión de Excusas)**: Solicitud y aprobación de excusas que neutralizan las inasistencias en el cálculo del IVE.

---

### 4. Criterios No Funcionales (RNF)

* **RNF-01 (Latencia)**: Tiempo de respuesta del servidor $< 1.5$ segundos.
* **RNF-02 (Data-Light)**: Consumo mínimo de datos optimizado para redes 2G/3G/4G rurales.
* **RNF-03 (Resiliencia PWA)**: Operatividad offline continua sin pérdida de registros.
* **RNF-04 (Seguridad)**: Cifrado HTTPS/TLS en tránsito y hash de credenciales en reposo.
* **RNF-06 (Estándar PEP 8)**: Código limpio y legible validado con linter Python.

---

### 5. Restricciones Técnicas y Exclusiones

* **Diseño Data-Light**: Interfaz ligera para baja conectividad. Sin archivos pesados ni imágenes 4K.
* **Exclusiones Explícitas**:
  - No se desarrollarán apps nativas móviles (iOS/Android); funcionará exclusivamente como PWA.
  - No incluye módulos de recaudo ni pasarelas de pago.
  - No incluye servicios de videollamadas ni streaming.
