import { describe, expect, it } from 'vitest'

import { htmlRespuesta } from '../markdownRespuesta'

// Una nota de Notion con instrucciones podría hacer que Claude escriba HTML:
// nada de lo que se pinta puede cargar recursos externos ni ejecutar código.
describe('htmlRespuesta', () => {
  it.each([
    ['vídeo', '<video poster="https://malo/p.png" src="https://malo/v.mp4"></video>', 'video'],
    ['audio', '<audio src="https://malo/a.mp3"></audio>', 'audio'],
    ['picture', '<picture><source srcset="https://malo/s.png"></picture>', 'source'],
    ['svg con imagen', '<svg><image href="https://malo/x.png"></image></svg>', 'svg'],
    ['math', '<math><mi>x</mi></math>', 'math'],
    ['imagen', '<img src="https://malo/i.png">', 'img'],
    ['iframe', '<iframe src="https://malo"></iframe>', 'iframe'],
    ['textarea', '<textarea>x</textarea>', 'textarea'],
    ['select', '<select><option>x</option></select>', 'select'],
  ])('quita las etiquetas de %s', async (_nombre, html, etiqueta) => {
    const resultado = await htmlRespuesta(`Texto ${html}`)
    expect(resultado).not.toContain(`<${etiqueta}`)
    expect(resultado).not.toContain('https://malo')
  })

  it('la imagen de Markdown tampoco se pinta', async () => {
    expect(await htmlRespuesta('![x](https://malo/i.png)')).not.toContain('https://malo')
  })

  it('quita los enlaces javascript: y data:, y abre los demás en una pestaña nueva', async () => {
    const resultado = await htmlRespuesta(
      '[a](javascript:alert(1)) [b](data:text/html,x) [c](https://www.notion.so/p1)',
    )
    expect(resultado).not.toContain('javascript:')
    expect(resultado).not.toContain('data:text')
    expect(resultado).toContain('href="https://www.notion.so/p1"')
    expect(resultado).toContain('target="_blank"')
    expect(resultado).toContain('rel="noopener noreferrer"')
  })

  it('conserva el formato normal', async () => {
    const resultado = await htmlRespuesta('**negrita**, `código` y\n\n- lista')
    expect(resultado).toContain('<strong>negrita</strong>')
    expect(resultado).toContain('<code>código</code>')
    expect(resultado).toContain('<li>lista</li>')
  })
})
