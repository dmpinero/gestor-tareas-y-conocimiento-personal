import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import VencimientoCorto from '../VencimientoCorto.vue'

// Ahora: 13/11/2026 12:00:00 (hora local); el vencimiento ya pasó.
const AHORA = new Date(2026, 10, 13, 12, 0, 0)
const VENCIDA = '2026-11-12T10:00:00'

// Se desmontan al acabar cada test para que el reloj compartido se detenga.
const montados: { unmount: () => void }[] = []

function montar(completada: boolean, congeladaEn: string | null = null) {
  const envoltorio = mount(VencimientoCorto, {
    props: { vencimiento: VENCIDA, completada, congeladaEn },
  })
  montados.push(envoltorio)
  return envoltorio
}

function icono(envoltorio: ReturnType<typeof montar>) {
  return envoltorio.get('[data-testid="vencimiento-corto"]').attributes('data-icono')
}

describe('VencimientoCorto', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(AHORA)
  })
  afterEach(() => {
    montados.splice(0).forEach((envoltorio) => envoltorio.unmount())
    vi.useRealTimers()
  })

  it('marca como vencida una tarea pendiente cuyo vencimiento ya pasó', () => {
    expect(icono(montar(false))).toBe('vencida')
  })

  it('marca como completada una tarea completada', () => {
    expect(icono(montar(true, '2026-11-12T09:00:00Z'))).toBe('completada')
  })

  it('no marca como vencida una tarea con el contador congelado (en DONE)', () => {
    const envoltorio = montar(false, '2026-11-12T09:00:00Z')
    expect(icono(envoltorio)).toBeUndefined()
    expect(envoltorio.find('svg').exists()).toBe(false)
  })
})
