import { describe, expect, it } from 'vitest'

import { formatearTiempoFoco, textoFoco } from '@/lib/foco'

const DESDE = '2026-11-24T10:00:00'

describe('formatearTiempoFoco', () => {
  it('con menos de un minuto muestra "< 1 min"', () => {
    expect(formatearTiempoFoco(DESDE, new Date(2026, 10, 24, 10, 0, 59))).toBe('< 1 min')
  })

  it('si el reloj va por detrás de desde también muestra "< 1 min"', () => {
    expect(formatearTiempoFoco(DESDE, new Date(2026, 10, 24, 9, 58, 0))).toBe('< 1 min')
  })

  it('con menos de una hora muestra los minutos', () => {
    expect(formatearTiempoFoco(DESDE, new Date(2026, 10, 24, 10, 1, 0))).toBe('1 min')
    expect(formatearTiempoFoco(DESDE, new Date(2026, 10, 24, 10, 59, 59))).toBe('59 min')
  })

  it('con una hora o más muestra horas y minutos', () => {
    expect(formatearTiempoFoco(DESDE, new Date(2026, 10, 24, 11, 20, 30))).toBe('1 h 20 min')
    expect(formatearTiempoFoco(DESDE, new Date(2026, 10, 25, 12, 5, 0))).toBe('26 h 5 min')
  })

  it('con horas exactas omite los minutos', () => {
    expect(formatearTiempoFoco(DESDE, new Date(2026, 10, 24, 12, 0, 10))).toBe('2 h')
  })

  it('acepta un instante en UTC', () => {
    const desde = '2026-11-24T10:00:00Z'
    const ahora = new Date(Date.parse(desde) + 90 * 60_000)
    expect(formatearTiempoFoco(desde, ahora)).toBe('1 h 30 min')
  })
})

describe('textoFoco', () => {
  it('de una tarea muestra solo su nombre', () => {
    expect(
      textoFoco({
        tarea_id: 1,
        tarea_nombre: 'Migración portal',
        subtarea_id: null,
        subtarea_nombre: null,
        desde: DESDE,
      }),
    ).toBe('Migración portal')
  })

  it('de una subtarea muestra "Tarea › Subtarea"', () => {
    expect(
      textoFoco({
        tarea_id: 1,
        tarea_nombre: 'Migración portal',
        subtarea_id: 2,
        subtarea_nombre: 'Probar login',
        desde: DESDE,
      }),
    ).toBe('Migración portal › Probar login')
  })
})
