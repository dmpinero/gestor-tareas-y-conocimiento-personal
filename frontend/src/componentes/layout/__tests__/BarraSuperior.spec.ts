import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

// ConmutadorTema usa useModoOscuro, que lee matchMedia al cargarse el módulo,
// y jsdom no lo implementa: hay que definirlo antes de los imports de abajo.
vi.hoisted(() => {
  window.matchMedia = ((consulta: string) => ({
    matches: false,
    media: consulta,
    addEventListener: () => {},
    removeEventListener: () => {},
  })) as unknown as typeof window.matchMedia
})

vi.mock('@/api/github', () => ({
  obtenerHistorialDeReleases: vi.fn<() => Promise<never[]>>().mockResolvedValue([]),
}))

vi.mock('@/api/cliente', async (original) => ({
  ...(await original()),
  clienteApi: { obtener: vi.fn<(...args: unknown[]) => unknown>() },
}))

import { clienteApi } from '@/api/cliente'
import BarraSuperior from '../BarraSuperior.vue'

async function montar(foco: unknown) {
  vi.mocked(clienteApi.obtener).mockResolvedValue(foco)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:ruta(.*)*', component: { render: () => null } }],
  })
  const wrapper = mount(BarraSuperior, { global: { plugins: [createPinia(), router] } })
  await flushPromises()
  return { wrapper, router }
}

const FOCO = {
  tarea_id: 1,
  tarea_nombre: 'Migración portal',
  subtarea_id: null,
  subtarea_nombre: null,
  desde: new Date().toISOString(),
}

describe('BarraSuperior', () => {
  it('sin foco muestra el historial de foco, la ayuda y el conmutador de tema', async () => {
    const { wrapper } = await montar(null)

    const botones = wrapper.findAll('button')
    expect(botones).toHaveLength(3)
    expect(botones[0]?.attributes('aria-label')).toBe('Historial de foco')
    expect(botones[1]?.attributes('aria-label')).toBe('Ayuda: historial de cambios')
    expect(botones[2]?.attributes('role')).toBe('switch')
  })

  it.each([
    ['sin foco', null],
    ['con foco', FOCO],
  ])('el botón del reloj lleva al historial de foco (%s)', async (_caso, foco) => {
    const { wrapper, router } = await montar(foco)

    await wrapper.get('button[aria-label="Historial de foco"]').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/foco/historial')
  })

  it('con una tarea en foco muestra su píldora y después el reloj, antes de la ayuda', async () => {
    const { wrapper } = await montar(FOCO)

    expect(wrapper.get('[data-indicador-foco]').text()).toContain('Trabajando en: Migración portal')
    const botones = wrapper.findAll('button')
    expect(botones).toHaveLength(5)
    expect(botones[2]?.attributes('aria-label')).toBe('Historial de foco')
    expect(botones[3]?.attributes('aria-label')).toBe('Ayuda: historial de cambios')
  })
})
