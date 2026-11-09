import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clienteApi } from '@/api/cliente'
import { useTiendaTareas } from '@/stores/tareas'

vi.mock('@/api/cliente', () => ({
  clienteApi: {
    obtener: vi.fn<(...args: unknown[]) => unknown>(),
    crear: vi.fn<(...args: unknown[]) => unknown>(),
    actualizar: vi.fn<(...args: unknown[]) => unknown>(),
  },
}))

const tareaEjemplo = {
  id: 1,
  nombre: 'Escribir informe',
  prioridad: null,
  descripcion: 'Informe trimestral',
  fecha_creacion: '2026-11-09T10:00:00',
  fecha_vencimiento: null,
  etiquetas: ['Backend'],
  asignados: ['Ana'],
}

const ETIQUETAS = [
  { id: 1, nombre: 'Backend' },
  { id: 2, nombre: 'Urgente' },
]
const PERSONAS = [{ id: 1, nombre: 'Ana' }]

// Responde a cada ruta de `GET` con sus datos de ejemplo.
function simularObtener(tareas: unknown[] = [tareaEjemplo]): void {
  vi.mocked(clienteApi.obtener).mockImplementation((ruta) => {
    if (ruta === '/etiquetas') return Promise.resolve(ETIQUETAS)
    if (ruta === '/personas') return Promise.resolve(PERSONAS)
    return Promise.resolve(tareas)
  })
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
    const datos = {
      nombre: 'Escribir informe',
      prioridad: null,
      descripcion: 'Informe trimestral',
      fecha_creacion: '2026-11-09T10:00:00',
      fecha_vencimiento: null,
      etiquetas: ['Backend'],
      asignados: ['Ana'],
    }
    await tienda.crear(datos)

    expect(clienteApi.crear).toHaveBeenCalledWith('/tareas', datos)
    expect(tienda.tareas).toEqual([tareaEjemplo])
  })

  it('propaga el error de la API al crear y no altera la lista', async () => {
    vi.mocked(clienteApi.crear).mockRejectedValue(new Error('datos inválidos'))

    const tienda = useTiendaTareas()
    await expect(
      tienda.crear({
        nombre: 'x',
        prioridad: 3,
        descripcion: 'y',
        fecha_creacion: '2026-11-09T10:00:00',
        fecha_vencimiento: null,
        etiquetas: [],
        asignados: [],
      }),
    ).rejects.toThrow('datos inválidos')
    expect(tienda.tareas).toEqual([])
  })

  it('envía la tarea a PUT /tareas/{id} y reemplaza la actualizada en la lista', async () => {
    const otra = { ...tareaEjemplo, id: 2, nombre: 'Otra' }
    vi.mocked(clienteApi.obtener).mockResolvedValue([tareaEjemplo, otra])
    const actualizada = { ...tareaEjemplo, nombre: 'Informe final', prioridad: 1 }
    vi.mocked(clienteApi.actualizar).mockResolvedValue(actualizada)

    const tienda = useTiendaTareas()
    await tienda.cargar()
    const datos = {
      nombre: 'Informe final',
      prioridad: 1,
      descripcion: 'Informe trimestral',
      fecha_creacion: '2026-11-09T10:00:00',
      fecha_vencimiento: null,
      etiquetas: ['Backend'],
      asignados: ['Ana'],
    }
    await tienda.actualizar(1, datos)

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/tareas/1', datos)
    expect(tienda.tareas).toEqual([actualizada, otra])
  })

  it('propaga el error de la API al actualizar y no altera la lista', async () => {
    vi.mocked(clienteApi.obtener).mockResolvedValue([tareaEjemplo])
    vi.mocked(clienteApi.actualizar).mockRejectedValue(new Error('Tarea no encontrada'))

    const tienda = useTiendaTareas()
    await tienda.cargar()
    await expect(
      tienda.actualizar(1, {
        nombre: 'x',
        prioridad: null,
        descripcion: 'y',
        fecha_creacion: '2026-11-09T10:00:00',
        fecha_vencimiento: null,
        etiquetas: [],
        asignados: [],
      }),
    ).rejects.toThrow('Tarea no encontrada')
    expect(tienda.tareas).toEqual([tareaEjemplo])
  })
  it('carga los catálogos de etiquetas y personas como listas de nombres', async () => {
    simularObtener()

    const tienda = useTiendaTareas()
    await tienda.cargarCatalogos()

    expect(clienteApi.obtener).toHaveBeenCalledWith('/etiquetas')
    expect(clienteApi.obtener).toHaveBeenCalledWith('/personas')
    expect(tienda.etiquetas).toEqual(['Backend', 'Urgente'])
    expect(tienda.personas).toEqual(['Ana'])
  })

  it('si falla la carga de los catálogos los deja como estaban y no marca error', async () => {
    vi.mocked(clienteApi.obtener).mockRejectedValue(new Error('fallo de red'))

    const tienda = useTiendaTareas()
    await tienda.cargarCatalogos()

    expect(tienda.etiquetas).toEqual([])
    expect(tienda.personas).toEqual([])
    expect(tienda.error).toBeNull()
  })

  it('refresca los catálogos tras crear una tarea', async () => {
    simularObtener()
    vi.mocked(clienteApi.crear).mockResolvedValue(tareaEjemplo)

    const tienda = useTiendaTareas()
    await tienda.crear({
      nombre: 'x',
      prioridad: null,
      descripcion: 'y',
      fecha_creacion: '2026-11-09T10:00:00',
      fecha_vencimiento: null,
      etiquetas: ['Urgente'],
      asignados: ['Ana'],
    })

    expect(clienteApi.obtener).toHaveBeenCalledWith('/etiquetas')
    expect(clienteApi.obtener).toHaveBeenCalledWith('/personas')
    expect(tienda.etiquetas).toEqual(['Backend', 'Urgente'])
    expect(tienda.personas).toEqual(['Ana'])
  })

  it('refresca los catálogos tras actualizar una tarea', async () => {
    simularObtener()
    vi.mocked(clienteApi.actualizar).mockResolvedValue(tareaEjemplo)

    const tienda = useTiendaTareas()
    await tienda.cargar()
    vi.mocked(clienteApi.obtener).mockClear()
    await tienda.actualizar(1, {
      nombre: 'x',
      prioridad: null,
      descripcion: 'y',
      fecha_creacion: '2026-11-09T10:00:00',
      fecha_vencimiento: null,
      etiquetas: ['Backend'],
      asignados: ['Ana'],
    })

    expect(clienteApi.obtener).toHaveBeenCalledWith('/etiquetas')
    expect(clienteApi.obtener).toHaveBeenCalledWith('/personas')
    expect(tienda.etiquetas).toEqual(['Backend', 'Urgente'])
  })

  it('no refresca los catálogos si la API falla al guardar', async () => {
    vi.mocked(clienteApi.crear).mockRejectedValue(new Error('datos inválidos'))

    const tienda = useTiendaTareas()
    await expect(
      tienda.crear({
        nombre: 'x',
        prioridad: null,
        descripcion: 'y',
        fecha_creacion: '2026-11-09T10:00:00',
        fecha_vencimiento: null,
        etiquetas: [],
        asignados: [],
      }),
    ).rejects.toThrow('datos inválidos')
    expect(clienteApi.obtener).not.toHaveBeenCalled()
  })
})
