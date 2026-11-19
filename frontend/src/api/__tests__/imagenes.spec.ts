import { afterEach, describe, expect, it, vi } from 'vitest'

import { ErrorApi } from '../cliente'
import { subirImagen } from '../imagenes'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('subirImagen', () => {
  it('envía la imagen como multipart en el campo "archivo" y devuelve su URL', async () => {
    const respuesta = {
      id: 'a'.repeat(32),
      url: `/api/v1/imagenes/${'a'.repeat(32)}`,
      tipo: 'image/png',
      tamano: 3,
    }
    const fetchFalso = vi.fn<(...args: unknown[]) => Promise<Response>>(
      async () => new Response(JSON.stringify(respuesta), { status: 201 }),
    )
    vi.stubGlobal('fetch', fetchFalso)
    const fichero = new File([new Uint8Array([1, 2, 3])], 'captura.png', { type: 'image/png' })

    await expect(subirImagen(fichero)).resolves.toEqual(respuesta)

    const [url, opciones] = fetchFalso.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('/api/v1/imagenes')
    expect(opciones.method).toBe('POST')
    expect((opciones.body as FormData).get('archivo')).toBeInstanceOf(File)
    // La API exige esta cabecera para que otro sitio no pueda subir imágenes (CORS).
    expect(new Headers(opciones.headers).get('X-Requested-With')).toBe('gestor-tareas')
  })

  it('rechaza con el mensaje de la API si no la admite', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<() => Promise<Response>>(
        async () =>
          new Response(JSON.stringify({ detalle: 'La imagen no puede pasar de 5 MB' }), {
            status: 413,
          }),
      ),
    )

    const error = await subirImagen(new File(['x'], 'a.png')).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ErrorApi)
    expect((error as ErrorApi).estado).toBe(413)
    expect((error as ErrorApi).message).toBe('La imagen no puede pasar de 5 MB')
  })
})
