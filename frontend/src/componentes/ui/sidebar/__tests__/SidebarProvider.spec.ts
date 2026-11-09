import { describe, it, expect, beforeEach } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import SidebarProvider from '../SidebarProvider.vue'
import { CLAVE_ALMACENAMIENTO, useSidebar, type EstadoPanelLateral } from '../useSidebar'

function montarConConsumidor(): { panel: EstadoPanelLateral } {
  const capturado: { panel?: EstadoPanelLateral } = {}
  const componenteConsumidor = defineComponent({
    setup() {
      capturado.panel = useSidebar()
      return () => h('span')
    },
  })
  mount(SidebarProvider, { slots: { default: () => h(componenteConsumidor) } })
  return { panel: capturado.panel! }
}

describe('SidebarProvider', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('arranca colapsado cuando no hay preferencia guardada', () => {
    const { panel } = montarConConsumidor()

    expect(panel.estado.value).toBe('colapsado')
  })

  it('respeta la preferencia guardada de panel expandido', () => {
    localStorage.setItem(CLAVE_ALMACENAMIENTO, 'expandido')

    const { panel } = montarConConsumidor()

    expect(panel.estado.value).toBe('expandido')
  })

  it('respeta la preferencia guardada de panel colapsado', () => {
    localStorage.setItem(CLAVE_ALMACENAMIENTO, 'colapsado')

    const { panel } = montarConConsumidor()

    expect(panel.estado.value).toBe('colapsado')
  })

  it('alternar expande el panel y guarda la preferencia', async () => {
    const { panel } = montarConConsumidor()

    panel.alternar()
    await nextTick()

    expect(panel.estado.value).toBe('expandido')
    expect(localStorage.getItem(CLAVE_ALMACENAMIENTO)).toBe('expandido')
  })
})
