import { describe, expect, it } from 'vitest'
import {
  aSolicitudAlta,
  aSolicitudAltaAxasMs3,
  nombrePrevisto,
  nombrePrevistoAxasMs3,
  validarCamposAlta,
  validarCamposAxasMs3,
  type CamposAlta,
  type CamposAltaAxasMs3,
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

describe('alta AXAS MS3', () => {
  const VALIDOS: CamposAltaAxasMs3 = {
    codigo: 'AXAS0024',
    descripcion: 'Migración portal',
    duracion: '6',
    importe: '10000,50',
    coste: '8000',
  }

  it('el nombre es AXAS-MS3-EV pegado a los 2 últimos caracteres del código, un guion y la descripción', () => {
    expect(nombrePrevistoAxasMs3('AXAS0024', '  Migración portal ')).toBe(
      'AXAS-MS3-EV24-Migración portal',
    )
    expect(nombrePrevistoAxasMs3('SERV-AB', 'Algo')).toBe('AXAS-MS3-EVAB-Algo')
  })

  it('sin código ni descripción el nombre muestra marcadores', () => {
    expect(nombrePrevistoAxasMs3('', '')).toBe('AXAS-MS3-EVXX-descripción')
  })

  it('el código y la descripción son obligatorios; duración, importe y coste como en ANES', () => {
    expect(validarCamposAxasMs3(VALIDOS)).toEqual({})
    expect(
      validarCamposAxasMs3({
        codigo: '',
        descripcion: '  ',
        duracion: '0',
        importe: '',
        coste: 'x',
      }),
    ).toEqual({
      codigo: 'Elige o crea un código de servicio.',
      descripcion: 'La descripción es obligatoria.',
      duracion: 'La duración debe ser un número entero de meses mayor que cero.',
      importe: 'El importe total previsto es obligatorio.',
      coste: 'El coste total previsto debe ser un número mayor o igual que cero.',
    })
  })

  it('construye la petición con la descripción recortada y los números', () => {
    expect(aSolicitudAltaAxasMs3({ ...VALIDOS, descripcion: ' Migración portal ' })).toEqual({
      codigo_servicio: 'AXAS0024',
      descripcion: 'Migración portal',
      duracion: 6,
      importe: 10000.5,
      coste: 8000,
    })
  })
})
