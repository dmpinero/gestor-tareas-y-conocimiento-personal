import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clienteApi, ErrorApi } from '@/api/cliente'
import type { GrupoEstados } from '@/api/tipos'
import { useTiendaGruposEstados } from '@/stores/gruposEstados'

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

const RUTA = '/grupos-estados'

const DESARROLLO: GrupoEstados = {
  id: 1,
  nombre: 'Desarrollo',
  tareas: 3,
  estados: [
    { id: 10, nombre: 'Pendiente', posicion: 1, tareas: 2 },
    { id: 11, nombre: 'En curso', posicion: 2, tareas: 1 },
  ],
}
const SOPORTE: GrupoEstados = { id: 2, nombre: 'Soporte', tareas: 0, estados: [] }

async function tiendaCargada(grupos: GrupoEstados[] = [DESARROLLO, SOPORTE]) {
  vi.mocked(clienteApi.obtener).mockResolvedValue(structuredClone(grupos))
  const tienda = useTiendaGruposEstados()
  await tienda.cargar()
  return tienda
}

describe('useTiendaGruposEstados', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('carga los grupos desde GET /grupos-estados con los estados por posición', async () => {
    const desordenado = { ...DESARROLLO, estados: [...DESARROLLO.estados].reverse() }
    const tienda = await tiendaCargada([desordenado, SOPORTE])

    expect(clienteApi.obtener).toHaveBeenCalledWith(RUTA)
    expect(tienda.grupos).toEqual([DESARROLLO, SOPORTE])
    expect(tienda.cargando).toBe(false)
    expect(tienda.error).toBeNull()
  })

  it('guarda el mensaje de error si la carga falla', async () => {
    vi.mocked(clienteApi.obtener).mockRejectedValue(new ErrorApi(500, 'Error del servidor'))
    const tienda = useTiendaGruposEstados()
    await tienda.cargar()

    expect(tienda.error).toBe('Error del servidor')
    expect(tienda.grupos).toEqual([])
    expect(tienda.cargando).toBe(false)
  })

  it('crear envía POST con el nombre y añade el grupo', async () => {
    const tienda = await tiendaCargada([DESARROLLO])
    vi.mocked(clienteApi.crear).mockResolvedValue(structuredClone(SOPORTE))

    expect(await tienda.crear('Soporte')).toBe(true)
    expect(clienteApi.crear).toHaveBeenCalledWith(RUTA, { nombre: 'Soporte' })
    expect(tienda.grupos.map((g) => g.nombre)).toEqual(['Desarrollo', 'Soporte'])
  })

  it('si la API falla, crear devuelve false, guarda el error y no cambia la lista', async () => {
    const tienda = await tiendaCargada([DESARROLLO])
    vi.mocked(clienteApi.crear).mockRejectedValue(new ErrorApi(409, 'Ya existe un grupo'))

    expect(await tienda.crear('Desarrollo')).toBe(false)
    expect(tienda.error).toBe('Ya existe un grupo')
    expect(tienda.grupos).toEqual([DESARROLLO])
  })

  it('renombrar envía PUT y reemplaza el grupo con la respuesta', async () => {
    const tienda = await tiendaCargada()
    vi.mocked(clienteApi.actualizar).mockResolvedValue({ ...DESARROLLO, nombre: 'Producto' })

    expect(await tienda.renombrar(1, 'Producto')).toBe(true)
    expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/1`, { nombre: 'Producto' })
    expect(tienda.grupos.map((g) => g.nombre)).toEqual(['Producto', 'Soporte'])
  })

  it('eliminar envía DELETE y quita el grupo', async () => {
    const tienda = await tiendaCargada()
    vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)

    expect(await tienda.eliminar(1)).toBe(true)
    expect(clienteApi.eliminar).toHaveBeenCalledWith(`${RUTA}/1`)
    expect(tienda.grupos).toEqual([SOPORTE])
  })

  it('si eliminar falla, conserva el grupo y guarda el error', async () => {
    const tienda = await tiendaCargada()
    vi.mocked(clienteApi.eliminar).mockRejectedValue(new ErrorApi(500, 'Fallo'))

    expect(await tienda.eliminar(1)).toBe(false)
    expect(tienda.error).toBe('Fallo')
    expect(tienda.grupos).toHaveLength(2)
  })

  it('anadirEstado envía POST a /estados y reemplaza el grupo', async () => {
    const tienda = await tiendaCargada()
    const conEstado = {
      ...SOPORTE,
      estados: [{ id: 20, nombre: 'Abierta', posicion: 1, tareas: 0 }],
    }
    vi.mocked(clienteApi.crear).mockResolvedValue(conEstado)

    expect(await tienda.anadirEstado(2, 'Abierta')).toBe(true)
    expect(clienteApi.crear).toHaveBeenCalledWith(`${RUTA}/2/estados`, { nombre: 'Abierta' })
    expect(tienda.grupos[1]).toEqual(conEstado)
  })

  it('renombrarEstado envía PUT al estado y reemplaza el grupo', async () => {
    const tienda = await tiendaCargada()
    const renombrado = {
      ...DESARROLLO,
      estados: [DESARROLLO.estados[0]!, { ...DESARROLLO.estados[1]!, nombre: 'Haciendo' }],
    }
    vi.mocked(clienteApi.actualizar).mockResolvedValue(renombrado)

    expect(await tienda.renombrarEstado(1, 11, 'Haciendo')).toBe(true)
    expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/1/estados/11`, {
      nombre: 'Haciendo',
    })
    expect(tienda.grupos[0]).toEqual(renombrado)
  })

  it('eliminarEstado sin tareas envía DELETE sin mover_a', async () => {
    const tienda = await tiendaCargada()
    vi.mocked(clienteApi.eliminar).mockResolvedValue({
      ...DESARROLLO,
      estados: [DESARROLLO.estados[0]],
    })

    expect(await tienda.eliminarEstado(1, 11)).toBe(true)
    expect(clienteApi.eliminar).toHaveBeenCalledWith(`${RUTA}/1/estados/11`)
    expect(tienda.grupos[0]!.estados.map((e) => e.nombre)).toEqual(['Pendiente'])
  })

  it('eliminarEstado con destino envía mover_a y reemplaza el grupo', async () => {
    const tienda = await tiendaCargada()
    vi.mocked(clienteApi.eliminar).mockResolvedValue({
      ...DESARROLLO,
      estados: [{ ...DESARROLLO.estados[1]!, posicion: 1, tareas: 3 }],
    })

    expect(await tienda.eliminarEstado(1, 10, 11)).toBe(true)
    expect(clienteApi.eliminar).toHaveBeenCalledWith(`${RUTA}/1/estados/10?mover_a=11`)
    expect(tienda.grupos[0]!.estados).toEqual([
      { id: 11, nombre: 'En curso', posicion: 1, tareas: 3 },
    ])
  })

  it('si eliminarEstado devuelve 409, conserva el grupo y guarda el error', async () => {
    const tienda = await tiendaCargada()
    vi.mocked(clienteApi.eliminar).mockRejectedValue(new ErrorApi(409, 'Tiene tareas'))

    expect(await tienda.eliminarEstado(1, 10)).toBe(false)
    expect(tienda.error).toBe('Tiene tareas')
    expect(tienda.grupos[0]).toEqual(DESARROLLO)
  })

  it('reordenarEstados envía PUT /orden con los ids y ordena por posición', async () => {
    const tienda = await tiendaCargada()
    // La respuesta llega con las posiciones nuevas, en cualquier orden.
    vi.mocked(clienteApi.actualizar).mockResolvedValue({
      ...DESARROLLO,
      estados: [
        { id: 10, nombre: 'Pendiente', posicion: 2, tareas: 2 },
        { id: 11, nombre: 'En curso', posicion: 1, tareas: 1 },
      ],
    })

    expect(await tienda.reordenarEstados(1, [11, 10])).toBe(true)
    expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/1/orden`, { ids: [11, 10] })
    expect(tienda.grupos[0]!.estados.map((e) => e.nombre)).toEqual(['En curso', 'Pendiente'])
  })
})
