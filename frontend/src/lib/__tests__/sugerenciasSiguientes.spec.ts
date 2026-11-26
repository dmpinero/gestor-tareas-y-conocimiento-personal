import { describe, expect, it } from 'vitest'

import type { Tarea } from '@/api/tipos'
import { sugerenciasSiguientes } from '@/lib/sugerenciasSiguientes'

function tarea(id: number, extra: Partial<Tarea> = {}): Tarea {
  return {
    id,
    nombre: `Tarea ${id}`,
    prioridad: null,
    descripcion: '',
    fecha_creacion: '2026-11-10T09:00:00',
    fecha_vencimiento: null,
    etiquetas: [],
    asignados: [],
    tipo: null,
    oportunidad: null,
    completada: false,
    subtareas: [],
    grupo_estados: null,
    estado: null,
    workflow: null,
    subestado: null,
    congelada_en: null,
    hibernada_desde: null,
    vinculadas: [],
    ...extra,
  }
}

const ids = (tareas: Tarea[]) => tareas.map((t) => t.id)

describe('sugerenciasSiguientes', () => {
  it('ordena por vencimiento: vencido o más cercano primero, sin vencimiento al final', () => {
    const tareas = [
      tarea(1),
      tarea(2, { fecha_vencimiento: '2026-12-10T10:00:00' }),
      tarea(3, { fecha_vencimiento: '2026-11-01T10:00:00' }),
      tarea(4, { fecha_vencimiento: '2026-11-30T10:00:00' }),
    ]

    expect(ids(sugerenciasSiguientes(tareas, [], null))).toEqual([3, 4, 2, 1])
  })

  it('con el mismo vencimiento ordena por prioridad (1 primero, sin prioridad al final)', () => {
    const vence = '2026-12-01T10:00:00'
    const tareas = [
      tarea(1, { fecha_vencimiento: vence }),
      tarea(2, { fecha_vencimiento: vence, prioridad: 3 }),
      tarea(3, { fecha_vencimiento: vence, prioridad: 1 }),
    ]

    expect(ids(sugerenciasSiguientes(tareas, [], null))).toEqual([3, 2, 1])
  })

  it('después ordena por fecha de creación (más antigua primero) y por id', () => {
    const tareas = [
      tarea(5, { fecha_creacion: '2026-11-10T09:00:00' }),
      tarea(4, { fecha_creacion: '2026-11-10T09:00:00' }),
      tarea(3, { fecha_creacion: '2026-10-01T09:00:00' }),
    ]

    expect(ids(sugerenciasSiguientes(tareas, [], null))).toEqual([3, 4, 5])
  })

  it('excluye completadas, hibernadas, las de la cola y la del foco', () => {
    const tareas = [
      tarea(1, { completada: true }),
      tarea(2, { hibernada_desde: '2026-11-20T10:00:00Z' }),
      tarea(3),
      tarea(4),
      tarea(5),
    ]

    expect(ids(sugerenciasSiguientes(tareas, [3], 4))).toEqual([5])
  })

  it('devuelve como mucho 5', () => {
    const tareas = [1, 2, 3, 4, 5, 6, 7].map((id) => tarea(id))

    expect(ids(sugerenciasSiguientes(tareas, [], null))).toEqual([1, 2, 3, 4, 5])
  })

  it('no modifica la lista recibida', () => {
    const tareas = [tarea(2), tarea(1)]

    sugerenciasSiguientes(tareas, [], null)

    expect(ids(tareas)).toEqual([2, 1])
  })
})
