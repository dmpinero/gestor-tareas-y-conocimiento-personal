import { describe, expect, it } from 'vitest'

import { aFechaHoraIso, formatearFechaHora, formatearMarcaTemporalFichero } from '@/lib/fechas'

describe('formatearFechaHora', () => {
  it('formatea un Date como dd/mm/aaaa hh:mm:ss en hora local', () => {
    expect(formatearFechaHora(new Date(2026, 0, 5, 7, 3, 9))).toBe('05/01/2026 07:03:09')
  })

  it('formatea una cadena ISO sin zona horaria tal como está escrita', () => {
    expect(formatearFechaHora('2026-11-09T18:45:30')).toBe('09/11/2026 18:45:30')
  })
})

describe('aFechaHoraIso', () => {
  it('convierte dd/mm/aaaa hh:mm:ss a ISO sin zona horaria', () => {
    expect(aFechaHoraIso('09/11/2026 18:45:30')).toBe('2026-11-09T18:45:30')
  })

  it('acepta espacios alrededor del valor', () => {
    expect(aFechaHoraIso('  29/02/2028 00:00:00 ')).toBe('2028-02-29T00:00:00')
  })

  it.each([
    ['', 'vacío'],
    ['09/11/2026', 'sin hora'],
    ['9/11/2026 18:45:30', 'día de una cifra'],
    ['2026-11-09T18:45:30', 'formato ISO'],
    ['09/11/2026 18/45/30', 'separadores de hora erróneos'],
    ['09/11/2026 18:45', 'sin segundos'],
  ])('devuelve null con una forma incorrecta: %s (%s)', (valor) => {
    expect(aFechaHoraIso(valor)).toBeNull()
  })

  it.each([
    ['31/02/2026 10:00:00', '31 de febrero'],
    ['29/02/2026 10:00:00', '29 de febrero en año no bisiesto'],
    ['00/01/2026 10:00:00', 'día cero'],
    ['10/13/2026 10:00:00', 'mes 13'],
    ['10/01/2026 25:00:00', 'hora 25'],
    ['10/01/2026 10:60:00', 'minuto 60'],
    ['10/01/2026 10:00:60', 'segundo 60'],
  ])('devuelve null con una fecha inexistente: %s (%s)', (valor) => {
    expect(aFechaHoraIso(valor)).toBeNull()
  })
})

describe('formatearMarcaTemporalFichero', () => {
  it('formatea un Date como ddmmaaaa_hhmmss en hora local', () => {
    expect(formatearMarcaTemporalFichero(new Date(2026, 0, 5, 9, 3, 7))).toBe('05012026_090307')
  })
})
