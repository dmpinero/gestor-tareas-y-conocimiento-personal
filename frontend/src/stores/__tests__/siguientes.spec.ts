import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clienteApi } from '@/api/cliente'
import type { Foco, Tarea, TareaSiguiente } from '@/api/tipos'
import { useTiendaFoco } from '@/stores/foco'
import { useTiendaSiguientes } from '@/stores/siguientes'
import { useTiendaTareas } from '@/stores/tareas'

vi.mock('@/api/cliente', async (original) => ({
  ...(await original()),
  clienteApi: {
    obtener: vi.fn<(...args: unknown[]) => unknown>(),
    crear: vi.fn<(...args: unknown[]) => unknown>(),
    actualizar: vi.fn<(...args: unknown[]) => unknown>(),
    parchear: vi.fn<(...args: unknown[]) => unknown>(),
    eliminar: vi.fn<(...args: unknown[]) => unknown>(),
  },
}))

const A: TareaSiguiente = { tarea_id: 1, tarea_nombre: 'A' }
const B: TareaSiguiente = { tarea_id: 2, tarea_nombre: 'B' }
const C: TareaSiguiente = { tarea_id: 3, tarea_nombre: 'C' }

const FOCO: Foco = {
  tarea_id: 1,
  tarea_nombre: 'A',
  subtarea_id: null,
  subtarea_nombre: null,
  desde: '2026-11-26T10:00:00',
}

describe('useTiendaSiguientes', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('cargar pide GET /siguientes y guarda la cola', async () => {
    vi.mocked(clienteApi.obtener).mockResolvedValue([A, B])
    const tienda = useTiendaSiguientes()

    expect(await tienda.cargar()).toBe(true)

    expect(clienteApi.obtener).toHaveBeenCalledWith('/siguientes')
    expect(tienda.cola).toEqual([A, B])
  })

  it('cargar con un fallo guarda el error, devuelve false y conserva la cola', async () => {
    vi.mocked(clienteApi.obtener).mockRejectedValue(new Error('caído'))
    const tienda = useTiendaSiguientes()
    tienda.cola = [A]

    expect(await tienda.cargar()).toBe(false)

    expect(tienda.error).toBe('caído')
    expect(tienda.cola).toEqual([A])
  })

  it('anadir envía POST /siguientes con el id y guarda la cola devuelta', async () => {
    vi.mocked(clienteApi.crear).mockResolvedValue([A, B])
    const tienda = useTiendaSiguientes()
    tienda.cola = [A]

    expect(await tienda.anadir(2)).toBe(true)

    expect(clienteApi.crear).toHaveBeenCalledWith('/siguientes', { tarea_id: 2 })
    expect(tienda.cola).toEqual([A, B])
    expect(tienda.estaEnCola(2)).toBe(true)
    expect(tienda.estaEnCola(9)).toBe(false)
  })

  it('anadir con un fallo guarda el error y conserva la cola', async () => {
    vi.mocked(clienteApi.crear).mockRejectedValue(new Error('Completada'))
    const tienda = useTiendaSiguientes()
    tienda.cola = [A]

    expect(await tienda.anadir(2)).toBe(false)

    expect(tienda.error).toBe('Completada')
    expect(tienda.cola).toEqual([A])
  })

  it('anadirVarias las añade una a una, en el orden dado', async () => {
    vi.mocked(clienteApi.crear).mockResolvedValueOnce([A, C]).mockResolvedValueOnce([A, C, B])
    const tienda = useTiendaSiguientes()
    tienda.cola = [A]

    expect(await tienda.anadirVarias([3, 2])).toBe(true)

    expect(vi.mocked(clienteApi.crear).mock.calls).toEqual([
      ['/siguientes', { tarea_id: 3 }],
      ['/siguientes', { tarea_id: 2 }],
    ])
    expect(tienda.cola).toEqual([A, C, B])
  })

  it('anadirVarias se detiene en el primer fallo y guarda el error', async () => {
    vi.mocked(clienteApi.crear)
      .mockResolvedValueOnce([A, C])
      .mockRejectedValueOnce(new Error('Tarea completada'))
    const tienda = useTiendaSiguientes()
    tienda.cola = [A]

    expect(await tienda.anadirVarias([3, 2, 4])).toBe(false)

    expect(clienteApi.crear).toHaveBeenCalledTimes(2)
    expect(tienda.cola).toEqual([A, C])
    expect(tienda.error).toBe('Tarea completada')
  })

  it('reordenar envía PUT /siguientes con los ids', async () => {
    vi.mocked(clienteApi.actualizar).mockResolvedValue([B, A])
    const tienda = useTiendaSiguientes()
    tienda.cola = [A, B]

    expect(await tienda.reordenar([2, 1])).toBe(true)

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/siguientes', { ids: [2, 1] })
    expect(tienda.cola).toEqual([B, A])
  })

  it('subir y bajar intercambian con la vecina; en los extremos no piden nada', async () => {
    vi.mocked(clienteApi.actualizar).mockImplementation(async (_ruta, cuerpo) =>
      (cuerpo as { ids: number[] }).ids.map((id) => [A, B, C].find((t) => t.tarea_id === id)!),
    )
    const tienda = useTiendaSiguientes()
    tienda.cola = [A, B, C]

    await tienda.subir(2)
    expect(clienteApi.actualizar).toHaveBeenLastCalledWith('/siguientes', { ids: [2, 1, 3] })
    await tienda.bajar(2)
    expect(clienteApi.actualizar).toHaveBeenLastCalledWith('/siguientes', { ids: [1, 2, 3] })

    vi.mocked(clienteApi.actualizar).mockClear()
    expect(await tienda.subir(1)).toBe(true)
    expect(await tienda.bajar(3)).toBe(true)
    expect(clienteApi.actualizar).not.toHaveBeenCalled()
  })

  it('moverA lleva la tarea a otra posición con PUT /siguientes; a la misma no pide nada', async () => {
    vi.mocked(clienteApi.actualizar).mockImplementation(async (_ruta, cuerpo) =>
      (cuerpo as { ids: number[] }).ids.map((id) => [A, B, C].find((t) => t.tarea_id === id)!),
    )
    const tienda = useTiendaSiguientes()
    tienda.cola = [A, B, C]

    expect(await tienda.moverA(3, 0)).toBe(true)
    expect(clienteApi.actualizar).toHaveBeenLastCalledWith('/siguientes', { ids: [3, 1, 2] })
    expect(tienda.cola).toEqual([C, A, B])
    await tienda.moverA(3, 2)
    expect(clienteApi.actualizar).toHaveBeenLastCalledWith('/siguientes', { ids: [1, 2, 3] })

    vi.mocked(clienteApi.actualizar).mockClear()
    expect(await tienda.moverA(2, 1)).toBe(true)
    expect(await tienda.moverA(9, 0)).toBe(true)
    expect(clienteApi.actualizar).not.toHaveBeenCalled()
  })

  it('quitar envía DELETE /siguientes/{id} y guarda la cola devuelta', async () => {
    vi.mocked(clienteApi.eliminar).mockResolvedValue([B])
    const tienda = useTiendaSiguientes()
    tienda.cola = [A, B]

    expect(await tienda.quitar(1)).toBe(true)

    expect(clienteApi.eliminar).toHaveBeenCalledWith('/siguientes/1')
    expect(tienda.cola).toEqual([B])
  })

  it('pasarALaSiguiente fija el foco en la primera y recarga la cola', async () => {
    vi.mocked(clienteApi.actualizar).mockResolvedValue(FOCO)
    vi.mocked(clienteApi.obtener).mockResolvedValue([B])
    const tienda = useTiendaSiguientes()
    tienda.cola = [A, B]

    expect(await tienda.pasarALaSiguiente()).toBe(true)

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/foco', { tarea_id: 1, subtarea_id: null })
    expect(useTiendaFoco().foco).toEqual(FOCO)
    expect(clienteApi.obtener).toHaveBeenCalledWith('/siguientes')
    expect(tienda.cola).toEqual([B])
  })

  it('pasarALaSiguiente con la cola vacía no hace nada y devuelve false', async () => {
    const tienda = useTiendaSiguientes()

    expect(await tienda.pasarALaSiguiente()).toBe(false)

    expect(clienteApi.actualizar).not.toHaveBeenCalled()
  })

  it('pasarALaSiguiente con un fallo del foco guarda el error y conserva la cola', async () => {
    vi.mocked(clienteApi.actualizar).mockRejectedValue(new Error('No existe'))
    const tienda = useTiendaSiguientes()
    tienda.cola = [A, B]

    expect(await tienda.pasarALaSiguiente()).toBe(false)

    expect(tienda.error).toBe('No existe')
    expect(tienda.cola).toEqual([A, B])
    expect(clienteApi.obtener).not.toHaveBeenCalled()
  })

  it('olvidarTarea la quita de la cola sin pedir nada', () => {
    const tienda = useTiendaSiguientes()
    tienda.cola = [A, B]

    tienda.olvidarTarea(1)

    expect(tienda.cola).toEqual([B])
  })

  it('al fijar el foco en una tarea (o subtarea suya) desde la tienda de foco sale de la cola', async () => {
    vi.mocked(clienteApi.actualizar).mockResolvedValue({ ...FOCO, tarea_id: 2, subtarea_id: 20 })
    const tienda = useTiendaSiguientes()
    tienda.cola = [A, B]

    await useTiendaFoco().fijar(2, 20)

    expect(tienda.cola).toEqual([A])
  })

  it('si fijar el foco falla la cola no cambia', async () => {
    vi.mocked(clienteApi.actualizar).mockRejectedValue(new Error('No'))
    const tienda = useTiendaSiguientes()
    tienda.cola = [A, B]

    await useTiendaFoco().fijar(2)

    expect(tienda.cola).toEqual([A, B])
  })

  it('al borrar una tarea desde la tienda de tareas sale de la cola', async () => {
    vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)
    const tienda = useTiendaSiguientes()
    tienda.cola = [A, B]

    await useTiendaTareas().eliminarTarea(1)

    expect(tienda.cola).toEqual([B])
  })

  it('al completar una tarea de la cola sale de ella; al reabrirla se recarga la cola', async () => {
    const tiendaTareas = useTiendaTareas()
    tiendaTareas.tareas = [{ id: 1, completada: false } as Tarea]
    const tienda = useTiendaSiguientes()
    tienda.cola = [A, B]

    vi.mocked(clienteApi.parchear).mockResolvedValue({ id: 1, completada: true } as Tarea)
    await tiendaTareas.alternarCompletada(1)
    expect(tienda.cola).toEqual([B])

    vi.mocked(clienteApi.parchear).mockResolvedValue({ id: 1, completada: false } as Tarea)
    vi.mocked(clienteApi.obtener).mockResolvedValue([A, B])
    await tiendaTareas.alternarCompletada(1)
    await vi.waitFor(() => expect(tienda.cola).toEqual([A, B]))
    expect(clienteApi.obtener).toHaveBeenCalledWith('/siguientes')
  })
  describe('sugerencias elegidas', () => {
    it('cargarElegidas pide GET /sugerencias y las guarda', async () => {
      vi.mocked(clienteApi.obtener).mockResolvedValue([C])
      const tienda = useTiendaSiguientes()

      expect(await tienda.cargarElegidas()).toBe(true)

      expect(clienteApi.obtener).toHaveBeenCalledWith('/sugerencias')
      expect(tienda.elegidas).toEqual([C])
      expect(tienda.estaElegida(3)).toBe(true)
      expect(tienda.estaElegida(1)).toBe(false)
    })

    it('cargarElegidas con un fallo guarda el error y conserva la lista', async () => {
      vi.mocked(clienteApi.obtener).mockRejectedValue(new Error('caído'))
      const tienda = useTiendaSiguientes()
      tienda.elegidas = [C]

      expect(await tienda.cargarElegidas()).toBe(false)

      expect(tienda.error).toBe('caído')
      expect(tienda.elegidas).toEqual([C])
    })

    it('anadirElegida envía POST /sugerencias y la saca de la cola localmente', async () => {
      vi.mocked(clienteApi.crear).mockResolvedValue([C, A])
      const tienda = useTiendaSiguientes()
      tienda.cola = [A, B]
      tienda.elegidas = [C]

      expect(await tienda.anadirElegida(1)).toBe(true)

      expect(clienteApi.crear).toHaveBeenCalledWith('/sugerencias', { tarea_id: 1 })
      expect(tienda.elegidas).toEqual([C, A])
      expect(tienda.cola).toEqual([B])
    })

    it('anadirElegida con un fallo guarda el error y no cambia ninguna lista', async () => {
      vi.mocked(clienteApi.crear).mockRejectedValue(new Error('Completada'))
      const tienda = useTiendaSiguientes()
      tienda.cola = [A, B]
      tienda.elegidas = [C]

      expect(await tienda.anadirElegida(1)).toBe(false)

      expect(tienda.error).toBe('Completada')
      expect(tienda.cola).toEqual([A, B])
      expect(tienda.elegidas).toEqual([C])
    })

    it('anadirElegidas las añade una a una y se detiene en el primer fallo', async () => {
      vi.mocked(clienteApi.crear)
        .mockResolvedValueOnce([B])
        .mockRejectedValueOnce(new Error('No existe'))
      const tienda = useTiendaSiguientes()
      tienda.cola = [A, B]

      expect(await tienda.anadirElegidas([2, 9, 3])).toBe(false)

      expect(vi.mocked(clienteApi.crear).mock.calls).toEqual([
        ['/sugerencias', { tarea_id: 2 }],
        ['/sugerencias', { tarea_id: 9 }],
      ])
      expect(tienda.elegidas).toEqual([B])
      expect(tienda.cola).toEqual([A])
      expect(tienda.error).toBe('No existe')
    })

    it('anadir a la cola una elegida la saca de las elegidas localmente', async () => {
      vi.mocked(clienteApi.crear).mockResolvedValue([A, C])
      const tienda = useTiendaSiguientes()
      tienda.cola = [A]
      tienda.elegidas = [B, C]

      expect(await tienda.anadir(3)).toBe(true)

      expect(clienteApi.crear).toHaveBeenCalledWith('/siguientes', { tarea_id: 3 })
      expect(tienda.cola).toEqual([A, C])
      expect(tienda.elegidas).toEqual([B])
    })

    it('si anadir a la cola falla, las elegidas no cambian', async () => {
      vi.mocked(clienteApi.crear).mockRejectedValue(new Error('No'))
      const tienda = useTiendaSiguientes()
      tienda.elegidas = [C]

      expect(await tienda.anadir(3)).toBe(false)

      expect(tienda.elegidas).toEqual([C])
    })

    it('quitarElegida envía DELETE /sugerencias/{id} y guarda la lista devuelta', async () => {
      vi.mocked(clienteApi.eliminar).mockResolvedValue([C])
      const tienda = useTiendaSiguientes()
      tienda.cola = [A]
      tienda.elegidas = [B, C]

      expect(await tienda.quitarElegida(2)).toBe(true)

      expect(clienteApi.eliminar).toHaveBeenCalledWith('/sugerencias/2')
      expect(tienda.elegidas).toEqual([C])
      expect(tienda.cola).toEqual([A])
    })

    it('quitarElegida con un fallo guarda el error y conserva la lista', async () => {
      vi.mocked(clienteApi.eliminar).mockRejectedValue(new Error('caído'))
      const tienda = useTiendaSiguientes()
      tienda.elegidas = [B, C]

      expect(await tienda.quitarElegida(2)).toBe(false)

      expect(tienda.error).toBe('caído')
      expect(tienda.elegidas).toEqual([B, C])
    })

    it('olvidarTarea la quita también de las elegidas', () => {
      const tienda = useTiendaSiguientes()
      tienda.cola = [A]
      tienda.elegidas = [B, C]

      tienda.olvidarTarea(2)

      expect(tienda.elegidas).toEqual([C])
    })

    it('fijar el foco, borrar o completar una elegida la saca de las elegidas', async () => {
      const tiendaTareas = useTiendaTareas()
      tiendaTareas.tareas = [{ id: 3, completada: false } as Tarea]
      const tienda = useTiendaSiguientes()
      tienda.elegidas = [A, B, C]

      vi.mocked(clienteApi.actualizar).mockResolvedValue({ ...FOCO, tarea_id: 1 })
      await useTiendaFoco().fijar(1)
      expect(tienda.elegidas).toEqual([B, C])

      vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)
      await tiendaTareas.eliminarTarea(2)
      expect(tienda.elegidas).toEqual([C])

      vi.mocked(clienteApi.parchear).mockResolvedValue({ id: 3, completada: true } as Tarea)
      await tiendaTareas.alternarCompletada(3)
      expect(tienda.elegidas).toEqual([])
    })

    it('al reabrir una tarea se recargan también las elegidas', async () => {
      const tiendaTareas = useTiendaTareas()
      tiendaTareas.tareas = [{ id: 3, completada: true } as Tarea]
      const tienda = useTiendaSiguientes()
      vi.mocked(clienteApi.obtener).mockImplementation(async (ruta) =>
        ruta === '/sugerencias' ? [C] : [A],
      )

      vi.mocked(clienteApi.parchear).mockResolvedValue({ id: 3, completada: false } as Tarea)
      await tiendaTareas.alternarCompletada(3)

      await vi.waitFor(() => expect(tienda.elegidas).toEqual([C]))
      expect(tienda.cola).toEqual([A])
    })
  })
})
