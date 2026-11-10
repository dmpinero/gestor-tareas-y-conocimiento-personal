import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import ContadorVencimiento from '../ContadorVencimiento.vue'

const VENCIMIENTO = '2026-11-20T18:00:00'

function montar(vencimiento = VENCIMIENTO) {
  return mount(ContadorVencimiento, { props: { vencimiento } })
}

describe('ContadorVencimiento', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('muestra cuánto falta para vencer sin el color de vencida', () => {
    vi.setSystemTime(new Date(2026, 10, 18, 14, 44, 40))

    const contador = montar()

    const span = contador.get('[data-testid="contador-vencimiento"]')
    expect(span.text()).toBe('Vence en 2 d 03 h 15 min 20 s')
    expect(span.classes()).not.toContain('text-destructive')
    expect(span.classes()).toContain('text-muted-foreground')
    expect(span.attributes('data-vencida')).toBe('false')
    contador.unmount()
  })

  it('cuenta hacia atrás cada segundo', async () => {
    vi.setSystemTime(new Date(2026, 10, 20, 17, 59, 15))
    const contador = montar()
    expect(contador.text()).toBe('Vence en 00 h 00 min 45 s')

    vi.advanceTimersByTime(1000)
    await contador.vm.$nextTick()

    expect(contador.text()).toBe('Vence en 00 h 00 min 44 s')
    contador.unmount()
  })

  it('al llegar el vencimiento pasa a "Vencida hace" en rojo', async () => {
    vi.setSystemTime(new Date(2026, 10, 20, 17, 59, 59))
    const contador = montar()

    vi.advanceTimersByTime(1000)
    await contador.vm.$nextTick()

    const span = contador.get('[data-testid="contador-vencimiento"]')
    expect(span.text()).toBe('Vencida hace 00 h 00 min')
    expect(span.classes()).toContain('text-destructive')
    expect(span.classes()).not.toContain('text-muted-foreground')
    expect(span.attributes('data-vencida')).toBe('true')
    contador.unmount()
  })

  it('no anuncia cada segundo a los lectores de pantalla', () => {
    vi.setSystemTime(new Date(2026, 10, 18, 14, 44, 40))

    const contador = montar()

    const span = contador.get('[data-testid="contador-vencimiento"]')
    // El rol `timer` tiene `aria-live="off"` implícito.
    expect(span.attributes('role')).toBe('timer')
    expect(span.attributes('aria-live')).toBeUndefined()
    expect(contador.find('[aria-live]').exists()).toBe(false)
    contador.unmount()
  })

  it('se actualiza si cambia la fecha de vencimiento', async () => {
    vi.setSystemTime(new Date(2026, 10, 18, 14, 44, 40))
    const contador = montar()

    await contador.setProps({ vencimiento: '2026-11-18T14:45:00' })

    expect(contador.text()).toBe('Vence en 00 h 00 min 20 s')
    contador.unmount()
  })
})
