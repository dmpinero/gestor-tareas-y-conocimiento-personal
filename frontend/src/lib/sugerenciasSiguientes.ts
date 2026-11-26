import type { Tarea } from '@/api/tipos'
import { estaHibernada } from '@/lib/hibernacion'

/** Cuántas sugerencias se muestran como mucho. */
export const MAXIMO_SUGERENCIAS = 5

// `null` va siempre detrás. Las fechas son ISO sin zona del mismo formato, así
// que se comparan como texto.
function compararNulosAlFinal<T extends string | number>(a: T | null, b: T | null): number {
  if (a === b) return 0
  if (a === null) return 1
  if (b === null) return -1
  return a < b ? -1 : 1
}

/**
 * Tareas que se sugieren para la cola de siguientes: hasta 5, ordenadas por
 * vencimiento (el más cercano o vencido primero; sin vencimiento al final),
 * después por prioridad (1 primero; sin prioridad al final), después por fecha
 * de creación (la más antigua primero) y por id. Quedan fuera las completadas,
 * las hibernadas, las que ya están en la cola y la del foco.
 */
export function sugerenciasSiguientes(
  tareas: readonly Tarea[],
  idsCola: readonly number[],
  idFoco: number | null,
): Tarea[] {
  const enCola = new Set(idsCola)
  return tareas
    .filter(
      (tarea) =>
        !tarea.completada && !estaHibernada(tarea) && !enCola.has(tarea.id) && tarea.id !== idFoco,
    )
    .sort(
      (a, b) =>
        compararNulosAlFinal(a.fecha_vencimiento, b.fecha_vencimiento) ||
        compararNulosAlFinal(a.prioridad, b.prioridad) ||
        compararNulosAlFinal(a.fecha_creacion, b.fecha_creacion) ||
        a.id - b.id,
    )
    .slice(0, MAXIMO_SUGERENCIAS)
}
