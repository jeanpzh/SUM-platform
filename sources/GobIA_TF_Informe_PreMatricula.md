# Gobernanza de Inteligencia Artificial con Enfoque OCDE

**INFORME FINAL**  
Trabajo Final — Plantilla Oficial

| **Caso transversal** | Sistema híbrido de apoyo a la pre-matrícula con RAG agéntico acotado para estudiantes de la FISI |
|----------------------|--------------------------------------------------------------------------------------------------|
| **Integrantes**      | JeanPierre D'Angelo Motta Chumbe — Felipe Santiago Triveño Daza — Diego Andres Flores Tello      |
| **Fecha de entrega** | 24 de septiembre de 2026                                                                         |
| **Docente**          | Jorge Pantoja Collantes                                                                          |

# Resumen ejecutivo

El presente informe define la gobernanza de un prototipo académico de apoyo a la pre-matrícula de estudiantes de la FISI-UNMSM. El sistema simula alternativas, valida restricciones y explica los resultados; no ejecuta matrícula oficial ni modifica registros del Sistema Único de Matrícula (SUM).

La arquitectura está definida en tres componentes. Un motor determinístico evalúa reglas formalizables como prerrequisitos, límites de créditos, cursos aprobados y cruces de horario. Un RAG institucional recupera reglamentos, planes de estudio y documentación académica versionada. Un orquestador LLM con comportamiento de RAG agéntico acotado interpreta preferencias, selecciona herramientas autorizadas, coordina la recuperación y genera explicaciones sobre resultados previamente verificados.

El comportamiento agéntico se restringe a lectura, recuperación, simulación y orquestación dentro de una lista de herramientas autorizadas. No modifica reglas, no dispone de permisos de escritura y no ejecuta operaciones académicas oficiales. Los documentos institucionales compartidos se mantienen separados de los datos personales; el historial académico, cuando forme parte de un escenario autorizado, se consulta desde una fuente estructurada y no se incorpora al índice vectorial compartido.

El análisis de gobernanza considera riesgos de privacidad, transparencia, exactitud, equidad, autonomía, responsabilidad, seguridad, supervisión humana, inclusión y proporcionalidad. Los controles propuestos priorizan trazabilidad, mínimo privilegio, fuentes versionadas, validación determinística y separación entre recomendación y decisión oficial.

El alcance del trabajo es académico. La integración con SUM, el uso de datos institucionales no autorizados, la ejecución de matrícula y la participación formal de unidades administrativas no forman parte del prototipo. Los horizontes institucionales incluidos en la plantilla se presentan únicamente como escenarios de referencia para el análisis de gobernanza y no como compromisos, cronogramas ni actividades asumidas por el equipo.

# 1. Introducción y contexto del caso

## 1.1 Descripción del caso

La iniciativa consiste en un simulador inteligente de pre-matrícula orientado a estudiantes de la FISI-UNMSM. El estudiante selecciona asignaturas, secciones y preferencias de horario o distribución de carga académica. La arquitectura comprende: (1) un motor determinístico para reglas académicas formalizables; (2) un RAG institucional para recuperar documentación académica y normativa versionada; y (3) un orquestador LLM con RAG agéntico acotado para interpretar preferencias, decidir entre recuperación documental y herramientas autorizadas, y explicar resultados. El comportamiento agéntico se limita a lectura, recuperación y simulación; no incluye acciones transaccionales ni modificación de sistemas institucionales.

## 1.2 Procesos académicos involucrados

El caso comprende la consulta de oferta académica, revisión de asignaturas habilitadas, verificación de prerrequisitos, revisión del historial académico cuando el escenario lo autorice, detección de cruces de horario, validación de límites y reglas académicas, simulación de combinaciones de asignaturas y secciones, explicación de reglamentos y comparación de alternativas. La salida del prototipo es una simulación o recomendación y se mantiene separada del proceso formal de matrícula.

## 1.3 Estado actual de la iniciativa

El sistema se define como prototipo académico. Su alcance comprende el motor determinístico, el RAG documental, el orquestador LLM con RAG agéntico acotado, la interfaz de simulación y el registro de ejecución. El trabajo utiliza datos sintéticos, anonimizados o expresamente autorizados. No presupone acceso al SUM, integración con bases institucionales reales ni participación acordada de autoridades o unidades administrativas.

# 2. Inventario y alineamiento con principios OCDE

Tabla 2.1 — Matriz de alineamiento OCDE

| **Iniciativa IA**              | **Área responsable** | **Estado** | **Principio OCDE impactado**                   | **Nivel de impacto** | **Observaciones**                                                                                       |
|--------------------------------|----------------------|------------|------------------------------------------------|----------------------|---------------------------------------------------------------------------------------------------------|
| Interpretación de preferencias | Equipo del prototipo | Prototipo  | Transparencia y explicabilidad                 | Medio                | LLM/orquestador. Convierte lenguaje natural a restricciones estructuradas y explicita ambigüedades.     |
| Validación académica           | Equipo del prototipo | Prototipo  | Robustez, seguridad y responsabilidad          | Alto                 | Motor determinístico. Las reglas cubiertas por el prototipo no dependen del razonamiento libre del LLM. |
| Consulta normativa             | Equipo del prototipo | Prototipo  | Transparencia y explicabilidad                 | Alto                 | RAG institucional. La explicación identifica fuente, versión y vigencia del documento recuperado.       |
| Recomendación de alternativas  | Equipo del prototipo | Prototipo  | Crecimiento inclusivo, equidad y transparencia | Alto                 | Orquestador + motor determinístico. Los criterios utilizados quedan visibles y auditables.              |
| Explicación de resultados      | Equipo del prototipo | Prototipo  | Transparencia y explicabilidad                 | Alto                 | LLM + evidencia recuperada. El texto explica resultados verificados y no altera las reglas calculadas.  |
| Registro de ejecución          | Equipo del prototipo | Prototipo  | Responsabilidad y trazabilidad                 | Alto                 | Registra herramientas, fuentes, versiones, resultados y errores del flujo ejecutado.                    |

# 3. Evaluación de riesgos y criterios de aceptabilidad

Tabla 3.1 — Matriz de riesgos, aceptabilidad y controles mínimos

| **Dimensión ética**                    | **Riesgo concreto**                                                                                | **Dim. de impacto**     | **Nivel (A/A+C/NA)** | **Control mínimo exigible**                                                                                 | **Nivel de aceptabilidad** | **Controles mínimos asignados**                                                      | **Mecanismo de revisión**                       | **Justificación (\*)**                                                                              |
|----------------------------------------|----------------------------------------------------------------------------------------------------|-------------------------|----------------------|-------------------------------------------------------------------------------------------------------------|----------------------------|--------------------------------------------------------------------------------------|-------------------------------------------------|-----------------------------------------------------------------------------------------------------|
| Privacidad y datos personales          | Exposición de historial académico o identificadores a componentes no autorizados.                  | Legal / individual      | A+C                  | Minimización, autorización, cifrado y control de acceso.                                                    | Aceptable con controles    | Datos personales fuera del índice vectorial compartido; acceso de mínimo privilegio. | Auditoría de accesos y pruebas del flujo.       | El dato personal solo se incorpora al flujo cuando el escenario lo requiere y existe autorización.  |
| Transparencia y explicabilidad         | El estudiante no comprende la regla, fuente o criterio aplicado.                                   | Académico / individual  | A+C                  | Mostrar regla aplicada, fuente, versión y separación entre cálculo y texto LLM.                             | Aceptable con controles    | Procedencia obligatoria y plantilla de explicación.                                  | Muestreo de respuestas.                         | La recomendación debe poder comprenderse y reconstruirse.                                           |
| Exactitud y confiabilidad              | Reglas o documentos desactualizados producen resultados incorrectos.                               | Académico / técnico     | A+C                  | Versionado, vigencia, fecha de corte y validaciones determinísticas.                                        | Aceptable con controles    | Filtros de versión, freshness checks y casos de prueba.                              | Pruebas por versión y evaluación del retrieval. | La salida depende de que las fuentes y reglas utilizadas correspondan a la versión declarada.       |
| Equidad y no discriminación            | Los criterios de recomendación favorecen opciones sin una regla académica o preferencia explícita. | Individual / colectivo  | A+C                  | Criterios de ranking explícitos, configurables y auditables.                                                | Aceptable con controles    | Ranking trazable y evaluación por escenarios equivalentes.                           | Evaluación comparativa.                         | Los criterios ocultos pueden producir diferencias no justificadas entre escenarios equivalentes.    |
| Autonomía y agencia humana             | El usuario interpreta una simulación como matrícula o decisión oficial.                            | Individual / académico  | NA                   | Bloquear transacciones y diferenciar explícitamente simulación de matrícula oficial.                        | No aceptable               | Sin credenciales de escritura; interfaz y mensajes de alcance.                       | Pruebas de permisos y revisión de UI.           | Las operaciones oficiales se encuentran fuera del alcance del prototipo.                            |
| Responsabilidad y rendición de cuentas | No puede reconstruirse cómo se generó una recomendación.                                           | Institucional / técnico | A+C                  | Registrar entrada, reglas, herramientas, fuentes, versiones, salida y errores.                              | Aceptable con controles    | ID de ejecución y log estructurado.                                                  | Revisión de trazas.                             | Sin evidencia de ejecución no es posible investigar errores ni reproducir resultados.               |
| Seguridad y ciberseguridad             | Prompt injection, abuso de herramientas o acceso indebido a fuentes.                               | Técnico / institucional | A+C                  | Allowlist, validación de entradas, mínimo privilegio y secretos fuera del prompt.                           | Aceptable con controles    | Permisos por herramienta, rate limiting y mecanismo de detención.                    | Pruebas adversariales.                          | El orquestador solo debe operar dentro de herramientas y permisos definidos.                        |
| Supervisión humana                     | Casos no modelados o excepciones se presentan como resultados concluyentes.                        | Académico / individual  | A+C                  | Identificar excepciones y derivarlas a revisión humana; marcar límites de la simulación.                    | Aceptable con controles    | Reglas de escalamiento y registro de casos no cubiertos.                             | Revisión de casos excepcionales.                | El prototipo no sustituye interpretación académica para situaciones fuera de las reglas modeladas.  |
| Inclusión y accesibilidad              | La interfaz o explicación dificulta el uso a determinados estudiantes.                             | Individual / social     | A+C                  | Lenguaje claro, navegación accesible y alternativa no conversacional para resultados esenciales.            | Aceptable con controles    | Pruebas de accesibilidad y UX sobre el prototipo.                                    | Revisión de interfaz.                           | La explicación no debe convertirse en una barrera adicional para acceder a la información simulada. |
| Sostenibilidad y proporcionalidad      | Uso del LLM en validaciones que pueden resolverse de forma determinística.                         | Técnico / operativo     | A                    | Reservar LLM para interpretación, recuperación y explicación; reglas críticas en funciones determinísticas. | Aceptable                  | Enrutamiento por tipo de tarea y registro de llamadas.                               | Revisión de consumo en pruebas.                 | La separación de responsabilidades limita dependencias innecesarias del componente generativo.      |

<u>Leyenda</u>: (\*) Para cada riesgo calificado como 'No aceptable' o 'Aceptable con controles', justifica brevemente la calificación. ¿Por qué ese nivel? ¿Qué haría que cambie?

# 4. Gobernanza de proyectos y gestión de proveedores

## 4.1 Checklist de evaluación del proveedor / solución IA

| **Criterio de gobernanza** | **Requerimiento mínimo**                                                      | **Estado para el caso** | **Evidencia disponible**                                                              | **Brecha / Acción**                                                           |
|----------------------------|-------------------------------------------------------------------------------|-------------------------|---------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| Origen de la solución      | Identificar si la solución es interna, externa o mixta.                       | Parcial                 | Diseño mixto: componentes propios y una interfaz desacoplada para el LLM.             | Registrar proveedor, modelo y versión utilizados en las pruebas.              |
| Responsable institucional  | Definir área dueña, responsable funcional y técnico.                          | No aplica               | El presente trabajo corresponde a un prototipo académico.                             | La designación institucional no forma parte del alcance del prototipo.        |
| Documentación funcional    | Describir función, usuarios, alcance, límites y proceso impactado.            | Cumple                  | Alcance y límites documentados en el informe.                                         | Mantener coherencia entre informe e implementación.                           |
| Documentación técnica      | Documentar arquitectura, modelo, datos, integraciones, seguridad y versiones. | Parcial                 | Arquitectura y componentes definidos.                                                 | Completar la evidencia técnica de la implementación realizada.                |
| Desempeño / KPIs           | Definir métricas de exactitud, errores, latencia, costo y calidad.            | Parcial                 | Métricas definidas para reglas, retrieval, explicaciones, trazabilidad y rendimiento. | Reportar únicamente resultados observados en las pruebas ejecutadas.          |
| Datos utilizados           | Clasificar datos públicos, internos, confidenciales o restringidos.           | Parcial                 | Se distingue documentación compartida de datos personales.                            | Documentar la clasificación del dataset efectivamente utilizado.              |
| Trazabilidad               | Registrar fuente, sesión, prompt, salida, versión, herramientas y validación. | Parcial                 | Esquema de logging definido.                                                          | Implementar y comprobar la completitud del registro.                          |
| Auditabilidad              | Permitir revisión posterior de una ejecución.                                 | Parcial                 | ID de ejecución y evidencias previstas en el diseño.                                  | Conservar evidencia suficiente para reconstruir las pruebas.                  |
| Gestión de proveedor       | Documentar tratamiento de datos, confidencialidad, retención y portabilidad.  | Pendiente               | El proveedor/modelo no se asume como compromiso fijo del proyecto.                    | Documentar las condiciones del proveedor efectivamente usado en el prototipo. |
| Continuidad operativa      | Definir comportamiento ante fallo de modelo, API o integración.               | Parcial                 | Motor determinístico separado de la capa generativa.                                  | Probar el modo degradado dentro del alcance implementado.                     |

## 4.2 Gobernanza de agentes IA (si aplica al caso)

| **Grupo de criterio**     | **Criterio**                 | **Pregunta de evaluación**                                     | **Estado para el caso** | **Evidencia disponible**                                                                         | **Brecha / acción requerida**                                                               |
|---------------------------|------------------------------|----------------------------------------------------------------|-------------------------|--------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| Autonomía y alcance       | Nivel de autonomía           | ¿El agente recomienda, requiere aprobación o ejecuta acciones? | Parcial                 | Orquestador de lectura, recuperación, simulación y explicación; sin acciones oficiales.          | Verificar mediante pruebas que no existan rutas transaccionales.                            |
| Autonomía y alcance       | Herramientas conectadas      | ¿Qué sistemas, documentos o herramientas puede consultar?      | Parcial                 | Retriever institucional y funciones determinísticas cubiertas por el prototipo.                  | Mantener allowlist y registrar cada invocación.                                             |
| Autonomía y alcance       | Tipo de acciones             | ¿Lee información, escribe datos o ejecuta transacciones?       | Parcial                 | Lectura, recuperación documental, cálculo y simulación.                                          | Mantener bloqueadas operaciones de escritura institucional.                                 |
| Control y supervisión     | Política de permisos         | ¿Se aplica mínimo privilegio?                                  | Pendiente               | Permisos previstos por herramienta; acceso limitado a allowlist.                                 | Implementar y probar los permisos definidos para el prototipo.                              |
| Control y supervisión     | Logs auditables              | ¿Qué eventos quedan registrados?                               | Pendiente               | Esquema previsto: sesión, consulta, fuente, herramienta, modelo, salida y error.                 | Implementar el registro y comprobar su completitud.                                         |
| Control y supervisión     | Validación humana            | ¿Qué salidas requieren revisión humana?                        | Pendiente               | Casos no modelados se marcan como excepción; resultados ordinarios siguen siendo simulaciones.   | Documentar el tratamiento de excepciones en los flujos implementados.                       |
| Resiliencia y continuidad | Mecanismo de detención       | ¿Puede pausarse o desactivarse el componente agéntico?         | Pendiente               | La capa LLM puede desactivarse sin habilitar operaciones alternativas de escritura.              | Probar el modo degradado.                                                                   |
| Resiliencia y continuidad | Gestión de memoria           | ¿Qué información retiene y por cuánto tiempo?                  | Pendiente               | Estado temporal de sesión; sin memoria persistente del agente en el alcance definido.            | Aplicar retención de sesión coherente con el prototipo.                                     |
| Resiliencia y continuidad | Plan de contingencia         | ¿Qué ocurre si falla el proveedor, modelo, API o nube?         | Parcial                 | El núcleo determinístico permanece separado de la generación.                                    | Verificar el comportamiento del flujo sin la capa generativa.                               |
| Dependencias IA           | Modelo base                  | ¿De qué modelo depende la solución y cómo se versiona?         | Pendiente               | Interfaz de modelo desacoplada y configurable.                                                   | Registrar proveedor, modelo y versión de cada ejecución.                                    |
| Dependencias IA           | APIs y herramientas externas | ¿Qué servicios externos son necesarios?                        | Pendiente               | La implementación puede requerir API de modelo y servicios de despliegue según el entorno usado. | Inventariar solo las dependencias efectivamente empleadas.                                  |
| Dependencias IA           | Costos variables             | ¿El costo depende de tokens, consultas o infraestructura?      | Pendiente               | Se prevé registrar llamadas, tokens y duración.                                                  | Incorporar estas métricas al registro de pruebas.                                           |
| Dependencias IA           | Continuidad del proveedor    | ¿Existe dependencia que dificulte cambiar de proveedor?        | Parcial                 | La interfaz del modelo se mantiene desacoplada de la lógica de reglas y retrieval.               | Conservar configuración y contratos de interfaz suficientes para sustituir el modelo usado. |

**Estados sugeridos**

| **Estado** | **Uso**                                                       |
|------------|---------------------------------------------------------------|
| Cumple     | Hay evidencia suficiente y el criterio está cubierto.         |
| Parcial    | Hay avance, pero falta precisión, evidencia o responsable.    |
| Pendiente  | No hay evidencia suficiente o falta completar el criterio.    |
| No aplica  | El criterio no corresponde al caso y se justifica brevemente. |

## RAG agéntico acotado

El prototipo utiliza un patrón de RAG agéntico acotado. Un único orquestador interpreta la solicitud, consulta el RAG institucional cuando necesita evidencia documental e invoca herramientas determinísticas para las reglas académicas. Si la evidencia recuperada es insuficiente, puede realizar una recuperación adicional dentro de las fuentes autorizadas. El flujo finaliza con una explicación sustentada en resultados de herramientas y documentos recuperados.

El componente agéntico no mantiene agentes persistentes, no modifica reglas, no dispone de credenciales de escritura y no ejecuta matrícula ni otras acciones oficiales. Las invocaciones del orquestador se registran para conservar procedencia y trazabilidad. El núcleo determinístico permanece separado de la capa generativa.

> **Principio arquitectónico:** las reglas críticas permanecen determinísticas; el RAG aporta conocimiento institucional versionado; y el componente de RAG agéntico se limita a orquestar recuperación y herramientas autorizadas, sin permisos de escritura ni autonomía transaccional.

# 5. Lineamientos operativos para uso responsable de IA

## 5.1 Clasificación de usos de IA en el caso transversal

| **\#** | **Actor**            | **Caso de uso / acción**                                 | **Clasificación**        | **Condición o control requerido**                                                         | **Guardrail operativo asociado**                                                             | **Fundamento OCDE / norma peruana**    |
|--------|----------------------|----------------------------------------------------------|--------------------------|-------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------|----------------------------------------|
| 1      | Estudiante           | Solicitar simulación y explicación                       | Permitido                | Solo sobre el escenario de simulación disponible.                                         | Mostrar que el resultado no constituye matrícula oficial; incluir fuente cuando corresponda. | OCDE / NIST AI RMF                     |
| 2      | Agente IA            | Recomendar alternativas                                  | Restringido              | Solo candidatos previamente validados por el motor determinístico.                        | Registrar criterios y no recomendar cuando falten datos críticos.                            | OCDE / NIST AI RMF                     |
| 3      | Sistema              | Consultar historial académico                            | Restringido              | Solo en escenarios autorizados y con mínimo privilegio.                                   | Mantener datos personales fuera del índice vectorial compartido y registrar acceso.          | Ley 29733                              |
| 4      | Agente IA            | Modificar matrícula o registros del SUM                  | No permitido             | Sin excepciones dentro del prototipo.                                                     | No disponer de credenciales o herramientas de escritura.                                     | Robustez / seguridad / normativa UNMSM |
| 5      | Equipo del prototipo | Usar datos personales reales en pruebas                  | Restringido              | Solo con autorización aplicable y minimización; preferir datos sintéticos o anonimizados. | Control de acceso y tratamiento proporcional.                                                | Ley 29733 / ISO 42001                  |
| 6      | Proveedor externo    | Retener o reutilizar datos académicos para entrenamiento | No permitido por defecto | El prototipo no presupone autorización para uso secundario.                               | Revisar configuración, retención y condiciones del proveedor usado.                          | Ley 29733 / OCDE                       |

| **Actor**            | **Caso de uso / acción**                         | **Clasificación** | **Condición o control requerido**                                                                     | **Guardrail operativo asociado**                   | **Fundamento**                                |
|----------------------|--------------------------------------------------|-------------------|-------------------------------------------------------------------------------------------------------|----------------------------------------------------|-----------------------------------------------|
| Criterio transversal | Decisiones oficiales permanecen fuera del agente | Restringido       | Cualquier decisión oficial corresponde al procedimiento y a la instancia competente, no al prototipo. | HITL para excepciones + logs + fuentes versionadas | Ley 31814 / DS 115-2025-PCM / normativa UNMSM |

## 5.2 Lineamientos para IA generativa

| **\#** | **Uso de IA generativa** | **Riesgo asociado**                       | **Lineamiento operativo**                                                                                  | **Guardrail asociado**              | **Evidencia mínima requerida**                       |
|--------|--------------------------|-------------------------------------------|------------------------------------------------------------------------------------------------------------|-------------------------------------|------------------------------------------------------|
| 1      | Interpretar preferencias | Interpretación ambigua o prompt injection | Convertir preferencias a un esquema estructurado; instrucciones del usuario no cambian reglas ni permisos. | Entrada / validación de esquema     | Input, esquema resultante, versión del modelo y log. |
| 2      | Explicar resultados      | Alucinación o atribución normativa falsa  | Explicar únicamente resultados de herramientas y evidencia recuperada; no inventar reglas.                 | Salida / RAG + motor determinístico | Resultado estructurado, fuente/versión y log.        |
| 3      | Recomendar alternativas  | Recomendación inválida                    | Solo explicar candidatos previamente validados por el motor determinístico.                                | Tool calling                        | Resultados de herramientas y criterios utilizados.   |

| **Uso de IA generativa** | **Riesgo asociado**                   | **Lineamiento operativo**                                                                      | **Guardrail asociado**                      | **Evidencia mínima requerida**                             |
|--------------------------|---------------------------------------|------------------------------------------------------------------------------------------------|---------------------------------------------|------------------------------------------------------------|
| Consulta normativa       | Fuente desactualizada o no pertinente | Filtrar por vigencia y procedencia; si no existe evidencia suficiente, declarar la limitación. | Metadatos temporales y recuperación acotada | Documento recuperado, versión y trazabilidad de retrieval. |

# 6. Modelo institucional de gobernanza de IA

## 6.1 Estructura de roles y responsabilidades

La siguiente tabla se incluye para responder al componente institucional de la plantilla. Describe roles de referencia en un escenario hipotético de institucionalización; no representa designaciones, coordinaciones, solicitudes, aprobaciones ni compromisos actuales de la FISI, el SUM u otra unidad de la UNMSM.

| **Rol institucional de referencia** | **Responsabilidad en un escenario institucional**                      | **Instancia de referencia**             | **Gap identificado**                                      |
|-------------------------------------|------------------------------------------------------------------------|-----------------------------------------|-----------------------------------------------------------|
| Dueño funcional                     | Validar alcance y criterios académicos.                                | Instancia académica competente.         | No existe designación dentro del prototipo académico.     |
| Custodio de información académica   | Autorizar fuentes y condiciones de acceso.                             | Instancia custodio competente.          | No se presupone acceso institucional en el prototipo.     |
| Responsable técnico                 | Gestionar infraestructura, seguridad y operación.                      | Unidad técnica competente.              | No existe designación institucional en el alcance actual. |
| Autoridad del sistema oficial       | Definir cualquier mecanismo autorizado de consulta al sistema oficial. | Instancia responsable del sistema.      | El prototipo no se integra con SUM.                       |
| Gobernanza IA                       | Revisar riesgos y controles en un eventual uso institucional.          | Instancia que la universidad determine. | No forma parte del alcance académico.                     |

## 6.2 Integración normativa

| **Marco normativo / referencia** | **Elemento del modelo que aplica**                        | **Estado de alineamiento** | **Acción necesaria**                                                                                |
|----------------------------------|-----------------------------------------------------------|----------------------------|-----------------------------------------------------------------------------------------------------|
| OECD AI Principles               | Transparencia, robustez, derechos y accountability.       | Alineado conceptualmente   | Conservar evidencia de los controles aplicados al prototipo.                                        |
| Ley N.° 31814                    | Uso responsable de IA.                                    | Alineado conceptualmente   | Documentar el alcance y las medidas de gobernanza aplicadas al prototipo.                           |
| D.S. N.° 115-2025-PCM            | Gobernanza basada en riesgo, transparencia y supervisión. | Parcial                    | Identificar las obligaciones aplicables al uso concreto que se documente.                           |
| Ley N.° 29733                    | Tratamiento de datos personales.                          | Requiere controles         | Aplicar minimización, autorización y control de acceso cuando el dataset contenga datos personales. |
| NIST AI RMF 1.0                  | Gobernar, mapear, medir y gestionar riesgos.              | Alineado                   | Mantener registro de riesgos y evidencia de evaluación.                                             |
| NIST AI 600-1                    | Riesgos específicos de IA generativa.                     | Alineado                   | Incluir pruebas del componente generativo y de recuperación.                                        |
| ISO/IEC 42001:2023               | Políticas, responsabilidades, riesgos y evidencia.        | Referencial                | Aplicar controles proporcionales al alcance académico.                                              |
| Reglamento de matrícula UNMSM    | Reglas del dominio y separación del proceso oficial.      | Crítico                    | Mantener reglas y documentos utilizados como fuentes versionadas.                                   |
| PEI UNMSM 2026-2030              | Referencia institucional incluida por la plantilla.       | Referencial                | No se atribuye alineamiento operativo ni compromiso institucional dentro del prototipo.             |

## 6.3 Hoja de ruta — alcance académico y escenarios de referencia

## Alcance temporal del prototipo académico — 8 semanas

La tabla organiza el trabajo académico del prototipo dentro del período del curso. No constituye un cronograma institucional ni implica continuidad posterior. Cada actividad se limita a producir evidencia del componente implementado y de sus límites.

| **Semana** | **Actividades del prototipo**                                                       | **Evidencia esperada**                                     |
|------------|-------------------------------------------------------------------------------------|------------------------------------------------------------|
| 1          | Formalizar alcance, reglas cubiertas, dataset de prueba y arquitectura ya definida. | Especificación y casos de prueba.                          |
| 2          | Implementar las reglas académicas cubiertas por el prototipo.                       | Pruebas unitarias de las reglas implementadas.             |
| 3          | Integrar el motor determinístico en el servicio de simulación.                      | Servicio de simulación funcional para el alcance cubierto. |
| 4          | Implementar el RAG documental con fuentes, metadatos y versiones.                   | Índice documental y resultados de recuperación.            |
| 5          | Integrar el orquestador LLM con RAG agéntico acotado y tool calling.                | Flujo end-to-end instrumentado.                            |
| 6          | Integrar interfaz, estado de sesión, logging y controles del prototipo.             | Prototipo integrado.                                       |
| 7          | Ejecutar pruebas funcionales, de seguridad y rendimiento sobre lo implementado.     | Resultados de prueba registrados.                          |
| 8          | Corregir incidencias observadas y consolidar documentación y demostración.          | Versión académica y reporte de resultados.                 |

## Alcance técnico del prototipo académico

- Simulación de horarios, verificación de prerrequisitos, detección de cruces y aplicación de límites académicos modelados.

- Interpretación de preferencias, recuperación documental, explicaciones con procedencia y logging.

- Separación explícita entre recomendación y matrícula oficial.

- Fuera de alcance: modificación de SUM, automatización de matrícula, uso de datos personales no autorizados, decisiones académicas oficiales y autonomía transaccional.

## Horizontes de referencia exigidos por la plantilla — escenarios analíticos, no compromisos

| **Horizonte**             | **Período orientativo** | **Condiciones de referencia**                                                                                    | **Indicador de referencia**                          | **Criterio de referencia**                                   |
|---------------------------|-------------------------|------------------------------------------------------------------------------------------------------------------|------------------------------------------------------|--------------------------------------------------------------|
| H1 — Fundamentos          | 0–6 meses               | En un escenario institucional: fuentes, privacidad, seguridad y responsabilidades requerirían definición formal. | Existencia de controles y responsables documentados. | El análisis no presupone que este horizonte será iniciado.   |
| H2 — Piloto controlado    | 6–12 meses              | En un escenario autorizado: usuarios y datos acotados, observabilidad, soporte y contingencia.                   | Resultados y riesgos residuales documentados.        | El análisis no constituye propuesta ni compromiso de piloto. |
| H3 — Institucionalización | 12–24 meses             | En un escenario de adopción formal: integración con mínimo privilegio, auditoría y continuidad.                  | Operación con trazabilidad y responsables definidos. | El análisis no implica decisión de institucionalización.     |

## Separación entre RAG institucional y datos personales

El RAG contiene conocimiento institucional compartido: reglamentos, planes de estudio y documentación versionada. El historial académico y otros datos personales permanecen en una fuente estructurada separada, con control de acceso, y se consultan únicamente cuando son necesarios para la simulación de la sesión. Estos datos no se incorporan al índice vectorial compartido.

## Métricas del prototipo

Las métricas definen qué observar durante las pruebas del prototipo. El informe debe reportar únicamente valores obtenidos sobre el alcance implementado y el conjunto de evaluación utilizado, sin anticipar porcentajes o capacidades no medidos.

| **Área**        | **Métricas / criterio**                                                                            |
|-----------------|----------------------------------------------------------------------------------------------------|
| Reglas críticas | Exactitud sobre casos de prueba, cobertura de reglas y errores observados.                         |
| Retrieval       | Recall@k, Precision@k, procedencia y vigencia de las fuentes recuperadas.                          |
| Explicaciones   | Consistencia con el resultado determinístico, fidelidad a fuentes y ausencia de reglas inventadas. |
| Trazabilidad    | Proporción de ejecuciones con el registro definido para el prototipo.                              |
| Rendimiento     | p50/p95, tasa de errores, throughput, duración de retrieval y costo por consulta.                  |

# 7. Conclusiones y próximos pasos

## Conclusiones

- La arquitectura separa responsabilidades: el motor determinístico valida las reglas académicas, el RAG aporta evidencia documental versionada y el orquestador RAG agéntico coordina recuperación, herramientas y explicación.
- El comportamiento agéntico está acotado a lectura, recuperación y simulación. No modifica reglas, no dispone de escritura sobre SUM y no produce decisiones académicas oficiales.
- El alcance es académico y acotado: no incluye modificación del SUM, decisiones oficiales, datos personales no autorizados ni participación institucional comprometida.

## Próximos pasos inmediatos (60 días) — plan de trabajo del prototipo académico

| **Acción**                                                                        | **Responsable**  | **Plazo**   | **Resultado esperado**                                                          |
|-----------------------------------------------------------------------------------|------------------|-------------|---------------------------------------------------------------------------------|
| Formalizar alcance y reglas cubiertas por el prototipo                            | Equipo académico | Semanas 1–2 | Especificación, casos de prueba y reglas priorizadas.                           |
| Implementar motor determinístico                                                  | Equipo académico | Semanas 2–3 | Servicio de simulación para las reglas cubiertas.                               |
| Implementar RAG documental e integrar el orquestador LLM con RAG agéntico acotado | Equipo académico | Semanas 4–5 | Recuperación con procedencia y flujo instrumentado de retrieval + tool calling. |
| Integrar interfaz, sesión, logging y controles                                    | Equipo académico | Semana 6    | Prototipo integrado.                                                            |
| Ejecutar pruebas y consolidar documentación y demostración                        | Equipo académico | Semanas 7–8 | Resultados registrados, versión académica y reporte de limitaciones.            |

# Bibliografía

## Fuentes adicionales del caso y del enfoque técnico

- Congreso de la República del Perú. (2011). Ley N.° 29733, Ley de Protección de Datos Personales.
- National Institute of Standards and Technology. (2024). *Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile (NIST AI 600-1).*
- Universidad Nacional Mayor de San Marcos. (2026). *Reglamento General de Matrícula para Pregrado.*
- Universidad Nacional Mayor de San Marcos, Sistema Único de Matrícula. (2026). *Información y cronograma del proceso de matrícula.*
- Universidad Nacional Mayor de San Marcos. (2025). *Plan Estratégico Institucional 2026-2030.*

**Nota metodológica:** la arquitectura de RAG agéntico acotado corresponde al alcance académico del prototipo. Los roles y horizontes institucionales se incluyen únicamente como referencias analíticas exigidas por la plantilla; no suponen acceso al SUM, aprobación previa, continuidad del proyecto ni compromiso de participación de unidades institucionales.

## Referencias

- OECD. (2024). *OECD AI Principles.* https://www.oecd.org/en/topics/ai-principles.html
- OECD. (2025). *Governing with Artificial Intelligence.* https://www.oecd.org/en/publications/governing-with-artificial-intelligence_795de142-en.html
- NIST. (2023). *AI Risk Management Framework (AI RMF 1.0).* https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf
- NIST. (2024). *Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile (NIST AI 600-1).* https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf
- ISO. (2023). *ISO/IEC 42001:2023 Artificial intelligence management system.* https://www.iso.org/standard/42001
- Congreso del Perú. (2023). *Ley N.° 31814 — Ley de IA.* https://www.gob.pe/institucion/congreso-de-la-republica/normas-legales/4565760-31814
- PCM. (2025). *DS N.° 115-2025-PCM — Reglamento Ley 31814.* https://www.gob.pe/institucion/pcm/normas-legales/7133522-115-2025-pcm
- UNESCO. (2021). *Recommendation on the Ethics of AI.* https://www.unesco.org/en/legal-affairs/recommendation-ethics-artificial-intelligence
