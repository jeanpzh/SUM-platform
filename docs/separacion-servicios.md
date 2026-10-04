# Separación de servicios del MVP

Estado: Backend API, su despachador e Indexer Service implementados inicialmente; AI Service y SUM Gateway continúan como diseño. Consulta la [guía del indexador](indexer-service.md) para los contratos ejecutables y los límites de validación.

**AI Service e Indexer Service pertenecen al sistema backend y se ejecutan por separado de Backend API.** La palabra backend describe el conjunto de servicios del servidor; Backend API designa exclusivamente la entrada pública y el control del ciclo de vida de las solicitudes.

## Responsabilidades y límites

| Servicio | Responsabilidad | Datos que administra | Forma de ejecución |
|---|---|---|---|
| Backend API | Autenticar, autorizar, aceptar solicitudes, registrar documentos/versiones, crear trabajos, cancelar, guardar progreso/resultados y servir REST/SSE. | Consultas, eventos, artefactos privados de consulta, trabajos, outbox, catálogo de fuentes y vínculos usuario/conexión. | API pública y despachador outbox como proceso auxiliar del mismo servicio. |
| AI Service | Recuperar evidencia publicada, consultar relaciones, pedir contexto académico, ejecutar reglas revisadas y redactar/validar orientación. | Configuración del flujo, herramientas y reglas; los artefactos durables de consulta se guardan mediante Backend API. | Aplicación interna con su propio host de flujos y límites de llamadas al modelo. |
| Indexer Service | Leer fuentes registradas, extraer texto, fragmentar, generar embeddings, validar y publicar el índice. | Texto derivado, fragmentos, vectores, relaciones derivadas y manifiestos de publicación del corpus institucional. | Trabajadores asíncronos con concurrencia y reintentos propios. |
| SUM Gateway | Administrar conexiones del adaptador, recopilar campos autorizados, normalizar, minimizar y borrar datos al vencer o desconectarse. | Sesiones efímeras del adaptador e instantáneas académicas privadas. | Servicio interno; adaptador simulado primero, Playwright local después y API institucional cuando exista una integración autorizada. |

Las interfaces llaman únicamente a Backend API. El endpoint SDK de un host de flujos admite llamadas autenticadas del orquestador; no es una API pública para estudiantes. Los contratos entre servicios validan identidad del servicio, alcance y operación. Un ID de ejecución o instantánea por sí solo no concede acceso.

## Flujo de consultas

1. Backend API valida al usuario y crea consulta + outbox en una transacción.
2. Su despachador envía a Inngest una referencia de ejecución; Inngest invoca el host de AI Service.
3. AI Service obtiene el contexto autorizado mediante un contrato interno de Backend API y consulta únicamente versiones publicadas del corpus.
4. Si necesita datos académicos, AI Service solicita a SUM Gateway los campos permitidos para la conexión vinculada por Backend API. La pasarela conserva la instantánea y entrega sus datos minimizados mediante su contrato autorizado.
5. AI Service envía artefactos, progreso y resultado a Backend API. Backend API valida las transiciones, cancelación, eliminación y vencimiento, y persiste los cambios idempotentemente.
6. Backend API entrega los eventos SSE y la respuesta validada a la interfaz.

AI Service no escribe directamente las tablas de consultas. SUM Gateway no escribe tablas del corpus. El flujo de consultas usa el último índice publicado mientras se procesa una nueva versión.

## Flujo de indexación

1. Backend API registra el documento, su versión y la referencia al archivo fuente; crea trabajo + outbox en una transacción.
2. El despacho durable entrega un trabajo de indexación a Indexer Service. Inngest recibe referencias de trabajos e invoca las funciones registradas en el host del indexador; los archivos permanecen en almacenamiento de objetos.
3. Indexer Service obtiene una referencia autorizada a la versión fuente y prepara sus derivados en un área de trabajo sin publicar.
4. Tras validar el procesamiento completo, prepara un manifiesto que vincula fuentes, fragmentos, relaciones, versión del modelo de embeddings, dimensión y configuración de fragmentación. AI Service utiliza el modelo y la dimensión compatibles con ese índice para las consultas vectoriales.
5. Indexer Service informa progreso y finalización a Backend API mediante un contrato interno. Backend API verifica que la versión siga vigente y el trabajo no haya sido cancelado; actualiza el puntero del catálogo publicado y el estado del trabajo en una transacción. La vista de recuperación solo expone las generaciones completas señaladas por ese catálogo.

Los trabajos y callbacks usan IDs estables para tolerar entregas repetidas. Una ingesta fallida conserva la versión publicada anterior. Una publicación solo cambia a una versión completa; no mezcla fragmentos parciales. Las retiradas de fuentes se coordinan mediante trabajos del indexador y validación de versión/vigencia al publicar y recuperar. Backend API no modifica directamente las tablas del índice.

## Contratos y propiedad de datos

| Conexión | Contenido permitido y responsabilidad |
|---|---|
| Backend API → orquestador/cola | IDs de consulta o trabajo, versión del contrato y metadatos técnicos permitidos. |
| AI Service → Backend API | Solicitud de contexto autorizado, lectura/escritura de artefactos de consulta, progreso y resultado validado. El backend conserva el control de las transiciones y de la propiedad. |
| Indexer Service → Backend API | Obtener la fuente/versionado y reportar progreso, error seguro o referencia al manifiesto publicado. |
| Backend API → SUM Gateway | Crear/revocar conexión y borrar sus instantáneas; Backend API verifica al usuario y la pasarela aplica el alcance recibido. |
| AI Service → SUM Gateway | Solicitar/leer solo los campos permitidos de la instantánea vinculada a la consulta; verificar vencimiento y autorización. |
| AI Service → corpus publicado | Lectura de evidencia y relaciones; acceso restringido a versiones publicadas y aplicables. |

Preguntas, datos académicos y respuestas personalizadas viajan únicamente por contratos privados autenticados y se almacenan con la retención de la consulta. Los eventos y resultados de pasos durables contienen referencias. Los contratos internos no permiten SQL, URL de navegador ni acciones arbitrarias elegidas por el modelo.

El MVP puede compartir una instancia PostgreSQL, con esquemas y credenciales distintos: `application` para Backend API, `institutional` para Indexer Service y `academic` para SUM Gateway. AI Service tiene lectura del corpus publicado; accede al estado privado a través de los contratos. Compartir servidor de base de datos no permite compartir escrituras entre servicios. Los archivos fuente y los derivados también tienen permisos por servicio; una referencia de almacenamiento no implica acceso público.

## Estructura de servicios

```text
UI/                            # Interfaz; indexación simulada pendiente de conexión
services/
  backend-api/                 # REST/SSE, permisos, estado, catálogo, outbox
  ai-service/                  # Flujos, runner, retrieval, reglas, modelo
  indexer-service/             # Extracción, fragmentación, embeddings, publicación
  sum-gateway/                 # Adaptadores, normalización, instantáneas
packages/
  contracts/                   # Esquemas versionados de mensajes y resultados
infra/                         # Despliegue, orquestador, almacenamiento, permisos
```

Backend API e Indexer Service tienen sus propios puntos de entrada, dependencias, secretos, configuración y contenedores. Las carpetas de AI Service y SUM Gateway aún no están implementadas. El código compartido se limita a contratos y utilidades pequeñas; ningún servicio importa repositorios de base de datos, rutas HTTP o ejecutores de otro servicio. La recuperación y las reglas son módulos de AI Service; la extracción y fragmentación son módulos de Indexer Service.

Inngest, la cola durable y PostgreSQL son infraestructura. Se pueden alojar en la misma máquina junto a los servicios, con capacidad de despliegue y concurrencia independiente para consultas, indexación y navegador. Separar servicios no exige Kubernetes ni repositorios diferentes.

[Arquitectura general](../ARQUITECTURA.md) · [Consulta estudiantil detallada](arquitectura-detallada-estudiante.md)
