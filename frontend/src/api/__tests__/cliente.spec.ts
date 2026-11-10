import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clienteApi, ErrorApi } from '../cliente'

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn<typeof fetch>())
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('cliente API - propagación de errores', () => {
  it('un error 500 con traza en el JSON se propaga en ErrorApi.traza', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detalle: 'boom', traza: 'Traceback...' }), { status: 500 }),
    )

    await expect(clienteApi.obtener('/algo')).rejects.toMatchObject({
      estado: 500,
      message: 'boom',
      traza: 'Traceback...',
    })
  })

  it('un error 422 sin traza deja ErrorApi.traza undefined', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detalle: 'dato inválido' }), { status: 422 }),
    )

    const error = (await clienteApi.obtener('/algo').catch((e: unknown) => e)) as ErrorApi

    expect(error).toBeInstanceOf(ErrorApi)
    expect(error.traza).toBeUndefined()
  })
})

describe('cliente API - respuestas correctas', () => {
  it('devuelve el JSON de la respuesta y llama a la ruta bajo el prefijo /api/v1', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ estado: 'ok' }), { status: 200 }),
    )

    await expect(clienteApi.obtener('/salud')).resolves.toEqual({ estado: 'ok' })
    expect(vi.mocked(fetch).mock.calls[0]?.[0]).toBe('/api/v1/salud')
  })

  it('una respuesta 204 resuelve con undefined', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 204 }))

    await expect(clienteApi.eliminar('/algo/1')).resolves.toBeUndefined()
  })

  it('eliminar devuelve el JSON de la respuesta cuando el DELETE trae cuerpo', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ id: 1, subtareas: [] }), { status: 200 }),
    )

    await expect(clienteApi.eliminar('/tareas/1/subtareas/2')).resolves.toEqual({
      id: 1,
      subtareas: [],
    })
    expect(vi.mocked(fetch).mock.calls[0]?.[1]?.method).toBe('DELETE')
  })

  it('parchear envía un PATCH con el cuerpo JSON y devuelve la respuesta', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ id: 1, completada: true }), { status: 200 }),
    )

    await expect(
      clienteApi.parchear('/tareas/1/completada', { completada: true }),
    ).resolves.toEqual({ id: 1, completada: true })
    const [url, opciones] = vi.mocked(fetch).mock.calls[0]!
    expect(url).toBe('/api/v1/tareas/1/completada')
    expect(opciones?.method).toBe('PATCH')
    expect(opciones?.body).toBe(JSON.stringify({ completada: true }))
  })

  it('parchear envía también un cuerpo con valor falso', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }))

    await clienteApi.parchear('/tareas/1/completada', { completada: false })

    expect(vi.mocked(fetch).mock.calls[0]?.[1]?.body).toBe(JSON.stringify({ completada: false }))
  })

  it('parchear propaga los errores como ErrorApi', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Tarea no encontrada' }), { status: 404 }),
    )

    await expect(
      clienteApi.parchear('/tareas/99/completada', { completada: true }),
    ).rejects.toMatchObject({ estado: 404, message: 'Tarea no encontrada' })
  })
})
