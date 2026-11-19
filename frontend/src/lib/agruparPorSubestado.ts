import { compararTexto } from '@/composables/useOrdenacionTabla'

/** Clave del grupo de las tareas sin subestado. */
export const CLAVE_SIN_SUBESTADO = 'sin'

/**
 * Clave estable de un grupo: `'sin'` sin subestado o `'subestado:<nombre>'`.
 * Las tareas guardan el nombre del subestado (no su id); el prefijo evita que
 * un subestado llamado "sin" se confunda con el grupo sin subestado.
 */
export function claveSubestado(subestado: string | null): string {
  return subestado === null ? CLAVE_SIN_SUBESTADO : `subestado:${subestado}`
}

export interface GrupoSubestado<T> {
  clave: string
  /** Nombre del subestado, o `null` en el grupo "Sin subestado". */
  subestado: string | null
  tareas: T[]
}

/**
 * Reparte las tareas (ya filtradas y ordenadas) en grupos por subestado:
 * ordenados por nombre como el catálogo y "Sin subestado" al final. Dentro de
 * cada grupo se conserva el orden de entrada y no hay grupos vacíos.
 */
export function agruparPorSubestado<T extends { subestado: string | null }>(
  tareas: readonly T[],
): GrupoSubestado<T>[] {
  const grupos = new Map<string, GrupoSubestado<T>>()
  for (const tarea of tareas) {
    const subestado = tarea.subestado || null
    const clave = claveSubestado(subestado)
    let grupo = grupos.get(clave)
    if (grupo === undefined) {
      grupo = { clave, subestado, tareas: [] }
      grupos.set(clave, grupo)
    }
    grupo.tareas.push(tarea)
  }
  return [...grupos.values()].sort((a, b) => {
    if (a.subestado === null) return b.subestado === null ? 0 : 1
    if (b.subestado === null) return -1
    return compararTexto(a.subestado, b.subestado)
  })
}
