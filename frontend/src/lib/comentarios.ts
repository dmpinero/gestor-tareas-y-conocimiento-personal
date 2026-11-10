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
  /** Fecha y hora de alta en UTC ISO 8601 con `Z`. */
  creado: string
}

export interface ComentarioMostrado extends Comentario {
  /** Hora local `HH:MM`. */
  hora: string
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

/** Agrupa los comentarios por día local, en orden cronológico (el más antiguo primero). */
export function agruparComentariosPorDia(
  comentarios: readonly Comentario[],
  hoy: Date = new Date(),
): GrupoDiaComentarios[] {
  const ordenados = comentarios
    .map((comentario, indice) => ({ comentario, indice, fecha: new Date(comentario.creado) }))
    .sort((a, b) => a.fecha.getTime() - b.fecha.getTime() || a.indice - b.indice)

  const grupos: GrupoDiaComentarios[] = []
  for (const { comentario, fecha } of ordenados) {
    const clave = claveDiaLocal(fecha)
    let grupo = grupos[grupos.length - 1]
    if (!grupo || grupo.clave !== clave) {
      grupo = { clave, etiqueta: formatearDiaComentario(fecha, hoy), comentarios: [] }
      grupos.push(grupo)
    }
    grupo.comentarios.push({ ...comentario, hora: formatearHoraComentario(comentario.creado) })
  }
  return grupos
}
