# Diccionario sencillo de los 39 documentos adquiridos

**Actualizado:** 29 de septiembre de 2026, hora de Lima.  
**Para quién:** estudiantes, personal de FISI y cualquier persona que necesite entender qué contiene cada archivo.  
**Qué es esta lista:** una guía de lectura de los 39 PDF descargados. No significa que todos estén vigentes, que todos se deban indexar ni que ya tengamos todos los planes de estudio.

Cada entrada tiene enlaces al **PDF original** y al **texto extraído con páginas**. En la ficha también se indica qué pregunta ayuda a contestar y qué no permite concluir. La fecha, dirección de descarga, tamaño y SHA-256 están en [`sources/source_manifest.csv`](../sources/source_manifest.csv); el estado de incorporación y la aplicabilidad están en [`data/document_inventory_audited.csv`](../data/document_inventory_audited.csv).

## En pocas palabras: ¿qué falta buscar?

Lo más importante no son más guías generales, sino los **planes y anexos que contienen los cursos reales**:

1. El anexo de **96 folios** del RD 000163-2023-D-FISI, que debe contener el Programa Curricular 2023 de Ingeniería de Sistemas. El PDF público descargado trae solo la resolución de una página.
2. El anexo de **cinco folios** con equivalencias entre los planes 2014 y 2018 aprobado por RD 000609-2022-D-FISI. El PDF público también trae solo la resolución de una página.
3. El texto completo de **RR 00698-R-20** y su tabla de equivalencias de los planes 2009 y 2014, mencionados en el Acta del Consejo de Facultad de 22 de septiembre de 2020.
4. **RD 000510-D-FISI-19** y **RR 00721-R-20**, que aparecen citados como la cadena que dejó sin vigencia el Plan 2009; sus PDF y cláusulas operativas no se localizaron.
5. La decisión posterior que adoptó —si la hubo— la migración y tabla 2009→2018 propuestas en julio de 2021. El acta del 27 de julio dice que esos puntos quedaron **pendientes de aprobación**.
6. Los planes aprobados, resoluciones, modificaciones, prerrequisitos, créditos, cursos discontinuados y reglas por cohorte para las cuatro escuelas de pregrado: Ingeniería de Sistemas, Ingeniería de Software, Ciencia de la Computación e Inteligencia Artificial.
7. La correspondencia oficial entre **año de ingreso, plan asignado y reglas de retorno**. No se debe deducir el plan de una persona por el año escrito en el nombre del plan.
8. Requisitos FISI de bachiller y título actualizados por cohorte; además, OCR y revisión humana del Estatuto escaneado y de los anexos escaneados de la directiva de tesis.

La cobertura detallada está en [`fisi_plan_coverage_matrix.md`](fisi_plan_coverage_matrix.md). Las direcciones exactas de los documentos faltantes aparecen en [`source_collection_report.md`](source_collection_report.md).

## Cómo entender las palabras que aparecen en estos documentos

| Palabra | En sencillo | Importante para no confundir |
|---|---|---|
| **Plan de estudios / currículo** | La ruta oficial de una carrera: cursos, ciclos, créditos y, normalmente, requisitos previos. | Un horario o listado de cursos programados no es el plan completo ni prueba quién tiene asignado ese plan. |
| **Prerrequisito** | Curso u otra condición que se debe cumplir antes de matricularse en otro curso. | Los archivos de programación 2026-0 no contienen la lista completa de prerrequisitos. |
| **Resolución** | Documento que deja constancia de una decisión de una autoridad. | El título del archivo no basta: hay que leer qué aprueba, desde cuándo y a quién se aplica. |
| **Anexo** | Las páginas adjuntas a una resolución; pueden contener el plan o la tabla que la resolución aprueba. | Si el PDF descargado trae solo la resolución y no el anexo citado, falta la parte sustantiva. |
| **Convalidación** | Reconocer cursos aprobados antes para que cuenten dentro del plan de destino, normalmente tras una evaluación. | La norma de convalidación universitaria y una tabla de equivalencia entre dos planes son cosas distintas. |
| **Equivalencia** | Relación aprobada entre un curso de un plan y un curso de otro plan. | Una tabla que relaciona dos cursos no vuelve equivalentes todos los cursos de esos planes. |
| **Reactualización** | Procedimiento para recuperar la condición de estudiante después de dejar de matricularse, si todavía corresponde. | El reglamento universitario 2026 dice que se hace en el plan vigente; si hay abandono o separación, pueden existir impedimentos. |
| **Reserva de matrícula** | Autorización formal para postergar la matrícula. | La Directiva SUM antigua habla de dos años; el reglamento 2026 habla de tres. No se deben mezclar como si fueran una sola regla vigente. |
| **PDF escaneado / OCR** | PDF formado por imágenes de páginas, sin texto que la computadora pueda leer con fiabilidad. | Hace falta OCR y luego revisar el texto contra la imagen. Un extracto vacío no significa que la página esté vacía. |
| **Cohorte / plan asignado** | Grupo de estudiantes al que una regla o plan se aplica expresamente; el plan que oficialmente figura para una persona. | El año del plan no demuestra el año de ingreso ni el plan asignado a una persona. |

## Los 39 archivos, uno por uno

### Calendario, planes y equivalencias

#### DOC-008 — Cronograma académico de pregrado 2026 (anexo)
- [PDF original](../sources/originals/Cronograma-Pregrado-2026-anexo.pdf) · [texto extraído](../sources/extracted/Cronograma-Pregrado-2026-anexo.txt)
- **Qué es:** calendario anual de actividades universitarias, con fechas para matrícula, rectificación y otros procesos.
- **Sirve para:** preguntar qué fecha corresponde a un trámite durante 2026.
- **No sirve para:** establecer el plan asignado a un estudiante, sus cursos o los requisitos de graduación. Es temporal; las facultades pueden fijar plazos de presentación anteriores a la fecha administrativa del SUM.

#### DOC-022 — Directiva SUM 001-2021: registro de planes de estudio
- [PDF original](../sources/originals/Directiva-SUM-001-2021-registro-plan.pdf) · [texto extraído](../sources/extracted/Directiva-SUM-001-2021-registro-plan.txt)
- **Qué es:** instrucciones para registrar un plan de estudios.
- **Sirve para:** saber qué debe contener o acompañar un plan registrado; menciona prerrequisitos, equivalencias y total de créditos.
- **No sirve para:** conocer la malla de Sistemas, Software, Computación o Inteligencia Artificial. Es una pauta de registro, no un plan de carrera.

#### DOC-121 — RD 000163-2023-D-FISI: Programa Curricular 2023 de Ingeniería de Sistemas
- [PDF original](../sources/originals/RD-000163-2023-D-FISI-programa-curricular-2023.pdf) · [texto extraído](../sources/extracted/RD-000163-2023-D-FISI-programa-curricular-2023.txt)
- **Qué es:** resolución decanal que aprueba el Programa Curricular 2023 de Ingeniería de Sistemas y lo eleva para ratificación.
- **Sirve para:** comprobar que existe una aprobación decanal y que la resolución cita un anexo de 96 folios.
- **No sirve para:** ver cursos, créditos, prerrequisitos o requisitos de egreso: el archivo descargado tiene solo la resolución de una página y **no incluye las 96 páginas del programa**. No indexar como si contuviera la malla.

#### DOC-122 — RD 000609-2022-D-FISI: equivalencias Plan 2014 a Plan 2018
- [PDF original](../sources/originals/RD-000609-2022-D-FISI-equivalencias-plan-2014-2018.pdf) · [texto extraído](../sources/extracted/RD-000609-2022-D-FISI-equivalencias-plan-2014-2018.txt)
- **Qué es:** resolución que aprueba una tabla para relacionar cursos de Sistemas en los planes 2014 y 2018.
- **Sirve para:** verificar la existencia y el sentido de esa tabla; cita RR 02137-R-15 y los RR 07026-R-17, 06615-R-18 y 01529-R-19.
- **No sirve para:** decir qué curso específico convalida con cuál. La resolución dice que la tabla ocupa cinco folios, pero el archivo obtenido solo contiene la página de la resolución.

#### DOC-120 — RR 000046-2026-R: corrección de equivalencias Plan 2018–Plan 2023
- [PDF original](../sources/originals/RR-000046-2026-R-UNMSM.pdf) · [texto extraído, páginas 1–2](../sources/extracted/RR-000046-2026-R-UNMSM.txt)
- **Qué es:** resolución rectoral que ratifica modificaciones de la tabla de equivalencias de Ingeniería de Sistemas.
- **Sirve para:** contestar solo sobre las dos filas corregidas en la página 2: Programación y Computación, y Emprendimiento e Innovación; incluye código, ciclo, créditos y tipo.
- **No sirve para:** declarar que todos los cursos de los planes 2018 y 2023 son equivalentes. Tampoco indica qué plan tiene asignado cada estudiante. Revisar las celdas contra la imagen antes de indexarlas.

#### DOC-123 — Cursos programados: Ingeniería de Sistemas, Plan 2018, periodo 2026-0
- [PDF original](../sources/originals/Programacion-asignaturas-Sistemas-Plan-2018.pdf) · [texto extraído](../sources/extracted/Programacion-asignaturas-Sistemas-Plan-2018.txt)
- **Qué es:** listado de cursos y secciones programadas para un periodo específico.
- **Sirve para:** averiguar qué cursos aparecen programados en 2026-0 bajo el Plan 2018.
- **No sirve para:** afirmar la malla completa, créditos, prerrequisitos, sustituciones o que una persona está asignada al Plan 2018. Incluye identificadores de personal; no incorporarlo en bruto a un corpus general.

#### DOC-124 — Cursos programados: Ingeniería de Software, Plan 2018, periodo 2026-0
- [PDF original](../sources/originals/Programacion-asignaturas-Software-Plan-2018.pdf) · [texto extraído](../sources/extracted/Programacion-asignaturas-Software-Plan-2018.txt)
- **Qué es:** listado temporal de cursos/secciones para Ingeniería de Software.
- **Sirve para:** consultar las ofertas que aparecen en el reporte 2026-0.
- **No sirve para:** probar la aprobación del plan, sus prerrequisitos o la cohorte a la que se asigna. Contiene identificadores de personal; excluir el archivo en bruto del corpus común.

#### DOC-125 — Cursos programados: Ciencia de la Computación, Plan 2023, periodo 2026-0
- [PDF original](../sources/originals/Programacion-asignaturas-Ciencia-Computacion-Plan-2023.pdf) · [texto extraído](../sources/extracted/Programacion-asignaturas-Ciencia-Computacion-Plan-2023.txt)
- **Qué es:** reporte de cursos/secciones programados que identifica el Plan 2023 de Ciencia de la Computación.
- **Sirve para:** verificar qué aparece en ese reporte de 2026-0.
- **No sirve para:** sustituir el plan aprobado, determinar créditos o prerrequisitos completos ni asignar plan por año de ingreso.

#### Fuente web asociada — DOC-118, aviso FISI sobre el Plan 2009 (no es uno de los 39 PDF)
- [Página FISI](https://sistemas.unmsm.edu.pe/site/noticias/35-importante/188-comunicado-sobre-la-vigencia-del-plan-de-estudios-2009-de-la-escuela-profesional-de-ingenieria-de-sistemas)
- **Qué es:** aviso de la Escuela de Ingeniería de Sistemas. Dice que el Plan 2009 regía hasta 2021-II y propone rutas según ciclo: I–VI a 2018, VII–VIII a 2014, IX–X podían acabar en 2009.
- **Sirve para:** conocer qué informó FISI a sus estudiantes sobre el fin del Plan 2009.
- **No sirve para:** determinar año de ingreso, plan asignado, obligatoriedad de migración ni equivalencia de cualquier curso. La ruta ciclo a ciclo no aparece demostrada por el acta del Consejo obtenida.

También se usa como fuente web asociada **DOC-119**, [registro Gob.pe de RR 000046-2026-R](https://www.gob.pe/institucion/unmsm/normas-legales/7601870-000046-2026-r-unmsm). No es uno de los 39 PDF locales; el PDF adjunto es DOC-120.

#### DOC-128 — Acta Consejo de Facultad, sesión 13, 20 de julio de 2021
- [PDF original](../sources/originals/FISI-Acta-Consejo-Facultad-2021-07-20-sesion-13.pdf) · [extracto redacted](../sources/extracted/FISI-Acta24-migration-redacted-extract.txt)
- **Qué es:** acta donde la directora solicita que el Consejo considere una tabla de equivalencias 2009→2018 en una sesión extraordinaria.
- **Sirve para:** demostrar que se pidió consideración/aprobación de esa tabla.
- **No sirve para:** decir que la tabla quedó aprobada. Es minuta con información personal; usar solo un extracto depurado.

#### DOC-129 — Acta Consejo de Facultad, sesión 14, 27 de julio de 2021
- [PDF original](../sources/originals/FISI-Acta-Consejo-Facultad-2021-07-27-sesion-14.pdf) · [extracto redacted](../sources/extracted/FISI-Acta24-migration-redacted-extract.txt)
- **Qué es:** acta que describe la propuesta 2009→2018/2014 y la tabla 2009→2018.
- **Sirve para:** entender los ciclos que se propusieron mover y los criterios discutidos.
- **No sirve para:** presentar esa tabla/migración como aprobada: el acta dice que ambos puntos quedaron pendientes de aprobación en esa reunión.

#### DOC-130 — Acta Consejo de Facultad Virtual 17, sesión 12, 22 de septiembre de 2020
- [PDF original](../sources/originals/FISI-Acta-Consejo-Facultad-2020-09-22-virtual17-ordinaria12.pdf) · [extracto depurado](../sources/extracted/FISI-Acta17-plan2009-redacted-extract.txt)
- **Qué es:** acta del Consejo FISI que registra las propuestas y votaciones sobre el Plan 2009.
- **Sirve para:** comprobar que se rechazó el cierre inmediato en 2020 y se aceptó (8 votos a favor, 1 abstención) dejar sin efecto el plan desde 2022-I; esto sitúa el último semestre en 2021-II. También cita RR 00698-R-20 como aprobación de una tabla 2009→2014.
- **No sirve para:** probar los grupos de migración del comunicado, porque no aparecen en esa votación. El RR 00698 y su tabla todavía faltan. El acta completa incluye nombres: en el índice de búsqueda debe usarse solo el extracto depurado.

### Matrícula y trámites

#### DOC-005 — RR 002642-2026-R
- [PDF original](../sources/originals/RR-002642-2026-R.pdf) · [texto extraído](../sources/extracted/RR-002642-2026-R.txt)
- **Qué es:** resolución rectoral que aprueba el Reglamento General de Matrícula para Pregrado 2026.
- **Sirve para:** saber qué reglamento aprobó la Universidad y desde cuándo se aplica; es el documento de aprobación, no el anexo detallado.
- **No sirve para:** identificar por sí solo el plan curricular o la cohorte de una persona.

#### DOC-002 — Reglamento General de Matrícula para Pregrado 2026 (anexo SUM)
- [PDF original](../sources/originals/Reglamento-Matricula-Pregrado-2026.pdf) · [texto extraído](../sources/extracted/Reglamento-Matricula-Pregrado-2026.txt)
- **Qué es:** las 18 páginas de reglas de matrícula de pregrado aprobadas por DOC-005.
- **Sirve para:** procesos de matrícula y reglas generales, incluida la ubicación de estudiantes reactualizados en el plan vigente (Art. 31) y la diferencia entre plan vigente y plan en extinción.
- **No sirve para:** listar los cursos o decidir un caso individual sin saber escuela, plan asignado, interrupción y si existe abandono/separación.

#### DOC-079 — Copia VRAP combinada de RR 002642-2026 más reglamento
- [PDF original](../sources/originals/Reglamento-Matricula-Pregrado-VRAP-2026.pdf) · [texto extraído](../sources/extracted/Reglamento-Matricula-Pregrado-VRAP-2026.txt)
- **Qué es:** un PDF con dos páginas de resolución seguidas de las mismas 18 páginas del reglamento.
- **Sirve para:** fuente alternativa del RR (páginas 1–2) y del anexo (páginas 3–20). El texto extraído de esos segmentos coincide exactamente con DOC-005 y DOC-002.
- **No sirve para:** crear copias duplicadas de los mismos capítulos en la indexación. Mantener sus dos roles y enlazar la URL alternativa.

#### DOC-029 — Directiva SUM 005-2012, reactualización
- [PDF original](../sources/originals/Directiva-SUM-005-reactualizacion.pdf) · [texto extraído](../sources/extracted/Directiva-SUM-005-reactualizacion.txt)
- **Qué es:** procedimiento antiguo para enviar y tramitar solicitudes de reactualización.
- **Sirve para:** entender el flujo administrativo y los documentos que pedía esa directiva.
- **No sirve para:** reemplazar el Reglamento de Matrícula 2026 ni asegurar que siga vigente cada requisito de 2012.

#### DOC-030 — Directiva SUM 006-2012, rectificación
- [PDF original](../sources/originals/Directiva-SUM-006-rectificacion.pdf) · [texto extraído](../sources/extracted/Directiva-SUM-006-rectificacion.txt)
- **Qué es:** procedimiento antiguo de rectificación de matrícula.
- **Sirve para:** localizar antecedentes de trámite.
- **No sirve para:** fijar fechas o requisitos actuales sin compararlo con el reglamento y cronograma aplicables.

#### DOC-035 — Directiva SUM 009-2012, reserva
- [PDF original](../sources/originals/Directiva-SUM-009-reserva.pdf) · [texto extraído](../sources/extracted/Directiva-SUM-009-reserva.txt)
- **Qué es:** pautas antiguas de reserva; menciona máximo de dos años académicos.
- **Sirve para:** entender el procedimiento histórico.
- **No sirve para:** reemplazar el reglamento de matrícula 2026, que establece el plazo vigente de reserva de tres años; la incompatibilidad se debe resolver por la norma actual.

#### DOC-036 — Directiva SUM 010-2012, matrícula extemporánea
- [PDF original](../sources/originals/Directiva-SUM-010-extemporanea.pdf) · [texto extraído](../sources/extracted/Directiva-SUM-010-extemporanea.txt)
- **Qué es:** procedimiento de matrícula fuera del periodo ordinario.
- **Sirve para:** localizar el antecedente de trámite.
- **No sirve para:** determinar fechas actuales; usar el cronograma del año y la regla de aprobación que corresponda.

#### DOC-033 — Directiva SUM 008-2012, equivalencia de asignaturas
- [PDF original](../sources/originals/Directiva-SUM-008-equivalencia.pdf) · [texto extraído](../sources/extracted/Directiva-SUM-008-equivalencia.txt)
- **Qué es:** flujo administrativo antiguo para registrar equivalencias cuando cambia un plan.
- **Sirve para:** entender que se debe aprobar y documentar una tabla de equivalencias.
- **No sirve para:** conocer la tabla FISI ni afirmar que el procedimiento del 2012 siga vigente sin revisión.

#### DOC-031 — Directiva SUM 007-2012, convalidación
- [PDF original](../sources/originals/Directiva-SUM-007-convalidacion.pdf) · [texto extraído](../sources/extracted/Directiva-SUM-007-convalidacion.txt)
- **Qué es:** flujo administrativo antiguo para pedir convalidación.
- **Sirve para:** identificar los pasos y el tipo de información de la solicitud.
- **No sirve para:** sustituir el reglamento universitario de convalidación de 2021.

#### DOC-086 — RR 005516-2021, Reglamento de Convalidación
- [PDF original](../sources/originals/Reglamento-Convalidacion-2021.pdf) · [texto extraído](../sources/extracted/Reglamento-Convalidacion-2021.txt)
- **Qué es:** reglamento universitario para convalidar cursos de pregrado.
- **Sirve para:** conocer los criterios que el documento establece, como coincidencia mínima de contenido de sílabo y créditos respecto al curso de destino. Distingue el reingreso por concurso de la reactualización.
- **No sirve para:** afirmar que un curso FISI concreto está convalidado sin el plan de destino y la resolución/tabla específica. Revisar cambios posteriores antes de tratarlo como norma actual.

#### DOC-037 — Directiva SUM 011-2012, registro de planes
- [PDF original](../sources/originals/Directiva-SUM-011-registro-plan.pdf) · [texto extraído](../sources/extracted/Directiva-SUM-011-registro-plan.txt)
- **Qué es:** procedimiento SUM para registrar planes.
- **Sirve para:** entender la ruta administrativa de registro.
- **No sirve para:** responder cursos, créditos o asignación de plan de una escuela.

#### DOC-052 — RR 04005-R-16, regularización de matrícula
- [PDF original](../sources/originals/RR-04005-R-16-regularizacion-matricula.pdf) · [texto extraído](../sources/extracted/RR-04005-R-16-regularizacion-matricula.txt)
- **Qué es:** medida excepcional de 2016 para una población concreta de estudiantes ingresados antes de la Ley 30220.
- **Sirve para:** entender la aplicación de repitencias y matrícula en ese caso histórico; el documento cita el Estatuto y la Ley.
- **No sirve para:** aplicar automáticamente esa excepción hoy. Para casos actuales hay que leer Ley, Estatuto y Reglamento de Matrícula vigentes.

#### DOC-053 — RR 0438-R-09, modificación sobre reactualización
- [PDF original](../sources/originals/RR-0438-R-09-reactualizacion.pdf) · [extracción OCR pendiente](../sources/extracted/RR-0438-R-09-reactualizacion.txt)
- **Qué es:** resolución antigua escaneada relacionada con reactualización.
- **Sirve para:** antecedente histórico cuando se investiga una matrícula de ese periodo.
- **No sirve para:** citar reglas actuales sin OCR, leer el texto completo y compararlo con las normas posteriores.

#### DOC-018 — RR 013045-2021-R, registro de planes
- [PDF original](../sources/originals/RR-013045-2021-R-pautas-registro-plan.pdf) · [texto extraído](../sources/extracted/RR-013045-2021-R-pautas-registro-plan.txt)
- **Qué es:** resolución titulada como pautas de registro de plan de estudios.
- **Sirve para:** identificar el marco universitario de registro.
- **No sirve para:** aportar una malla FISI concreta. El archivo de una página requiere comprobar visualmente alcance y relación exacta con la directiva del SUM.

#### DOC-105 — Flujograma FISI de reactualización/reserva (2023-I)
- [PDF original](../sources/originals/FISI-flujograma-reactualizacion-reserva.pdf) · [texto extraído](../sources/extracted/FISI-flujograma-reactualizacion-reserva.txt)
- **Qué es:** hoja de proceso FISI para el semestre 2023-I.
- **Sirve para:** entender qué decía FISI sobre matrícula en ese semestre.
- **No sirve para:** asumir fechas o pasos actuales.

### Derechos, evaluaciones y títulos

#### DOC-081 — Guía del Estudiante de Pregrado 2026
- [PDF original](../sources/originals/Guia-Estudiante-Pregrado-2026.pdf) · [texto extraído](../sources/extracted/Guia-Estudiante-Pregrado-2026.txt)
- **Qué es:** guía general para estudiantes, con definiciones, reglas de matrícula resumidas y cronograma 2026.
- **Sirve para:** orientación general y localizar normas universitarias.
- **No sirve para:** reemplazar la resolución o el reglamento completo, ni dar el plan/prerrequisito de una escuela.

#### DOC-072 — Ley Universitaria 30220 (copia SUM)
- [PDF original](../sources/originals/Ley-Universitaria-30220-SUM.pdf) · [texto extraído](../sources/extracted/Ley-Universitaria-30220-SUM.txt)
- **Qué es:** copia de la ley universitaria alojada por el SUM.
- **Sirve para:** entender el marco general de universidad, matrícula, grados y títulos.
- **No sirve para:** asumir que esta copia incorpora todas las modificaciones posteriores; verificar la versión legal aplicable a la fecha/cohorte.

#### DOC-070 — Estatuto Universitario
- [PDF original](../sources/originals/Reglamento-Estatuto-UNMSM.pdf) · [marcadores de páginas sin OCR](../sources/extracted/Reglamento-Estatuto-UNMSM.txt)
- **Qué es:** norma institucional que complementa la Ley y reglamentos.
- **Sirve para:** responder cuestiones de gobierno, permanencia y matrícula cuando se haya leído el artículo aplicable.
- **No sirve todavía para citar Art. 189 desde el extracto: las 84 páginas están escaneadas y requieren OCR y verificación visual.

#### DOC-054 — RR 04626-R-06, régimen de estudios y evaluación
- [PDF original](../sources/originals/RR-04626-R-06-regimen-estudios-evaluacion.pdf) · [extracción OCR pendiente](../sources/extracted/RR-04626-R-06-regimen-estudios-evaluacion.txt)
- **Qué es:** reglamento histórico de régimen/evaluación para pregrado.
- **Sirve para:** investigar casos de los años en que se aplicaba.
- **No sirve para:** responder evaluación actual sin OCR y comparación con RR 007510-2021 y reglas por plan.

#### DOC-117 — RR 007510-2021, evaluación de pregrado
- [PDF original](../sources/originals/Reglamento-Evaluacion-Pregrado-RR-007510-2021.pdf) · [texto extraído](../sources/extracted/Reglamento-Evaluacion-Pregrado-RR-007510-2021.txt)
- **Qué es:** reglas para evaluar y calificar, con alcance expreso a planes 2019 y anteriores.
- **Sirve para:** preguntas de evaluación de esa población/planes.
- **No sirve para:** afirmar cobertura automática del Plan 2023; la regla aplicable a planes posteriores no está establecida por este archivo.

#### DOC-084 — Grados y Títulos (paquete 2021)
- [PDF original](../sources/originals/Reglamento-Grados-Titulos-2021.pdf) · [texto extraído](../sources/extracted/Reglamento-Grados-Titulos-2021.txt)
- **Qué es:** modificación 2021 del reglamento general aprobado en 2017; incluye reglas transitorias de bachiller automático y documentos requeridos entonces.
- **Sirve para:** preguntas históricas de los años 2020–2021 y su norma base.
- **No sirve para:** presentarlo como la regla final: páginas 6–10 requieren OCR y el archivo 2022 contiene otra extensión distinta.

#### DOC-083 — Grados y Títulos (paquete 2022)
- [PDF original](../sources/originals/Reglamento-Grados-Titulos-2022.pdf) · [texto extraído](../sources/extracted/Reglamento-Grados-Titulos-2022.txt)
- **Qué es:** paquete que contiene RR 004503-2021, RR 003078-2022 y el reglamento de 2017 como base.
- **Sirve para:** comprobar que la excepción de bachiller automático se amplió hasta el ciclo 2023-II.
- **No sirve para:** decir que el bachiller automático aplica a toda cohorte actual ni sustituir requisitos de FISI. Se diferencia del paquete 2021; no son duplicados.

#### DOC-126 — RR 014041-2024, acreditación de idioma extranjero
- [PDF original](../sources/originals/Directiva-idioma-extranjero-pregrado-2024.pdf) · [texto extraído](../sources/extracted/Directiva-idioma-extranjero-pregrado-2024.txt)
- **Qué es:** resolución que aprueba la directiva universitaria de acreditación de idioma para grados y títulos.
- **Sirve para:** conocer el nivel básico requerido, formas de acreditación y alternativa de aprobar cursos de idioma dentro del plan. Art. 3 define a quién alcanza.
- **No sirve para:** ignorar la cohorte o decidir equivalencia de idioma sin revisar el plan asignado.

#### DOC-127 — RR 00744-R-20, trabajo de investigación/tesis/suficiencia
- [PDF original](../sources/originals/Directiva-investigacion-grados-titulos-RR-00744-2020.pdf) · [texto con OCR pendiente](../sources/extracted/Directiva-investigacion-grados-titulos-RR-00744-2020.txt)
- **Qué es:** directiva general de trabajo de investigación para bachiller, tesis o suficiencia para título.
- **Sirve para:** localizar el marco procedimental; la resolución p.1 dice que se dirige a estudiantes que ingresaron desde 2016 o se incorporaron a planes del año de referencia.
- **No sirve todavía para:** dar instrucciones completas; el anexo pp.3–18 es solo imagen y requiere OCR/QA.

#### DOC-103 — Trámite FISI de bachiller
- [PDF original](../sources/originals/FISI-Tramite-grado-bachiller.pdf) · [texto extraído](../sources/extracted/FISI-Tramite-grado-bachiller.txt)
- **Qué es:** lista administrativa FISI de documentos para iniciar el trámite.
- **Sirve para:** orientarse sobre expediente, fotografía y condición de egresado en SUM.
- **No sirve para:** fijar por sí solo requisitos legales actuales: no muestra fecha/acto aprobatorio y califica idioma como opcional, mientras la directiva universitaria 2024 regula el requisito y sus alternativas.

#### DOC-104 — Trámite FISI de título profesional
- [PDF original](../sources/originals/FISI-Tramite-titulo-profesional.pdf) · [texto extraído](../sources/extracted/FISI-Tramite-titulo-profesional.txt)
- **Qué es:** checklist FISI para presentar tesis o trabajo de suficiencia y documentos del trámite.
- **Sirve para:** orientación administrativa preliminar.
- **No sirve para:** ser lista oficial por cohorte: no tiene fecha/versionamiento ni se contrastó con la directiva aprobada vigente.

### Reglas de registro y procedencia de directivas

#### DOC-019 — RR 2272-R-13, aprobación de directivas SUM
- [PDF original escaneado](../sources/originals/RR-2272-R-13-aprueba-directivas-SUM.pdf) · [OCR pendiente](../sources/extracted/RR-2272-R-13-aprueba-directivas-SUM.txt)
- **Qué es:** una de las resoluciones antiguas que el SUM lista como aprobación de directivas.
- **Sirve para:** rastrear su aprobación cuando el documento se OCRice.
- **No sirve todavía para:** identificar sus cláusulas/anexos desde el archivo textual vacío.

#### DOC-020 — RR 2810-R-13, aprobación de directivas SUM
- [PDF original escaneado](../sources/originals/RR-2810-R-13-aprueba-directivas-SUM.pdf) · [OCR pendiente](../sources/extracted/RR-2810-R-13-aprueba-directivas-SUM.txt)
- **Qué es:** otra resolución antigua de aprobación de directivas del SUM.
- **Sirve para:** investigar qué directivas quedaron aprobadas y en qué términos, después de OCR.
- **No sirve todavía para:** sostener una vigencia actual o atribuirle una directiva concreta sin lectura.

## Un corpus inicial pequeño

Para comenzar la indexación en el runtime, considerar como fuentes con texto usable y alcance claro: DOC-005/DOC-002 matrícula 2026 (sin duplicar la regulación contenida dentro de DOC-079); DOC-008 calendario 2026; DOC-126 idioma 2024 con filtro de alcance Art. 3; DOC-086 convalidación 2021 solo como texto de esa resolución, con revisión de vigencia; y DOC-120 para las dos equivalencias explícitas, con filtro a Ingeniería de Sistemas y QA manual. Los archivos DOC-121 y DOC-122 no contienen sus anexos curriculares/tabulares, así que no deben ser tratados como currículo/equivalencia indexable.

## Enlaces para continuar

- [Qué falta buscar y por qué](source_collection_report.md)
- [Cobertura por escuela/plan y citas](fisi_plan_coverage_matrix.md)
- [Inventario completo y metadatos](../data/document_inventory_audited.csv)
- [Relaciones documentales](../data/document_relationships.csv)
- [Hash y estado de cada descarga](../sources/source_manifest.csv)
