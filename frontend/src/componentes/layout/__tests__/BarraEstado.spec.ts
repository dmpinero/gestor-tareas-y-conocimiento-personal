import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import BarraEstado from '../BarraEstado.vue'

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn<typeof fetch>())
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

describe('BarraEstado', () => {
  it('muestra la versión obtenida de la última release de GitHub', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ tag_name: 'v1.0.1' }), { status: 200 }),
    )

    const wrapper = mount(BarraEstado)
    await new Promise((resolver) => setTimeout(resolver, 0))
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('v1.0.1')
  })

  it('no muestra ninguna versión si la petición a GitHub falla', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 404 }))

    const wrapper = mount(BarraEstado)
    await new Promise((resolver) => setTimeout(resolver, 0))
    await wrapper.vm.$nextTick()

    expect(wrapper.find('span').exists()).toBe(false)
  })

  it('si GitHub falla muestra la última versión conocida', async () => {
    localStorage.setItem(
      'gestor-tareas:version',
      JSON.stringify({ version: '1.48.0', consultada: 0 }),
    )
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 403 }))

    const wrapper = mount(BarraEstado)
    await new Promise((resolver) => setTimeout(resolver, 0))
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('v1.48.0')
  })
})
