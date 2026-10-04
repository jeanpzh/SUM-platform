export interface PlanResponse {
    message:  null;
    codError: null;
    data:     Datum[];
}

export interface Datum {
    codFacultad:      number;
    codEscuela:       number;
    codPlan:          CodPlan;
    codEspecialidad:  number;
    ciclo:            number;
    codAsignatura:    string;
    desAsignatura:    string;
    creditos:         number;
    tipoAsignatura:   TipoAsignatura;
    codGrupo:         CodGrupo;
    codAsignaturaPre: string;
    desAsignaturaPre: string;
    codGrupoPre:      CodGrupo;
    creditosPre:      number;
}

export type CodGrupo = "GEG" | "--";

export type CodPlan = "2018  ";

export type TipoAsignatura = "E" | "O";
