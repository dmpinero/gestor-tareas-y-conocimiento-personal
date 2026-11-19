import { describe, expect, it } from 'vitest'

import { CLAVE_SIN_SUBESTADO, agruparPorSubestado, claveSubestado } from '@/lib/agruparPorSubestado'

function tarea(id: number, subestado: string | null) {
  return { id, subestado }
}

describe('agruparPorSubestado', () => {
  it('sin tareas no devuelve ningún grupo', () => {
    expect(agruparPorSubestado([])).toEqual([])
  })

  it('ordena los grupos por nombre como el catálogo y deja "Sin subestado" al final', () => {
    const grupos = agruparPorSubestado([
      tarea(1, null),
      tarea(2, 'Revisión'),
      tarea(3, 'ánimo'),
      tarea(4, 'Bloqueado'),
      tarea(5, 'en espera'),
    ])

    expect(grupos.map((grupo) => grupo.subestado)).toEqual([
      'ánimo',
      'Bloqueado',
      'en espera',
      'Revisión',
      null,
    ])
    expect(grupos[grupos.length - 1]?.clave).toBe(CLAVE_SIN_SUBESTADO)
  })

  it('mantiene dentro de cada grupo el orden de entrada', () => {
    const grupos = agruparPorSubestado([
      tarea(3, 'B'),
      tarea(1, null),
      tarea(5, 'A'),
      tarea(2, 'B'),
      tarea(4, null),
      tarea(6, 'B'),
    ])

    expect(grupos.map((grupo) => [grupo.clave, grupo.tareas.map((t) => t.id)])).toEqual([
      [claveSubestado('A'), [5]],
      [claveSubestado('B'), [3, 2, 6]],
      [CLAVE_SIN_SUBESTADO, [1, 4]],
    ])
  })

  it('no muestra grupos vacíos: sin tareas sin subestado no hay grupo "Sin subestado"', () => {
    const grupos = agruparPorSubestado([tarea(1, 'A')])

    expect(grupos).toEqual([
      { clave: claveSubestado('A'), subestado: 'A', tareas: [tarea(1, 'A')] },
    ])
  })

  it('la clave de un subestado nunca coincide con la de "Sin subestado"', () => {
    expect(claveSubestado('sin')).not.toBe(CLAVE_SIN_SUBESTADO)
    expect(claveSubestado(null)).toBe(CLAVE_SIN_SUBESTADO)
  })
})
