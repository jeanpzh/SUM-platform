# Asistente estudiantil: plan de implementación

**Objetivo:** UI estudiantil según DESIGN.md y orquestación contextual con LangChain, RAG, herramientas acotadas, cuotas por sesión y auditoría durable.

**Arquitectura:** reutilizar runs/outbox/Inngest y corpus publicado. Separar identidad estudiantil, selección de modelo del servidor y contratos de contexto. Vercel AI SDK transporta progreso y resultados validados; el estado durable sigue en Backend API.

**Restricciones:** no crear ni ejecutar pruebas funcionales; SUMAdapter e interfaces SUM están pendientes. No inferir umbrales académicos. SQLAlchemy Core para consultas Python. No exponer credenciales ni razonamiento interno. Aplicar DESIGN.md.

- [x] Contratos de consulta, planificación, contexto minimizado, comprobaciones y componentes UI permitidos.
- [x] API estudiantil autenticada, idempotencia, historial paginado, cancelación y stream AI SDK reconectable por run.
- [x] Orquestador con clasificación estructurada, contexto por herramienta, RAG y reglas registradas; presupuestos compartidos y LangSmith opcional con entradas/salidas ocultas.
- [x] UI /assistant, /assistant/$runId, /connections/sum, AI SDK useChat, fuentes, progreso e historial.
- [x] Configuración, documentación de integración pendiente y comprobaciones estáticas/compilación sin pruebas funcionales.

Resultado: UI compilada; lint y sintaxis Python revisados; capturas de escritorio/móvil disponibles en `artifacts/student-ui`. TypeScript global conserva seis errores en módulos demo ajenos a este flujo. No se ejecutaron pruebas funcionales ni llamadas a modelos. Por instrucción posterior del usuario, no realizar más validaciones pesadas. SUMAdapter, gestión de conexiones, reglas institucionales revisadas y servidor MCP quedan como integraciones explícitamente pendientes.

Revisión: identidad por sesión, aislamiento de propietario, reintentos y consumo, contexto vencido, corpus sin evidencia, desconexión sin cancelación, citas permitidas y componentes sin ejecución arbitraria.
