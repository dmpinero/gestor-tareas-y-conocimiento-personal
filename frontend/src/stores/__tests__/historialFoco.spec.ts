import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clienteApi } from '@/api/cliente'
import type { EntradaHistorialFoco } from '@/api/tipos'
import { useTiendaHistorialFoco } from '@/stores/historialFoco'

vi.mock('@/api/cliente', async (original) => ({
  ...(await original()),
  clienteApi: { obtener: vi.fn<(...args: unknown[]) => unknown>() },
}))

const ENTRADA: EntradaHistorialFoco = {
  id: 1,
  tarea_id: 7,
  tarea_nombre: 'Portal',
  subtarea_id: null,
  subtarea_nombre: null,
  desde: '2026-11-24T09:00:00Z',
  hasta: null,
}

describe('useTiendaHistorialFoco', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('cargarDia pide el día local, de medianoche a medianoche, en UTC', async () => {
    vi.mocked(clienteApi.obtener).mockResolvedValue([ENTRADA])
    const tienda = useTiendaHistorialFoco()

    expect(await tienda.cargarDia('2026-11-24')).toBe(true)

    const consulta = new URLSearchParams({
      desde: new Date(2026, 10, 24).toISOString(),
      hasta: new Date(2026, 10, 25).toISOString(),
    })
    expect(clienteApi.obtener).toHaveBeenCalledWith(`/foco/historial?${consulta}`)
    expect(tienda.entradas).toEqual([ENTRADA])
    expect(tienda.cargando).toBe(false)
  })

  it('cargarTodo pide el historial completo sin parámetros', async () => {
    vi.mocked(clienteApi.obtener).mockResolvedValue([ENTRADA])
    const tienda = useTiendaHistorialFoco()

    await tienda.cargarTodo()

    expect(clienteApi.obtener).toHaveBeenCalledWith('/foco/historial')
    expect(tienda.entradas).toEqual([ENTRADA])
  })

  it('con un fallo guarda el error y vacía las entradas', async () => {
    vi.mocked(clienteApi.obtener).mockRejectedValue(new Error('caído'))
    const tienda = useTiendaHistorialFoco()
    tienda.entradas = [ENTRADA]

    expect(await tienda.cargarTodo()).toBe(false)

    expect(tienda.error).toBe('caído')
    expect(tienda.entradas).toEqual([])
    expect(tienda.cargando).toBe(false)
  })

  it('si llegan dos respuestas desordenadas se queda con la última pedida', async () => {
    let resolverPrimera: (valor: unknown) => void = () => {}
    vi.mocked(clienteApi.obtener)
      .mockImplementationOnce(() => new Promise((r) => (resolverPrimera = r)))
      .mockResolvedValueOnce([ENTRADA])
    const tienda = useTiendaHistorialFoco()

    const primera = tienda.cargarDia('2026-11-23')
    await tienda.cargarTodo()
    resolverPrimera([])
    await primera

    expect(tienda.entradas).toEqual([ENTRADA])
  })
})
