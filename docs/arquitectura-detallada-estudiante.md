# Consulta estudiantil — arquitectura detallada del MVP

Actualización: la UI, contratos y orquestación inicial están descritos en [Asistente del estudiante](student-assistant.md). SUMAdapter y gestión de conexiones permanecen pendientes; este documento conserva el diseño completo del flujo previsto.

Estado: diseño propuesto, todavía no implementado. Caso de referencia: desaprobación reiterada de un curso. La evidencia regulatoria proviene del RAG institucional; los datos académicos minimizados se producen en la pasarela SUM después de recopilarlos. Primero se implementará una fuente simulada. No se presupone un umbral institucional de desaprobación ni un esquema de datos SUM.

[Arquitectura general](../ARQUITECTURA.md) · [Separación de servicios](separacion-servicios.md) · [Diagrama editable de componentes](componentes-estudiante.drawio)

## 1. Componentes y despliegue

~~~mermaid
flowchart LR
  UI[Interfaz: React / Vite / TanStack Router] -->|REST + SSE| API[Backend API: FastAPI]
  API -->|Transacción| State[(Estado privado / eventos de consulta)]
  API --> Outbox[Despachador outbox]
  Outbox -->|Solo referencia de ejecución| Inngest[Servidor Inngest]
  Inngest -->|Invoca endpoint SDK| AI[AI Service / host de flujos FastAPI]
  AI --> Runner[Ejecutor acotado de consultas]
  Runner --> Tools[Registro de herramientas aprobadas]
  Runner --> Model[Adaptador de modelo independiente del proveedor]
  Runner -->|Contexto, artefactos y progreso: contrato interno| API
  Tools --> RAG[Recuperación + relaciones documentales]
  RAG --> KB[(PostgreSQL institucional / pgvector opcional)]
  Tools --> Checks[Comprobaciones deterministas versionadas]
  Tools --> Gateway[SUM Gateway / contexto académico]
  API -->|Crear o revocar conexión| Gateway
  Gateway --> Mock[Adaptador SUM simulado]
  Gateway -.-> Future[Adaptador futuro Playwright / API autorizada]
  Gateway --> Snapshot[(Instantáneas privadas con vencimiento)]
~~~

El sistema backend contiene cuatro servicios independientes: Backend API, AI Service/host del flujo, SUM Gateway e Indexer Service. Este diagrama de consulta estudiantil omite la ingesta. Inngest proporciona ejecución durable; no es el proceso que ejecuta el código Python de la aplicación. AI Service aloja el endpoint SDK de Inngest y ejecuta las funciones registradas cuando se invocan. Cada servicio tiene su propio proceso o contenedor aunque el código esté en un mismo repositorio y una misma máquina.

Al principio, una instancia PostgreSQL puede alojar los esquemas `application`, `institutional` y `academic`, administrados respectivamente por Backend API, Indexer Service y SUM Gateway. AI Service lee el corpus publicado y solicita contexto, artefactos y cambios de estado mediante los contratos internos. No escribe las tablas privadas de otros servicios. No se guardan vectores de estudiantes en el esquema institucional.

### Módulos de frontend

- /assistant: formulario de consulta y contexto académico simulado seleccionado.
- /assistant/$runId: cronología de progreso, flujo reconectable, panel de evidencia y orientación final.
- /connections/sum: gestión inicial de una conexión simulada; posteriormente, inicio de sesión visible con Playwright local.
- Cliente API: crear, cancelar y consultar una ejecución; reconectar a SSE desde el último número de secuencia recibido.
- Mostrar solo etapas públicas, evidencia y resultados; nunca el razonamiento interno del modelo.

### Módulos del backend

- consultations: validación de propiedad, validación de entradas, creación idempotente y transiciones de estado.
- connections: vínculos entre el usuario autenticado y los identificadores opacos de la pasarela; creación/revocación mediante SUM Gateway. La selección de datos de prueba se marca como simulada.
- event_stream: reproducción SSE autorizada y entrega en directo desde eventos persistidos.
- outbox: despacho confiable de eventos de ejecución a Inngest después de confirmar la transacción de base de datos.
- repositories: acceso privado a ejecuciones, resultados, eventos y conexiones.
- internal_execution_api: contexto autorizado, artefactos y actualizaciones idempotentes para AI Service; valida cancelación, eliminación y vencimiento antes de aceptar cambios.

### Módulos de la API de IA

- workflow: ejecución durable de fases y límites de reintento.
- runner: etapas principales fijas con un ciclo acotado de seguimiento mediante herramientas.
- tools: entradas y salidas permitidas, ejecución con validación de propiedad y límites de tiempo.
- retrieval: evidencia y relaciones entre documentos que consideran su aplicabilidad.
- rule_registry: reglas revisadas y codificadas explícitamente, vinculadas a versiones de fuentes.
- model_adapter: invocación de herramientas independiente del proveedor y generación de respuestas estructuradas.
- answer_validator: integridad de citas, detección de afirmaciones no respaldadas y manejo de datos faltantes.

### Módulos de la pasarela SUM

- connections: ciclo de vida del adaptador y alcance autorizado de las conexiones solicitadas por Backend API.
- adapter: recopilar los campos fuente necesarios mediante un simulador y, después, Playwright o una API institucional.
- normalizer: mapeo específico del adaptador entre los datos de origen y el dominio; los valores desconocidos siguen siendo desconocidos.
- minimizer: conservar solo los datos permitidos y eliminar de forma determinista identificadores innecesarios.
- snapshot_store: artefactos estructurados privados con fecha, procedencia y vencimiento.

El JSON SUM sin procesar permanece dentro de la pasarela: no se registra ni se escribe en Inngest. Los datos normalizados se minimizan o seudonimizan; esto no garantiza anonimato.

## 2. Secuencia de consulta

~~~mermaid
sequenceDiagram
  actor S as Estudiante
  participant UI as Interfaz React
  participant API as Backend API
  participant DB as PostgreSQL privado
  participant O as Despachador outbox
  participant I as Inngest
  participant AI as AI Service / host del flujo
  participant R as Recuperación institucional
  participant G as SUM Gateway
  participant GS as Almacén privado de la pasarela
  participant M as Adaptador del modelo
  S->>UI: Consultar por desaprobación reiterada
  UI->>API: POST /v1/consultations + clave de idempotencia
  API->>DB: Crear ejecución y outbox en una transacción
  API-->>UI: 202 run_id + stream_url
  UI->>API: Obtener eventos (SSE)
  O->>DB: Reclamar registro outbox pendiente
  O->>I: consultation.requested {run_id}
  I->>AI: Invocar pasos del flujo registrado
  AI->>API: Obtener contexto autorizado (contrato interno)
  API->>DB: Cargar ejecución, pregunta y vínculo de conexión
  API-->>AI: Contexto permitido + estado vigente
  AI->>R: Buscar reglas candidatas y su aplicabilidad
  R-->>AI: Pasajes + versiones de fuentes + relaciones
  opt Se requieren datos personales
    AI->>G: Recopilar datos permitidos de la conexión vinculada
    G->>G: Simular recopilación → normalizar → minimizar
    G->>GS: Guardar instantánea con vencimiento
    G-->>AI: Referencia a la instantánea
    AI->>G: Leer únicamente los datos autorizados de la instantánea
    G-->>AI: Contexto minimizado + faltantes + vencimiento
  end
  AI->>AI: Evaluar comprobaciones registradas; en otro caso, marcar desconocido
  loop Seguimiento acotado mediante herramientas cuando se justifique
    AI->>M: Datos necesarios + evidencia + herramientas permitidas
    M-->>AI: Propuesta de llamada a herramienta o síntesis estructurada
    AI->>AI: Validar argumentos, límites y aplicabilidad
    AI->>R: Solicitar evidencia adicional o consulta de relaciones
    R-->>AI: Evidencia o brecha explícita
  end
  AI->>M: Redactar orientación con citas
  M-->>AI: Respuesta estructurada
  AI->>AI: Validar citas y conclusiones calificadas
  AI->>API: Publicar resultado validado (contrato interno idempotente)
  API->>DB: Verificar estado y guardar resultado + evento terminal en una transacción
  API-->>UI: Progreso SSE y referencia al resultado final
  UI->>API: GET /v1/consultations/{run_id}
  API-->>UI: Respuesta + citas + limitaciones
  Note over I,AI: Los datos durables contienen solo referencias
  Note over API,UI: La desconexión SSE no cancela el trabajo
~~~

AI Service envía el progreso mediante el contrato interno de Backend API, que guarda los eventos SSE durante toda la ejecución, no solo al finalizar. Los artefactos de fases también se leen y guardan mediante ese contrato. El ciclo puede solicitar contexto adicional acotado y evidencia. Lo limita la política de la aplicación, no la cantidad de documentos del corpus.

## 3. Contratos de API pública

Endpoints propuestos; todas las rutas de usuario validan la propiedad de la ejecución o la conexión.

| Endpoint | Contrato |
|---|---|
| POST /v1/connections/sum/mock | Crear una conexión explícitamente simulada y vinculada al usuario, usando datos permitidos. Devolver un ID de conexión opaco. |
| DELETE /v1/connections/sum/{connection_id} | Desconectar, revocar el identificador, borrar instantáneas e impedir nuevas recopilaciones. |
| POST /v1/consultations | Aceptar pregunta, ID de conexión opcional e indicio del curso objetivo. Crear atómicamente la ejecución y el evento outbox. Devolver 202, el ID y la URL del flujo. |
| GET /v1/consultations/{run_id} | Devolver el estado actual y, si está disponible, el resultado estructurado. |
| GET /v1/consultations/{run_id}/events | SSE con IDs ordenados, reproducción desde Last-Event-ID y señales de actividad. |
| POST /v1/consultations/{run_id}/cancel | Registrar una cancelación cooperativa; los trabajadores verifican antes de usar herramientas y publicar resultados. |
| DELETE /v1/consultations/{run_id} | Solicitar eliminación, cancelar el trabajo activo e impedir que se regeneren artefactos eliminados. |

Usar el mismo origen para desarrollo y servicio, o un cliente de flujo autenticado; el EventSource nativo del navegador no puede enviar cabeceras Authorization arbitrarias. No incluir tokens de portador en las URL del flujo. El mecanismo de autenticación sigue pendiente de decisión.

La clave de idempotencia se limita al usuario y al cuerpo de la solicitud. Reutilizarla con contenido distinto produce un conflicto. También hace falta deduplicar el despacho porque el envío al outbox puede completarse antes de registrar su confirmación.

## 4. Estado, progreso y transmisión

Estados de ejecución: queued → running → completed | failed | cancelled. Una ejecución en cola se puede cancelar. Si faltan datos, puede terminar con orientación condicionada en lugar de fallar. La etapa es un campo separado: retrieving, collecting_context, checking, following_up, composing, validating.

El evento SSE contiene ID o secuencia, ID de ejecución, tipo de evento, fecha y contenido público permitido. Tipos propuestos:

- run.started
- stage.changed
- evidence.available (IDs de documentos y citas)
- context.status (disponible, faltante o vencido; sin datos académicos)
- run.completed (referencia al resultado)
- run.failed (código de error seguro)
- run.cancelled

Guardar cada evento antes de entregarlo, con un valor único (run_id, sequence). El SSE del MVP puede consultar PostgreSQL periódicamente; no hace falta un broker nuevo. Al reconectar, reproducir los eventos posteriores al ID confirmado y continuar la transmisión sin dejar un hueco entre reproducción y directo. Si se perdió el período de retención, devolver una respuesta explícita de resincronización para que la interfaz recargue el estado. Cerrar después de entregar un evento terminal. La desconexión solo cierra al suscriptor.

Transmitir primero el progreso y entregar la respuesta final después de validarla. La transmisión de tokens puede añadirse más adelante: el texto parcial todavía no es orientación validada y es difícil retractarlo.

## 5. Datos académicos y contratos de herramientas

Estos contratos de dominio internos son propuestas; no afirman cuál es el esquema de respuesta de SUM.

### Instantánea académica

snapshot_id, referencia a propietario/conexión, source=mock|sum, retrieved_at, expires_at, campos solicitados, datos disponibles, campos faltantes y advertencias de normalización. SUM Gateway administra la instantánea; AI Service accede mediante su contrato, con alcance y vencimiento verificados.

Para el caso de referencia, los posibles datos son el curso objetivo, la versión curricular, los períodos académicos y los intentos relevantes del curso. Cada intento conserva el estado fuente y un resultado normalizado (passed, failed, withdrawn, unknown) cuando el mapeo esté verificado. Nunca se infiere que un retiro equivale a desaprobar. Solo se recopilan estados adicionales si una regla recuperada los necesita.

### Herramientas aprobadas

| Herramienta | Entradas | Resultado |
|---|---|---|
| retrieve_regulations | Pregunta y filtros de aplicabilidad admitidos. | Pasajes, IDs de documento/versión, localizadores y metadatos de aplicabilidad. |
| inspect_document_relationships | IDs de documentos recuperados. | Enlaces de modificación o reemplazo y evidencia de esas relaciones. |
| request_academic_context | Conjunto permitido de campos y curso objetivo. | Referencia a instantánea privada, disponibilidad y campos faltantes. |
| evaluate_registered_rule | ID de regla conocida, IDs de evidencia y referencia a instantánea. | Cumple/no cumple/desconocido, datos usados, faltantes, versión de la regla y citas. |

El código de la aplicación inyecta la propiedad y la identidad de la conexión; el modelo nunca las elige. Las herramientas no aceptan SQL, URL, acciones de navegador ni código arbitrarios. El texto recuperado y el contenido SUM son datos, no instrucciones que puedan cambiar la política de herramientas.

### Límites del razonamiento regulatorio

El RAG aporta evidencia, pero el texto recuperado no se convierte automáticamente en una regla determinista ejecutable. Para obtener consecuencias deterministas hace falta un registro de reglas revisadas. Sin una regla registrada, el asistente ofrece una interpretación con citas e indica si la aplicabilidad no está resuelta. Antes de aplicar un umbral se revisan las modificaciones y el período académico. Que un documento esté en el corpus no demuestra que rija para ese estudiante.

## 6. Modelo de datos y durabilidad de la ejecución

| Tabla o artefacto lógico | Propietario | Propósito |
|---|---|---|
| consultations | Backend API | Propietario, pregunta privada, estado/etapa, conexión, marcas de cancelación/eliminación, fechas y vencimiento. |
| consultation_events | Backend API | Eventos públicos de progreso ordenados para reproducir SSE. |
| outbox | Backend API | Referencia de despacho y estado de entrega; no guarda preguntas ni instantáneas. |
| Vínculos usuario/conexión | Backend API | Asociar el usuario al identificador opaco de SUM Gateway. |
| academic_connections | SUM Gateway | Identificador del adaptador, alcance autorizado, origen, ciclo de vida y vencimiento; sin contraseñas. |
| academic_snapshots | SUM Gateway | Datos privados minimizados, procedencia y vencimiento. |
| consultation_artifacts | Backend API | Resultados privados por fase, selección de evidencia y respuestas personalizadas, enviados por AI Service. |
| tool_executions | Backend API | ID de operación estable, estado, referencia al artefacto y código de fallo seguro; sin datos sin procesar en los logs. |
| Catálogo de documentos/versiones y trabajos | Backend API | Registro administrativo de fuentes y solicitudes de ingesta. |
| Texto derivado, fragmentos, vectores y relaciones institucionales | Indexer Service | Corpus regulatorio publicado; índice pgvector opcional. AI Service tiene acceso de lectura. |
| Registro de reglas revisadas | AI Service | Comprobaciones codificadas y vinculadas a versiones verificadas de las fuentes; puede empezar como configuración versionada de la aplicación. |

Fases durables: inicializar, recuperar evidencia, obtener contexto si hace falta, comprobar/continuar, redactar/validar y finalizar. Cada paso obtiene datos privados mediante contratos internos y una referencia, y devuelve solo un ID de artefacto o un estado seguro. El resultado final de la función Inngest también contiene solo referencias. Los errores de pasos se limpian para evitar que las excepciones filtren cuerpos de respuesta o instrucciones.

La reproducción de Inngest no garantiza que las llamadas externas se ejecuten una sola vez. Se necesitan IDs estables por ejecución/fase/iteración de herramienta, artefactos privados memorizados y escrituras de estado idempotentes. Si una llamada al modelo tiene éxito pero el proceso falla antes de guardar el resultado, un reintento puede repetirla y generar un costo; hace falta una política de reintentos acotada. La reconexión SSE no debe repetir todo el ciclo del agente.

La transacción que crea la ejecución también crea el registro outbox. El despacho puede repetirse de forma segura. Backend API guarda el resultado final, el estado terminal y su evento en una sola transacción; rechaza publicaciones después de una cancelación, eliminación o vencimiento. AI Service también verifica esas condiciones antes de usar herramientas. La eliminación de una consulta coordina el borrado de sus instantáneas mediante SUM Gateway, con reintentos idempotentes si la pasarela no está disponible.

## 7. Privacidad, fallos y límites provisionales

- No incluir datos estudiantiles SUM, minimizados o sin procesar, instrucciones, respuestas personalizadas ni tokens del navegador en eventos/pasos de Inngest, logs de consola o el corpus vectorial compartido.
- Las respuestas SUM sin procesar solo existen durante el procesamiento en la pasarela. Guardar únicamente los datos necesarios y minimizados en privado.
- Las solicitudes al modelo reciben solo los datos necesarios y la evidencia seleccionada; la retención del proveedor queda pendiente de la selección del proveedor.
- Los resultados simulados se identifican claramente, incluida la respuesta final. No se afirma que se hayan verificado con SUM en vivo.
- La orientación general continúa disponible sin SUM. Si faltan datos académicos, las comprobaciones se marcan como desconocidas o condicionadas.
- Los fallos de SUM, tiempos de espera del modelo, brechas de recuperación y errores de normalización tienen códigos seguros diferentes. Reintentar operaciones transitorias con espera acotada; no reintentar indefinidamente esquemas inválidos ni reglas sin respaldo.
- Límites iniciales propuestos: 8 llamadas a herramientas, 2 rondas de seguimiento, 120 segundos por consulta y 1 operación SUM concurrente por conexión. Son propuestas de ajuste, no requisitos confirmados; los límites reales del proveedor y del navegador se configuran por separado.
- Retención provisional con enfoque de privacidad: las instantáneas y artefactos vencen al cabo de una hora o antes si se desconecta o elimina la conexión; las ejecuciones obsoletas se detienen antes de usar datos vencidos. Los metadatos generales de ejecución/eventos vencen en 24 horas. La pregunta y la respuesta también son artefactos privados sujetos a vencimiento; los metadatos retenidos no deben conservarlas.
- La eliminación debe abarcar filas privadas, logs, copias de seguridad según una política documentada y, si corresponde, almacenamiento del proveedor. Las referencias en los eventos de Inngest reducen la exposición, pero no eliminan la retención de identificadores.

## 8. Demostración y decisiones pendientes

Demostración: elegir un registro académico sintético claramente identificado → consultar por desaprobación reiterada → mostrar en transmisión las etapas de recuperación/contexto/comprobación → recibir orientación condicionada y con citas. Después, desconectar la fuente simulada y mostrar que siguen disponibles las consultas regulatorias generales. Un adaptador simulado o real implementa el mismo contrato de la pasarela.

Antes de implementar, confirmar: autenticación de la aplicación, proveedor/adaptador del modelo, despliegue y versión probada de Inngest, límites de retención y mapeo de campos SUM al dominio. Los umbrales institucionales se obtienen de evidencia RAG verificada y definiciones de reglas revisadas; nunca de constantes de datos de prueba.

## Referencias

- [Ciclo de vida de ejecución de Inngest para Python](https://github.com/inngest/inngest-py/blob/main/pkg/inngest/docs/REQUEST_LIFECYCLE.md)
- [SDK de Inngest para Python](https://github.com/inngest/inngest-py)
- [SSE en FastAPI](https://fastapi.tiangolo.com/tutorial/server-sent-events/)
- [Respuestas en transmisión de FastAPI](https://fastapi.tiangolo.com/advanced/custom-response/)

Los diagramas Mermaid de Markdown se pueden importar mediante la opción Mermaid de draw.io. El archivo .drawio permite editar los componentes.
