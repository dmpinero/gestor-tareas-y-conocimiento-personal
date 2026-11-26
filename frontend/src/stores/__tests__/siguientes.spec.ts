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
})
