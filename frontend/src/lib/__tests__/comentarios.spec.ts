import { describe, expect, it } from 'vitest'

import {
  agruparComentariosPorDia,
  formatearDiaComentario,
  formatearHoraComentario,
  type Comentario,
} from '@/lib/comentarios'

// Las marcas se construyen desde la hora local y se pasan a UTC con `Z`, como
// las envía la API, para que los tests no dependan de la zona horaria.
function isoUtcDesdeLocal(
  anio: number,
  mes: number,
  dia: number,
  hora: number,
  minuto: number,
): string {
  return new Date(anio, mes - 1, dia, hora, minuto, 5).toISOString().replace(/\.\d{3}Z$/, 'Z')
}

function comentario(id: number, creado: string, texto = `Comentario ${id}`): Comentario {
  return { id, texto, creado }
}

const HOY = new Date(2026, 10, 10, 12, 0, 0)

describe('formatearHoraComentario', () => {
  it('muestra la hora local como HH:MM con dos cifras', () => {
    expect(formatearHoraComentario(isoUtcDesdeLocal(2026, 4, 1, 9, 5))).toBe('09:05')
  })

  it('convierte de UTC a hora local', () => {
    const local = new Date('2026-04-01T16:30:05Z')
    const esperado = `${String(local.getHours()).padStart(2, '0')}:${String(local.getMinutes()).padStart(2, '0')}`
    expect(formatearHoraComentario('2026-04-01T16:30:05Z')).toBe(esperado)
  })
})

describe('formatearDiaComentario', () => {
  it('muestra día de la semana, día y mes sin año si es el año en curso', () => {
    expect(formatearDiaComentario(new Date(2026, 3, 1, 10, 0), HOY)).toBe('miércoles, 1 de abril')
  })

  it('añade el año cuando no es el año en curso', () => {
    expect(formatearDiaComentario(new Date(2025, 11, 31, 10, 0), HOY)).toBe(
      'miércoles, 31 de diciembre de 2025',
    )
  })
})

describe('agruparComentariosPorDia', () => {
  it('devuelve una lista vacía sin comentarios', () => {
    expect(agruparComentariosPorDia([], HOY)).toEqual([])
  })

  it('agrupa por día local en orden cronológico, con etiqueta y hora', () => {
    const primero = comentario(1, isoUtcDesdeLocal(2026, 4, 1, 23, 50))
    const segundo = comentario(2, isoUtcDesdeLocal(2026, 4, 2, 0, 10))
    const tercero = comentario(3, isoUtcDesdeLocal(2026, 4, 2, 8, 0))

    const grupos = agruparComentariosPorDia([primero, segundo, tercero], HOY)

    expect(grupos.map((grupo) => grupo.etiqueta)).toEqual([
      'miércoles, 1 de abril',
      'jueves, 2 de abril',
    ])
    expect(grupos.map((grupo) => grupo.clave)).toEqual(['2026-04-01', '2026-04-02'])
    expect(grupos.map((grupo) => grupo.comentarios.map((c) => [c.id, c.hora]))).toEqual([
      [[1, '23:50']],
      [
        [2, '00:10'],
        [3, '08:00'],
      ],
    ])
  })

  it('ordena cronológicamente aunque lleguen desordenados', () => {
    const antiguo = comentario(1, isoUtcDesdeLocal(2026, 4, 1, 10, 0))
    const reciente = comentario(2, isoUtcDesdeLocal(2026, 4, 3, 10, 0))

    const grupos = agruparComentariosPorDia([reciente, antiguo], HOY)

    expect(grupos.map((grupo) => grupo.comentarios[0]!.id)).toEqual([1, 2])
  })

  it('conserva el texto tal cual, con sus saltos de línea', () => {
    const conSaltos = comentario(1, isoUtcDesdeLocal(2026, 4, 1, 10, 0), 'Línea 1\nLínea 2')

    const grupos = agruparComentariosPorDia([conSaltos], HOY)

    expect(grupos[0]!.comentarios[0]!.texto).toBe('Línea 1\nLínea 2')
  })
})
