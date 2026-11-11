/**
 * Utilidades para el histórico de comentarios de una tarea.
 *
 * La API envía `creado` en UTC ISO 8601 con `Z` (`2026-11-10T16:30:05Z`); aquí
 * se convierte a hora local para agrupar por día y mostrar la hora.
 */

import { dosCifras } from '@/lib/fechas'

export interface Comentario {
  id: number
  texto: string
  /** Fecha y hora de alta en UTC ISO 8601 con `Z`. No cambia al editarlo. */
  creado: string
  /** Fecha y hora de la última edición en UTC ISO 8601 con `Z`; `null` si
   * nunca se ha editado. */
  editado: string | null
}

export interface ComentarioMostrado extends Comentario {
  /** Hora local `HH:MM`. */
  hora: string
  /**
   * Referencia legible y única dentro del historial, para los nombres
   * accesibles de sus botones: `de las 18:30 del miércoles, 1 de abril`, con
   * ` (2)`, ` (3)`… si varios coinciden en día y hora.
   */
  referencia: string
}

export interface GrupoDiaComentarios {
  /** Día local `YYYY-MM-DD`, único por grupo. */
  clave: string
  /** Separador legible, p. ej. `miércoles, 1 de abril`. */
  etiqueta: string
  comentarios: ComentarioMostrado[]
}

function claveDiaLocal(fecha: Date): string {
  return `${fecha.getFullYear()}-${dosCifras(fecha.getMonth() + 1)}-${dosCifras(fecha.getDate())}`
}

/** Hora local `HH:MM` de una marca UTC ISO 8601. */
export function formatearHoraComentario(creado: string): string {
  const fecha = new Date(creado)
  return `${dosCifras(fecha.getHours())}:${dosCifras(fecha.getMinutes())}`
}

/**
 * Etiqueta del día (`miércoles, 1 de abril`), con el año solo cuando no es el
 * del día de referencia (`hoy`).
 */
export function formatearDiaComentario(fecha: Date, hoy: Date = new Date()): string {
  const opciones: Intl.DateTimeFormatOptions = {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    ...(fecha.getFullYear() === hoy.getFullYear() ? {} : { year: 'numeric' }),
  }
  return new Intl.DateTimeFormat('es-ES', opciones).format(fecha)
}

/** Día y hora local de la edición: `martes, 10 de noviembre a las 17:45`. */
export function formatearEdicionComentario(editado: string, hoy: Date = new Date()): string {
  return `${formatearDiaComentario(new Date(editado), hoy)} a las ${formatearHoraComentario(editado)}`
}

/** Agrupa los comentarios por día local, en orden cronológico (el más antiguo primero). */
export function agruparComentariosPorDia(
  comentarios: readonly Comentario[],
  hoy: Date = new Date(),
): GrupoDiaComentarios[] {
  const ordenados = comentarios
    .map((comentario, indice) => ({ comentario, indice, fecha: new Date(comentario.creado) }))
    .sort((a, b) => a.fecha.getTime() - b.fecha.getTime() || a.indice - b.indice)

  const grupos: GrupoDiaComentarios[] = []
  const repeticiones = new Map<string, number>()
  for (const { comentario, fecha } of ordenados) {
    const clave = claveDiaLocal(fecha)
    let grupo = grupos[grupos.length - 1]
    if (!grupo || grupo.clave !== clave) {
      grupo = { clave, etiqueta: formatearDiaComentario(fecha, hoy), comentarios: [] }
      grupos.push(grupo)
    }
    const hora = formatearHoraComentario(comentario.creado)
    const base = `de las ${hora} del ${grupo.etiqueta}`
    const repeticion = (repeticiones.get(base) ?? 0) + 1
    repeticiones.set(base, repeticion)
    const referencia = repeticion === 1 ? base : `${base} (${repeticion})`
    grupo.comentarios.push({ ...comentario, hora, referencia })
  }
  return grupos
}
