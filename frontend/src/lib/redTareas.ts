// Red de tareas: cada tarea es un nodo y cada etiqueta, persona, subestado u
// oportunidad que comparten dos o más tareas es un nodo propio al que se unen
// (uno con una sola tarea no relaciona nada). Las tareas relacionadas
// (`vinculadas`) se unen directamente entre sí. Función pura y determinista:
// el orden de entrada no cambia el resultado, para que la disposición tampoco.
import type { Tarea } from '@/api/tipos'

/** Uniones que se pueden mostrar u ocultar en la red. */
export type TipoUnion = 'relacionadas' | 'etiquetas' | 'personas' | 'subestados' | 'oportunidades'

export const TIPOS_UNION: readonly TipoUnion[] = [
  'relacionadas',
  'etiquetas',
  'personas',
  'subestados',
  'oportunidades',
]

/** Tipo de los nodos propios (los que no son tareas). */
export type TipoNodoPropio = 'etiqueta' | 'persona' | 'subestado' | 'oportunidad'

export const TIPOS_NODO_PROPIO: readonly TipoNodoPropio[] = [
  'etiqueta',
  'persona',
  'subestado',
  'oportunidad',
]

export interface NodoTarea {
  /** `tarea:<id>`. */
  id: string
  clase: 'tarea'
  tarea: Tarea
}

export interface NodoPropio {
  /** `<tipo>:<nombre>`, p. ej. `etiqueta:Cliente X`. */
  id: string
  clase: TipoNodoPropio
  nombre: string
  /** Ids de las tareas que une, en orden ascendente. */
  tareas: number[]
}

export type NodoRed = NodoTarea | NodoPropio

export interface AristaRed {
  origen: string
  destino: string
  tipo: TipoUnion
}

export interface Red {
  /** Primero las tareas (por id) y después los nodos propios por tipo y nombre. */
  nodos: NodoRed[]
  aristas: AristaRed[]
}

const UNION_DE_TIPO: Record<TipoNodoPropio, TipoUnion> = {
  etiqueta: 'etiquetas',
  persona: 'personas',
  subestado: 'subestados',
  oportunidad: 'oportunidades',
}

function nombresDe(tarea: Tarea, tipo: TipoNodoPropio): string[] {
  switch (tipo) {
    case 'etiqueta':
      return tarea.etiquetas
    case 'persona':
      return tarea.asignados
    case 'subestado':
      return tarea.subestado ? [tarea.subestado] : []
    case 'oportunidad':
      return tarea.oportunidad?.codigo ? [tarea.oportunidad.codigo] : []
  }
}

export function idTarea(id: number): string {
  return `tarea:${id}`
}

function comparar(a: string, b: string): number {
  return a.localeCompare(b, 'es') || (a < b ? -1 : a > b ? 1 : 0)
}

export function construirRed(tareas: readonly Tarea[], uniones: Iterable<TipoUnion>): Red {
  const activas = new Set(uniones)
  const ordenadas = [...tareas].sort((a, b) => a.id - b.id)
  const presentes = new Set(ordenadas.map((tarea) => tarea.id))
  const nodos: NodoRed[] = ordenadas.map((tarea) => ({
    id: idTarea(tarea.id),
    clase: 'tarea',
    tarea,
  }))
  const aristas: AristaRed[] = []

  if (activas.has('relacionadas')) {
    for (const tarea of ordenadas) {
      const otras = [...new Set(tarea.vinculadas)].sort((a, b) => a - b)
      for (const otra of otras) {
        // Cada par una sola vez (desde la de menor id) y solo si ambas se ven.
        if (otra <= tarea.id || !presentes.has(otra)) continue
        aristas.push({ origen: idTarea(tarea.id), destino: idTarea(otra), tipo: 'relacionadas' })
      }
    }
  }

  for (const tipo of TIPOS_NODO_PROPIO) {
    const union = UNION_DE_TIPO[tipo]
    if (!activas.has(union)) continue
    const porNombre = new Map<string, number[]>()
    for (const tarea of ordenadas) {
      for (const nombre of new Set(nombresDe(tarea, tipo))) {
        porNombre.set(nombre, [...(porNombre.get(nombre) ?? []), tarea.id])
      }
    }
    const nombres = [...porNombre.keys()].sort(comparar)
    for (const nombre of nombres) {
      const idsTareas = porNombre.get(nombre)!
      if (idsTareas.length < 2) continue
      const id = `${tipo}:${nombre}`
      nodos.push({ id, clase: tipo, nombre, tareas: idsTareas })
      for (const idDeTarea of idsTareas) {
        aristas.push({ origen: idTarea(idDeTarea), destino: id, tipo: union })
      }
    }
  }

  return { nodos, aristas }
}

/** Vecinos de cada nodo (en ambos sentidos), en el orden de las aristas. */
export function vecinosDe(red: Red): Map<string, Set<string>> {
  const vecinos = new Map<string, Set<string>>(red.nodos.map((nodo) => [nodo.id, new Set()]))
  for (const { origen, destino } of red.aristas) {
    vecinos.get(origen)?.add(destino)
    vecinos.get(destino)?.add(origen)
  }
  return vecinos
}
