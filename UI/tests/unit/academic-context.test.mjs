import assert from 'node:assert/strict'
import { test } from 'node:test'
import { ContextPlanner } from '../../src/academic/context/context-planner.ts'
import { AcademicContextBuilder } from '../../src/academic/context/context-builder.ts'
import {
  academicQueryContextSchema,
  validateContextForPlan,
} from '../../src/academic/context/schemas.ts'
import { createAcademicGatewayHandler } from '../../src/integrations/sum/academic-gateway.server.ts'

const secrets = {
  nombre: 'PRIVATE_NAME',
  dni: 'PRIVATE_DNI',
  cookie: 'PRIVATE_COOKIE',
  token: 'PRIVATE_TOKEN',
  email: 'PRIVATE_EMAIL',
  Authorization: 'PRIVATE_AUTH',
  password: 'PRIVATE_PASSWORD',
  financialData: 'PRIVATE_FINANCE',
}
// Fixed model outputs test privacy/projection, not the linguistic accuracy of an external model.
const modelPlans = new Map([
  [
    '¿Cuántos créditos he aprobado?',
    {
      intent: 'COMPLETED_CREDITS',
      entities: {},
      requirements: ['ACADEMIC_HISTORY'],
    },
  ],
  [
    '¿Qué horario tiene Inteligencia Artificial?',
    {
      intent: 'GET_COURSE_SCHEDULE',
      entities: { courseNames: ['Inteligencia Artificial'] },
      requirements: ['ACADEMIC_PROGRAMMING'],
    },
  ],
  [
    '¿Qué horario tiene Curso inexistente?',
    {
      intent: 'GET_COURSE_SCHEDULE',
      entities: { courseNames: ['Curso inexistente'] },
      requirements: ['ACADEMIC_PROGRAMMING'],
    },
  ],
  [
    '¿Puedo llevar Compiladores?',
    {
      intent: 'CHECK_COURSE_ELIGIBILITY',
      entities: { courseNames: ['Compiladores'] },
      requirements: ['ACADEMIC_HISTORY', 'STUDY_PLAN', 'INSTITUTIONAL_RULES'],
    },
  ],
  [
    '¿Cuál es el reglamento para retiro de curso?',
    {
      intent: 'GENERAL_ACADEMIC_RULE',
      entities: {},
      requirements: ['INSTITUTIONAL_RULES'],
    },
  ],
  [
    '¿Qué nota obtuve en Base de Datos?',
    {
      intent: 'GRADE_QUERY',
      entities: { courseNames: ['Base de Datos'] },
      requirements: ['ACADEMIC_HISTORY'],
    },
  ],
  [
    '¿Qué cursos me faltan para terminar?',
    {
      intent: 'REMAINING_COURSES',
      entities: {},
      requirements: ['ACADEMIC_HISTORY', 'STUDY_PLAN'],
    },
  ],
  [
    '¿Qué cursos puedo matricular el próximo ciclo?',
    {
      intent: 'LIST_AVAILABLE_COURSES',
      entities: {},
      requirements: [
        'ACADEMIC_HISTORY',
        'STUDY_PLAN',
        'ACADEMIC_PROGRAMMING',
        'INSTITUTIONAL_RULES',
      ],
    },
  ],
  [
    '¿Cuál es el prerrequisito de Compiladores?',
    {
      intent: 'CHECK_PREREQUISITES',
      entities: { courseNames: ['Compiladores'] },
      requirements: ['STUDY_PLAN'],
    },
  ],
  [
    '¿Ya cumplo los prerrequisitos para Compiladores?',
    {
      intent: 'CHECK_PREREQUISITE_FULFILLMENT',
      entities: { courseNames: ['Compiladores'] },
      requirements: ['ACADEMIC_HISTORY', 'STUDY_PLAN'],
    },
  ],
])
const fixturePlanner = () =>
  new ContextPlanner(async ({ query }) => {
    const plan = modelPlans.get(query)
    assert.ok(plan, `Provide a model-output fixture for: ${query}`)
    return structuredClone(plan)
  })

test('every query is interpreted by the LLM port, including apparently obvious questions', async () => {
  let calls = 0
  const planner = new ContextPlanner(async () => {
    calls++
    return { intent: 'OTHER', entities: {}, requirements: [] }
  })
  assert.equal(
    (await planner.plan({ query: '¿Cuántos créditos he aprobado?' })).intent,
    'OTHER',
  )
  assert.equal(calls, 1)
})
function attempt(code, name, grade, credits = 4) {
  return {
    codAlumno: null,
    codSemestre: '2025-2',
    codFacultad: 20,
    codEscuela: 1,
    codEspecialidad: 0,
    codPlan: '2018  ',
    codSeccion: 1,
    ciclo: 3,
    codTipoAsignatura: 'O',
    creditos: credits,
    codAsignatura: code,
    desAsignatura: name,
    calificacion: grade,
    codTipoActa: 'P',
    numActa: 'PRIVATE_ACTA',
    numResConv: null,
    ...secrets,
  }
}
function row(code, name, pre = '', preName = '') {
  return {
    codFacultad: 20,
    codEscuela: 1,
    codPlan: '2018  ',
    codEspecialidad: 0,
    ciclo: 5,
    codAsignatura: code,
    desAsignatura: name,
    creditos: 4,
    tipoAsignatura: 'O',
    codGrupo: '--',
    codAsignaturaPre: pre,
    desAsignaturaPre: preName,
    codGrupoPre: '--',
    creditosPre: 0,
    ...secrets,
  }
}
function offering(code, name) {
  return {
    ciclo: 5,
    codAsignatura: code,
    desAsignatura: name,
    creditos: 4,
    codSeccion: 1,
    horario: 1,
    codDocente: 'PRIVATE_TEACHER_ID',
    nomDocente: 'PRIVATE_TEACHER',
    apePatDocente: 'P',
    apeMatDocente: 'M',
    topeAlumnos: 40,
    matriculados: 15,
    horarios: [
      {
        codSemestre: null,
        codFacultad: 20,
        codEscuela: 1,
        codEspecialidad: 0,
        codPlan: null,
        codAsignatura: code,
        desAsignatura: null,
        codSeccion: 1,
        codDocente: 'PRIVATE_TEACHER_ID',
        nomDocente: null,
        horario: 1,
        dia: 'LUNES',
        horaInicio: '08:00',
        horaFin: '10:00',
        horaInicioMin: 480,
        horaFinMin: 600,
        codAula: 'A101',
        topeAlumnosLab: 20,
        matriculadosLab: 10,
        codTipoHoraAsignatura: 'T',
        desTipoHoraAsignatura: 'Teoría',
        ...secrets,
      },
    ],
    ...secrets,
  }
}
export function fixture() {
  const history = {
    message: null,
    codError: null,
    data: {
      historial: [
        attempt('PR', 'Lenguajes de Programación', 15),
        attempt('BD', 'Base de Datos', 16),
        attempt('OT', 'Curso ajeno', 18),
      ],
      promedios: [{ semestre: '2025-2', promedio: 16 }],
      creditaje: { unknownKey: 9999 },
      criterioCalificacion: false,
      anioIngreso: 2020,
      facultad: 20,
      escuela: 1,
      ...secrets,
    },
    ...secrets,
  }
  const plan = {
    message: null,
    codError: null,
    data: [
      row('CO', 'Compiladores', 'PR', 'Lenguajes de Programación'),
      row('PR', 'Lenguajes de Programación'),
      row('BD', 'Base de Datos'),
      row('OT', 'Curso ajeno'),
      row('IA', 'Inteligencia Artificial'),
    ],
    ...secrets,
  }
  const programming = {
    message: null,
    codError: null,
    data: {
      alumno: {
        codAlumno: 'PRIVATE_STUDENT',
        apePaterno: 'PRIVATE_NAME',
        apeMaterno: 'PRIVATE_NAME',
        nomAlumno: 'PRIVATE_NAME',
        codFacultad: 20,
        desFacultad: 'Facultad',
        areaFacultad: 1,
        codEscuela: 1,
        desEscuela: 'Escuela',
        areaEscuela: 1,
        codEspecialidad: 0,
        desEspecialidad: '',
        codPlan: '2018',
        desPlan: '',
        ponderado: 17,
        actualizoFormulario: true,
        habEncuesta: false,
        habEncuestaEgresados: false,
        habMatricula: true,
        periodo: '2026-1',
        urlFoto: 'PRIVATE_PHOTO',
        foto: 'PRIVATE_PHOTO',
        codPermanencia: '',
        desPermanencia: '',
        codSituacion: '',
        desSituacion: '',
        regimen: '',
        egresadoEG: '',
        cicloEstudios: 5,
        anioIngreso: 2020,
        correoInstitucional: 'PRIVATE_EMAIL',
        sexo: '',
        nroTicketMatEG: 1,
        infoSemestre: {
          fecSistema: null,
          fecInicioEncuestaDocente: new Date(),
          fecFinEncuestaDocente: new Date(),
          fecInicioEncuestaDocenteS1: new Date(),
          fecFinEncuestaDocenteS1: new Date(),
          fecInicioEncuestaDocenteS2: new Date(),
          fecFinEncuestaDocenteS2: new Date(),
          fecInicioEncuestaDocenteA1: new Date(),
          fecFinEncuestaDocenteA1: new Date(),
          fecInicioEncuestaDocenteA2: new Date(),
          fecFinEncuestaDocenteA2: new Date(),
        },
        infoMatricula: null,
        anioEstudio: 3,
        codSede: '',
        sedeAlumno: '',
        difCriterioCalif: false,
        ...secrets,
      },
      programacion: [
        offering('IA', 'Inteligencia Artificial'),
        offering('BD', 'Base de Datos'),
        offering('CO', 'Compiladores'),
      ],
      ...secrets,
    },
    ...secrets,
  }
  const calls = []
  const builder = new AcademicContextBuilder({
    planner: fixturePlanner(),
    sources: {
      async history() {
        calls.push('history')
        return history
      },
      async plan() {
        calls.push('plan')
        return plan
      },
      async programming() {
        calls.push('programming')
        return programming
      },
    },
    policy: {
      version: 'test-reviewed-policy',
      outcome: ({ grade }) => (grade >= 11 ? 'PASSED' : 'FAILED'),
    },
    async retrieveRules() {
      calls.push('rules')
      return [
        {
          citationId: '00000000-0000-4000-8000-000000000001',
          text: 'Regla institucional publicada de ejemplo.',
          ...secrets,
        },
      ]
    },
  })
  return { builder, calls, history, plan, programming }
}
const session = {
  connectionId: 'PRIVATE_CONNECTION',
  planCode: '2018',
  historyComplete: true,
}

test('A: schedule exposes only matching programming and never fetches history', async () => {
  const { builder, calls } = fixture()
  const context = await builder.build(
    '¿Qué horario tiene Inteligencia Artificial?',
    session,
  )
  assert.deepEqual(Object.keys(context), ['academicProgramming'])
  assert.deepEqual(calls, ['programming'])
  assert.deepEqual(
    context.academicProgramming.courses.map((c) => c.courseCode),
    ['IA'],
  )
  assert.equal(JSON.stringify(context).includes('grade'), false)
})
test('B: approved credits is a derived total, deduplicates passed retakes', async () => {
  const { builder, calls, history } = fixture()
  history.data.historial.push(attempt('BD', 'Base de Datos', 18))
  const context = await builder.build('¿Cuántos créditos he aprobado?', session)
  assert.deepEqual(context, { academicHistory: { completedCredits: 12 } })
  assert.deepEqual(calls, ['history'])
})
test('C: eligibility includes only target prerequisite graph and related course statuses', async () => {
  const { builder } = fixture()
  const context = await builder.build('¿Puedo llevar Compiladores?', session)
  assert.deepEqual(context.academicHistory.courses, [
    { courseCode: 'PR', status: 'PASSED' },
    { courseCode: 'CO', status: 'NOT_TAKEN' },
  ])
  assert.deepEqual(
    context.studyPlan.courses.map((c) => c.courseCode),
    ['CO', 'PR'],
  )
  assert.equal(JSON.stringify(context).includes('Curso ajeno'), false)
  assert.equal(JSON.stringify(context).includes('grade'), false)
})
test('D: general withdrawal regulation uses shared RAG and no SUM endpoint', async () => {
  const { builder, calls } = fixture()
  const context = await builder.build(
    '¿Cuál es el reglamento para retiro de curso?',
    session,
  )
  assert.deepEqual(Object.keys(context), ['institutionalRules'])
  assert.deepEqual(calls, ['rules'])
})
test('E: injected raw secrets at every level cannot survive allowlist mapping', async () => {
  const { builder } = fixture()
  for (const query of [
    '¿Qué horario tiene Inteligencia Artificial?',
    '¿Cuántos créditos he aprobado?',
    '¿Puedo llevar Compiladores?',
    '¿Cuál es el reglamento para retiro de curso?',
    '¿Qué nota obtuve en Base de Datos?',
    '¿Qué cursos me faltan para terminar?',
    '¿Qué cursos puedo matricular el próximo ciclo?',
  ]) {
    const context = await builder.build(query, session)
    const serialized = JSON.stringify(context)
    for (const value of Object.values(secrets))
      assert.equal(serialized.includes(value), false, query)
    assert.equal(serialized.includes('PRIVATE_'), false, query)
    assert.equal(academicQueryContextSchema.safeParse(context).success, true)
  }
})
test('planner distinguishes definition from personal prerequisite fulfillment', async () => {
  const planner = fixturePlanner()
  assert.deepEqual(
    (
      await planner.plan({
        query: '¿Cuál es el prerrequisito de Compiladores?',
      })
    ).requirements,
    ['STUDY_PLAN'],
  )
  assert.deepEqual(
    (
      await planner.plan({
        query: '¿Ya cumplo los prerrequisitos para Compiladores?',
      })
    ).requirements,
    ['ACADEMIC_HISTORY', 'STUDY_PLAN'],
  )
})
test('ambiguous semantics goes to a classifier with ONLY the query and closed output', async () => {
  let input
  const planner = new ContextPlanner(async (value) => {
    input = value
    return {
      intent: 'GET_COURSE_SCHEDULE',
      entities: { courseNames: ['Inteligencia Artificial'] },
      requirements: ['ACADEMIC_PROGRAMMING'],
    }
  })
  const plan = await planner.plan({
    query: 'Necesito organizar mi lunes para asistir a IA',
  })
  assert.deepEqual(input, {
    query: 'Necesito organizar mi lunes para asistir a IA',
  })
  assert.equal(plan.intent, 'GET_COURSE_SCHEDULE')
  await assert.rejects(() =>
    planner.plan({ query: 'Una consulta', student: secrets }),
  )
  const invalid = new ContextPlanner(async () => ({
    intent: 'GET_COURSE_SCHEDULE',
    entities: { courseNames: ['IA'] },
    requirements: ['ACADEMIC_HISTORY', 'ACADEMIC_PROGRAMMING'],
  }))
  await assert.rejects(() => invalid.plan({ query: 'Consulta ambigua' }))
})
test('unknown course never falls back to sending the complete source', async () => {
  const { builder } = fixture()
  const context = await builder.build(
    '¿Qué horario tiene Curso inexistente?',
    session,
  )
  assert.deepEqual(context.academicProgramming.courses, [])
})
test('missing grading policy gives unknown rather than inventing pass threshold', async () => {
  const { history, plan, programming } = fixture()
  const builder = new AcademicContextBuilder({
    planner: fixturePlanner(),
    sources: {
      history: async () => history,
      plan: async () => plan,
      programming: async () => programming,
    },
  })
  assert.deepEqual(
    await builder.build('¿Cuántos créditos he aprobado?', session),
    { academicHistory: { completedCredits: null, unresolvedCourses: 3 } },
  )
})
test('strict nested schemas reject forbidden fields and unrelated projection fields', () => {
  assert.equal(
    academicQueryContextSchema.safeParse({
      academicHistory: { completedCredits: 12, token: 'x' },
    }).success,
    false,
  )
  assert.equal(
    academicQueryContextSchema.safeParse({
      academicProgramming: {
        courses: [{ courseCode: 'IA', courseName: 'IA', grade: 20 }],
      },
    }).success,
    false,
  )
})

test('gateway authenticates and resolves ownership before selecting SUM sources', async () => {
  const { builder, calls } = fixture()
  const connection = '00000000-0000-4000-8000-000000000003'
  const body = {
    schema_version: 'academic-context-v2',
    run_id: '00000000-0000-4000-8000-000000000002',
    owner_id: 'student:private',
    connection_id: connection,
    query: '¿Cuántos créditos he aprobado?',
    plan: {
      intent: 'COMPLETED_CREDITS',
      entities: {},
      requirements: ['ACADEMIC_HISTORY'],
    },
  }
  const request = () =>
    new Request('http://gateway/internal/academic-context', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  const forbidden = createAcademicGatewayHandler({
    authorize: async () => false,
    resolveSession: async () => assert.fail('Must authenticate first'),
    builder,
  })
  assert.equal((await forbidden(request())).status, 403)
  assert.deepEqual(calls, [])
  const owned = createAcademicGatewayHandler({
    authorize: async () => true,
    resolveSession: async () => ({
      connectionId: connection,
      planCode: '2018',
      historyComplete: true,
    }),
    builder,
  })
  const response = await owned(request())
  assert.equal(response.status, 200)
  const result = await response.json()
  assert.equal(result.schemaVersion, 'academic-context-v2')
  assert.deepEqual(result.context, {
    academicHistory: { completedCredits: 12 },
  })
  assert.equal(JSON.stringify(result.context).includes(connection), false)
})

test('prerequisite definitions project only the target, not the entire ancestor graph', async () => {
  const { builder } = fixture()
  const context = await builder.build(
    '¿Cuál es el prerrequisito de Compiladores?',
    session,
  )
  assert.deepEqual(Object.keys(context), ['studyPlan'])
  assert.deepEqual(
    context.studyPlan.courses.map((c) => c.courseCode),
    ['CO'],
  )
  assert.equal('credits' in context.studyPlan.courses[0], false)
  assert.equal('type' in context.studyPlan.courses[0], false)
})

test('cycles terminate and credit/group prerequisites are preserved without invented course codes', async () => {
  const { builder, plan } = fixture()
  plan.data.push(row('PR', 'Lenguajes de Programación', 'CO', 'Compiladores'))
  const creditRow = row('CO', 'Compiladores')
  creditRow.codGrupoPre = 'GEG'
  creditRow.creditosPre = 40
  plan.data.push(creditRow)
  const context = await builder.build('¿Puedo llevar Compiladores?', session)
  assert.equal(context.studyPlan.courses.length, 2)
  assert.ok(
    context.studyPlan.courses[0].prerequisites.some(
      (p) => p.courseCode === null && p.group === 'GEG' && p.credits === 40,
    ),
  )
})

test('explicit grade term filters attempts before projecting to the model', async () => {
  const { history, plan, programming } = fixture()
  const old = attempt('BD', 'Base de Datos', 9)
  old.codSemestre = '2024-1'
  history.data.historial.push(old)
  const planner = new ContextPlanner(async () => ({
    intent: 'GRADE_QUERY',
    entities: { courseCodes: ['BD'], term: '2025-2' },
    requirements: ['ACADEMIC_HISTORY'],
  }))
  const builder = new AcademicContextBuilder({
    planner,
    sources: {
      history: async () => history,
      plan: async () => plan,
      programming: async () => programming,
    },
  })
  const context = await builder.build(
    'Mi calificación de BD en el periodo 2025-2',
    session,
  )
  assert.deepEqual(context.academicHistory.courses, [
    { courseCode: 'BD', status: 'UNKNOWN', grade: 16, term: '2025-2' },
  ])
})

test('plan-aware validation rejects unrelated courses even in an allowed source', async () => {
  const planner = fixturePlanner()
  const plan = await planner.plan({
    query: '¿Qué horario tiene Inteligencia Artificial?',
  })
  assert.throws(() =>
    validateContextForPlan(
      {
        academicProgramming: {
          courses: [
            {
              courseCode: 'BD',
              courseName: 'Base de Datos',
              section: 1,
              schedule: [],
            },
          ],
        },
      },
      plan,
    ),
  )
})

test('simulation projection exposes credits only for selected targets and schedule times only', async () => {
  const f = fixture()
  const plan = {
    intent: 'SIMULATE_ENROLLMENT',
    entities: { courseCodes: ['CO', 'IA'] },
    requirements: [
      'ACADEMIC_HISTORY',
      'STUDY_PLAN',
      'ACADEMIC_PROGRAMMING',
      'INSTITUTIONAL_RULES',
    ],
  }
  const context = await f.builder.buildFromPlan('Simula CO e IA', session, plan)
  assert.equal(
    context.studyPlan.courses.find((c) => c.courseCode === 'CO').credits,
    4,
  )
  assert.ok(
    !(
      'credits' in context.studyPlan.courses.find((c) => c.courseCode === 'PR')
    ),
  )
  for (const course of context.academicProgramming.courses) {
    assert.ok(['CO', 'IA'].includes(course.courseCode))
    for (const slot of course.schedule)
      assert.deepEqual(Object.keys(slot).sort(), ['day', 'end', 'start'])
  }
  assert.doesNotMatch(JSON.stringify(context), /grade|PRIVATE_/)
})

test('credit-load projection never fetches private history or programming', async () => {
  const f = fixture()
  const context = await f.builder.buildFromPlan(
    'Comprueba la carga de IA',
    session,
    {
      intent: 'CHECK_CREDIT_LOAD',
      entities: { courseCodes: ['IA'] },
      requirements: ['STUDY_PLAN', 'INSTITUTIONAL_RULES'],
    },
  )
  assert.deepEqual(context.studyPlan.courses, [
    { courseCode: 'IA', courseName: 'Inteligencia Artificial', credits: 4 },
  ])
  assert.ok(!('academicHistory' in context))
  assert.ok(!('academicProgramming' in context))
  assert.ok(!f.calls.includes('history'))
  assert.ok(!f.calls.includes('programming'))
})

test('explicit section selection cannot return other sections or private fields', async () => {
  const f = fixture()
  const context = await f.builder.buildFromPlan(
    'Horario de IA sección inexistente',
    session,
    {
      intent: 'GET_COURSE_SCHEDULE',
      entities: {
        courseCodes: ['IA'],
        sections: [{ courseCode: 'IA', section: 999 }],
      },
      requirements: ['ACADEMIC_PROGRAMMING'],
    },
  )
  assert.deepEqual(context, { academicProgramming: { courses: [] } })
})
