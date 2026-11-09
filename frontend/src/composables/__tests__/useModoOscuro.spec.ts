import { nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

function definirMatchMedia(coincideOscuro: boolean): void {
  window.matchMedia = vi.fn<(consulta: string) => unknown>().mockImplementation((consulta) => ({
    matches: coincideOscuro,
    media: consulta,
    addEventListener: vi.fn<() => void>(),
    removeEventListener: vi.fn<() => void>(),
  })) as unknown as typeof window.matchMedia
}

beforeEach(() => {
  localStorage.clear()
  document.documentElement.classList.remove('dark')
  vi.resetModules()
})

describe('useModoOscuro', () => {
  it('sin preferencia guardada, respeta el modo oscuro del sistema operativo', async () => {
    definirMatchMedia(true)
    const { useModoOscuro } = await import('../useModoOscuro')
    const { temaActual } = useModoOscuro()

    expect(temaActual.value).toBe('oscuro')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('sin preferencia guardada, respeta el modo claro del sistema operativo', async () => {
    definirMatchMedia(false)
    const { useModoOscuro } = await import('../useModoOscuro')
    const { temaActual } = useModoOscuro()

    expect(temaActual.value).toBe('claro')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('con preferencia guardada, la respeta aunque el sistema indique lo contrario', async () => {
    definirMatchMedia(true)
    localStorage.setItem('tema-preferido', 'claro')
    const { useModoOscuro } = await import('../useModoOscuro')
    const { temaActual } = useModoOscuro()

    expect(temaActual.value).toBe('claro')
  })

  it('alternar cambia el tema, actualiza el DOM y lo persiste en localStorage', async () => {
    definirMatchMedia(false)
    const { useModoOscuro } = await import('../useModoOscuro')
    const { temaActual, alternar } = useModoOscuro()

    alternar()
    await nextTick()

    expect(temaActual.value).toBe('oscuro')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('tema-preferido')).toBe('oscuro')
  })
})
