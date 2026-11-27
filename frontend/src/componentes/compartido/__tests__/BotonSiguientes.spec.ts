import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clienteApi } from '@/api/cliente'
import type { TareaSiguiente } from '@/api/tipos'
import { useTiendaSiguientes } from '@/stores/siguientes'
import BotonSiguientes from '../BotonSiguientes.vue'

vi.mock('@/api/cliente', async (original) => ({
  ...(await original()),
  clienteApi: {
    obtener: vi.fn<(...args: unknown[]) => unknown>(),
    crear: vi.fn<(...args: unknown[]) => unknown>(),
    actualizar: vi.fn<(...args: unknown[]) => unknown>(),
    eliminar: vi.fn<(...args: unknown[]) => unknown>(),
  },
}))

const INFORME: TareaSiguiente = {
  tarea_id: 1,
  tarea_nombre: 'Informe',
  subtarea_id: null,
  subtarea_nombre: null,
}

function montar(props: {
  tareaId: number
  nombre?: string
  compacto?: boolean
  completada?: boolean
}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  return mount(BotonSiguientes, { props, global: { plugins: [pinia] } })
}

beforeEach(() => vi.clearAllMocks())

describe('BotonSiguientes', () => {
  it('fuera de la cola dice "Añadir a siguientes" y la añade al final', async () => {
    vi.mocked(clienteApi.crear).mockResolvedValue([INFORME])
    const wrapper = montar({ tareaId: 1 })

    expect(wrapper.text()).toBe('Añadir a siguientes')
    await wrapper.trigger('click')
    await flushPromises()

    expect(clienteApi.crear).toHaveBeenCalledWith('/siguientes', { tarea_id: 1 })
    expect(wrapper.text()).toBe('Quitar de siguientes')
    expect(wrapper.attributes('data-en-siguientes')).toBe('true')
  })

  it('en la cola dice "Quitar de siguientes" y la quita', async () => {
    vi.mocked(clienteApi.eliminar).mockResolvedValue([])
    const wrapper = montar({ tareaId: 1 })
    useTiendaSiguientes().cola = [INFORME]
    await flushPromises()

    expect(wrapper.text()).toBe('Quitar de siguientes')
    await wrapper.trigger('click')
    await flushPromises()

    expect(clienteApi.eliminar).toHaveBeenCalledWith('/siguientes/1')
    expect(wrapper.text()).toBe('Añadir a siguientes')
  })

  it('con nombre lo añade al nombre accesible; compacto queda en solo icono', () => {
    const conNombre = montar({ tareaId: 1, nombre: 'Informe' })
    expect(conNombre.text()).toBe('Añadir a siguientes')
    expect(conNombre.attributes('aria-label')).toBe('Añadir a siguientes (Informe)')
    expect(conNombre.attributes('title')).toBe('Añadir a siguientes')

    const compacto = montar({ tareaId: 1, compacto: true })
    expect(compacto.text()).toBe('')
    expect(compacto.attributes('aria-label')).toBe('Añadir a siguientes')
  })

  it('en una tarea completada no se muestra', () => {
    const wrapper = montar({ tareaId: 1, nombre: 'Informe', completada: true })

    expect(wrapper.find('[data-boton-siguientes]').exists()).toBe(false)
  })
})
