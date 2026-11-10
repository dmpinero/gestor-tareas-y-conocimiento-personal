import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import BotonAyuda from '../BotonAyuda.vue'

vi.mock('@/api/github', () => ({
  obtenerHistorialDeReleases: vi.fn<() => Promise<never[]>>().mockResolvedValue([]),
}))

// reka-ui usa ResizeObserver internamente para posicionar el contenido del
// Popover; jsdom no lo implementa.
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub)

afterEach(() => {
  document.body.innerHTML = ''
})

describe('BotonAyuda', () => {
  it('expone un aria-label descriptivo', () => {
    const wrapper = mount(BotonAyuda)

    expect(wrapper.get('button').attributes('aria-label')).toBe('Ayuda: historial de cambios')
  })

  it('al pulsarlo, muestra la opción "Historial de cambios" y no un manual de usuario', async () => {
    const wrapper = mount(BotonAyuda, { attachTo: document.body })

    await wrapper.get('button').trigger('click')
    await flushPromises()

    const opcion = Array.from(document.body.querySelectorAll('button')).find((boton) =>
      boton.textContent?.includes('Historial de cambios'),
    )
    expect(opcion).toBeDefined()
    expect(document.body.textContent).not.toContain('Manual de usuario')
    wrapper.unmount()
  })
})
