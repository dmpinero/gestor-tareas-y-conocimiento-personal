import { describe, expect, it } from 'vitest'

import type { Tarea } from '@/api/tipos'
import { TIPOS_UNION, construirRed, vecinosDe, type TipoUnion } from '../redTareas'

function tarea(id: number, cambios: Partial<Tarea> = {}): Tarea {
  return {
    id,
    nombre: `Tarea ${id}`,
    prioridad: null,
    descripcion: '',
    fecha_creacion: '2026-11-10T09:30:00',
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
    ...cambios,
  }
}

function oportunidad(codigo: string): Tarea['oportunidad'] {
  return { codigo, descripcion: null, observaciones: null }
}

const TODAS: readonly TipoUnion[] = TIPOS_UNION

function ids(red: ReturnType<typeof construirRed>): string[] {
  return red.nodos.map((nodo) => nodo.id)
}

function aristas(red: ReturnType<typeof construirRed>): string[] {
  return red.aristas.map((arista) => `${arista.origen}|${arista.destino}`)
}

describe('construirRed', () => {
  it('crea un nodo por tarea, ordenado por id, aunque no tenga uniones', () => {
    const red = construirRed([tarea(3), tarea(1), tarea(2)], TODAS)
    expect(ids(red)).toEqual(['tarea:1', 'tarea:2', 'tarea:3'])
    expect(red.aristas).toEqual([])
    const nodo = red.nodos[0]!
    expect(nodo.clase).toBe('tarea')
    if (nodo.clase === 'tarea') expect(nodo.tarea.id).toBe(1)
  })

  it('crea un nodo de etiqueta solo si une a 2 o más tareas', () => {
    const red = construirRed(
      [
        tarea(1, { etiquetas: ['Cliente X', 'Sola'] }),
        tarea(2, { etiquetas: ['Cliente X'] }),
        tarea(3, { etiquetas: ['Cliente X'] }),
      ],
      TODAS,
    )
    expect(ids(red)).toEqual(['tarea:1', 'tarea:2', 'tarea:3', 'etiqueta:Cliente X'])
    expect(aristas(red)).toEqual([
      'tarea:1|etiqueta:Cliente X',
      'tarea:2|etiqueta:Cliente X',
      'tarea:3|etiqueta:Cliente X',
    ])
    const nodo = red.nodos[3]!
    expect(nodo).toMatchObject({ clase: 'etiqueta', nombre: 'Cliente X', tareas: [1, 2, 3] })
    expect(red.aristas[0]!.tipo).toBe('etiquetas')
  })

  it('une por personas, subestados y oportunidades (código)', () => {
    const red = construirRed(
      [
        tarea(1, { asignados: ['Ana'], subestado: 'Esperando', oportunidad: oportunidad('OP1') }),
        tarea(2, { asignados: ['Ana'], subestado: 'Esperando', oportunidad: oportunidad('OP1') }),
      ],
      TODAS,
    )
    expect(ids(red)).toEqual([
      'tarea:1',
      'tarea:2',
      'persona:Ana',
      'subestado:Esperando',
      'oportunidad:OP1',
    ])
    expect(red.aristas.map((arista) => arista.tipo)).toEqual([
      'personas',
      'personas',
      'subestados',
      'subestados',
      'oportunidades',
      'oportunidades',
    ])
  })

  it.each<[TipoUnion, Partial<Tarea>, string]>([
    ['etiquetas', { etiquetas: ['E'] }, 'etiqueta:E'],
    ['personas', { asignados: ['Ana'] }, 'persona:Ana'],
    ['subestados', { subestado: 'S' }, 'subestado:S'],
    ['oportunidades', { oportunidad: oportunidad('OP') }, 'oportunidad:OP'],
  ])('sin la unión «%s» no crea sus nodos', (union, cambios, idNodo) => {
    const tareas = [tarea(1, cambios), tarea(2, cambios)]
    expect(ids(construirRed(tareas, TODAS))).toContain(idNodo)
    const red = construirRed(
      tareas,
      TODAS.filter((otra) => otra !== union),
    )
    expect(ids(red)).not.toContain(idNodo)
    expect(red.aristas).toEqual([])
  })

  it('une las tareas relacionadas entre sí una sola vez, solo si ambas están en la lista', () => {
    const tareas = [
      tarea(2, { vinculadas: [1, 9] }),
      tarea(1, { vinculadas: [2, 3] }),
      tarea(3, { vinculadas: [1] }),
    ]
    const red = construirRed(tareas, TODAS)
    expect(aristas(red)).toEqual(['tarea:1|tarea:2', 'tarea:1|tarea:3'])
    expect(red.aristas.every((arista) => arista.tipo === 'relacionadas')).toBe(true)
    expect(construirRed(tareas, ['etiquetas']).aristas).toEqual([])
  })

  it('es determinista aunque cambie el orden de entrada', () => {
    const a = tarea(1, { etiquetas: ['b', 'a'], asignados: ['Zoe', 'Ana'], vinculadas: [2] })
    const b = tarea(2, { etiquetas: ['a', 'b'], asignados: ['Ana', 'Zoe'], vinculadas: [1] })
    const uno = construirRed([a, b], TODAS)
    const otro = construirRed([b, a], TODAS)
    expect(otro).toEqual(uno)
    expect(ids(uno)).toEqual([
      'tarea:1',
      'tarea:2',
      'etiqueta:a',
      'etiqueta:b',
      'persona:Ana',
      'persona:Zoe',
    ])
  })
})

describe('vecinosDe', () => {
  it('devuelve los vecinos de cada nodo en ambos sentidos', () => {
    const red = construirRed(
      [
        tarea(1, { etiquetas: ['E'], vinculadas: [2] }),
        tarea(2, { etiquetas: ['E'], vinculadas: [1] }),
      ],
      TODAS,
    )
    const vecinos = vecinosDe(red)
    expect([...vecinos.get('tarea:1')!]).toEqual(['tarea:2', 'etiqueta:E'])
    expect([...vecinos.get('etiqueta:E')!]).toEqual(['tarea:1', 'tarea:2'])
  })

  it('una tarea sin uniones no tiene vecinos', () => {
    expect(vecinosDe(construirRed([tarea(1)], TODAS)).get('tarea:1')!.size).toBe(0)
  })
})
