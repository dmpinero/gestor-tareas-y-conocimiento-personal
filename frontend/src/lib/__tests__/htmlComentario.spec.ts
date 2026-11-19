import { describe, expect, it } from 'vitest'

import {
  htmlComentarioMostrado,
  sanitizarHtmlComentario,
  textoPlanoAHtml,
  textoVisible,
  tieneContenidoComentario,
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

describe('imágenes de los comentarios', () => {
  const ID = '0123456789abcdef0123456789abcdef'
  const SRC = `/api/v1/imagenes/${ID}`

  it('conserva las imágenes guardadas en la aplicación con su texto alternativo', () => {
    const html = `<p>Mira:</p><img src="${SRC}" alt="Captura de pantalla">`

    expect(sanitizarHtmlComentario(html)).toBe(html)
  })

  it.each([
    'https://ejemplo.com/a.png',
    `//ejemplo.com${SRC}`,
    'data:image/png;base64,iVBORw0KGgo=',
    'javascript:alert(1)',
    '/api/v1/imagenes/../tareas',
    `${SRC}/../../tareas`,
    `${SRC}?x=1`,
    '/api/v1/imagenes/123',
    '/api/v1/tareas/1',
    '',
  ])('quita las imágenes que no son de la aplicación (%s)', (src) => {
    expect(sanitizarHtmlComentario(`<p>a</p><img src="${src}" alt="x">`)).toBe('<p>a</p>')
  })

  it('quita a las imágenes los atributos no permitidos', () => {
    expect(
      sanitizarHtmlComentario(
        `<img src="${SRC}" alt="x" onerror="alert(1)" style="position:fixed" width="9" title="t" class="c" srcset="https://e.com/a.png 2x">`,
      ),
    ).toBe(`<img src="${SRC}" alt="x">`)
  })

  it('tieneContenidoComentario cuenta las imágenes guardadas como contenido', () => {
    expect(tieneContenidoComentario(`<img src="${SRC}" alt="x">`)).toBe(true)
    expect(tieneContenidoComentario('<p>a</p>')).toBe(true)
    expect(tieneContenidoComentario('<p> </p>')).toBe(false)
    expect(tieneContenidoComentario('<img src="https://ejemplo.com/a.png">')).toBe(false)
    expect(tieneContenidoComentario('')).toBe(false)
  })

  it('al mostrarla, la imagen es un enlace que la abre entera en una pestaña nueva', () => {
    expect(htmlComentarioMostrado(`<p>a</p><img src="${SRC}" alt="Captura de pantalla">`)).toBe(
      `<p>a</p><a href="${SRC}" target="_blank" rel="noopener noreferrer nofollow"><img src="${SRC}" alt="Captura de pantalla"></a>`,
    )
  })

  it('al mostrarla, una imagen ya enlazada no se vuelve a enlazar', () => {
    const html = `<a href="https://ejemplo.com" target="_blank" rel="noopener noreferrer nofollow"><img src="${SRC}" alt="x"></a>`

    expect(htmlComentarioMostrado(html)).toBe(html)
  })
})

describe('saneado de imágenes y enlaces (pruebas de verificación)', () => {
  const H = '0123456789abcdef0123456789abcdef'
  const U = `/api/v1/imagenes/${H}`

  it('conserva el href de los enlaces con el esquema en mayúsculas', () => {
    expect(htmlComentarioMostrado('<p><a href="HTTPS://example.com">up</a></p>')).toContain(
      'href="HTTPS://example.com"',
    )
    expect(htmlComentarioMostrado('<p><a href="Mailto:a@b.c">m</a></p>')).toContain(
      'href="Mailto:a@b.c"',
    )
  })

  it.each([
    `<img src="${U.toUpperCase()}">`,
    `<img src="/api/v1/imagenes/\t${H}">`,
    `<img src="${U}?x">`,
    `<img src="//evil.com${U}">`,
    '<img src="data:image/png;base64,AAAA">',
    '<img src="javascript:alert(1)">',
    '<svg><image href="http://e/x"></image></svg>',
  ])('quita por completo %s', (entrada) => {
    expect(htmlComentarioMostrado(entrada)).toBe('')
  })

  it('de una imagen solo quedan src y alt, y se enlaza a sí misma', () => {
    const salida = htmlComentarioMostrado(
      `<img src="${U}" alt="&quot; onerror=&quot;x()" onerror="x()" srcset="http://e 1x" class="c">`,
    )
    const plantilla = document.createElement('template')
    plantilla.innerHTML = salida
    const enlace = plantilla.content.firstElementChild as HTMLAnchorElement
    expect(enlace.tagName).toBe('A')
    expect(enlace.getAttribute('href')).toBe(U)
    expect(enlace.getAttribute('target')).toBe('_blank')
    expect(enlace.getAttribute('rel')).toBe('noopener noreferrer nofollow')
    const imagen = enlace.querySelector('img')!
    expect(imagen.getAttributeNames().sort()).toEqual(['alt', 'src'])
    expect(imagen.getAttribute('src')).toBe(U)
    expect(imagen.getAttribute('alt')).toBe('" onerror="x()')
  })

  it('una imagen dentro de un enlace javascript: no conserva el javascript', () => {
    expect(
      htmlComentarioMostrado(`<a href="javascript:alert(1)"><img src="${U}"></a>`),
    ).not.toContain('javascript')
  })
})
