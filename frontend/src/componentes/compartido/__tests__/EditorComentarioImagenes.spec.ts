import { Slice } from '@tiptap/pm/model'
import type { Editor } from '@tiptap/vue-3'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Ref } from 'vue'

import { ErrorApi } from '@/api/cliente'
import { subirImagen } from '@/api/imagenes'
import EditorComentario from '../EditorComentario.vue'

vi.mock('@/api/imagenes', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('@/api/imagenes')>()
  return { ...original, subirImagen: vi.fn<typeof original.subirImagen>() }
})

const subir = vi.mocked(subirImagen)

const ID = '0123456789abcdef0123456789abcdef'
const URL_IMAGEN = `/api/v1/imagenes/${ID}`
const IMAGEN_INSERTADA = `<img src="${URL_IMAGEN}" alt="Captura de pantalla">`

let contenedor: VueWrapper | null = null

async function montar(modelValue = ''): Promise<VueWrapper> {
  contenedor = mount(EditorComentario, {
    props: {
      modelValue,
      etiqueta: 'Escribe un comentario',
      'onUpdate:modelValue': (valor: string) => contenedor?.setProps({ modelValue: valor }),
    },
    attachTo: document.body,
  })
  await flushPromises()
  return contenedor
}

function editable(): HTMLElement {
  return document.querySelector<HTMLElement>('[role="textbox"]')!
}

function ultimoValor(envoltorio: VueWrapper): string {
  const emitidos = envoltorio.emitted('update:modelValue') ?? []
  return (emitidos[emitidos.length - 1]?.[0] as string | undefined) ?? ''
}

function ultimoSubiendo(envoltorio: VueWrapper): unknown[] | undefined {
  const emitidos = envoltorio.emitted('subiendo') ?? []
  return emitidos[emitidos.length - 1]
}

function editorDe(envoltorio: VueWrapper): Editor {
  return (envoltorio.vm as unknown as { editor: Ref<Editor> }).editor as unknown as Editor
}

function png(nombre = 'captura.png', tamano = 8): File {
  return new File([new Uint8Array(tamano)], nombre, { type: 'image/png' })
}

/** Datos del portapapeles o del arrastre con estos ficheros (jsdom no tiene DataTransfer). */
function datosCon(ficheros: File[]) {
  return {
    files: ficheros,
    items: ficheros.map((f) => ({ kind: 'file', type: f.type, getAsFile: () => f })),
    types: ficheros.length ? ['Files'] : [],
    getData: () => '',
  }
}

async function pegar(ficheros: File[]): Promise<Event> {
  const evento = new Event('paste', { bubbles: true, cancelable: true })
  Object.defineProperty(evento, 'clipboardData', { value: datosCon(ficheros) })
  editable().dispatchEvent(evento)
  await flushPromises()
  return evento
}

// jsdom no da medidas a los rangos de texto: ProseMirror las pide para
// desplazarse hasta el cursor al insertar la imagen.
const rectVacio = () => new DOMRect(0, 0, 0, 0)
const listaVacia = () => [] as unknown as DOMRectList
const originales = {
  getClientRects: Range.prototype.getClientRects,
  getBoundingClientRect: Range.prototype.getBoundingClientRect,
}

beforeAll(() => {
  Range.prototype.getClientRects = listaVacia
  Range.prototype.getBoundingClientRect = rectVacio
})

afterAll(() => {
  Range.prototype.getClientRects = originales.getClientRects
  Range.prototype.getBoundingClientRect = originales.getBoundingClientRect
})

beforeEach(() => {
  subir.mockReset()
  subir.mockResolvedValue({ id: ID, url: URL_IMAGEN, tipo: 'image/png', tamano: 8 })
})

afterEach(() => {
  contenedor?.unmount()
  contenedor = null
  document.body.innerHTML = ''
})

describe('EditorComentario: imágenes', () => {
  it('pegar una captura de pantalla la sube y la inserta en el comentario', async () => {
    const envoltorio = await montar('<p>Mira:</p>')
    const fichero = png()

    const evento = await pegar([fichero])

    expect(evento.defaultPrevented).toBe(true)
    expect(subir).toHaveBeenCalledWith(fichero)
    expect(ultimoValor(envoltorio)).toContain(IMAGEN_INSERTADA)
    expect(ultimoValor(envoltorio)).toContain('<p>Mira:</p>')
  })

  it('pegar sin imágenes no sube nada', async () => {
    await montar()

    await pegar([new File(['hola'], 'notas.txt', { type: 'text/plain' })])

    expect(subir).not.toHaveBeenCalled()
  })

  it('soltar una imagen la sube y la inserta', async () => {
    const envoltorio = await montar('<p>Texto</p>')
    const fichero = png()
    const evento = new Event('drop', { bubbles: true, cancelable: true })
    Object.defineProperty(evento, 'dataTransfer', { value: datosCon([fichero]) })
    const editor = editorDe(envoltorio)

    // jsdom no calcula posiciones en pantalla: se llama al manejador del editor.
    const tratado = editor.view.someProp('handleDrop', (manejador) =>
      manejador(editor.view, evento as DragEvent, Slice.empty, false),
    )
    await flushPromises()

    expect(tratado).toBe(true)
    expect(subir).toHaveBeenCalledWith(fichero)
    expect(ultimoValor(envoltorio)).toContain(IMAGEN_INSERTADA)
  })

  it('el botón "Imagen" abre el selector de archivos y sube la imagen elegida', async () => {
    const envoltorio = await montar()
    const boton = document.querySelector<HTMLButtonElement>('button[aria-label="Imagen"]')!
    const selector = document.querySelector<HTMLInputElement>('input[type="file"]')!
    const alAbrir = vi.spyOn(selector, 'click')

    boton.click()
    expect(alAbrir).toHaveBeenCalled()
    expect(selector.accept).toBe('image/png,image/jpeg,image/gif,image/webp')
    expect(selector.getAttribute('aria-hidden')).toBe('true')

    const fichero = png()
    Object.defineProperty(selector, 'files', { value: [fichero], configurable: true })
    selector.dispatchEvent(new Event('change'))
    await flushPromises()

    expect(subir).toHaveBeenCalledWith(fichero)
    expect(ultimoValor(envoltorio)).toContain(IMAGEN_INSERTADA)
  })

  it('mientras sube, lo indica y avisa al padre; al terminar deja de indicarlo', async () => {
    let terminar: (valor: Awaited<ReturnType<typeof subirImagen>>) => void = () => {}
    subir.mockReturnValue(new Promise((resolver) => (terminar = resolver)))
    const envoltorio = await montar()

    await pegar([png()])

    expect(document.querySelector('[role="status"]')?.textContent).toContain('Subiendo imagen…')
    expect(ultimoSubiendo(envoltorio)).toEqual([true])

    terminar({ id: ID, url: URL_IMAGEN, tipo: 'image/png', tamano: 8 })
    await flushPromises()

    expect(document.querySelector('[role="status"]')?.textContent ?? '').not.toContain('Subiendo')
    expect(ultimoSubiendo(envoltorio)).toEqual([false])
  })

  it('si la subida falla, muestra el motivo y no inserta nada', async () => {
    subir.mockRejectedValue(new ErrorApi(422, 'El archivo no es una imagen PNG, JPEG, GIF o WebP'))
    const envoltorio = await montar('<p>Hola</p>')

    await pegar([png()])

    expect(document.querySelector('[role="alert"]')?.textContent).toBe(
      'No se pudo subir la imagen: El archivo no es una imagen PNG, JPEG, GIF o WebP',
    )
    expect(ultimoValor(envoltorio)).not.toContain('<img')
    expect(ultimoSubiendo(envoltorio)).toEqual([false])
  })

  it('una imagen de más de 5 MB no se sube y se avisa', async () => {
    const envoltorio = await montar()

    await pegar([png('grande.png', 5 * 1024 * 1024 + 1)])

    expect(subir).not.toHaveBeenCalled()
    expect(document.querySelector('[role="alert"]')?.textContent).toBe(
      'No se pudo subir la imagen: La imagen no puede pasar de 5 MB',
    )
    expect(ultimoValor(envoltorio)).not.toContain('<img')
  })

  it('un comentario con solo una imagen no se da por vacío', async () => {
    const envoltorio = await montar()

    await pegar([png()])

    expect(ultimoValor(envoltorio)).toBe(IMAGEN_INSERTADA)
  })

  it('muestra las imágenes de un comentario guardado y no admite otras', async () => {
    await montar(`<p>a</p>${IMAGEN_INSERTADA}<img src="https://ejemplo.com/x.png">`)

    const imagenes = [...editable().querySelectorAll('img')]
    expect(imagenes.map((i) => i.getAttribute('src'))).toEqual([URL_IMAGEN])
  })

  it('en solo lectura el botón "Imagen" está desactivado', async () => {
    contenedor = mount(EditorComentario, {
      props: { modelValue: '', etiqueta: 'x', soloLectura: true },
      attachTo: document.body,
    })
    await flushPromises()

    expect(document.querySelector<HTMLButtonElement>('button[aria-label="Imagen"]')!.disabled).toBe(
      true,
    )
  })
})
