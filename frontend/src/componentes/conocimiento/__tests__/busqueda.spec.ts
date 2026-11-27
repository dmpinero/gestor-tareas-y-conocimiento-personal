import { describe, expect, it } from 'vitest'

import type { ResultadoBusquedaConocimiento } from '@/api/tipos'
import { agruparPorPagina, esUrlWeb, palabrasBuscadas, segmentosResaltados } from '../busqueda'

function resaltados(texto: string, consulta: string): string[] {
  return segmentosResaltados(texto, consulta)
    .filter((s) => s.resaltado)
    .map((s) => s.texto)
}

function unir(texto: string, consulta: string): string {
  return segmentosResaltados(texto, consulta)
    .map((s) => s.texto)
    .join('')
}

describe('palabrasBuscadas', () => {
  it('separa por lo que no es letra o número e ignora las de menos de 3 letras', () => {
    expect(palabrasBuscadas('¿Qué lleva la paella, de azafrán?')).toEqual([
      'que',
      'lleva',
      'paella',
      'azafran',
    ])
    expect(palabrasBuscadas('  * - ¿? ')).toEqual([])
  })
})

describe('segmentosResaltados', () => {
  it('resalta las palabras buscadas sin distinguir mayúsculas ni tildes', () => {
    const texto = 'La PAELLA lleva Azafrán y arroz.'
    expect(resaltados(texto, 'paella azafran')).toEqual(['PAELLA', 'Azafrán'])
    expect(resaltados('Reunión con Ana', 'REUNION')).toEqual(['Reunión'])
    expect(unir(texto, 'paella azafran')).toBe(texto)
  })

  it('solo resalta palabras enteras', () => {
    expect(resaltados('La paellera y la paella', 'paella')).toEqual(['paella'])
  })

  it('respeta los caracteres combinados y los que ocupan dos unidades', () => {
    const combinado = 'Café con 😀 cafe'
    expect(resaltados(combinado, 'café')).toEqual(['Café', 'cafe'])
    expect(unir(combinado, 'café')).toBe(combinado)
  })

  it('sin palabras que buscar devuelve el texto tal cual', () => {
    expect(segmentosResaltados('Hola', '* ?')).toEqual([{ texto: 'Hola', resaltado: false }])
    expect(segmentosResaltados('', 'hola')).toEqual([])
  })

  it('el HTML del fragmento queda como texto en los segmentos', () => {
    const texto = '<img src=x onerror="alert(1)"> paella'
    expect(segmentosResaltados(texto, 'paella')).toEqual([
      { texto: '<img src=x onerror="alert(1)"> ', resaltado: false },
      { texto: 'paella', resaltado: true },
    ])
  })
})

describe('agruparPorPagina', () => {
  const r = (id: string, orden: number, fragmento = `${id}${orden}`) =>
    ({
      pagina_id: id,
      titulo: `Título ${id}`,
      url: `https://n.so/${id}`,
      fragmento,
      orden,
    }) satisfies ResultadoBusquedaConocimiento

  it('agrupa por página en el orden de relevancia y sus trozos por su orden en la página', () => {
    const grupos = agruparPorPagina([r('b', 3), r('a', 0), r('b', 1)])
    expect(grupos).toEqual([
      {
        pagina_id: 'b',
        titulo: 'Título b',
        url: 'https://n.so/b',
        fragmentos: [
          { orden: 1, texto: 'b1' },
          { orden: 3, texto: 'b3' },
        ],
      },
      {
        pagina_id: 'a',
        titulo: 'Título a',
        url: 'https://n.so/a',
        fragmentos: [{ orden: 0, texto: 'a0' }],
      },
    ])
  })

  it('sin resultados no hay grupos', () => {
    expect(agruparPorPagina([])).toEqual([])
  })
})

describe('esUrlWeb', () => {
  it('solo acepta http y https', () => {
    expect(esUrlWeb('https://www.notion.so/p')).toBe(true)
    expect(esUrlWeb('HTTP://ejemplo.com')).toBe(true)
    expect(esUrlWeb('javascript:alert(1)')).toBe(false)
    expect(esUrlWeb('data:text/html,hola')).toBe(false)
    expect(esUrlWeb('')).toBe(false)
  })
})
