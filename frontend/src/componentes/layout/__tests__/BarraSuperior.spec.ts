import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

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

import BarraSuperior from '../BarraSuperior.vue'

describe('BarraSuperior', () => {
  it('muestra el botón de ayuda justo antes del conmutador de tema', () => {
    const wrapper = mount(BarraSuperior)

    const botones = wrapper.findAll('button')
    expect(botones).toHaveLength(2)
    expect(botones[0]?.attributes('aria-label')).toBe('Ayuda: historial de cambios')
    expect(botones[1]?.attributes('role')).toBe('switch')
  })
})
