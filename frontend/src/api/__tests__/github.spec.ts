import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { obtenerHistorialDeReleases, obtenerUltimaVersion } from '../github'

function release(tag: string) {
  return {
    tag_name: tag,
    name: tag,
    body: `cambios de ${tag}`,
    published_at: '2026-08-15T00:00:00Z',
    html_url: `https://github.com/dmpinero/gestor-tareas-y-conocimiento-personal/releases/tag/${tag}`,
  }
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn<typeof fetch>())
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('obtenerHistorialDeReleases', () => {
  it('recorre todas las páginas de la API de GitHub y las concatena', async () => {
    const primeraPagina = Array.from({ length: 100 }, (_, i) => release(`v2.${99 - i}.0`))
    const segundaPagina = [release('v1.0.0')]
    vi.mocked(fetch)
      .mockResolvedValueOnce(new Response(JSON.stringify(primeraPagina), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(segundaPagina), { status: 200 }))

    const releases = await obtenerHistorialDeReleases()

    expect(fetch).toHaveBeenCalledTimes(2)
    expect(vi.mocked(fetch).mock.calls[0]?.[0]).toContain('page=1')
    expect(vi.mocked(fetch).mock.calls[1]?.[0]).toContain('page=2')
    expect(releases).toHaveLength(101)
    expect(releases[releases.length - 1]?.tag_name).toBe('v1.0.0')
  })

  it('con una única página incompleta, no hace una segunda llamada', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify([release('v1.0.0')]), { status: 200 }),
    )

    const releases = await obtenerHistorialDeReleases()

    expect(fetch).toHaveBeenCalledTimes(1)
    expect(releases).toHaveLength(1)
  })

  it('lanza un error si una página falla', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 500 }))

    await expect(obtenerHistorialDeReleases()).rejects.toThrow(
      'No se pudo obtener el historial de cambios desde GitHub.',
    )
  })
})

describe('obtenerUltimaVersion', () => {
  it('devuelve el nombre de la etiqueta sin el prefijo "v"', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(release('v1.48.0')), { status: 200 }),
    )

    await expect(obtenerUltimaVersion()).resolves.toBe('1.48.0')
  })
})
