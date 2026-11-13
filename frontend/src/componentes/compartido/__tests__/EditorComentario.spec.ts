import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'

import EditorComentario from '../EditorComentario.vue'

let contenedor: VueWrapper | null = null

async function montar(
  props: Partial<{ modelValue: string; soloLectura: boolean; autoenfoque: boolean }> = {},
): Promise<VueWrapper> {
  contenedor = mount(EditorComentario, {
    props: {
      modelValue: '',
      etiqueta: 'Escribe un comentario',
      id: 'campo-prueba',
      'onUpdate:modelValue': (valor: string) => contenedor?.setProps({ modelValue: valor }),
      ...props,
    },
    attachTo: document.body,
  })
  await flushPromises()
  return contenedor
}

function editable(envoltorio: VueWrapper) {
  return envoltorio.get('[role="textbox"]')
}

function boton(nombre: string): HTMLButtonElement {
  // Por nombre accesible: aria-label o, si no tiene, su texto.
  const encontrado = [...document.querySelectorAll<HTMLButtonElement>('button')].find(
    (b) => (b.getAttribute('aria-label') ?? b.textContent?.trim()) === nombre,
  )
  if (!encontrado) throw new Error(`No hay botón «${nombre}»`)
  return encontrado
}

function ultimoValor(envoltorio: VueWrapper): string {
  const emitidos = envoltorio.emitted('update:modelValue') ?? []
  return (emitidos[emitidos.length - 1]?.[0] as string | undefined) ?? ''
}

async function seleccionarTodo(envoltorio: VueWrapper): Promise<void> {
  await editable(envoltorio).trigger('keydown', { key: 'a', ctrlKey: true })
  await flushPromises()
}

// Los popovers de reka-ui abren y cierran en el siguiente fotograma: se espera
// a él para que el siguiente clic no los encuentre a medias.
async function pulsar(nombre: string): Promise<void> {
  boton(nombre).click()
  await flushPromises()
  await new Promise((resolver) => requestAnimationFrame(() => setTimeout(resolver)))
  await flushPromises()
}

async function escribirUrl(valor: string): Promise<void> {
  const campoUrl = document.querySelector<HTMLInputElement>('input[aria-label="URL del enlace"]')!
  campoUrl.value = valor
  campoUrl.dispatchEvent(new Event('input'))
  await flushPromises()
}

afterEach(() => {
  contenedor?.unmount()
  contenedor = null
  document.body.innerHTML = ''
})

describe('EditorComentario', () => {
  it('el área editable es un textbox multilínea con el nombre recibido', async () => {
    const envoltorio = await montar()

    const campo = editable(envoltorio)
    expect(campo.attributes('aria-label')).toBe('Escribe un comentario')
    expect(campo.attributes('aria-multiline')).toBe('true')
    expect(campo.attributes('id')).toBe('campo-prueba')
    expect(campo.attributes('contenteditable')).toBe('true')
  })

  it('la barra tiene los botones de formato con nombre y aria-pressed', async () => {
    await montar()

    for (const nombre of [
      'Negrita',
      'Cursiva',
      'Subrayado',
      'Tachado',
      'Color del texto',
      'Resaltado',
      'Lista con viñetas',
      'Lista numerada',
      'Enlace',
    ]) {
      expect(boton(nombre).getAttribute('aria-pressed')).toBe('false')
    }
  })

  it('muestra el contenido recibido por v-model', async () => {
    const envoltorio = await montar({ modelValue: '<p><strong>Hola</strong></p>' })

    expect(editable(envoltorio).element.innerHTML).toContain('<strong>Hola</strong>')
  })

  it.each([
    ['Negrita', '<p><strong>Hola</strong></p>'],
    ['Cursiva', '<p><em>Hola</em></p>'],
    ['Subrayado', '<p><u>Hola</u></p>'],
    ['Tachado', '<p><s>Hola</s></p>'],
    ['Lista con viñetas', '<ul><li><p>Hola</p></li></ul>'],
    ['Lista numerada', '<ol><li><p>Hola</p></li></ol>'],
  ])('el botón %s aplica su formato y queda pulsado', async (nombre, esperado) => {
    const envoltorio = await montar({ modelValue: '<p>Hola</p>' })
    await seleccionarTodo(envoltorio)

    await pulsar(nombre)

    expect(ultimoValor(envoltorio)).toBe(esperado)
    expect(boton(nombre).getAttribute('aria-pressed')).toBe('true')
  })

  it('los atajos de teclado de Tiptap siguen funcionando (Ctrl+B)', async () => {
    const envoltorio = await montar({ modelValue: '<p>Hola</p>' })
    await seleccionarTodo(envoltorio)

    await editable(envoltorio).trigger('keydown', { key: 'b', ctrlKey: true })
    await flushPromises()

    expect(ultimoValor(envoltorio)).toBe('<p><strong>Hola</strong></p>')
  })

  it('el color del texto se elige de una paleta y se puede quitar', async () => {
    const envoltorio = await montar({ modelValue: '<p>Hola</p>' })
    await seleccionarTodo(envoltorio)

    await pulsar('Color del texto')
    await pulsar('Rojo')
    expect(ultimoValor(envoltorio)).toMatch(
      /^<p><span style="color: (#dc2626|rgb\(220, 38, 38\));?">Hola<\/span><\/p>$/,
    )
    expect(boton('Color del texto').getAttribute('aria-pressed')).toBe('true')

    await pulsar('Color del texto')
    await pulsar('Quitar color')
    expect(ultimoValor(envoltorio)).toBe('<p>Hola</p>')
  })

  it('el resaltado se elige de una paleta y se puede quitar', async () => {
    const envoltorio = await montar({ modelValue: '<p>Hola</p>' })
    await seleccionarTodo(envoltorio)

    await pulsar('Resaltado')
    await pulsar('Amarillo')
    expect(ultimoValor(envoltorio)).toMatch(
      /^<p><mark data-color="#[0-9a-f]{6}"[^>]*>Hola<\/mark><\/p>$/,
    )

    await pulsar('Resaltado')
    await pulsar('Quitar resaltado')
    expect(ultimoValor(envoltorio)).toBe('<p>Hola</p>')
  })

  it('el enlace pide la URL en línea y la aplica', async () => {
    const envoltorio = await montar({ modelValue: '<p>Hola</p>' })
    await seleccionarTodo(envoltorio)

    await pulsar('Enlace')
    await escribirUrl('https://ejemplo.com')
    await pulsar('Aplicar enlace')

    expect(ultimoValor(envoltorio)).toContain('href="https://ejemplo.com"')
    expect(ultimoValor(envoltorio)).toContain('rel="noopener noreferrer nofollow"')
    expect(boton('Enlace').getAttribute('aria-pressed')).toBe('true')

    await pulsar('Enlace')
    await pulsar('Quitar enlace')
    expect(ultimoValor(envoltorio)).toBe('<p>Hola</p>')
  })

  it('rechaza enlaces que no sean http, https o mailto', async () => {
    const envoltorio = await montar({ modelValue: '<p>Hola</p>' })
    await seleccionarTodo(envoltorio)

    await pulsar('Enlace')
    await escribirUrl('javascript:alert(1)')
    await pulsar('Aplicar enlace')

    expect(document.querySelector('[role="alert"]')?.textContent).toContain('http://')
    expect(ultimoValor(envoltorio)).not.toContain('href')
  })

  it.each([
    ['Ctrl+Enter', { ctrlKey: true }],
    ['Cmd+Enter', { metaKey: true }],
  ])('%s emite enviar', async (_nombre, modificador) => {
    const envoltorio = await montar({ modelValue: '<p>Hola</p>' })

    await editable(envoltorio).trigger('keydown', { key: 'Enter', ...modificador })

    expect(envoltorio.emitted('enviar')).toHaveLength(1)
  })

  it('Enter sin modificador no emite enviar', async () => {
    const envoltorio = await montar({ modelValue: '<p>Hola</p>' })

    await editable(envoltorio).trigger('keydown', { key: 'Enter' })

    expect(envoltorio.emitted('enviar')).toBeUndefined()
  })

  it('al vaciarse el v-model desde fuera, el editor queda vacío', async () => {
    const envoltorio = await montar({ modelValue: '<p>Hola</p>' })

    await envoltorio.setProps({ modelValue: '' })
    await flushPromises()

    expect(editable(envoltorio).text()).toBe('')
  })

  it('no deja pasar de 500 caracteres visibles', async () => {
    const envoltorio = await montar({ modelValue: `<p>${'a'.repeat(500)}</p>` })
    const vm = envoltorio.vm as unknown as {
      editor: { commands: { insertContent: (t: string) => boolean } }
    }

    vm.editor.commands.insertContent('b')
    await flushPromises()

    expect(editable(envoltorio).text()).toBe('a'.repeat(500))
  })

  it('en solo lectura no es editable y desactiva la barra', async () => {
    const envoltorio = await montar({ modelValue: '<p>Hola</p>', soloLectura: true })

    expect(editable(envoltorio).attributes('contenteditable')).toBe('false')
    expect(editable(envoltorio).attributes('aria-readonly')).toBe('true')
    expect(boton('Negrita').disabled).toBe(true)
  })

  it('Escape llega a la ventana sin cancelar y una sola vez, para que la modal se cierre', async () => {
    // ProseMirror cancela el Escape (preventDefault) y las modales de reka-ui
    // no se cierran con un Escape cancelado.
    const envoltorio = await montar()
    const recibidos: boolean[] = []
    const alPulsar = (evento: KeyboardEvent): void => {
      if (evento.key === 'Escape') recibidos.push(evento.defaultPrevented)
    }
    window.addEventListener('keydown', alPulsar)
    try {
      editable(envoltorio).element.dispatchEvent(
        new KeyboardEvent('keydown', {
          key: 'Escape',
          keyCode: 27,
          bubbles: true,
          cancelable: true,
        }),
      )
      await flushPromises()
    } finally {
      window.removeEventListener('keydown', alPulsar)
    }

    expect(recibidos).toEqual([false])
  })

  it('no recorta un comentario guardado que ya pasa del límite al abrirlo para editar', async () => {
    // 300 emoji son 300 caracteres para la API, pero 600 unidades UTF-16.
    const guardado = `<p>${'😀'.repeat(300)}</p>`
    const envoltorio = await montar({ modelValue: guardado, autoenfoque: true })
    // El enfoque inicial llega tras un instante y es la transacción que recortaba.
    await new Promise((resolver) => setTimeout(resolver, 50))
    await flushPromises()

    expect(editable(envoltorio).text()).toBe('😀'.repeat(300))
    const emitidos = (envoltorio.emitted('update:modelValue') ?? []).map((e) => e[0])
    expect(emitidos.every((valor) => valor === guardado)).toBe(true)
  })
})
