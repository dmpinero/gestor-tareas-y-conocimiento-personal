import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clienteApi } from '@/api/cliente'
import type { Foco } from '@/api/tipos'
import { useTiendaFoco } from '@/stores/foco'
import BotonFoco from '../BotonFoco.vue'

vi.mock('@/api/cliente', async (original) => ({
  ...(await original()),
  clienteApi: {
    obtener: vi.fn<(...args: unknown[]) => unknown>(),
    actualizar: vi.fn<(...args: unknown[]) => unknown>(),
    eliminar: vi.fn<(...args: unknown[]) => unknown>(),
  },
}))

const FOCO: Foco = {
  tarea_id: 1,
  tarea_nombre: 'A',
  subtarea_id: null,
  subtarea_nombre: null,
  desde: '2026-11-24T10:00:00',
}

function montar(props: {
  tareaId: number
  subtareaId?: number | null
  nombre?: string
  compacto?: boolean
}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  return mount(BotonFoco, { props, global: { plugins: [pinia] } })
}

beforeEach(() => vi.clearAllMocks())

describe('BotonFoco', () => {
  it('sin foco dice "Trabajar en esta" y pone la tarea en foco', async () => {
    vi.mocked(clienteApi.actualizar).mockResolvedValue(FOCO)
    const wrapper = montar({ tareaId: 1 })

    expect(wrapper.text()).toBe('Trabajar en esta')
    await wrapper.trigger('click')
    await flushPromises()

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/foco', { tarea_id: 1, subtarea_id: null })
    expect(wrapper.text()).toBe('Dejar de trabajar')
    expect(wrapper.attributes('data-en-foco')).toBe('true')
  })

  it('sobre la tarea en foco dice "Dejar de trabajar" y quita el foco', async () => {
    vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)
    const wrapper = montar({ tareaId: 1 })
    useTiendaFoco().foco = FOCO
    await flushPromises()

    expect(wrapper.text()).toBe('Dejar de trabajar')
    await wrapper.trigger('click')
    await flushPromises()

    expect(clienteApi.eliminar).toHaveBeenCalledWith('/foco')
    expect(wrapper.text()).toBe('Trabajar en esta')
  })

  it('con otra tarea en foco la sustituye sin preguntar', async () => {
    vi.mocked(clienteApi.actualizar).mockResolvedValue({ ...FOCO, tarea_id: 2 })
    const wrapper = montar({ tareaId: 2 })
    useTiendaFoco().foco = FOCO
    await flushPromises()

    expect(wrapper.text()).toBe('Trabajar en esta')
    await wrapper.trigger('click')
    await flushPromises()

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/foco', { tarea_id: 2, subtarea_id: null })
    expect(useTiendaFoco().foco?.tarea_id).toBe(2)
  })

  it('con nombre lo añade al nombre accesible sin cambiar el texto visible', () => {
    const wrapper = montar({ tareaId: 1, nombre: 'Informe' })

    expect(wrapper.text()).toBe('Trabajar en esta')
    expect(wrapper.attributes('aria-label')).toBe('Trabajar en esta (Informe)')
  })

  it('de una subtarea pone en foco la subtarea; la tarea en foco no cuenta como ella', async () => {
    vi.mocked(clienteApi.actualizar).mockResolvedValue({ ...FOCO, subtarea_id: 10 })
    const wrapper = montar({ tareaId: 1, subtareaId: 10, compacto: true })
    useTiendaFoco().foco = FOCO
    await flushPromises()

    expect(wrapper.attributes('aria-label')).toBe('Trabajar en esta')
    await wrapper.trigger('click')
    await flushPromises()

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/foco', { tarea_id: 1, subtarea_id: 10 })
    expect(wrapper.attributes('aria-label')).toBe('Dejar de trabajar')
  })
})
