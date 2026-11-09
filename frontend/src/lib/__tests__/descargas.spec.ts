import { afterEach, describe, expect, it, vi } from 'vitest'

import { descargarBlob } from '@/lib/descargas'

describe('descargarBlob', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('crea un enlace temporal con el nombre de fichero, dispara la descarga y libera la URL', () => {
    const url = 'blob:url-de-prueba'
    const crearUrl = vi.fn<(blob: Blob) => string>().mockReturnValue(url)
    const liberarUrl = vi.fn<(url: string) => void>()
    vi.stubGlobal('URL', { ...URL, createObjectURL: crearUrl, revokeObjectURL: liberarUrl })

    const pulsar = vi.fn<() => void>()
    const enlaceFalso = { href: '', download: '', click: pulsar } as unknown as HTMLAnchorElement
    const crearElementoOriginal = document.createElement.bind(document)
    vi.spyOn(document, 'createElement').mockImplementation((etiqueta: string) =>
      etiqueta === 'a' ? enlaceFalso : crearElementoOriginal(etiqueta),
    )

    const blob = new Blob(['contenido'])
    descargarBlob(blob, 'Tareas_05012026_090307.xlsx')

    expect(crearUrl).toHaveBeenCalledWith(blob)
    expect(enlaceFalso.href).toBe(url)
    expect(enlaceFalso.download).toBe('Tareas_05012026_090307.xlsx')
    expect(pulsar).toHaveBeenCalledOnce()
    expect(liberarUrl).toHaveBeenCalledWith(url)
  })
})
