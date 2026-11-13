import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import AvisoVencimiento from '../AvisoVencimiento.vue'

// Ahora: 13/11/2026 12:00:00 (hora local).
const AHORA = new Date(2026, 10, 13, 12, 0, 0)

// Se desmontan al acabar cada test para que el reloj compartido se detenga.
const montados: { unmount: () => void }[] = []

function montar(vencimiento: string | null, completada = false) {
  const envoltorio = mount(AvisoVencimiento, { props: { vencimiento, completada } })
  montados.push(envoltorio)
  return envoltorio
}

function campanas(envoltorio: ReturnType<typeof montar>) {
  return envoltorio.findAll('[data-campana]')
}

describe('AvisoVencimiento', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(AHORA)
  })
  afterEach(() => {
    montados.splice(0).forEach((envoltorio) => envoltorio.unmount())
    vi.useRealTimers()
  })

  it('con menos de 2 días para vencer muestra una campana animada', () => {
    const envoltorio = montar('2026-11-15T10:00:00')
    expect(campanas(envoltorio)).toHaveLength(1)
    const aviso = envoltorio.get('[role="img"]')
    expect(aviso.attributes('aria-label')).toBe('Vence en menos de 2 días')
    expect(aviso.attributes('title')).toBe('Vence en menos de 2 días')
    expect(campanas(envoltorio)[0]!.classes()).toContain('motion-safe:animate-campana')
  })

  it('con menos de 1 día para vencer muestra dos campanas', () => {
    const envoltorio = montar('2026-11-14T08:00:00')
    expect(campanas(envoltorio)).toHaveLength(2)
    expect(envoltorio.get('[role="img"]').attributes('aria-label')).toBe('Vence en menos de 1 día')
  })

  it('con 2 días o más no muestra nada', () => {
    expect(montar('2026-11-15T12:00:00').html()).toBe('<!--v-if-->')
  })

  it('no avisa si la tarea está completada, ya vencida o sin vencimiento', () => {
    expect(campanas(montar('2026-11-14T08:00:00', true))).toHaveLength(0)
    expect(campanas(montar('2026-11-13T11:00:00'))).toHaveLength(0)
    expect(campanas(montar(null))).toHaveLength(0)
  })

  it('pasa de una a dos campanas sola cuando baja de 24 h', async () => {
    const envoltorio = montar('2026-11-14T12:00:05')
    expect(campanas(envoltorio)).toHaveLength(1)

    await vi.advanceTimersByTimeAsync(10_000)

    expect(campanas(envoltorio)).toHaveLength(2)
  })
})
