import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clienteApi, ErrorApi } from '@/api/cliente'
import { useTiendaWorkflowOportunidades } from '@/stores/workflowOportunidades'

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

const RUTA = '/workflow-oportunidades/pasos'
const PASOS = [
  { id: 1, numero: 1, nombre: 'Contacto inicial' },
  { id: 2, numero: 2, nombre: 'Propuesta' },
  { id: 3, numero: 3, nombre: 'Cierre' },
]

describe('useTiendaWorkflowOportunidades', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('carga los pasos desde GET /workflow-oportunidades/pasos', async () => {
    vi.mocked(clienteApi.obtener).mockResolvedValue(PASOS)

    const tienda = useTiendaWorkflowOportunidades()
    await tienda.cargar()

    expect(clienteApi.obtener).toHaveBeenCalledWith(RUTA)
    expect(tienda.pasos).toEqual(PASOS)
    expect(tienda.cargando).toBe(false)
    expect(tienda.error).toBeNull()
  })

  it('guarda el mensaje de error si la carga falla', async () => {
    vi.mocked(clienteApi.obtener).mockRejectedValue(new ErrorApi(500, 'Error del servidor'))

    const tienda = useTiendaWorkflowOportunidades()
    await tienda.cargar()

    expect(tienda.error).toBe('Error del servidor')
    expect(tienda.pasos).toEqual([])
    expect(tienda.cargando).toBe(false)
  })

  it('crear envía POST con el nombre y añade el paso al final', async () => {
    vi.mocked(clienteApi.obtener).mockResolvedValue(PASOS.slice(0, 2))
    vi.mocked(clienteApi.crear).mockResolvedValue(PASOS[2])

    const tienda = useTiendaWorkflowOportunidades()
    await tienda.cargar()
    const resultado = await tienda.crear('Cierre')

    expect(resultado).toBe(true)
    expect(clienteApi.crear).toHaveBeenCalledWith(RUTA, { nombre: 'Cierre' })
    expect(tienda.pasos).toEqual(PASOS)
  })

  it('crear devuelve false y guarda el error si la API falla', async () => {
    vi.mocked(clienteApi.crear).mockRejectedValue(new ErrorApi(422, 'Nombre inválido'))

    const tienda = useTiendaWorkflowOportunidades()
    const resultado = await tienda.crear('x')

    expect(resultado).toBe(false)
    expect(tienda.error).toBe('Nombre inválido')
    expect(tienda.pasos).toEqual([])
  })

  it('renombrar envía PUT al paso y sustituye el paso en la lista', async () => {
    vi.mocked(clienteApi.obtener).mockResolvedValue(PASOS)
    vi.mocked(clienteApi.actualizar).mockResolvedValue({ id: 2, numero: 2, nombre: 'Oferta' })

    const tienda = useTiendaWorkflowOportunidades()
    await tienda.cargar()
    const resultado = await tienda.renombrar(2, 'Oferta')

    expect(resultado).toBe(true)
    expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/2`, { nombre: 'Oferta' })
    expect(tienda.pasos.map((paso) => paso.nombre)).toEqual([
      'Contacto inicial',
      'Oferta',
      'Cierre',
    ])
  })

  it('eliminar envía DELETE y recarga la lista renumerada', async () => {
    vi.mocked(clienteApi.obtener)
      .mockResolvedValueOnce(PASOS)
      .mockResolvedValueOnce([
        { id: 1, numero: 1, nombre: 'Contacto inicial' },
        { id: 3, numero: 2, nombre: 'Cierre' },
      ])
    vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)

    const tienda = useTiendaWorkflowOportunidades()
    await tienda.cargar()
    const resultado = await tienda.eliminar(2)

    expect(resultado).toBe(true)
    expect(clienteApi.eliminar).toHaveBeenCalledWith(`${RUTA}/2`)
    expect(tienda.pasos).toEqual([
      { id: 1, numero: 1, nombre: 'Contacto inicial' },
      { id: 3, numero: 2, nombre: 'Cierre' },
    ])
  })

  it('reordenar envía PUT /orden con los ids y usa la lista devuelta', async () => {
    const reordenados = [
      { id: 3, numero: 1, nombre: 'Cierre' },
      { id: 1, numero: 2, nombre: 'Contacto inicial' },
      { id: 2, numero: 3, nombre: 'Propuesta' },
    ]
    vi.mocked(clienteApi.obtener).mockResolvedValue(PASOS)
    vi.mocked(clienteApi.actualizar).mockResolvedValue(reordenados)

    const tienda = useTiendaWorkflowOportunidades()
    await tienda.cargar()
    const resultado = await tienda.reordenar([3, 1, 2])

    expect(resultado).toBe(true)
    expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/orden`, { ids: [3, 1, 2] })
    expect(tienda.pasos).toEqual(reordenados)
  })

  it('reordenar conserva el orden anterior y guarda el error si la API falla', async () => {
    vi.mocked(clienteApi.obtener).mockResolvedValue(PASOS)
    vi.mocked(clienteApi.actualizar).mockRejectedValue(new ErrorApi(422, 'Orden inválido'))

    const tienda = useTiendaWorkflowOportunidades()
    await tienda.cargar()
    const resultado = await tienda.reordenar([3, 1, 2])

    expect(resultado).toBe(false)
    expect(tienda.error).toBe('Orden inválido')
    expect(tienda.pasos).toEqual(PASOS)
  })
})
