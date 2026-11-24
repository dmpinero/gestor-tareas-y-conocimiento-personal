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
  return wrapper
}

describe('BarraSuperior', () => {
  it('muestra el botón de ayuda justo antes del conmutador de tema', async () => {
    const wrapper = await montar(null)

    const botones = wrapper.findAll('button')
    expect(botones).toHaveLength(2)
    expect(botones[0]?.attributes('aria-label')).toBe('Ayuda: historial de cambios')
    expect(botones[1]?.attributes('role')).toBe('switch')
  })

  it('con una tarea en foco muestra su píldora antes de la ayuda', async () => {
    const wrapper = await montar({
      tarea_id: 1,
      tarea_nombre: 'Migración portal',
      subtarea_id: null,
      subtarea_nombre: null,
      desde: new Date().toISOString(),
    })

    expect(wrapper.get('[data-indicador-foco]').text()).toContain('Trabajando en: Migración portal')
    const botones = wrapper.findAll('button')
    expect(botones).toHaveLength(4)
    expect(botones[2]?.attributes('aria-label')).toBe('Ayuda: historial de cambios')
  })
})
