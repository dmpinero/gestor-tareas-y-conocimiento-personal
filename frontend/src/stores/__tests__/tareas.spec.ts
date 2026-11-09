import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clienteApi } from '@/api/cliente'
import { useTiendaTareas } from '@/stores/tareas'

vi.mock('@/api/cliente', () => ({
  clienteApi: {
    obtener: vi.fn<(...args: unknown[]) => unknown>(),
    crear: vi.fn<(...args: unknown[]) => unknown>(),
  },
}))

const tareaEjemplo = {
  id: 1,
  nombre: 'Escribir informe',
  prioridad: null,
  descripcion: 'Informe trimestral',
}

describe('useTiendaTareas', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('carga las tareas desde GET /tareas', async () => {
    vi.mocked(clienteApi.obtener).mockResolvedValue([tareaEjemplo])

    const tienda = useTiendaTareas()
    await tienda.cargar()

    expect(clienteApi.obtener).toHaveBeenCalledWith('/tareas')
    expect(tienda.tareas).toEqual([tareaEjemplo])
    expect(tienda.cargando).toBe(false)
    expect(tienda.error).toBeNull()
  })

  it('guarda el mensaje de error si falla la carga', async () => {
    vi.mocked(clienteApi.obtener).mockRejectedValue(new Error('fallo de red'))

    const tienda = useTiendaTareas()
    await tienda.cargar()

    expect(tienda.error).toBe('fallo de red')
    expect(tienda.tareas).toEqual([])
    expect(tienda.cargando).toBe(false)
  })

  it('envía la tarea a POST /tareas y añade la creada a la lista', async () => {
    vi.mocked(clienteApi.crear).mockResolvedValue(tareaEjemplo)

    const tienda = useTiendaTareas()
    const datos = { nombre: 'Escribir informe', prioridad: null, descripcion: 'Informe trimestral' }
    await tienda.crear(datos)

    expect(clienteApi.crear).toHaveBeenCalledWith('/tareas', datos)
    expect(tienda.tareas).toEqual([tareaEjemplo])
  })

  it('propaga el error de la API al crear y no altera la lista', async () => {
    vi.mocked(clienteApi.crear).mockRejectedValue(new Error('datos inválidos'))

    const tienda = useTiendaTareas()
    await expect(tienda.crear({ nombre: 'x', prioridad: 3, descripcion: 'y' })).rejects.toThrow(
      'datos inválidos',
    )
    expect(tienda.tareas).toEqual([])
  })
})
