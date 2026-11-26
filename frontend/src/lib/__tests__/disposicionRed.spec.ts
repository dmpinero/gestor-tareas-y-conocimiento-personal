import { describe, expect, it } from 'vitest'

import { disponerRed, MARGEN_CAJA } from '../disposicionRed'
import type { Red } from '../redTareas'

function redDe(idsTareas: number[], aristas: [string, string][] = []): Red {
  return {
    nodos: idsTareas.map((id) => ({
      id: `tarea:${id}`,
      clase: 'tarea' as const,
      tarea: { id } as never,
    })),
    aristas: aristas.map(([origen, destino]) => ({ origen, destino, tipo: 'relacionadas' })),
  }
}

const RED = redDe(
  [1, 2, 3, 4, 5],
  [
    ['tarea:1', 'tarea:2'],
    ['tarea:2', 'tarea:3'],
    ['tarea:4', 'tarea:5'],
  ],
)

describe('disponerRed', () => {
  it('da las mismas posiciones para la misma entrada', () => {
    const una = disponerRed(RED)
    const otra = disponerRed(structuredClone(RED))
    expect([...otra.posiciones.entries()]).toEqual([...una.posiciones.entries()])
    expect(otra.caja).toEqual(una.caja)
  })

  it('da una posición finita a cada nodo', () => {
    const { posiciones } = disponerRed(RED)
    expect([...posiciones.keys()]).toEqual(RED.nodos.map((nodo) => nodo.id))
    for (const { x, y } of posiciones.values()) {
      expect(Number.isFinite(x)).toBe(true)
      expect(Number.isFinite(y)).toBe(true)
    }
  })

  it('acerca los nodos unidos más que los que no lo están', () => {
    const { posiciones } = disponerRed(RED)
    const distancia = (a: string, b: string) => {
      const p = posiciones.get(a)!
      const q = posiciones.get(b)!
      return Math.hypot(p.x - q.x, p.y - q.y)
    }
    expect(distancia('tarea:1', 'tarea:2')).toBeLessThan(distancia('tarea:1', 'tarea:5'))
  })

  it('la caja contiene todos los nodos con su margen', () => {
    const { posiciones, caja } = disponerRed(RED)
    for (const { x, y } of posiciones.values()) {
      expect(x - MARGEN_CAJA).toBeGreaterThanOrEqual(caja.x - 1e-9)
      expect(y - MARGEN_CAJA).toBeGreaterThanOrEqual(caja.y - 1e-9)
      expect(x + MARGEN_CAJA).toBeLessThanOrEqual(caja.x + caja.ancho + 1e-9)
      expect(y + MARGEN_CAJA).toBeLessThanOrEqual(caja.y + caja.alto + 1e-9)
    }
  })

  it('sin nodos da una caja por defecto y no falla', () => {
    const { posiciones, caja } = disponerRed({ nodos: [], aristas: [] })
    expect(posiciones.size).toBe(0)
    expect(caja.ancho).toBeGreaterThan(0)
    expect(caja.alto).toBeGreaterThan(0)
  })

  it('no modifica la red recibida', () => {
    const copia = structuredClone(RED)
    disponerRed(RED)
    expect(RED).toEqual(copia)
  })
})
