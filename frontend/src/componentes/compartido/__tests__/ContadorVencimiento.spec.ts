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

  it('con 48 horas o más muestra cuánto falta en verde', () => {
    vi.setSystemTime(new Date(2026, 10, 18, 14, 44, 40))

    const contador = montar()

    const span = contador.get('[data-testid="contador-vencimiento"]')
    expect(span.text()).toBe('Vence en 2 d 03 h 15 min 20 s')
    expect(span.classes()).toEqual(
      expect.arrayContaining(['text-green-700', 'dark:text-green-400']),
    )
    expect(span.classes()).not.toContain('text-destructive')
    expect(span.attributes('data-nivel')).toBe('holgada')
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
    expect(span.attributes('data-nivel')).toBe('vencida')
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

  it('con más de 24 y menos de 48 horas se muestra en naranja', () => {
    vi.setSystemTime(new Date(2026, 10, 19, 12, 0, 0))

    const contador = montar()

    const span = contador.get('[data-testid="contador-vencimiento"]')
    expect(span.text()).toBe('Vence en 1 d 06 h 00 min 00 s')
    expect(span.classes()).toEqual(
      expect.arrayContaining(['text-orange-700', 'dark:text-orange-400']),
    )
    expect(span.attributes('data-nivel')).toBe('menos-de-48h')
    contador.unmount()
  })

  it('con menos de 24 horas se muestra en rojo y cambia de color al cruzar el umbral', async () => {
    vi.setSystemTime(new Date(2026, 10, 19, 17, 59, 59))
    const contador = montar()
    const span = () => contador.get('[data-testid="contador-vencimiento"]')
    expect(span().attributes('data-nivel')).toBe('menos-de-48h')

    vi.advanceTimersByTime(2000)
    await contador.vm.$nextTick()

    expect(span().text()).toBe('Vence en 23 h 59 min 59 s')
    expect(span().classes()).toContain('text-destructive')
    expect(span().attributes('data-nivel')).toBe('menos-de-24h')
    contador.unmount()
  })
})
