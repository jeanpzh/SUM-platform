export interface ProgramacionResponse {
    message:  null;
    codError: null;
    data:     Data;
}

export interface Data {
    alumno:       Alumno;
    programacion: Programacion[];
}

export interface Alumno {
    codAlumno:            string;
    apePaterno:           string;
    apeMaterno:           string;
    nomAlumno:            string;
    codFacultad:          number;
    desFacultad:          string;
    areaFacultad:         number;
    codEscuela:           number;
    desEscuela:           string;
    areaEscuela:          number;
    codEspecialidad:      number;
    desEspecialidad:      string;
    codPlan:              string;
    desPlan:              string;
    ponderado:            number;
    actualizoFormulario:  boolean;
    habEncuesta:          boolean;
    habEncuestaEgresados: boolean;
    habMatricula:         boolean;
    periodo:              string;
    urlFoto:              string;
    foto:                 string;
    codPermanencia:       string;
    desPermanencia:       string;
    codSituacion:         string;
    desSituacion:         string;
    regimen:              string;
    egresadoEG:           string;
    cicloEstudios:        number;
    anioIngreso:          number;
    correoInstitucional:  string;
    sexo:                 string;
    nroTicketMatEG:       number;
    infoSemestre:         InfoSemestre;
    infoMatricula:        null;
    anioEstudio:          number;
    codSede:              string;
    sedeAlumno:           string;
    difCriterioCalif:     boolean;
}

export interface InfoSemestre {
    fecSistema:                 null;
    fecInicioEncuestaDocente:   Date;
    fecFinEncuestaDocente:      Date;
    fecInicioEncuestaDocenteS1: Date;
    fecFinEncuestaDocenteS1:    Date;
    fecInicioEncuestaDocenteS2: Date;
    fecFinEncuestaDocenteS2:    Date;
    fecInicioEncuestaDocenteA1: Date;
    fecFinEncuestaDocenteA1:    Date;
    fecInicioEncuestaDocenteA2: Date;
    fecFinEncuestaDocenteA2:    Date;
}

export interface Programacion {
    ciclo:         number;
    codAsignatura: string;
    desAsignatura: string;
    creditos:      number;
    codSeccion:    number;
    horario:       number;
    codDocente:    string;
    nomDocente:    string;
    apePatDocente: string;
    apeMatDocente: string;
    topeAlumnos:   number;
    matriculados:  number;
    horarios:      Horario[];
}

export interface Horario {
    codSemestre:           null;
    codFacultad:           number;
    codEscuela:            number;
    codEspecialidad:       number;
    codPlan:               null;
    codAsignatura:         string;
    desAsignatura:         null;
    codSeccion:            number;
    codDocente:            string;
    nomDocente:            null;
    horario:               number;
    dia:                   Dia;
    horaInicio:            Hora;
    horaFin:               Hora;
    horaInicioMin:         number;
    horaFinMin:            number;
    codAula:               string;
    topeAlumnosLab:        number;
    matriculadosLab:       number;
    codTipoHoraAsignatura: CodTipoHoraAsignatura;
    desTipoHoraAsignatura: DESTipoHoraAsignatura;
}

export type CodTipoHoraAsignatura = "T" | "P" | "L";

export type DESTipoHoraAsignatura = "Teoría" | "Práctica" | "Laboratorio";

export type Dia = "JUEVES" | "SABADO" | "MIERCOLES" | "LUNES" | "VIERNES" | "MARTES";

export type Hora = "08:00" | "09:00" | "11:00" | "12:00" | "10:00" | "14:00" | "16:00" | "15:00" | "18:00" | "17:00" | "20:00" | "19:00" | "13:00" | "22:00" | "21:00";
