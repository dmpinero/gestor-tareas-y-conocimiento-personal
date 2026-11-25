import { describe, expect, it } from 'vitest'

import { estaHibernada, instanteCongelado } from '@/lib/hibernacion'

describe('instanteCongelado', () => {
  it('sin congelar ni hibernar devuelve null', () => {
    expect(instanteCongelado({ congelada_en: null, hibernada_desde: null })).toBeNull()
  })

  it('si la API no manda `hibernada_desde` usa solo `congelada_en`', () => {
    expect(instanteCongelado({ congelada_en: '2026-11-20T10:00:00Z' })).toBe('2026-11-20T10:00:00Z')
    expect(instanteCongelado({ congelada_en: null })).toBeNull()
  })

  it('solo hibernada devuelve el instante de la hibernación', () => {
    expect(instanteCongelado({ congelada_en: null, hibernada_desde: '2026-11-21T08:30:00Z' })).toBe(
      '2026-11-21T08:30:00Z',
    )
  })

  it('congelada e hibernada devuelve el instante más antiguo de los dos', () => {
    expect(
      instanteCongelado({
        congelada_en: '2026-11-22T09:00:00Z',
        hibernada_desde: '2026-11-21T08:30:00Z',
      }),
    ).toBe('2026-11-21T08:30:00Z')
    expect(
      instanteCongelado({
        congelada_en: '2026-11-20T09:00:00Z',
        hibernada_desde: '2026-11-21T08:30:00Z',
      }),
    ).toBe('2026-11-20T09:00:00Z')
  })
})

describe('estaHibernada', () => {
  it('es cierto solo con `hibernada_desde`', () => {
    expect(estaHibernada({ hibernada_desde: '2026-11-21T08:30:00Z' })).toBe(true)
    expect(estaHibernada({ hibernada_desde: null })).toBe(false)
    expect(estaHibernada({})).toBe(false)
  })
})
