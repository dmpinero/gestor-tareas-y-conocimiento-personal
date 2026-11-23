import { describe, expect, it } from 'vitest'

import {
  ERROR_CODIGO_SERVICIO_CON_ESPACIOS,
  ERROR_CODIGO_SERVICIO_CORTO,
  ERROR_CODIGO_SERVICIO_LARGO,
  MAX_CODIGO_SERVICIO,
  MIN_CODIGO_SERVICIO,
  validarCodigoServicio,
} from '../codigosServicio'

describe('validarCodigoServicio', () => {
  it('usa los mismos límites y mensajes que la API', () => {
    expect([MIN_CODIGO_SERVICIO, MAX_CODIGO_SERVICIO]).toEqual([2, 20])
    expect(ERROR_CODIGO_SERVICIO_CORTO).toBe(
      'El código de servicio debe tener al menos 2 caracteres.',
    )
    expect(ERROR_CODIGO_SERVICIO_LARGO).toBe(
      'El código de servicio no puede superar los 20 caracteres.',
    )
    expect(ERROR_CODIGO_SERVICIO_CON_ESPACIOS).toBe(
      'El código de servicio no puede contener espacios.',
    )
  })

  it.each(['AXAS0024', '24', 'A'.repeat(20), 'axas-0025'])('admite «%s»', (nombre) => {
    expect(validarCodigoServicio(nombre)).toEqual({ nombre })
  })

  it('recorta los espacios de los extremos', () => {
    expect(validarCodigoServicio('  AXAS0024 \t')).toEqual({ nombre: 'AXAS0024' })
  })

  it.each(['', '   ', 'A', ' A '])('rechaza «%s» por corto', (nombre) => {
    expect(validarCodigoServicio(nombre)).toEqual({ error: ERROR_CODIGO_SERVICIO_CORTO })
  })

  it('rechaza más de 20 caracteres', () => {
    expect(validarCodigoServicio('A'.repeat(21))).toEqual({ error: ERROR_CODIGO_SERVICIO_LARGO })
  })

  it.each(['AX AS', 'AX\tAS', 'AX AS'])('rechaza los espacios interiores (%j)', (nombre) => {
    expect(validarCodigoServicio(nombre)).toEqual({ error: ERROR_CODIGO_SERVICIO_CON_ESPACIOS })
  })
})
