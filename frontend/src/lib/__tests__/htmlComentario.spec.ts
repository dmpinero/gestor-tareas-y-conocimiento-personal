import { describe, expect, it } from 'vitest'

import {
  htmlComentarioMostrado,
  sanitizarHtmlComentario,
  textoPlanoAHtml,
  textoVisible,
} from '../htmlComentario'

describe('sanitizarHtmlComentario', () => {
  it('conserva el formato permitido', () => {
    const html =
      '<p><strong>N</strong> <em>C</em> <u>S</u> <s>T</s><br></p><ul><li><p>a</p></li></ul><ol><li><p>b</p></li></ol>'

    expect(sanitizarHtmlComentario(html)).toBe(html)
  })

  it('quita scripts, manejadores de eventos y etiquetas no permitidas, conservando su texto', () => {
    const limpio = sanitizarHtmlComentario(
      '<p onclick="alert(1)">Hola</p><script>alert(1)</script><img src=x onerror=alert(1)><b>negrita</b><h1>titulo</h1>',
    )

    expect(limpio).toBe('<p>Hola</p>negritatitulo')
  })

  it('solo admite enlaces http, https y mailto, y fuerza target y rel', () => {
    const limpio = sanitizarHtmlComentario(
      '<a href="https://ejemplo.com" rel="opener" target="_self">web</a>' +
        '<a href="mailto:a@b.c">correo</a>' +
        '<a href="javascript:alert(1)">mal</a>' +
        '<a href="data:text/html,x">datos</a>' +
        '<a href="/relativa">relativa</a>',
    )
    const raiz = document.createElement('div')
    raiz.innerHTML = limpio
    const enlaces = [...raiz.querySelectorAll('a')]

    expect(enlaces.map((a) => a.getAttribute('href'))).toEqual([
      'https://ejemplo.com',
      'mailto:a@b.c',
      null,
      null,
      null,
    ])
    for (const enlace of enlaces) {
      expect(enlace.getAttribute('rel')).toBe('noopener noreferrer nofollow')
      expect(enlace.getAttribute('target')).toBe('_blank')
    }
  })

  it('limita style a color en span y a background-color en mark', () => {
    const limpio = sanitizarHtmlComentario(
      '<span style="color: #ef4444; font-size: 40px; background-image: url(x)">rojo</span>' +
        '<mark data-color="#fef08a" style="background-color: #fef08a; color: inherit">resaltado</mark>' +
        '<p style="color: red">parrafo</p>' +
        '<span style="color: expression(alert(1))">raro</span>',
    )

    expect(limpio).toBe(
      '<span style="color: #ef4444">rojo</span>' +
        '<mark data-color="#fef08a" style="background-color: #fef08a">resaltado</mark>' +
        '<p>parrafo</p>' +
        '<span>raro</span>',
    )
  })

  it('no admite otros atributos data-* ni clases', () => {
    expect(
      sanitizarHtmlComentario('<span class="x" data-otro="1" data-color="#000">t</span>'),
    ).toBe('<span>t</span>')
  })
})

describe('textoVisible', () => {
  it('quita las etiquetas, decodifica entidades y recorta los extremos', () => {
    expect(textoVisible('<p> <strong>a &amp; b</strong></p><p>c&nbsp;</p> ')).toBe('a & bc')
  })

  it('es vacío para párrafos sin texto', () => {
    expect(textoVisible('<p> </p><p></p>')).toBe('')
    expect(textoVisible('')).toBe('')
  })
})

describe('textoPlanoAHtml y htmlComentarioMostrado', () => {
  it('convierte el texto plano en un párrafo escapado por línea', () => {
    expect(textoPlanoAHtml('a < b\n\nc & d')).toBe('<p>a &lt; b</p><p></p><p>c &amp; d</p>')
  })

  it('muestra el texto plano como párrafos y el HTML saneado', () => {
    expect(htmlComentarioMostrado('Línea 1\nLínea 2')).toBe('<p>Línea 1</p><p>Línea 2</p>')
    expect(htmlComentarioMostrado('<p>Hola</p><script>x</script>')).toBe('<p>Hola</p>')
  })
})
