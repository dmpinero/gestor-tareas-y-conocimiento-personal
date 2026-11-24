import type { Foco } from '@/api/tipos'

const MS_POR_MINUTO = 60_000

/**
 * Tiempo que se lleva trabajando desde `desde` (ISO 8601; sin zona se lee en
 * hora local) hasta `ahora`: `< 1 min`, `N min`, `N h M min`, o `N h` si los
 * minutos son 0.
 */
export function formatearTiempoFoco(desde: string, ahora: Date): string {
  const minutos = Math.floor((ahora.getTime() - new Date(desde).getTime()) / MS_POR_MINUTO)
  if (!(minutos >= 1)) return '< 1 min'
  if (minutos < 60) return `${minutos} min`
  const horas = Math.floor(minutos / 60)
  const resto = minutos % 60
  return resto === 0 ? `${horas} h` : `${horas} h ${resto} min`
}

/** Nombre del elemento en foco: la tarea, o `Tarea › Subtarea`. */
export function textoFoco(foco: Foco): string {
  return foco.subtarea_id === null || foco.subtarea_nombre === null
    ? foco.tarea_nombre
    : `${foco.tarea_nombre} › ${foco.subtarea_nombre}`
}
