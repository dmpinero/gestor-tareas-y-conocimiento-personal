import { describe, expect, it } from 'vitest'
import {
  aSolicitudAlta,
  nombrePrevisto,
  validarCamposAlta,
  type CamposAlta,
} from '../altaOportunidad'

const VALIDOS: CamposAlta = {
  prj: 'PRJ-00001',
  descripcion: '',
  duracion: '2',
  importe: '10000',
  coste: '8500,50',
}

describe('validarCamposAlta', () => {
  it('no devuelve errores con campos válidos y descripción vacía', () => {
    expect(validarCamposAlta(VALIDOS)).toEqual({})
  })

  it.each(['PRJ-1234', 'PRJ-123456', 'prj-12345', 'PRJ12345', ''])(
    'rechaza el código "%s" con el mismo mensaje que el script',
    (prj) => {
      expect(validarCamposAlta({ ...VALIDOS, prj }).prj).toBe(
        'El código debe tener el formato PRJ-XXXXX (5 dígitos).',
      )
    },
  )

  it.each([
    ['duracion', '', 'La duración es obligatoria.'],
    ['duracion', '0', 'La duración debe ser un número entero de meses mayor que cero.'],
    ['duracion', '1,5', 'La duración debe ser un número entero de meses mayor que cero.'],
    ['importe', '', 'El importe total previsto es obligatorio.'],
    ['importe', '-5', 'El importe total previsto debe ser un número mayor o igual que cero.'],
    ['coste', ' ', 'El coste total previsto es obligatorio.'],
    ['coste', 'mucho', 'El coste total previsto debe ser un número mayor o igual que cero.'],
  ] as const)('el campo %s con "%s" da "%s"', (campo, valor, mensaje) => {
    expect(validarCamposAlta({ ...VALIDOS, [campo]: valor })[campo]).toBe(mensaje)
  })
})

describe('nombrePrevisto', () => {
  it('es el código seguido de la descripción', () => {
    expect(nombrePrevisto('PRJ-00001', ' Mi proyecto ')).toBe('PRJ-00001 Mi proyecto')
  })

  it('avisa de que la descripción se buscará en Notion si está vacía', () => {
    expect(nombrePrevisto('PRJ-00001', '')).toBe('PRJ-00001 + descripción (se buscará en Notion)')
  })
})

describe('aSolicitudAlta', () => {
  it('convierte los textos en números y omite la descripción vacía', () => {
    expect(aSolicitudAlta(VALIDOS)).toEqual({
      prj: 'PRJ-00001',
      descripcion: null,
      duracion: 2,
      importe: 10000,
      coste: 8500.5,
    })
  })
})
