import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clienteApi, ErrorApi } from '@/api/cliente'
import type { Workflow } from '@/api/tipos'
import { useTiendaWorkflows } from '@/stores/workflows'

vi.mock('@/api/cliente', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('@/api/cliente')>()
  return {
    ...original,
    clienteApi: {
      obtener: vi.fn<(...args: unknown[]) => unknown>(),
      crear: vi.fn<(...args: unknown[]) => unknown>(),
      actualizar: vi.fn<(...args: unknown[]) => unknown>(),
      eliminar: vi.fn<(...args: unknown[]) => unknown>(),
    },
  }
})

const RUTA = '/workflows'

const OPORTUNIDADES: Workflow = {
  id: 1,
  nombre: 'Workflow Oportunidades',
  pasos: [
    { id: 10, numero: 1, nombre: 'Contacto inicial', comentarios: 0 },
    { id: 11, numero: 2, nombre: 'Propuesta', comentarios: 0 },
  ],
}
const ALTAS: Workflow = { id: 2, nombre: 'Altas', pasos: [] }

async function tiendaCargada(workflows: Workflow[] = [OPORTUNIDADES, ALTAS]) {
  vi.mocked(clienteApi.obtener).mockResolvedValue(structuredClone(workflows))
  const tienda = useTiendaWorkflows()
  await tienda.cargar()
  return tienda
}

describe('useTiendaWorkflows', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('carga los workflows desde GET /workflows con los pasos por número', async () => {
    const desordenado = { ...OPORTUNIDADES, pasos: [...OPORTUNIDADES.pasos].reverse() }
    const tienda = await tiendaCargada([desordenado, ALTAS])

    expect(clienteApi.obtener).toHaveBeenCalledWith(RUTA)
    expect(tienda.workflows).toEqual([OPORTUNIDADES, ALTAS])
    expect(tienda.cargando).toBe(false)
    expect(tienda.error).toBeNull()
  })

  it('guarda el mensaje de error si la carga falla', async () => {
    vi.mocked(clienteApi.obtener).mockRejectedValue(new ErrorApi(500, 'Error del servidor'))
    const tienda = useTiendaWorkflows()
    await tienda.cargar()

    expect(tienda.workflows).toEqual([])
    expect(tienda.error).toBe('Error del servidor')
    expect(tienda.cargando).toBe(false)
  })

  it('crea un workflow con POST /workflows y lo añade al final', async () => {
    const tienda = await tiendaCargada([OPORTUNIDADES])
    vi.mocked(clienteApi.crear).mockResolvedValue(structuredClone(ALTAS))

    expect(await tienda.crear('Altas')).toBe(true)
    expect(clienteApi.crear).toHaveBeenCalledWith(RUTA, { nombre: 'Altas' })
    expect(tienda.workflows).toEqual([OPORTUNIDADES, ALTAS])
  })

  it('si el alta falla devuelve false, guarda el error y no cambia la lista', async () => {
    const tienda = await tiendaCargada()
    vi.mocked(clienteApi.crear).mockRejectedValue(new ErrorApi(409, 'Ya existe un workflow'))

    expect(await tienda.crear('altas')).toBe(false)
    expect(tienda.error).toBe('Ya existe un workflow')
    expect(tienda.workflows).toEqual([OPORTUNIDADES, ALTAS])
  })

  it('renombra un workflow con PUT /workflows/{id} y lo reemplaza', async () => {
    const tienda = await tiendaCargada()
    vi.mocked(clienteApi.actualizar).mockResolvedValue({ ...ALTAS, nombre: 'Bajas' })

    expect(await tienda.renombrar(2, 'Bajas')).toBe(true)
    expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/2`, { nombre: 'Bajas' })
    expect(tienda.workflows.map((w) => w.nombre)).toEqual(['Workflow Oportunidades', 'Bajas'])
  })

  it('elimina un workflow con DELETE /workflows/{id} y lo quita de la lista', async () => {
    const tienda = await tiendaCargada()
    vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)

    expect(await tienda.eliminar(1)).toBe(true)
    expect(clienteApi.eliminar).toHaveBeenCalledWith(`${RUTA}/1`)
    expect(tienda.workflows).toEqual([ALTAS])
  })

  it('si el borrado falla conserva el workflow y guarda el error', async () => {
    const tienda = await tiendaCargada()
    vi.mocked(clienteApi.eliminar).mockRejectedValue(new ErrorApi(404, 'No existe'))

    expect(await tienda.eliminar(1)).toBe(false)
    expect(tienda.error).toBe('No existe')
    expect(tienda.workflows).toEqual([OPORTUNIDADES, ALTAS])
  })

  it('añade un paso con POST /workflows/{id}/pasos y reemplaza el workflow', async () => {
    const tienda = await tiendaCargada()
    const conPaso: Workflow = {
      ...ALTAS,
      pasos: [{ id: 20, numero: 1, nombre: 'Alta', comentarios: 0 }],
    }
    vi.mocked(clienteApi.crear).mockResolvedValue(conPaso)

    expect(await tienda.anadirPaso(2, 'Alta')).toBe(true)
    expect(clienteApi.crear).toHaveBeenCalledWith(`${RUTA}/2/pasos`, { nombre: 'Alta' })
    expect(tienda.workflows).toEqual([OPORTUNIDADES, conPaso])
  })

  it('renombra un paso con PUT /workflows/{id}/pasos/{id_paso}', async () => {
    const tienda = await tiendaCargada()
    const renombrado: Workflow = {
      ...OPORTUNIDADES,
      pasos: [OPORTUNIDADES.pasos[0]!, { id: 11, numero: 2, nombre: 'Oferta', comentarios: 0 }],
    }
    vi.mocked(clienteApi.actualizar).mockResolvedValue(renombrado)

    expect(await tienda.renombrarPaso(1, 11, 'Oferta')).toBe(true)
    expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/1/pasos/11`, { nombre: 'Oferta' })
    expect(tienda.workflows[0]).toEqual(renombrado)
  })

  it('elimina un paso con DELETE /workflows/{id}/pasos/{id_paso} y usa el workflow devuelto', async () => {
    const tienda = await tiendaCargada()
    const sinPaso: Workflow = {
      ...OPORTUNIDADES,
      pasos: [{ id: 11, numero: 1, nombre: 'Propuesta', comentarios: 0 }],
    }
    vi.mocked(clienteApi.eliminar).mockResolvedValue(sinPaso)

    expect(await tienda.eliminarPaso(1, 10)).toBe(true)
    expect(clienteApi.eliminar).toHaveBeenCalledWith(`${RUTA}/1/pasos/10`)
    expect(tienda.workflows[0]).toEqual(sinPaso)
  })

  it('si el borrado de un paso no devuelve cuerpo, recarga los workflows', async () => {
    const tienda = await tiendaCargada()
    const sinPaso: Workflow = {
      ...OPORTUNIDADES,
      pasos: [{ id: 11, numero: 1, nombre: 'Propuesta', comentarios: 0 }],
    }
    vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)
    vi.mocked(clienteApi.obtener).mockResolvedValue([sinPaso, ALTAS])

    expect(await tienda.eliminarPaso(1, 10)).toBe(true)
    expect(clienteApi.obtener).toHaveBeenLastCalledWith(RUTA)
    expect(tienda.workflows).toEqual([sinPaso, ALTAS])
  })

  it('reordena los pasos con PUT /workflows/{id}/orden y los deja por número', async () => {
    const tienda = await tiendaCargada()
    vi.mocked(clienteApi.actualizar).mockResolvedValue({
      ...OPORTUNIDADES,
      pasos: [
        { id: 10, numero: 2, nombre: 'Contacto inicial', comentarios: 0 },
        { id: 11, numero: 1, nombre: 'Propuesta', comentarios: 0 },
      ],
    })

    expect(await tienda.reordenarPasos(1, [11, 10])).toBe(true)
    expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/1/orden`, { ids: [11, 10] })
    expect(tienda.workflows[0]!.pasos.map((paso) => paso.id)).toEqual([11, 10])
  })

  it('si una acción sobre pasos falla conserva el workflow y guarda el error', async () => {
    const tienda = await tiendaCargada()
    vi.mocked(clienteApi.actualizar).mockRejectedValue(new ErrorApi(422, 'Orden inválido'))

    expect(await tienda.reordenarPasos(1, [11, 10])).toBe(false)
    expect(tienda.error).toBe('Orden inválido')
    expect(tienda.workflows).toEqual([OPORTUNIDADES, ALTAS])
  })

  it('fija el número de comentarios de un paso sin llamar a la API', async () => {
    const tienda = await tiendaCargada()
    vi.clearAllMocks()

    tienda.fijarComentariosPaso(1, 11, 3)

    expect(tienda.workflows[0]!.pasos.map((paso) => paso.comentarios)).toEqual([0, 3])
    expect(tienda.workflows[1]).toEqual(ALTAS)
    expect(clienteApi.obtener).not.toHaveBeenCalled()
  })

  it('ignora el número de comentarios de un paso que no existe', async () => {
    const tienda = await tiendaCargada()

    tienda.fijarComentariosPaso(1, 99, 3)
    tienda.fijarComentariosPaso(99, 10, 3)

    expect(tienda.workflows).toEqual([OPORTUNIDADES, ALTAS])
  })
})
