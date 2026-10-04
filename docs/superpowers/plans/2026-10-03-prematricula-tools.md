# Tools de pre-matrícula

Referencia: `sources/GobIA_TF_Informe_PreMatricula.md`, especialmente «RAG agéntico acotado» y §5.2.

1. Ampliar el plan semántico con simulación, cruces y carga de créditos; mantener input exclusivamente textual.
2. Añadir proyecciones mínimas de cursos/secciones seleccionados y preferencias. Tipos RAW intactos.
3. Implementar motor determinista y contratos de resultados: validación de prerrequisitos, créditos, conflictos y alternativas acotadas. Reglas solo revisadas/versionadas; ausencia → UNKNOWN.
4. Exponer catálogo de tools por intención, sin parámetros que permitan ampliar fuentes/cursos. Añadir recuperación RAG adicional acotada a publicaciones fijadas.
5. Integrar presupuesto, caché, auditoría de éxito/error y bloqueo de recomendaciones sin validación determinista.
6. Actualizar documentación. Ejecutar solo pruebas focalizadas de límites/minimización ya autorizadas y comprobaciones estáticas; no probar SUM real ni funcionalidad integral ni generar llamadas pagadas.

El flujo tiene un único orquestador por consulta y un paso auxiliar de planificación semántica. No hay agentes persistentes ni escrituras oficiales. El motor y las tools son independientes de la LLM.

## Entrega

Implementados los puntos 1–6. Catálogo: 10 tools académicas y 2 RAG; resultados tipados guardados y mostrados en UI. RAW conservados. Comprobación focalizada: 19 pruebas TS y 16 Python aprobadas; typecheck acotado aprobado. La funcionalidad integral del motor/SUM no se probó, según la restricción del usuario.
