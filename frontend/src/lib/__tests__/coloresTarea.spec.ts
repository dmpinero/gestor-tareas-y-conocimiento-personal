import { describe, expect, it } from 'vitest'

import {
  PALETA_AVATARES,
  PALETA_ETIQUETAS,
  colorAvatar,
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
