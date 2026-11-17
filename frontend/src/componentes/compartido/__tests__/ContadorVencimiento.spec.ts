import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import ContadorVencimiento from '../ContadorVencimiento.vue'

const VENCIMIENTO = '2026-11-20T18:00:00'

function montar(vencimiento = VENCIMIENTO, congeladaEn: string | null = null) {
  return mount(ContadorVencimiento, { props: { vencimiento, congeladaEn } })
}

// Instante en UTC, como lo da la API ("YYYY-MM-DDTHH:MM:SSZ"), de una hora local.
function instanteUtc(fechaLocal: Date): string {
  return fechaLocal.toISOString().replace(/\.\d{3}Z$/, 'Z')
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

  describe('congelado (tarea completada o en DONE)', () => {
    // Se congeló el 19/11/2026 a las 16:49:50, hora local.
    const CONGELADA_EN = instanteUtc(new Date(2026, 10, 19, 16, 49, 50))

    it('muestra fijo lo que faltaba al congelarse, sin color de urgencia y con un icono de pausa', () => {
      vi.setSystemTime(new Date(2026, 10, 18, 14, 44, 40))

      const contador = montar(VENCIMIENTO, CONGELADA_EN)

      const span = contador.get('[data-testid="contador-vencimiento"]')
      expect(span.attributes('role')).toBe('timer')
      expect(span.attributes('data-congelado')).toBe('true')
      expect(span.get('[data-testid="contador-texto"]').text()).toBe(
        'Vence en 1 d 01 h 10 min 10 s',
      )
      expect(span.find('[data-icono-pausa]').exists()).toBe(true)
      expect(span.find('[data-icono-pausa]').attributes('aria-hidden')).toBe('true')
      expect(span.get('.sr-only').text()).toBe('(contador detenido)')
      expect(span.attributes('title')).toBe('Contador detenido: la tarea está completada o en DONE')
      expect(span.classes()).toContain('text-muted-foreground')
      expect(span.classes()).not.toContain('text-destructive')
      expect(span.classes()).not.toContain('text-green-700')
      contador.unmount()
    })

    it('no avanza con el paso del tiempo', async () => {
      vi.setSystemTime(new Date(2026, 10, 18, 14, 44, 40))
      const contador = montar(VENCIMIENTO, CONGELADA_EN)

      vi.advanceTimersByTime(5000)
      await contador.vm.$nextTick()

      expect(contador.get('[data-testid="contador-texto"]').text()).toBe(
        'Vence en 1 d 01 h 10 min 10 s',
      )
      contador.unmount()
    })

    it('si ya había vencido al congelarse muestra fijo cuánto hacía que venció', () => {
      vi.setSystemTime(new Date(2026, 10, 25, 9, 0, 0))

      const contador = montar(VENCIMIENTO, instanteUtc(new Date(2026, 10, 21, 20, 30, 0)))

      const span = contador.get('[data-testid="contador-vencimiento"]')
      expect(span.get('[data-testid="contador-texto"]').text()).toBe('Vencida hace 1 d 02 h 30 min')
      expect(span.attributes('data-vencida')).toBe('true')
      expect(span.classes()).toContain('text-muted-foreground')
      expect(span.classes()).not.toContain('text-destructive')
      contador.unmount()
    })

    it('al cambiar el vencimiento recalcula el valor fijo desde el mismo instante', async () => {
      vi.setSystemTime(new Date(2026, 10, 18, 14, 44, 40))
      const contador = montar(VENCIMIENTO, CONGELADA_EN)

      await contador.setProps({ vencimiento: '2026-11-19T18:00:00' })

      expect(contador.get('[data-testid="contador-texto"]').text()).toBe(
        'Vence en 01 h 10 min 10 s',
      )
      contador.unmount()
    })

    it('al descongelarse vuelve a contar en vivo desde el vencimiento', async () => {
      vi.setSystemTime(new Date(2026, 10, 20, 17, 59, 15))
      const contador = montar(VENCIMIENTO, CONGELADA_EN)

      await contador.setProps({ congeladaEn: null })

      const span = contador.get('[data-testid="contador-vencimiento"]')
      expect(span.text()).toBe('Vence en 00 h 00 min 45 s')
      expect(span.attributes('data-congelado')).toBeUndefined()
      expect(span.find('[data-icono-pausa]').exists()).toBe(false)
      vi.advanceTimersByTime(1000)
      await contador.vm.$nextTick()
      expect(span.text()).toBe('Vence en 00 h 00 min 44 s')
      contador.unmount()
    })
  })
})
