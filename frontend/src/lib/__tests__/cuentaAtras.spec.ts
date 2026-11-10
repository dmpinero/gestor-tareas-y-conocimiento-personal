import { describe, expect, it } from 'vitest'

import { calcularCuentaAtras } from '@/lib/cuentaAtras'

// El vencimiento se interpreta en hora local, igual que el resto de fechas.
const VENCIMIENTO = '2026-11-20T18:00:00'

describe('calcularCuentaAtras', () => {
  it('con días restantes muestra días sin rellenar y horas, minutos y segundos a dos cifras', () => {
    const ahora = new Date(2026, 10, 18, 14, 44, 40)

    expect(calcularCuentaAtras(VENCIMIENTO, ahora)).toEqual({
      texto: 'Vence en 2 d 03 h 15 min 20 s',
      vencida: false,
    })
  })

  it('no rellena los días de dos o más cifras', () => {
    const ahora = new Date(2026, 10, 9, 18, 45, 30)

    expect(calcularCuentaAtras(VENCIMIENTO, ahora).texto).toBe('Vence en 10 d 23 h 14 min 30 s')
  })

  it('con menos de un día omite los días', () => {
    const ahora = new Date(2026, 10, 20, 17, 59, 15)

    expect(calcularCuentaAtras(VENCIMIENTO, ahora)).toEqual({
      texto: 'Vence en 00 h 00 min 45 s',
      vencida: false,
    })
  })

  it('en el instante exacto del vencimiento la tarea ya está vencida', () => {
    const ahora = new Date(2026, 10, 20, 18, 0, 0)

    expect(calcularCuentaAtras(VENCIMIENTO, ahora)).toEqual({
      texto: 'Vencida hace 00 h 00 min',
      vencida: true,
    })
  })

  it('vencida muestra días, horas y minutos sin segundos y con los minutos truncados', () => {
    const ahora = new Date(2026, 10, 21, 20, 5, 59)

    expect(calcularCuentaAtras(VENCIMIENTO, ahora)).toEqual({
      texto: 'Vencida hace 1 d 02 h 05 min',
      vencida: true,
    })
  })

  it('vencida hace menos de un día omite los días', () => {
    const ahora = new Date(2026, 10, 20, 18, 0, 59)

    expect(calcularCuentaAtras(VENCIMIENTO, ahora).texto).toBe('Vencida hace 00 h 00 min')
  })

  it('descarta las milésimas del instante actual al calcular los segundos que faltan', () => {
    const ahora = new Date(2026, 10, 20, 17, 59, 15, 400)

    expect(calcularCuentaAtras(VENCIMIENTO, ahora).texto).toBe('Vence en 00 h 00 min 44 s')
  })
})
