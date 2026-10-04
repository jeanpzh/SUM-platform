export interface HistorialResponse {
    message:  null;
    codError: null;
    data:     Data;
}

export interface Data {
    historial:            Historial[];
    promedios:            Promedio[];
    creditaje:            { [key: string]: number };
    criterioCalificacion: boolean;
    anioIngreso:          number;
    facultad:             number;
    escuela:              number;
}

export interface Historial {
    codAlumno:         null;
    codSemestre:       string;
    codFacultad:       number;
    codEscuela:        number;
    codEspecialidad:   number;
    codPlan:           string;
    codSeccion:        number;
    ciclo:             number;
    codTipoAsignatura: CodTipoAsignatura;
    creditos:          number;
    codAsignatura:     string;
    desAsignatura:     string;
    calificacion:      number;
    codTipoActa:       CodTipoActa;
    numActa:           string;
    numResConv:        null;
}

export type CodTipoActa = "P";

export type CodTipoAsignatura = "E" | "O";

export interface Promedio {
    semestre: string;
    promedio: number;
}
