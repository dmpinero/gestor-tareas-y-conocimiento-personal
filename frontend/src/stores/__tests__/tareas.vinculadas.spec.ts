import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clienteApi } from '@/api/cliente'
import type { Tarea } from '@/api/tipos'
import { useTiendaTareas } from '@/stores/tareas'

vi.mock('@/api/cliente', () => ({
  clienteApi: {
    obtener: vi.fn<(...args: unknown[]) => unknown>(),
    crear: vi.fn<(...args: unknown[]) => unknown>(),
    actualizar: vi.fn<(...args: unknown[]) => unknown>(),
    parchear: vi.fn<(...args: unknown[]) => unknown>(),
    eliminar: vi.fn<(...args: unknown[]) => unknown>(),
  },
}))

function tarea(id: number, vinculadas: number[] = []): Tarea {
  return {
    id,
    nombre: `Tarea ${id}`,
    prioridad: null,
    descripcion: '',
    fecha_creacion: '2026-11-20T10:00:00',
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
    vinculadas,
  }
}

async function tiendaCon(tareas: Tarea[]): Promise<ReturnType<typeof useTiendaTareas>> {
  vi.mocked(clienteApi.obtener).mockResolvedValue(structuredClone(tareas))
  const tienda = useTiendaTareas()
  await tienda.cargar()
  return tienda
}

function vinculadasDe(tienda: ReturnType<typeof useTiendaTareas>, id: number): number[] {
  return tienda.tareas.find((t) => t.id === id)!.vinculadas
}

describe('useTiendaTareas: tareas vinculadas', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('vincularTareas envía los ids a POST /tareas/{id}/vinculadas, reemplaza la tarea y añade la vuelta en las otras', async () => {
    const tienda = await tiendaCon([tarea(1), tarea(2, [4]), tarea(3), tarea(4, [2])])
    vi.mocked(clienteApi.crear).mockResolvedValue(tarea(1, [2, 3]))

    const resultado = await tienda.vincularTareas(1, [2, 3])

    expect(clienteApi.crear).toHaveBeenCalledWith('/tareas/1/vinculadas', { ids: [2, 3] })
    expect(resultado).toBe(true)
    expect(tienda.error).toBeNull()
    expect(vinculadasDe(tienda, 1)).toEqual([2, 3])
    // La vuelta se guarda en orden ascendente, junto a las que ya tenía.
    expect(vinculadasDe(tienda, 2)).toEqual([1, 4])
    expect(vinculadasDe(tienda, 3)).toEqual([1])
    expect(vinculadasDe(tienda, 4)).toEqual([2])
  })

  it('desvincularTarea llama a DELETE /tareas/{id}/vinculadas/{otra} y quita la relación en ambos sentidos', async () => {
    const tienda = await tiendaCon([tarea(1, [2, 3]), tarea(2, [1]), tarea(3, [1])])
    vi.mocked(clienteApi.eliminar).mockResolvedValue(tarea(1, [3]))

    const resultado = await tienda.desvincularTarea(1, 2)

    expect(clienteApi.eliminar).toHaveBeenCalledWith('/tareas/1/vinculadas/2')
    expect(resultado).toBe(true)
    expect(vinculadasDe(tienda, 1)).toEqual([3])
    expect(vinculadasDe(tienda, 2)).toEqual([])
    expect(vinculadasDe(tienda, 3)).toEqual([1])
  })

  it('si vincular falla guarda el mensaje, devuelve false y no altera la lista', async () => {
    const tareas = [tarea(1), tarea(2)]
    const tienda = await tiendaCon(tareas)
    vi.mocked(clienteApi.crear).mockRejectedValue(new Error('No existe la tarea con id 9'))

    expect(await tienda.vincularTareas(1, [2])).toBe(false)
    expect(tienda.error).toBe('No existe la tarea con id 9')
    expect(tienda.tareas).toEqual(tareas)
  })

  it('si desvincular falla guarda el mensaje, devuelve false y no altera la lista', async () => {
    const tareas = [tarea(1, [2]), tarea(2, [1])]
    const tienda = await tiendaCon(tareas)
    vi.mocked(clienteApi.eliminar).mockRejectedValue(new Error('fallo de red'))

    expect(await tienda.desvincularTarea(1, 2)).toBe(false)
    expect(tienda.error).toBe('fallo de red')
    expect(tienda.tareas).toEqual(tareas)
  })
})
