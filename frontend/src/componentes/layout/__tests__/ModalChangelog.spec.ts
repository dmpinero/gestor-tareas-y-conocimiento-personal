import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { obtenerHistorialDeReleases, type ReleaseGitHub } from '@/api/github'
import { reiniciarHistorialCambios } from '@/composables/useHistorialCambios'
import ModalChangelog from '../ModalChangelog.vue'

vi.mock('@/api/github', () => ({
  obtenerHistorialDeReleases: vi.fn<() => Promise<ReleaseGitHub[]>>(),
}))

const obtenerHistorialMock = vi.mocked(obtenerHistorialDeReleases)

function crearRelease(datos: Partial<ReleaseGitHub>): ReleaseGitHub {
  return {
    tag_name: 'v1.0.0',
    name: 'v1.0.0',
    body: '',
    published_at: '2026-08-15T00:00:00Z',
    html_url: 'https://github.com/dmpinero/gestor-tareas-y-conocimiento-personal/releases',
    ...datos,
  }
}

async function abrirModal(wrapper: ReturnType<typeof mount>): Promise<void> {
  await wrapper.get('button').trigger('click')
  await flushPromises()
}

function contenidoDialogo(): HTMLElement | null {
  return document.body.querySelector('[role="dialog"]')
}

afterEach(() => {
  vi.clearAllMocks()
  // La caché vive a nivel de módulo: se vacía para aislar cada test.
  reiniciarHistorialCambios()
  document.body.innerHTML = ''
})

describe('ModalChangelog', () => {
  it('muestra un botón "Historial de cambios" que abre el diálogo con su título', async () => {
    obtenerHistorialMock.mockResolvedValue([])
    const wrapper = mount(ModalChangelog, { attachTo: document.body })

    expect(wrapper.get('button').text()).toContain('Historial de cambios')
    await abrirModal(wrapper)

    const dialogo = contenidoDialogo()
    expect(dialogo?.querySelector('h2')?.textContent).toContain('Historial de cambios')
    expect(dialogo?.textContent).toContain(
      'Lista de cambios publicados en cada versión de la aplicación.',
    )
    wrapper.unmount()
  })

  it('no pide el historial hasta que se abre el diálogo', () => {
    obtenerHistorialMock.mockResolvedValue([])
    const wrapper = mount(ModalChangelog, { attachTo: document.body })

    expect(obtenerHistorialMock).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('renderiza el nombre de cada release como encabezado y su cuerpo como HTML', async () => {
    obtenerHistorialMock.mockResolvedValue([
      crearRelease({ name: 'v1.1.0', body: '### Novedades\n\n* segunda versión' }),
      crearRelease({ tag_name: 'v1.0.0', name: null, body: '* primera versión' }),
    ])
    const wrapper = mount(ModalChangelog, { attachTo: document.body })

    await abrirModal(wrapper)

    const dialogo = contenidoDialogo()
    const encabezados = Array.from(dialogo?.querySelectorAll('h2') ?? []).map((h) => h.textContent)
    expect(encabezados).toContain('v1.1.0')
    expect(encabezados).toContain('v1.0.0')
    expect(dialogo?.querySelector('h3')?.textContent).toBe('Novedades')
    const elementos = Array.from(dialogo?.querySelectorAll('li') ?? []).map((li) => li.textContent)
    expect(elementos).toEqual(['segunda versión', 'primera versión'])
    wrapper.unmount()
  })

  it('carga el historial una sola vez aunque el diálogo se abra de nuevo', async () => {
    obtenerHistorialMock.mockResolvedValue([crearRelease({ body: '* primera versión' })])
    const wrapper = mount(ModalChangelog, { attachTo: document.body })

    await abrirModal(wrapper)
    const botonCerrar = Array.from(document.body.querySelectorAll('button')).find((boton) =>
      boton.textContent?.includes('Cerrar'),
    )
    botonCerrar?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await flushPromises()
    expect(contenidoDialogo()).toBeNull()
    await abrirModal(wrapper)

    expect(obtenerHistorialMock).toHaveBeenCalledTimes(1)
    expect(contenidoDialogo()?.textContent).toContain('primera versión')
    wrapper.unmount()
  })

  it('muestra un error accesible si la carga del historial falla', async () => {
    obtenerHistorialMock.mockRejectedValue(new Error('fallo de red'))
    const wrapper = mount(ModalChangelog, { attachTo: document.body })

    await abrirModal(wrapper)

    expect(document.body.querySelector('[role="alert"]')?.textContent).toBe(
      'No se pudo cargar el historial de cambios.',
    )
    wrapper.unmount()
  })

  it('elimina los scripts y manejadores de eventos del cuerpo de las releases', async () => {
    obtenerHistorialMock.mockResolvedValue([
      crearRelease({
        body: 'texto seguro\n\n<script>window.inyectado = true</script>\n\n<img src="x" onerror="window.inyectado = true">',
      }),
    ])
    const wrapper = mount(ModalChangelog, { attachTo: document.body })

    await abrirModal(wrapper)

    const dialogo = contenidoDialogo()
    expect(dialogo?.textContent).toContain('texto seguro')
    expect(dialogo?.querySelector('script')).toBeNull()
    expect(dialogo?.querySelector('[onerror]')).toBeNull()
    expect(dialogo?.innerHTML).not.toContain('inyectado')
    wrapper.unmount()
  })

  // Regresión: la modal vive dentro del popover de ayuda, que reka desmonta al
  // cerrarse; con la caché dentro del componente se volvía a descargar todo el
  // historial en cada apertura (límite de 60 peticiones/hora de GitHub).
  it('no vuelve a pedir el historial al desmontar y volver a montar la modal', async () => {
    obtenerHistorialMock.mockResolvedValue([crearRelease({ body: '* primera versión' })])
    const primera = mount(ModalChangelog, { attachTo: document.body })
    await abrirModal(primera)
    primera.unmount()
    document.body.innerHTML = ''

    const segunda = mount(ModalChangelog, { attachTo: document.body })
    await abrirModal(segunda)

    expect(obtenerHistorialMock).toHaveBeenCalledTimes(1)
    expect(contenidoDialogo()?.textContent).toContain('primera versión')
    segunda.unmount()
  })

  it('reintenta la carga en la siguiente apertura si la anterior falló', async () => {
    obtenerHistorialMock.mockRejectedValueOnce(new Error('sin red'))
    obtenerHistorialMock.mockResolvedValueOnce([crearRelease({ body: '* recuperado' })])
    const primera = mount(ModalChangelog, { attachTo: document.body })
    await abrirModal(primera)
    expect(contenidoDialogo()?.textContent).toContain('No se pudo cargar el historial de cambios.')
    primera.unmount()
    document.body.innerHTML = ''

    const segunda = mount(ModalChangelog, { attachTo: document.body })
    await abrirModal(segunda)

    expect(obtenerHistorialMock).toHaveBeenCalledTimes(2)
    expect(contenidoDialogo()?.textContent).toContain('recuperado')
    segunda.unmount()
  })

  it('elimina las etiquetas <style> y los atributos style de las notas', async () => {
    obtenerHistorialMock.mockResolvedValue([
      crearRelease({
        body: '<style>body { display: none }</style>\n\n<p style="position:fixed">texto</p>',
      }),
    ])
    const wrapper = mount(ModalChangelog, { attachTo: document.body })
    await abrirModal(wrapper)

    const dialogo = contenidoDialogo()
    expect(dialogo?.textContent).toContain('texto')
    expect(dialogo?.querySelector('style')).toBeNull()
    expect(dialogo?.querySelector('[style]')).toBeNull()
    wrapper.unmount()
  })
})
