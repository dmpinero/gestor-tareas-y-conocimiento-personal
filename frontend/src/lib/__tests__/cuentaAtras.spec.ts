import { describe, expect, it } from 'vitest'

import { calcularCuentaAtras } from '@/lib/cuentaAtras'

// El vencimiento se interpreta en hora local, igual que el resto de fechas.
const VENCIMIENTO = '2026-11-20T18:00:00'

describe('calcularCuentaAtras', () => {
  it('con días restantes muestra días sin rellenar y horas, minutos y segundos a dos cifras', () => {
    const ahora = new Date(2026, 10, 18, 14, 44, 40)

    expect(calcularCuentaAtras(VENCIMIENTO, ahora)).toMatchObject({
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

    expect(calcularCuentaAtras(VENCIMIENTO, ahora)).toMatchObject({
      texto: 'Vence en 00 h 00 min 45 s',
      vencida: false,
    })
  })

  it('en el instante exacto del vencimiento la tarea ya está vencida', () => {
    const ahora = new Date(2026, 10, 20, 18, 0, 0)

    expect(calcularCuentaAtras(VENCIMIENTO, ahora)).toMatchObject({
      texto: 'Vencida hace 00 h 00 min',
      vencida: true,
    })
  })

  it('vencida muestra días, horas y minutos sin segundos y con los minutos truncados', () => {
    const ahora = new Date(2026, 10, 21, 20, 5, 59)

    expect(calcularCuentaAtras(VENCIMIENTO, ahora)).toMatchObject({
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

  describe('nivel de urgencia', () => {
    // Vencimiento: 20/11/2026 18:00:00 (hora local).
    const casos: [string, Date, string][] = [
      ['vencida', new Date(2026, 10, 20, 18, 0, 0), 'vencida'],
      ['quedan 23 h 59 min 59 s', new Date(2026, 10, 19, 18, 0, 1), 'menos-de-24h'],
      ['quedan exactamente 24 h', new Date(2026, 10, 19, 18, 0, 0), 'menos-de-48h'],
      ['quedan 47 h 59 min 59 s', new Date(2026, 10, 18, 18, 0, 1), 'menos-de-48h'],
      ['quedan exactamente 48 h', new Date(2026, 10, 18, 18, 0, 0), 'holgada'],
      ['quedan varios días', new Date(2026, 10, 10, 9, 0, 0), 'holgada'],
    ]

    for (const [caso, ahora, nivel] of casos) {
      it(`${caso} → ${nivel}`, () => {
        expect(calcularCuentaAtras(VENCIMIENTO, ahora).nivel).toBe(nivel)
      })
    }
  })
})
