import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clienteApi } from '@/api/cliente'
import type { Foco } from '@/api/tipos'
import { useTiendaFoco } from '@/stores/foco'

vi.mock('@/api/cliente', async (original) => ({
  ...(await original()),
  clienteApi: {
    obtener: vi.fn<(...args: unknown[]) => unknown>(),
    actualizar: vi.fn<(...args: unknown[]) => unknown>(),
    eliminar: vi.fn<(...args: unknown[]) => unknown>(),
  },
}))

const FOCO_TAREA: Foco = {
  tarea_id: 1,
  tarea_nombre: 'Migración portal',
  subtarea_id: null,
  subtarea_nombre: null,
  desde: '2026-11-24T10:00:00',
}

const FOCO_SUBTAREA: Foco = {
  tarea_id: 1,
  tarea_nombre: 'Migración portal',
  subtarea_id: 20,
  subtarea_nombre: 'Probar login',
  desde: '2026-11-24T11:00:00',
}

describe('useTiendaFoco', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('cargar pide GET /foco y guarda el foco', async () => {
    vi.mocked(clienteApi.obtener).mockResolvedValue(FOCO_TAREA)
    const tienda = useTiendaFoco()

    await tienda.cargar()

    expect(clienteApi.obtener).toHaveBeenCalledWith('/foco')
    expect(tienda.foco).toEqual(FOCO_TAREA)
  })

  it('cargar deja el foco a null si la API responde null', async () => {
    vi.mocked(clienteApi.obtener).mockResolvedValue(null)
    const tienda = useTiendaFoco()

    await tienda.cargar()

    expect(tienda.foco).toBeNull()
  })

  it('cargar con un fallo guarda el error y conserva el foco', async () => {
    vi.mocked(clienteApi.obtener).mockRejectedValue(new Error('caído'))
    const tienda = useTiendaFoco()
    tienda.foco = FOCO_TAREA

    await tienda.cargar()

    expect(tienda.error).toBe('caído')
    expect(tienda.foco).toEqual(FOCO_TAREA)
  })

  it('fijar envía PUT /foco y sustituye el foco por la respuesta', async () => {
    vi.mocked(clienteApi.actualizar).mockResolvedValue(FOCO_SUBTAREA)
    const tienda = useTiendaFoco()
    tienda.foco = FOCO_TAREA

    const resultado = await tienda.fijar(1, 20)

    expect(resultado).toBe(true)
    expect(clienteApi.actualizar).toHaveBeenCalledWith('/foco', { tarea_id: 1, subtarea_id: 20 })
    expect(tienda.foco).toEqual(FOCO_SUBTAREA)
  })

  it('fijar sin subtarea envía subtarea_id null', async () => {
    vi.mocked(clienteApi.actualizar).mockResolvedValue(FOCO_TAREA)
    const tienda = useTiendaFoco()

    await tienda.fijar(1)

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/foco', { tarea_id: 1, subtarea_id: null })
  })

  it('fijar con un fallo guarda el error, devuelve false y conserva el foco', async () => {
    vi.mocked(clienteApi.actualizar).mockRejectedValue(new Error('No existe'))
    const tienda = useTiendaFoco()
    tienda.foco = FOCO_TAREA

    const resultado = await tienda.fijar(9)

    expect(resultado).toBe(false)
    expect(tienda.error).toBe('No existe')
    expect(tienda.foco).toEqual(FOCO_TAREA)
  })

  it('quitar envía DELETE /foco y deja el foco a null', async () => {
    vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)
    const tienda = useTiendaFoco()
    tienda.foco = FOCO_TAREA

    const resultado = await tienda.quitar()

    expect(resultado).toBe(true)
    expect(clienteApi.eliminar).toHaveBeenCalledWith('/foco')
    expect(tienda.foco).toBeNull()
  })

  it('esTareaEnFoco solo es cierto si el foco es la tarea entera', () => {
    const tienda = useTiendaFoco()

    tienda.foco = FOCO_TAREA
    expect(tienda.esTareaEnFoco(1)).toBe(true)
    expect(tienda.esTareaEnFoco(2)).toBe(false)

    tienda.foco = FOCO_SUBTAREA
    expect(tienda.esTareaEnFoco(1)).toBe(false)
  })

  it('esSubtareaEnFoco y tareaContieneFoco reconocen la subtarea en foco', () => {
    const tienda = useTiendaFoco()
    tienda.foco = FOCO_SUBTAREA

    expect(tienda.esSubtareaEnFoco(20)).toBe(true)
    expect(tienda.esSubtareaEnFoco(21)).toBe(false)
    expect(tienda.tareaContieneFoco(1)).toBe(true)
    expect(tienda.tareaContieneFoco(2)).toBe(false)
  })

  it('olvidarTarea y olvidarSubtarea quitan el foco solo si coincide', () => {
    const tienda = useTiendaFoco()
    tienda.foco = FOCO_SUBTAREA

    tienda.olvidarSubtarea(21)
    expect(tienda.foco).toEqual(FOCO_SUBTAREA)
    tienda.olvidarSubtarea(20)
    expect(tienda.foco).toBeNull()

    tienda.foco = FOCO_TAREA
    tienda.olvidarTarea(2)
    expect(tienda.foco).toEqual(FOCO_TAREA)
    tienda.olvidarTarea(1)
    expect(tienda.foco).toBeNull()
  })
})
