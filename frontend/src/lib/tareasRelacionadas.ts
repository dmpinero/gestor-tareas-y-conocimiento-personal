import { etiquetaTipoTarea, type Subtarea, type Tarea } from '@/api/tipos'
import { estaHibernada } from '@/lib/hibernacion'

/** Lo que se puede pulsar en una tarea para ver las demás que lo comparten. */
export type TipoRelacion =
  | 'etiqueta'
  | 'persona'
  | 'subestado'
  | 'prioridad'
  | 'estado'
  | 'tipo'
  | 'completado'
  | 'hibernada'
  | 'sinVencimiento'

/** Texto de la píldora "Completada"/"Pendiente" de una tarea. */
export function textoCompletado(tarea: Pick<Tarea, 'completada'>): 'Completada' | 'Pendiente' {
  return tarea.completada ? 'Completada' : 'Pendiente'
}

interface Relacion {
  /** Nombre accesible del botón que abre el modal. */
  accesible: (nombre: string) => string
  /** Título del modal. */
  titulo: (nombre: string) => string
  descripcion: string
  /** Aviso cuando ninguna tarea coincide. */
  vacio: string
  coincide: (tarea: Tarea, nombre: string) => boolean
  /**
   * Solo en lo que también tienen las subtareas (persona y prioridad): el modal
   * añade la sección de subtareas, con su aviso si no hay ninguna.
   */
  subtareas?: { coincide: (subtarea: Subtarea, nombre: string) => boolean; vacio: string }
}

// El nombre accesible contiene siempre el texto visible (WCAG 2.5.3).
// `nombre` es siempre el texto que se ve en la píldora pulsada (p. ej. la
// prioridad "2", el tipo "Oportunidad" o "Completada"). El estado se compara
// por nombre: cuenta el mismo estado aunque esté en otro grupo.
export const RELACIONES: Record<TipoRelacion, Relacion> = {
  etiqueta: {
    accesible: (nombre) => `Ver tareas con la etiqueta ${nombre}`,
    titulo: (nombre) => `Etiqueta: ${nombre}`,
    descripcion: 'Tareas que llevan esta etiqueta.',
    vacio: 'No hay tareas con esta etiqueta.',
    coincide: (tarea, nombre) => tarea.etiquetas.includes(nombre),
  },
  persona: {
    accesible: (nombre) => `Ver tareas y subtareas de ${nombre}`,
    titulo: (nombre) => `Persona: ${nombre}`,
    descripcion: 'Tareas y subtareas asignadas a esta persona.',
    vacio: 'No hay tareas asignadas a esta persona.',
    coincide: (tarea, nombre) => tarea.asignados.includes(nombre),
    subtareas: {
      coincide: (subtarea, nombre) => subtarea.asignado === nombre,
      vacio: 'No hay subtareas asignadas a esta persona.',
    },
  },
  subestado: {
    accesible: (nombre) => `Ver tareas con el subestado ${nombre}`,
    titulo: (nombre) => `Subestado: ${nombre}`,
    descripcion: 'Tareas con este subestado.',
    vacio: 'No hay tareas con este subestado.',
    coincide: (tarea, nombre) => tarea.subestado === nombre,
  },
  prioridad: {
    accesible: (nombre) => `Ver tareas y subtareas con la prioridad ${nombre}`,
    titulo: (nombre) => `Prioridad: ${nombre}`,
    descripcion: 'Tareas y subtareas con esta prioridad.',
    vacio: 'No hay tareas con esta prioridad.',
    coincide: (tarea, nombre) => tarea.prioridad !== null && String(tarea.prioridad) === nombre,
    subtareas: {
      coincide: (subtarea, nombre) =>
        subtarea.prioridad !== null && String(subtarea.prioridad) === nombre,
      vacio: 'No hay subtareas con esta prioridad.',
    },
  },
  estado: {
    accesible: (nombre) => `Ver tareas en el estado ${nombre}`,
    titulo: (nombre) => `Estado: ${nombre}`,
    descripcion: 'Tareas en este estado de su grupo.',
    vacio: 'No hay tareas en este estado.',
    coincide: (tarea, nombre) => tarea.estado?.nombre === nombre,
  },
  tipo: {
    accesible: (nombre) => `Ver tareas de tipo ${nombre}`,
    titulo: (nombre) => `Tipo: ${nombre}`,
    descripcion: 'Tareas de este tipo.',
    vacio: 'No hay tareas de este tipo.',
    coincide: (tarea, nombre) => etiquetaTipoTarea(tarea.tipo) === nombre,
  },
  completado: {
    accesible: (nombre) => `Ver tareas: ${nombre}`,
    titulo: (nombre) => `Tareas ${nombre === 'Completada' ? 'completadas' : 'pendientes'}`,
    descripcion: '',
    vacio: '',
    coincide: (tarea, nombre) => textoCompletado(tarea) === nombre,
  },
  hibernada: {
    accesible: (nombre) => `Ver tareas: ${nombre}`,
    titulo: () => 'Tareas hibernadas',
    descripcion: 'Tareas con el reloj de vencimiento parado hasta reanudarlas.',
    vacio: 'No hay tareas hibernadas.',
    coincide: (tarea) => estaHibernada(tarea),
  },
  // `nombre` es el aviso del calendario ("3 tareas sin fecha de vencimiento").
  sinVencimiento: {
    accesible: (nombre) => `Ver ${nombre}`,
    titulo: () => 'Tareas sin fecha de vencimiento',
    descripcion: 'Tareas que no tienen fecha de vencimiento y no salen en el calendario.',
    vacio: 'No hay tareas sin fecha de vencimiento.',
    coincide: (tarea) => !tarea.fecha_vencimiento,
  },
}

/** Descripción y aviso del modal; los de "completado" dependen de cuál sea. */
export function textosRelacion(
  tipo: TipoRelacion,
  nombre: string,
): { descripcion: string; vacio: string } {
  if (tipo !== 'completado') return RELACIONES[tipo]
  return nombre === 'Completada'
    ? { descripcion: 'Tareas marcadas como completadas.', vacio: 'No hay tareas completadas.' }
    : { descripcion: 'Tareas sin completar.', vacio: 'No hay tareas pendientes.' }
}
