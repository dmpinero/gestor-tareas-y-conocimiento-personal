import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clienteApi } from '@/api/cliente'
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

const tareaEjemplo = {
  id: 1,
  nombre: 'Escribir informe',
  prioridad: null,
  descripcion: 'Informe trimestral',
  fecha_creacion: '2026-11-09T10:00:00',
  fecha_vencimiento: null,
  etiquetas: ['Backend'],
  asignados: ['Ana'],
  tipo: null,
  oportunidad: null,
  completada: false,
  subtareas: [],
  grupo_estados: null,
  estado: null,
  workflow: null,
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
      tipo: null,
      oportunidad: null,
      grupo_estados_id: null,
      workflow_id: null,
    }
    await tienda.crear(datos)

    expect(clienteApi.crear).toHaveBeenCalledWith('/tareas', datos)
    expect(tienda.tareas).toEqual([tareaEjemplo])
  })

  it('envía el tipo y los datos de la oportunidad tal cual y guarda la tarea devuelta', async () => {
    const oportunidad = { codigo: 'OP-1', descripcion: null, observaciones: 'Línea 1\nLínea 2' }
    const creada = { ...tareaEjemplo, tipo: 'oportunidad' as const, oportunidad }
    vi.mocked(clienteApi.crear).mockResolvedValue(creada)
    simularObtener()

    const tienda = useTiendaTareas()
    const datos = {
      nombre: 'Escribir informe',
      prioridad: null,
      descripcion: 'Informe trimestral',
      fecha_creacion: '2026-11-09T10:00:00',
      fecha_vencimiento: null,
      etiquetas: ['Backend'],
      asignados: ['Ana'],
      tipo: 'oportunidad' as const,
      oportunidad,
      grupo_estados_id: null,
      workflow_id: null,
    }
    await tienda.crear(datos)

    expect(clienteApi.crear).toHaveBeenCalledWith('/tareas', datos)
    expect(tienda.tareas).toEqual([creada])
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
        tipo: null,
        oportunidad: null,
        grupo_estados_id: null,
        workflow_id: null,
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
      tipo: null,
      oportunidad: null,
      grupo_estados_id: null,
      workflow_id: null,
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
        tipo: null,
        oportunidad: null,
        grupo_estados_id: null,
        workflow_id: null,
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
      tipo: null,
      oportunidad: null,
      grupo_estados_id: null,
      workflow_id: null,
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
      tipo: null,
      oportunidad: null,
      grupo_estados_id: null,
      workflow_id: null,
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
        tipo: null,
        oportunidad: null,
        grupo_estados_id: null,
        workflow_id: null,
      }),
    ).rejects.toThrow('datos inválidos')
    expect(clienteApi.obtener).not.toHaveBeenCalled()
  })

  describe('alternarCompletada', () => {
    it('marca como completada una tarea pendiente con PATCH /tareas/{id}/completada y la reemplaza', async () => {
      const otra = { ...tareaEjemplo, id: 2, nombre: 'Otra' }
      vi.mocked(clienteApi.obtener).mockResolvedValue([tareaEjemplo, otra])
      const completada = { ...tareaEjemplo, completada: true }
      vi.mocked(clienteApi.parchear).mockResolvedValue(completada)

      const tienda = useTiendaTareas()
      await tienda.cargar()
      await tienda.alternarCompletada(1)

      expect(clienteApi.parchear).toHaveBeenCalledWith('/tareas/1/completada', {
        completada: true,
      })
      expect(tienda.tareas).toEqual([completada, otra])
      expect(tienda.error).toBeNull()
    })

    it('vuelve a pendiente una tarea completada enviando el valor negado', async () => {
      const completada = { ...tareaEjemplo, completada: true }
      vi.mocked(clienteApi.obtener).mockResolvedValue([completada])
      vi.mocked(clienteApi.parchear).mockResolvedValue(tareaEjemplo)

      const tienda = useTiendaTareas()
      await tienda.cargar()
      await tienda.alternarCompletada(1)

      expect(clienteApi.parchear).toHaveBeenCalledWith('/tareas/1/completada', {
        completada: false,
      })
      expect(tienda.tareas).toEqual([tareaEjemplo])
    })

    it('si la API falla guarda el mensaje de error y no altera la lista', async () => {
      vi.mocked(clienteApi.obtener).mockResolvedValue([tareaEjemplo])
      vi.mocked(clienteApi.parchear).mockRejectedValue(new Error('Tarea no encontrada'))

      const tienda = useTiendaTareas()
      await tienda.cargar()
      await tienda.alternarCompletada(1)

      expect(tienda.error).toBe('Tarea no encontrada')
      expect(tienda.tareas).toEqual([tareaEjemplo])
    })

    it('con un id que no está en la lista no llama a la API', async () => {
      vi.mocked(clienteApi.obtener).mockResolvedValue([tareaEjemplo])

      const tienda = useTiendaTareas()
      await tienda.cargar()
      await tienda.alternarCompletada(99)

      expect(clienteApi.parchear).not.toHaveBeenCalled()
      expect(tienda.tareas).toEqual([tareaEjemplo])
    })
  })

  it('ya no ofrece la acción de alternar pasos del workflow', () => {
    expect('alternarPasoTarea' in useTiendaTareas()).toBe(false)
  })

  describe('eliminarTarea', () => {
    const otra = { ...tareaEjemplo, id: 2, nombre: 'Otra' }

    it('envía DELETE /tareas/{id}, la quita de la lista y devuelve true', async () => {
      vi.mocked(clienteApi.obtener).mockResolvedValue([tareaEjemplo, otra])
      vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)

      const tienda = useTiendaTareas()
      await tienda.cargar()
      const resultado = await tienda.eliminarTarea(1)

      expect(resultado).toBe(true)
      expect(clienteApi.eliminar).toHaveBeenCalledWith('/tareas/1')
      expect(tienda.tareas).toEqual([otra])
      expect(tienda.error).toBeNull()
    })

    it('si la API falla guarda el mensaje, conserva la tarea y devuelve false', async () => {
      vi.mocked(clienteApi.obtener).mockResolvedValue([tareaEjemplo, otra])
      vi.mocked(clienteApi.eliminar).mockRejectedValue(new Error('Tarea no encontrada'))

      const tienda = useTiendaTareas()
      await tienda.cargar()
      const resultado = await tienda.eliminarTarea(1)

      expect(resultado).toBe(false)
      expect(tienda.error).toBe('Tarea no encontrada')
      expect(tienda.tareas).toEqual([tareaEjemplo, otra])
    })
  })

  describe('fijarComentariosSubtarea', () => {
    it('cambia solo el número de comentarios de esa subtarea, sin llamar a la API', async () => {
      const subtareas = [
        { id: 20, nombre: 'A', asignado: null, prioridad: null, resuelta: false, comentarios: 0 },
        { id: 21, nombre: 'B', asignado: null, prioridad: null, resuelta: false, comentarios: 1 },
      ]
      vi.mocked(clienteApi.obtener).mockResolvedValue([{ ...tareaEjemplo, subtareas }])

      const tienda = useTiendaTareas()
      await tienda.cargar()
      tienda.fijarComentariosSubtarea(1, 21, 4)
      tienda.fijarComentariosSubtarea(99, 21, 7)

      expect(tienda.tareas[0]!.subtareas.map((s) => s.comentarios)).toEqual([0, 4])
      expect(clienteApi.parchear).not.toHaveBeenCalled()
    })
  })

  describe('subtareas', () => {
    const SUBTAREAS = [
      {
        id: 20,
        nombre: 'Redactar índice',
        asignado: 'Ana',
        prioridad: 2,
        resuelta: false,
        comentarios: 0,
      },
      {
        id: 21,
        nombre: 'Revisar cifras',
        asignado: null,
        prioridad: null,
        resuelta: true,
        comentarios: 0,
      },
    ]
    const conSubtareas = { ...tareaEjemplo, subtareas: SUBTAREAS }
    const otra = { ...tareaEjemplo, id: 2, nombre: 'Otra' }

    it('crearSubtarea envía POST /tareas/{id}/subtareas, reemplaza la tarea y refresca los catálogos', async () => {
      simularObtener([tareaEjemplo, otra])
      vi.mocked(clienteApi.crear).mockResolvedValue(conSubtareas)

      const tienda = useTiendaTareas()
      await tienda.cargar()
      vi.mocked(clienteApi.obtener).mockClear()
      const datos = { nombre: 'Redactar índice', asignado: 'Ana', prioridad: 2 }
      const resultado = await tienda.crearSubtarea(1, datos)

      expect(resultado).toBe(true)
      expect(clienteApi.crear).toHaveBeenCalledWith('/tareas/1/subtareas', datos)
      expect(tienda.tareas).toEqual([conSubtareas, otra])
      expect(clienteApi.obtener).toHaveBeenCalledWith('/personas')
      expect(tienda.personas).toEqual(['Ana'])
      expect(tienda.error).toBeNull()
    })

    it('crearSubtarea con un fallo de la API guarda el error, devuelve false y no altera la lista', async () => {
      simularObtener([tareaEjemplo])
      vi.mocked(clienteApi.crear).mockRejectedValue(new Error('Nombre obligatorio'))

      const tienda = useTiendaTareas()
      await tienda.cargar()
      const resultado = await tienda.crearSubtarea(1, { nombre: 'x' })

      expect(resultado).toBe(false)
      expect(tienda.error).toBe('Nombre obligatorio')
      expect(tienda.tareas).toEqual([tareaEjemplo])
    })

    it('alternarSubtarea marca como resuelta una pendiente con PATCH y reemplaza la tarea', async () => {
      simularObtener([conSubtareas, otra])
      const actualizada = {
        ...conSubtareas,
        subtareas: [{ ...SUBTAREAS[0]!, resuelta: true }, SUBTAREAS[1]!],
      }
      vi.mocked(clienteApi.parchear).mockResolvedValue(actualizada)

      const tienda = useTiendaTareas()
      await tienda.cargar()
      const resultado = await tienda.alternarSubtarea(1, 20)

      expect(resultado).toBe(true)
      expect(clienteApi.parchear).toHaveBeenCalledWith('/tareas/1/subtareas/20/resuelta', {
        resuelta: true,
      })
      expect(tienda.tareas).toEqual([actualizada, otra])
      expect(tienda.error).toBeNull()
    })

    it('alternarSubtarea reabre una resuelta enviando el valor negado', async () => {
      simularObtener([conSubtareas])
      vi.mocked(clienteApi.parchear).mockResolvedValue(conSubtareas)

      const tienda = useTiendaTareas()
      await tienda.cargar()
      await tienda.alternarSubtarea(1, 21)

      expect(clienteApi.parchear).toHaveBeenCalledWith('/tareas/1/subtareas/21/resuelta', {
        resuelta: false,
      })
    })

    it('alternarSubtarea con un fallo de la API guarda el error, devuelve false y no altera la lista', async () => {
      simularObtener([conSubtareas])
      vi.mocked(clienteApi.parchear).mockRejectedValue(new Error('Subtarea no encontrada'))

      const tienda = useTiendaTareas()
      await tienda.cargar()
      const resultado = await tienda.alternarSubtarea(1, 20)

      expect(resultado).toBe(false)
      expect(tienda.error).toBe('Subtarea no encontrada')
      expect(tienda.tareas).toEqual([conSubtareas])
    })

    it('alternarSubtarea con una tarea o subtarea que no están en la lista no llama a la API', async () => {
      simularObtener([conSubtareas])

      const tienda = useTiendaTareas()
      await tienda.cargar()
      expect(await tienda.alternarSubtarea(99, 20)).toBe(false)
      expect(await tienda.alternarSubtarea(1, 99)).toBe(false)

      expect(clienteApi.parchear).not.toHaveBeenCalled()
      expect(tienda.tareas).toEqual([conSubtareas])
    })

    it('eliminarSubtarea envía DELETE /tareas/{id}/subtareas/{id_subtarea} y reemplaza la tarea', async () => {
      simularObtener([conSubtareas, otra])
      const actualizada = { ...conSubtareas, subtareas: [SUBTAREAS[1]!] }
      vi.mocked(clienteApi.eliminar).mockResolvedValue(actualizada)

      const tienda = useTiendaTareas()
      await tienda.cargar()
      const resultado = await tienda.eliminarSubtarea(1, 20)

      expect(resultado).toBe(true)
      expect(clienteApi.eliminar).toHaveBeenCalledWith('/tareas/1/subtareas/20')
      expect(tienda.tareas).toEqual([actualizada, otra])
      expect(tienda.error).toBeNull()
    })

    it('eliminarSubtarea con un fallo de la API guarda el error, devuelve false y no altera la lista', async () => {
      simularObtener([conSubtareas])
      vi.mocked(clienteApi.eliminar).mockRejectedValue(new Error('Subtarea no encontrada'))

      const tienda = useTiendaTareas()
      await tienda.cargar()
      const resultado = await tienda.eliminarSubtarea(1, 20)

      expect(resultado).toBe(false)
      expect(tienda.error).toBe('Subtarea no encontrada')
      expect(tienda.tareas).toEqual([conSubtareas])
    })

    it('editarSubtarea envía PUT /tareas/{id}/subtareas/{id_subtarea}, reemplaza la tarea y refresca los catálogos', async () => {
      simularObtener([conSubtareas, otra])
      const actualizada = {
        ...conSubtareas,
        subtareas: [{ ...SUBTAREAS[0]!, nombre: 'Índice', asignado: null, prioridad: null }],
      }
      vi.mocked(clienteApi.actualizar).mockResolvedValue(actualizada)

      const tienda = useTiendaTareas()
      await tienda.cargar()
      vi.mocked(clienteApi.obtener).mockClear()
      const datos = { nombre: 'Índice', asignado: null, prioridad: null }
      const resultado = await tienda.editarSubtarea(1, 20, datos)

      expect(resultado).toBe(true)
      expect(clienteApi.actualizar).toHaveBeenCalledWith('/tareas/1/subtareas/20', datos)
      expect(tienda.tareas).toEqual([actualizada, otra])
      expect(clienteApi.obtener).toHaveBeenCalledWith('/personas')
      expect(tienda.error).toBeNull()
    })

    it('editarSubtarea con un fallo de la API guarda el error, devuelve false y no altera la lista', async () => {
      simularObtener([conSubtareas])
      vi.mocked(clienteApi.actualizar).mockRejectedValue(new Error('Subtarea no encontrada'))

      const tienda = useTiendaTareas()
      await tienda.cargar()
      vi.mocked(clienteApi.obtener).mockClear()
      const resultado = await tienda.editarSubtarea(1, 20, {
        nombre: 'x',
        asignado: 'Ana',
        prioridad: 1,
      })

      expect(resultado).toBe(false)
      expect(tienda.error).toBe('Subtarea no encontrada')
      expect(tienda.tareas).toEqual([conSubtareas])
      expect(clienteApi.obtener).not.toHaveBeenCalled()
    })
  })
  describe('cambiarEstadoTarea', () => {
    const enGrupo = {
      ...tareaEjemplo,
      grupo_estados: { id: 1, nombre: 'Desarrollo' },
      estado: { id: 10, nombre: 'Pendiente' },
    }

    it('envía PATCH /tareas/{id}/estado, reemplaza la tarea y devuelve true', async () => {
      simularObtener([enGrupo])
      const movida = { ...enGrupo, estado: { id: 11, nombre: 'En curso' } }
      vi.mocked(clienteApi.parchear).mockResolvedValue(movida)
      const tienda = useTiendaTareas()
      await tienda.cargar()

      expect(await tienda.cambiarEstadoTarea(1, 11)).toBe(true)
      expect(clienteApi.parchear).toHaveBeenCalledWith('/tareas/1/estado', { estado_id: 11 })
      expect(tienda.tareas).toEqual([movida])
      expect(tienda.error).toBeNull()
    })

    it('si la API falla guarda el error, devuelve false y deja la tarea como estaba', async () => {
      simularObtener([enGrupo])
      vi.mocked(clienteApi.parchear).mockRejectedValue(new Error('El estado no es del grupo'))
      const tienda = useTiendaTareas()
      await tienda.cargar()

      expect(await tienda.cambiarEstadoTarea(1, 99)).toBe(false)
      expect(tienda.error).toBe('El estado no es del grupo')
      expect(tienda.tareas).toEqual([enGrupo])
    })
  })

  it('crear devuelve la tarea creada', async () => {
    simularObtener([])
    vi.mocked(clienteApi.crear).mockResolvedValue(tareaEjemplo)
    const tienda = useTiendaTareas()

    const datos = {
      nombre: tareaEjemplo.nombre,
      prioridad: null,
      descripcion: tareaEjemplo.descripcion,
      fecha_creacion: tareaEjemplo.fecha_creacion,
      fecha_vencimiento: null,
      etiquetas: tareaEjemplo.etiquetas,
      asignados: tareaEjemplo.asignados,
      tipo: null,
      oportunidad: null,
    }
    expect(await tienda.crear({ ...datos, grupo_estados_id: null, workflow_id: null })).toEqual(
      tareaEjemplo,
    )
  })
})
