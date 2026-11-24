import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { clienteApi } from '@/api/cliente'
import type { Foco } from '@/api/tipos'
import { useTiendaFoco } from '@/stores/foco'
import IndicadorFoco from '../IndicadorFoco.vue'

vi.mock('@/api/cliente', async (original) => ({
  ...(await original()),
  clienteApi: {
    obtener: vi.fn<(...args: unknown[]) => unknown>(),
    actualizar: vi.fn<(...args: unknown[]) => unknown>(),
    eliminar: vi.fn<(...args: unknown[]) => unknown>(),
  },
}))

const FOCO_TAREA: Foco = {
  tarea_id: 7,
  tarea_nombre: 'Migración portal',
  subtarea_id: null,
  subtarea_nombre: null,
  desde: '2026-11-24T10:00:00',
}

const FOCO_SUBTAREA: Foco = {
  ...FOCO_TAREA,
  subtarea_id: 70,
  subtarea_nombre: 'Probar login',
}

let envoltorio: VueWrapper | null = null
let router: Router

async function montar(foco: Foco | null): Promise<VueWrapper> {
  vi.mocked(clienteApi.obtener).mockResolvedValue(foco)
  const pinia = createPinia()
  setActivePinia(pinia)
  router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:ruta(.*)*', component: { render: () => null } }],
  })
  await router.push('/')
  envoltorio = mount(IndicadorFoco, { global: { plugins: [pinia, router] } })
  await flushPromises()
  return envoltorio
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] })
  vi.setSystemTime(new Date(2026, 10, 24, 11, 20, 0))
})

afterEach(() => {
  envoltorio?.unmount()
  envoltorio = null
  vi.useRealTimers()
})

describe('IndicadorFoco', () => {
  it('carga el foco con GET /foco al montarse', async () => {
    await montar(null)

    expect(clienteApi.obtener).toHaveBeenCalledWith('/foco')
  })

  it('sin foco no se muestra', async () => {
    const wrapper = await montar(null)

    expect(wrapper.find('[data-indicador-foco]').exists()).toBe(false)
  })

  it('con una tarea en foco muestra su nombre y el tiempo', async () => {
    const wrapper = await montar(FOCO_TAREA)

    expect(wrapper.get('[data-abrir-foco]').text()).toBe(
      'Trabajando en: Migración portal · 1 h 20 min',
    )
  })

  it('con una subtarea en foco muestra "Tarea › Subtarea"', async () => {
    const wrapper = await montar(FOCO_SUBTAREA)

    expect(wrapper.get('[data-abrir-foco]').text()).toBe(
      'Trabajando en: Migración portal › Probar login · 1 h 20 min',
    )
  })

  it('refresca el tiempo cada minuto', async () => {
    const wrapper = await montar(FOCO_TAREA)

    vi.advanceTimersByTime(60_000)
    await flushPromises()

    expect(wrapper.get('[data-abrir-foco]').text()).toContain('· 1 h 21 min')
  })

  it('al pulsarla abre la tarea en /tareas?tarea=<id>', async () => {
    const wrapper = await montar(FOCO_SUBTAREA)

    await wrapper.get('[data-abrir-foco]').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/tareas')
    expect(router.currentRoute.value.query).toEqual({ tarea: '7' })
  })

  it('el ✕ deja de trabajar: DELETE /foco y la píldora desaparece', async () => {
    vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)
    const wrapper = await montar(FOCO_TAREA)

    await wrapper.get('button[aria-label="Dejar de trabajar"]').trigger('click')
    await flushPromises()

    expect(clienteApi.eliminar).toHaveBeenCalledWith('/foco')
    expect(useTiendaFoco().foco).toBeNull()
    expect(wrapper.find('[data-indicador-foco]').exists()).toBe(false)
  })

  it('al desmontarse detiene el reloj', async () => {
    const wrapper = await montar(FOCO_TAREA)

    wrapper.unmount()
    envoltorio = null

    expect(vi.getTimerCount()).toBe(0)
  })
})
