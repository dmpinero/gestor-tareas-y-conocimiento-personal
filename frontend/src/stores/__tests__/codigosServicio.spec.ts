import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clienteApi, ErrorApi } from '@/api/cliente'
import type { CodigoServicio } from '@/api/tipos'
import { useTiendaCodigosServicio } from '@/stores/codigosServicio'

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

const RUTA = '/codigos-servicio'
const CODIGOS: CodigoServicio[] = [
  { id: 1, nombre: 'AXAS0024' },
  { id: 2, nombre: 'AXAS0026' },
]

async function tiendaCargada(codigos: CodigoServicio[] = CODIGOS) {
  vi.mocked(clienteApi.obtener).mockResolvedValue(structuredClone(codigos))
  const tienda = useTiendaCodigosServicio()
  await tienda.cargar()
  return tienda
}

function nombres(tienda: ReturnType<typeof useTiendaCodigosServicio>): string[] {
  return tienda.codigos.map((c) => c.nombre)
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('useTiendaCodigosServicio', () => {
  it('carga el catálogo', async () => {
    const tienda = await tiendaCargada()

    expect(clienteApi.obtener).toHaveBeenCalledWith(RUTA)
    expect(tienda.codigos).toEqual(CODIGOS)
    expect(tienda.cargando).toBe(false)
    expect(tienda.error).toBeNull()
  })

  it('si la carga falla guarda el error y deja el catálogo vacío', async () => {
    vi.mocked(clienteApi.obtener).mockRejectedValue(new ErrorApi(500, 'Caída'))
    const tienda = useTiendaCodigosServicio()

    await tienda.cargar()

    expect(tienda.codigos).toEqual([])
    expect(tienda.error).toBe('Caída')
    expect(tienda.cargando).toBe(false)
  })

  it('crear devuelve el código creado y lo coloca por orden alfabético', async () => {
    const tienda = await tiendaCargada()
    vi.mocked(clienteApi.crear).mockResolvedValue({ id: 3, nombre: 'axas0025' })

    const creado = await tienda.crear('axas0025')

    expect(clienteApi.crear).toHaveBeenCalledWith(RUTA, { nombre: 'axas0025' })
    expect(creado).toEqual({ id: 3, nombre: 'axas0025' })
    expect(nombres(tienda)).toEqual(['AXAS0024', 'axas0025', 'AXAS0026'])
    expect(tienda.error).toBeNull()
  })

  it('si crear falla devuelve null, guarda el error y no cambia la lista', async () => {
    const tienda = await tiendaCargada()
    vi.mocked(clienteApi.crear).mockRejectedValue(
      new ErrorApi(409, 'Ya existe un código de servicio llamado «axas0024»'),
    )

    expect(await tienda.crear('axas0024')).toBeNull()
    expect(tienda.error).toBe('Ya existe un código de servicio llamado «axas0024»')
    expect(tienda.codigos).toEqual(CODIGOS)
  })

  it('renombrar reemplaza el código y reordena', async () => {
    const tienda = await tiendaCargada()
    vi.mocked(clienteApi.actualizar).mockResolvedValue({ id: 1, nombre: 'AXAS0099' })

    expect(await tienda.renombrar(1, 'AXAS0099')).toBe(true)

    expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/1`, { nombre: 'AXAS0099' })
    expect(tienda.codigos).toEqual([
      { id: 2, nombre: 'AXAS0026' },
      { id: 1, nombre: 'AXAS0099' },
    ])
  })

  it('si renombrar falla devuelve false y no cambia la lista', async () => {
    const tienda = await tiendaCargada()
    vi.mocked(clienteApi.actualizar).mockRejectedValue(new ErrorApi(404, 'No existe'))

    expect(await tienda.renombrar(1, 'AXAS0099')).toBe(false)
    expect(tienda.error).toBe('No existe')
    expect(tienda.codigos).toEqual(CODIGOS)
  })

  it('eliminar lo quita de la lista', async () => {
    const tienda = await tiendaCargada()
    vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)

    expect(await tienda.eliminar(1)).toBe(true)

    expect(clienteApi.eliminar).toHaveBeenCalledWith(`${RUTA}/1`)
    expect(nombres(tienda)).toEqual(['AXAS0026'])
  })

  it('si eliminar falla devuelve false y no cambia la lista', async () => {
    const tienda = await tiendaCargada()
    vi.mocked(clienteApi.eliminar).mockRejectedValue(new ErrorApi(404, 'No existe'))

    expect(await tienda.eliminar(1)).toBe(false)
    expect(tienda.error).toBe('No existe')
    expect(tienda.codigos).toEqual(CODIGOS)
  })
})
