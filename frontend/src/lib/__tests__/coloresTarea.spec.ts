import { describe, expect, it } from 'vitest'

import {
  PALETA_AVATARES,
  PALETA_ETIQUETAS,
  colorAvatar,
  colorEstadoTablero,
  colorEtiqueta,
  inicialesDe,
} from '@/lib/coloresTarea'

describe('colorEtiqueta y colorAvatar', () => {
  it('dan siempre el mismo color de su paleta para el mismo nombre', () => {
    for (const nombre of ['Backend', 'Urgente', 'Ana', 'José Luis', '']) {
      expect(colorEtiqueta(nombre)).toBe(colorEtiqueta(nombre))
      expect(PALETA_ETIQUETAS).toContain(colorEtiqueta(nombre))
      expect(colorAvatar(nombre)).toBe(colorAvatar(nombre))
      expect(PALETA_AVATARES).toContain(colorAvatar(nombre))
    }
  })

  it('reparte nombres distintos entre varios colores', () => {
    const nombres = ['Backend', 'Frontend', 'Urgente', 'Bug', 'Docs', 'Infra', 'QA', 'Diseño']
    expect(new Set(nombres.map(colorEtiqueta)).size).toBeGreaterThan(1)
    expect(new Set(nombres.map(colorAvatar)).size).toBeGreaterThan(1)
  })

  it('cada color tiene su variante para el modo oscuro', () => {
    for (const clases of PALETA_ETIQUETAS) expect(clases).toMatch(/dark:bg-/)
  })
})

describe('inicialesDe', () => {
  it.each([
    ['Ana', 'A'],
    ['ana lópez', 'AL'],
    ['  María José   Pérez Gil ', 'MJ'],
    ['Álvaro', 'Á'],
    ['', '?'],
  ])('%s → %s', (nombre, esperado) => {
    expect(inicialesDe(nombre)).toBe(esperado)
  })
})

describe('colorEstadoTablero', () => {
  it('el primer estado es gris, el último verde y los intermedios azul, naranja, violeta…', () => {
    const colores = [0, 1, 2, 3, 4].map((indice) => colorEstadoTablero(indice, 5).cabecera)
    expect(colores[0]).toContain('bg-gray-600')
    expect(colores[1]).toContain('bg-blue-700')
    expect(colores[2]).toContain('bg-orange-700')
    expect(colores[3]).toContain('bg-violet-700')
    expect(colores[4]).toContain('bg-emerald-700')
    expect(new Set(colores).size).toBe(5)
  })

  it('las cabeceras llevan texto blanco y el relleno de la barra su variante oscura', () => {
    for (const indice of [0, 1, 2, 3, 4, 5, 6, 7]) {
      const { cabecera, relleno } = colorEstadoTablero(indice, 8)
      expect(cabecera).toContain('text-white')
      expect(relleno).toMatch(/^bg-\S+ dark:bg-\S+$/)
    }
  })

  it('con un solo estado, o un estado que no está en el grupo, usa el gris', () => {
    expect(colorEstadoTablero(0, 1).cabecera).toContain('bg-gray-600')
    expect(colorEstadoTablero(-1, 3).cabecera).toContain('bg-gray-600')
  })

  it('con tres estados coincide con los tonos de la píldora de la tabla', () => {
    expect(colorEstadoTablero(1, 3).cabecera).toContain('blue')
    expect(colorEstadoTablero(2, 3).cabecera).toContain('emerald')
  })
})
