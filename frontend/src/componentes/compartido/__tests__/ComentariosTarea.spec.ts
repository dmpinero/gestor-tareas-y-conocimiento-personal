import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, onMounted, ref } from 'vue'

import { clienteApi, ErrorApi } from '@/api/cliente'
import type { Comentario } from '@/lib/comentarios'
import ComentariosTarea from '../ComentariosTarea.vue'

vi.mock('@/api/cliente', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('@/api/cliente')>()
  return {
    ...original,
    clienteApi: {
      obtener: vi.fn<(...args: unknown[]) => unknown>(),
      crear: vi.fn<(...args: unknown[]) => unknown>(),
      actualizar: vi.fn<(...args: unknown[]) => unknown>(),
      eliminar: vi.fn<(...args: unknown[]) => unknown>(),
    },
  }
})

const obtener = vi.mocked(clienteApi.obtener)
const crear = vi.mocked(clienteApi.crear)
const actualizar = vi.mocked(clienteApi.actualizar)
const eliminar = vi.mocked(clienteApi.eliminar)

// Marca UTC con `Z` (como la envía la API) de una hora local dada, para que
// los tests no dependan de la zona horaria.
function isoUtcDesdeLocal(mes: number, dia: number, hora: number, minuto: number): string {
  return new Date(2026, mes - 1, dia, hora, minuto, 5).toISOString().replace(/\.\d{3}Z$/, 'Z')
}

const COMENTARIOS: Comentario[] = [
  { id: 1, texto: 'Primer comentario', creado: isoUtcDesdeLocal(4, 1, 9, 5), editado: null },
  { id: 2, texto: 'Línea 1\nLínea 2', creado: isoUtcDesdeLocal(4, 1, 18, 30), editado: null },
  { id: 3, texto: '<b>sin formato</b>', creado: isoUtcDesdeLocal(4, 2, 8, 0), editado: null },
]

// ProseMirror no admite escribir en jsdom: en estos tests el editor se
// sustituye por un <textarea> con su misma interfaz (v-model con HTML, `id`,
// `etiqueta`, `limite`, `enviar` con Ctrl/Cmd+Enter). El editor real se prueba
// en EditorComentario.spec.ts y con un montaje sin sustituir más abajo.
const editorComentarioFalso = defineComponent({
  name: 'EditorComentario',
  props: {
    modelValue: { type: String, required: true },
    etiqueta: { type: String, required: true },
    id: { type: String, default: undefined },
    placeholder: { type: String, default: undefined },
    limite: { type: Number, default: 500 },
    describedBy: { type: String, default: undefined },
    invalido: Boolean,
    soloLectura: Boolean,
    autoenfoque: Boolean,
  },
  emits: ['update:modelValue', 'enviar'],
  setup(props, { emit }) {
    const campo = ref<HTMLTextAreaElement | null>(null)
    onMounted(() => {
      if (props.autoenfoque) campo.value?.focus()
    })
    return () =>
      h('textarea', {
        ref: campo,
        id: props.id,
        value: props.modelValue,
        'aria-label': props.etiqueta,
        placeholder: props.placeholder,
        maxlength: props.limite,
        'aria-describedby': props.describedBy,
        'aria-invalid': props.invalido ? 'true' : undefined,
        readonly: props.soloLectura,
        onInput: (evento: Event) =>
          emit('update:modelValue', (evento.target as HTMLTextAreaElement).value),
        onKeydown: (evento: KeyboardEvent) => {
          if (evento.key === 'Enter' && (evento.ctrlKey || evento.metaKey)) emit('enviar')
        },
      })
  },
})

let contenedor: VueWrapper | null = null

async function montar(idTarea = 7, sustituirEditor = true): Promise<VueWrapper> {
  contenedor = mount(ComentariosTarea, {
    props: { ruta: `/tareas/${idTarea}/comentarios` },
    attachTo: document.body,
    global: { stubs: sustituirEditor ? { EditorComentario: editorComentarioFalso } : {} },
  })
  await flushPromises()
  return contenedor
}

function historial(envoltorio: VueWrapper): HTMLElement {
  return envoltorio.get('[aria-label="Historial de comentarios"]').element as HTMLElement
}

function campoTexto(envoltorio: VueWrapper) {
  return envoltorio.get('textarea[aria-label="Escribe un comentario"]')
}

function textosComentarios(envoltorio: VueWrapper): (string | null)[] {
  return [...historial(envoltorio).querySelectorAll('[data-testid="texto-comentario"]')].map(
    (elemento) => elemento.textContent,
  )
}

function botonEnviar(envoltorio: VueWrapper) {
  return envoltorio.get('button[aria-label="Enviar comentario"]')
}

async function escribir(envoltorio: VueWrapper, texto: string): Promise<void> {
  await campoTexto(envoltorio).setValue(texto)
  await flushPromises()
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 10, 10, 12, 0, 0))
  obtener.mockReset()
  crear.mockReset()
  actualizar.mockReset()
  eliminar.mockReset()
})

afterEach(() => {
  contenedor?.unmount()
  contenedor = null
  vi.useRealTimers()
})

describe('ComentariosTarea: carga', () => {
  it('muestra el encabezado y el estado de carga mientras pide los comentarios de la tarea', async () => {
    obtener.mockReturnValue(new Promise(() => {}))

    const envoltorio = await montar(7)

    expect(envoltorio.get('h3').text()).toBe('Comentarios')
    expect(envoltorio.text()).toContain('Cargando comentarios…')
    expect(obtener).toHaveBeenCalledWith('/tareas/7/comentarios')
  })

  it('muestra el estado vacío cuando no hay comentarios', async () => {
    obtener.mockResolvedValue([])

    const envoltorio = await montar()

    expect(envoltorio.text()).toContain('Todavía no hay comentarios.')
    expect(envoltorio.text()).not.toContain('Cargando comentarios…')
  })

  it('muestra el error de carga en una alerta', async () => {
    obtener.mockRejectedValue(new ErrorApi(404, 'Tarea no encontrada'))

    const envoltorio = await montar()

    const alerta = envoltorio.get('[role="alert"]')
    expect(alerta.text()).toContain('Tarea no encontrada')
    expect(envoltorio.text()).not.toContain('Todavía no hay comentarios.')
  })

  it('vuelve a cargar cuando cambia la tarea', async () => {
    obtener.mockResolvedValueOnce(COMENTARIOS).mockResolvedValueOnce([])
    const envoltorio = await montar(7)

    await envoltorio.setProps({ ruta: '/tareas/8/comentarios' })
    await flushPromises()

    expect(obtener).toHaveBeenLastCalledWith('/tareas/8/comentarios')
    expect(envoltorio.text()).toContain('Todavía no hay comentarios.')
    expect(envoltorio.text()).not.toContain('Primer comentario')
  })

  it('ignora la respuesta tardía de una tarea anterior', async () => {
    let resolverAnterior: (valor: Comentario[]) => void = () => {}
    obtener
      .mockReturnValueOnce(new Promise((resolver) => (resolverAnterior = resolver)))
      .mockResolvedValueOnce([])
    const envoltorio = await montar(7)

    await envoltorio.setProps({ ruta: '/tareas/8/comentarios' })
    await flushPromises()
    resolverAnterior(COMENTARIOS)
    await flushPromises()

    expect(envoltorio.text()).toContain('Todavía no hay comentarios.')
    expect(envoltorio.text()).not.toContain('Primer comentario')
  })
})

describe('ComentariosTarea: historial', () => {
  it('agrupa por día con separadores y muestra hora y texto en orden cronológico', async () => {
    obtener.mockResolvedValue([COMENTARIOS[2], COMENTARIOS[0], COMENTARIOS[1]])

    const envoltorio = await montar()

    const lista = historial(envoltorio)
    expect(lista.tagName).toBe('OL')
    const separadores = [...lista.querySelectorAll('h4')].map((titulo) => titulo.textContent)
    expect(separadores).toEqual(['miércoles, 1 de abril', 'jueves, 2 de abril'])

    const filas = [...lista.querySelectorAll('li li')].map((fila) => [
      fila.querySelector('time')!.textContent,
      fila.querySelector('[data-testid="texto-comentario"]')!.textContent,
    ])
    // `<b>` no está en la lista permitida: se quita la etiqueta y queda su texto.
    expect(filas).toEqual([
      ['09:05', 'Primer comentario'],
      ['18:30', 'Línea 1Línea 2'],
      ['08:00', 'sin formato'],
    ])
    expect(lista.querySelector('b')).toBeNull()
  })

  it('cada día es una lista con el nombre de su separador', async () => {
    obtener.mockResolvedValue(COMENTARIOS)

    const envoltorio = await montar()

    const titulo = historial(envoltorio).querySelector('h4')!
    const listaDia = historial(envoltorio).querySelector(`ol[aria-labelledby="${titulo.id}"]`)
    expect(titulo.id).not.toBe('')
    expect(listaDia?.querySelectorAll('li')).toHaveLength(2)
  })

  it('respeta los saltos de línea del texto plano: un párrafo por línea', async () => {
    obtener.mockResolvedValue(COMENTARIOS)

    const envoltorio = await montar()

    const textos = historial(envoltorio).querySelectorAll('[data-testid="texto-comentario"]')
    expect(textos[1]!.innerHTML).toBe('<p>Línea 1</p><p>Línea 2</p>')
  })

  it('muestra el formato del comentario y no sus etiquetas', async () => {
    obtener.mockResolvedValue([
      {
        ...COMENTARIOS[0]!,
        texto:
          '<p><strong>N</strong> <em>C</em> <u>S</u> <s>T</s> <span style="color: #dc2626">rojo</span> <mark data-color="#fef08a" style="background-color: #fef08a">res</mark></p>' +
          '<ul><li><p>uno</p></li></ul><ol><li><p>dos</p></li></ol>' +
          '<p><a href="https://ejemplo.com">enlace</a></p>',
      },
    ])

    const envoltorio = await montar()

    const texto = historial(envoltorio).querySelector('[data-testid="texto-comentario"]')!
    expect(texto.textContent).not.toContain('<')
    const selectores = ['strong', 'em', 'u', 's', 'span[style]', 'mark', 'ul > li', 'ol > li']
    expect(selectores.filter((selector) => texto.querySelector(selector) === null)).toEqual([])
    const enlace = texto.querySelector('a')!
    expect(enlace.getAttribute('href')).toBe('https://ejemplo.com')
    expect(enlace.getAttribute('rel')).toBe('noopener noreferrer nofollow')
    expect(enlace.getAttribute('target')).toBe('_blank')
  })

  it('no pinta ni ejecuta HTML peligroso que llegue de la API', async () => {
    obtener.mockResolvedValue([
      {
        ...COMENTARIOS[0]!,
        texto:
          '<p onclick="alert(1)">Hola</p><img src=x onerror=alert(1)><script>alert(1)</script>' +
          '<a href="javascript:alert(1)">mal</a><iframe src="https://ejemplo.com"></iframe>',
      },
    ])

    const envoltorio = await montar()

    const texto = historial(envoltorio).querySelector('[data-testid="texto-comentario"]')!
    expect(texto.querySelector('img, script, iframe, [onclick], [onerror]')).toBeNull()
    expect(texto.querySelector('a')?.hasAttribute('href')).toBe(false)
    expect(texto.textContent).toBe('Holamal')
  })

  it('desplaza el historial hasta el comentario más reciente al cargar', async () => {
    obtener.mockResolvedValue(COMENTARIOS)
    const asignaciones: number[] = []
    const descriptorAltura = Object.getOwnPropertyDescriptor(Element.prototype, 'scrollHeight')
    const descriptorDesplazamiento = Object.getOwnPropertyDescriptor(Element.prototype, 'scrollTop')
    Object.defineProperty(Element.prototype, 'scrollHeight', {
      configurable: true,
      get: () => 640,
    })
    Object.defineProperty(Element.prototype, 'scrollTop', {
      configurable: true,
      get: () => 0,
      set: (valor: number) => {
        asignaciones.push(valor)
      },
    })

    try {
      await montar()
    } finally {
      Object.defineProperty(Element.prototype, 'scrollHeight', descriptorAltura!)
      Object.defineProperty(Element.prototype, 'scrollTop', descriptorDesplazamiento!)
    }

    expect(asignaciones).toContain(640)
  })
})

describe('ComentariosTarea: envío', () => {
  it('tiene un campo con placeholder, límite de 500 y contador', async () => {
    obtener.mockResolvedValue([])
    const envoltorio = await montar()

    const campo = campoTexto(envoltorio)
    expect(campo.attributes('placeholder')).toBe('Escribe un comentario')
    expect(campo.attributes('maxlength')).toBe('500')
    expect(envoltorio.text()).toContain('0/500')

    await escribir(envoltorio, 'Hola')

    expect(envoltorio.text()).toContain('4/500')
  })

  it('el contador cuenta solo el texto visible, sin etiquetas y con las entidades decodificadas', async () => {
    obtener.mockResolvedValue([])
    const envoltorio = await montar()

    await escribir(envoltorio, '<p><strong>Hola</strong> &amp;</p><ul><li><p>a</p></li></ul>')

    expect(envoltorio.text()).toContain('7/500')
  })

  it('el límite de 500 se aplica al texto visible, no al HTML', async () => {
    obtener.mockResolvedValue([])
    const envoltorio = await montar()

    await escribir(envoltorio, `<p><strong>${'a'.repeat(500)}</strong></p>`)

    expect(envoltorio.text()).toContain('500/500')
    expect(botonEnviar(envoltorio).attributes('disabled')).toBeUndefined()
  })

  it('envía el HTML del editor', async () => {
    obtener.mockResolvedValue([])
    crear.mockResolvedValue({
      id: 9,
      texto: '<p><strong>Hola</strong></p>',
      creado: isoUtcDesdeLocal(11, 10, 11, 45),
      editado: null,
    })
    const envoltorio = await montar(7)
    await escribir(envoltorio, '<p><strong>Hola</strong></p>')

    await botonEnviar(envoltorio).trigger('click')
    await flushPromises()

    expect(crear).toHaveBeenCalledWith('/tareas/7/comentarios', {
      texto: '<p><strong>Hola</strong></p>',
    })
    expect(historial(envoltorio).querySelector('strong')?.textContent).toBe('Hola')
  })

  it('desactiva el botón con el campo vacío o solo con espacios', async () => {
    obtener.mockResolvedValue([])
    const envoltorio = await montar()

    expect(botonEnviar(envoltorio).attributes('disabled')).toBeDefined()
    await escribir(envoltorio, '   \n ')
    expect(botonEnviar(envoltorio).attributes('disabled')).toBeDefined()
    await escribir(envoltorio, '<p> </p><p>&nbsp;</p>')
    expect(botonEnviar(envoltorio).attributes('disabled')).toBeDefined()

    await campoTexto(envoltorio).trigger('keydown', { key: 'Enter', ctrlKey: true })
    await flushPromises()
    expect(crear).not.toHaveBeenCalled()
  })

  it('envía con el botón, añade el comentario, vacía el campo y mantiene el foco', async () => {
    obtener.mockResolvedValue([COMENTARIOS[0]])
    const nuevo: Comentario = {
      id: 9,
      texto: 'Hola',
      creado: isoUtcDesdeLocal(11, 10, 11, 45),
      editado: null,
    }
    crear.mockResolvedValue(nuevo)
    const envoltorio = await montar(7)
    await escribir(envoltorio, '  Hola  ')
    ;(campoTexto(envoltorio).element as HTMLTextAreaElement).focus()

    await botonEnviar(envoltorio).trigger('click')
    await flushPromises()

    expect(crear).toHaveBeenCalledWith('/tareas/7/comentarios', { texto: '  Hola  ' })
    expect(textosComentarios(envoltorio)).toEqual(['Primer comentario', 'Hola'])
    expect(historial(envoltorio).querySelectorAll('h4')[1]!.textContent).toBe(
      'martes, 10 de noviembre',
    )
    expect((campoTexto(envoltorio).element as HTMLTextAreaElement).value).toBe('')
    expect(envoltorio.text()).toContain('0/500')
    expect(document.activeElement).toBe(campoTexto(envoltorio).element)
    expect(envoltorio.get('[aria-live="polite"]').text()).toBe('Comentario añadido')
  })

  // Regresión (accesibilidad): al enviar con el botón, este se desactiva al
  // vaciarse el campo y el foco caía en el <body>.
  it('tras enviar con el botón enfocado, el foco vuelve al campo de texto', async () => {
    obtener.mockResolvedValue([])
    crear.mockResolvedValue({
      id: 9,
      texto: 'Hola',
      creado: isoUtcDesdeLocal(11, 10, 11, 45),
      editado: null,
    })
    const envoltorio = await montar(7)
    await escribir(envoltorio, 'Hola')
    ;(botonEnviar(envoltorio).element as HTMLButtonElement).focus()

    await botonEnviar(envoltorio).trigger('click')
    await flushPromises()

    expect(document.activeElement).toBe(campoTexto(envoltorio).element)
  })

  // Regresión (axe `scrollable-region-focusable`): con muchos comentarios el
  // historial se desplaza y debe poder enfocarse con el teclado.
  it('el contenedor desplazable del historial se puede enfocar y tiene nombre', async () => {
    obtener.mockResolvedValue([COMENTARIOS[0]])
    const envoltorio = await montar(7)

    const contenedor = historial(envoltorio).parentElement!
    expect(contenedor.className).toContain('overflow-y-auto')
    expect(contenedor.getAttribute('tabindex')).toBe('0')
    expect(contenedor.getAttribute('role')).toBe('region')
    expect(contenedor.getAttribute('aria-label')).toBe('Comentarios anteriores')
  })

  it('el primer comentario sustituye al estado vacío', async () => {
    obtener.mockResolvedValue([])
    crear.mockResolvedValue({
      id: 9,
      texto: 'Hola',
      creado: isoUtcDesdeLocal(11, 10, 11, 45),
      editado: null,
    })
    const envoltorio = await montar()
    await escribir(envoltorio, 'Hola')

    await envoltorio.get('form').trigger('submit')
    await flushPromises()

    expect(envoltorio.text()).not.toContain('Todavía no hay comentarios.')
    expect(historial(envoltorio).textContent).toContain('Hola')
  })

  it.each([
    ['Ctrl+Enter', { ctrlKey: true }],
    ['Cmd+Enter', { metaKey: true }],
  ])('envía con %s', async (_nombre, modificador) => {
    obtener.mockResolvedValue([])
    crear.mockResolvedValue({
      id: 9,
      texto: 'Hola',
      creado: isoUtcDesdeLocal(11, 10, 11, 45),
      editado: null,
    })
    const envoltorio = await montar(7)
    await escribir(envoltorio, 'Hola')

    await campoTexto(envoltorio).trigger('keydown', { key: 'Enter', ...modificador })
    await flushPromises()

    expect(crear).toHaveBeenCalledWith('/tareas/7/comentarios', { texto: 'Hola' })
  })

  it('Enter sin modificador no envía (añade un salto de línea)', async () => {
    obtener.mockResolvedValue([])
    const envoltorio = await montar()
    await escribir(envoltorio, 'Hola')

    await campoTexto(envoltorio).trigger('keydown', { key: 'Enter' })
    await flushPromises()

    expect(crear).not.toHaveBeenCalled()
  })

  it('mientras envía desactiva el botón pero no el campo, y no envía dos veces', async () => {
    obtener.mockResolvedValue([])
    crear.mockReturnValue(new Promise(() => {}))
    const envoltorio = await montar()
    await escribir(envoltorio, 'Hola')
    const campo = campoTexto(envoltorio).element as HTMLTextAreaElement
    campo.focus()

    await campoTexto(envoltorio).trigger('keydown', { key: 'Enter', ctrlKey: true })
    await flushPromises()
    await campoTexto(envoltorio).trigger('keydown', { key: 'Enter', ctrlKey: true })
    await flushPromises()

    expect(crear).toHaveBeenCalledTimes(1)
    expect(botonEnviar(envoltorio).attributes('disabled')).toBeDefined()
    expect(campo.disabled).toBe(false)
    expect(document.activeElement).toBe(campo)
  })

  it('si falla el envío muestra una alerta y conserva el texto', async () => {
    obtener.mockResolvedValue([])
    crear.mockRejectedValue(new ErrorApi(422, 'El texto es obligatorio'))
    const envoltorio = await montar()
    await escribir(envoltorio, 'Hola')

    await botonEnviar(envoltorio).trigger('click')
    await flushPromises()

    expect(envoltorio.get('[role="alert"]').text()).toContain('El texto es obligatorio')
    expect((campoTexto(envoltorio).element as HTMLTextAreaElement).value).toBe('Hola')
    expect(botonEnviar(envoltorio).attributes('disabled')).toBeUndefined()
  })
})

// Nombre accesible del botón de editar o eliminar del comentario 2 (18:30 del 1 de abril).
const REFERENCIA_2 = 'de las 18:30 del miércoles, 1 de abril'

function botonPorNombre(envoltorio: VueWrapper, nombre: string) {
  return envoltorio.get(`button[aria-label="${nombre}"]`)
}

function botonDe(envoltorio: VueWrapper, selector: string, texto: string) {
  const encontrado = envoltorio
    .get(selector)
    .findAll('button')
    .find((b) => b.text().trim() === texto)
  if (!encontrado) throw new Error(`No hay botón «${texto}» en ${selector}`)
  return encontrado
}

function campoEdicion(envoltorio: VueWrapper) {
  return envoltorio.get('textarea[aria-label="Nuevo texto del comentario"]')
}

const GRUPO_GUARDAR = '[role="group"][aria-label="¿Guardar los cambios del comentario?"]'
const GRUPO_ELIMINAR = '[role="group"][aria-label="¿Eliminar el comentario?"]'

async function abrirEdicion(envoltorio: VueWrapper): Promise<void> {
  await botonPorNombre(envoltorio, `Editar comentario ${REFERENCIA_2}`).trigger('click')
  await flushPromises()
}

async function pedirGuardar(envoltorio: VueWrapper): Promise<void> {
  await envoltorio.get('form[aria-label="Editar comentario"]').trigger('submit')
  await flushPromises()
}

describe('ComentariosTarea: acciones por comentario', () => {
  it('cada comentario tiene botones de editar y eliminar con nombres únicos aunque coincida la hora', async () => {
    const mismaHora = {
      id: 4,
      texto: 'Otro a la misma hora',
      creado: COMENTARIOS[1]!.creado,
      editado: null,
    }
    obtener.mockResolvedValue([...COMENTARIOS, mismaHora])

    const envoltorio = await montar()

    const nombres = envoltorio
      .findAll('[aria-label="Historial de comentarios"] button')
      .map((b) => b.attributes('aria-label'))
    expect(nombres).toEqual([
      'Editar comentario de las 09:05 del miércoles, 1 de abril',
      'Eliminar comentario de las 09:05 del miércoles, 1 de abril',
      `Editar comentario ${REFERENCIA_2}`,
      `Eliminar comentario ${REFERENCIA_2}`,
      `Editar comentario ${REFERENCIA_2} (2)`,
      `Eliminar comentario ${REFERENCIA_2} (2)`,
      'Editar comentario de las 08:00 del jueves, 2 de abril',
      'Eliminar comentario de las 08:00 del jueves, 2 de abril',
    ])
  })

  it('marca "(editado)" los comentarios editados, con la hora local de la edición', async () => {
    const editado = { ...COMENTARIOS[1]!, editado: isoUtcDesdeLocal(11, 10, 17, 45) }
    obtener.mockResolvedValue([COMENTARIOS[0], editado])

    const envoltorio = await montar()

    const marcas = historial(envoltorio).querySelectorAll('[data-testid="marca-editado"]')
    expect(marcas).toHaveLength(1)
    const marca = marcas[0] as HTMLElement
    expect(marca.closest('li')?.textContent).toContain('Línea 1')
    expect(marca.getAttribute('title')).toBe('Editado el martes, 10 de noviembre a las 17:45')
    expect(marca.textContent?.replace(/\s+/g, ' ').trim()).toBe(
      '(editado el martes, 10 de noviembre a las 17:45)',
    )
    expect(marca.querySelector('.sr-only')?.textContent).toBe(
      ' el martes, 10 de noviembre a las 17:45',
    )
  })
})

describe('ComentariosTarea: editar', () => {
  it('convierte el comentario en un campo relleno con su texto, contador y el foco', async () => {
    obtener.mockResolvedValue(COMENTARIOS)
    const envoltorio = await montar()

    await abrirEdicion(envoltorio)

    const campo = campoEdicion(envoltorio).element as HTMLTextAreaElement
    // El texto plano (datos antiguos) llega al editor como un párrafo por línea.
    expect(campo.value).toBe('<p>Línea 1</p><p>Línea 2</p>')
    expect(campo.maxLength).toBe(500)
    expect(document.activeElement).toBe(campo)
    const contador = document.getElementById(campo.getAttribute('aria-describedby')!)
    expect(contador?.textContent?.trim()).toBe('14/500')
    expect(botonDe(envoltorio, 'form[aria-label="Editar comentario"]', 'Guardar').exists()).toBe(
      true,
    )
    expect(botonDe(envoltorio, 'form[aria-label="Editar comentario"]', 'Cancelar').exists()).toBe(
      true,
    )
  })

  it('con el texto vacío muestra un error y no pide confirmación', async () => {
    obtener.mockResolvedValue(COMENTARIOS)
    const envoltorio = await montar()
    await abrirEdicion(envoltorio)
    await campoEdicion(envoltorio).setValue('<p>  </p>')
    await flushPromises()

    await pedirGuardar(envoltorio)

    expect(envoltorio.get('[role="alert"]').text()).toBe('El comentario no puede estar vacío.')
    expect(envoltorio.find(GRUPO_GUARDAR).exists()).toBe(false)
    expect(actualizar).not.toHaveBeenCalled()
  })

  it('Guardar pide confirmación antes de llamar a la API', async () => {
    obtener.mockResolvedValue(COMENTARIOS)
    const envoltorio = await montar()
    await abrirEdicion(envoltorio)

    await botonDe(envoltorio, 'form[aria-label="Editar comentario"]', 'Guardar').trigger('click')
    await flushPromises()

    expect(envoltorio.find(GRUPO_GUARDAR).exists()).toBe(true)
    expect(document.activeElement).toBe(botonDe(envoltorio, GRUPO_GUARDAR, 'Cancelar').element)
    expect(actualizar).not.toHaveBeenCalled()
  })

  it('al confirmar envía el texto, lo muestra "(editado)" y devuelve el foco al botón de editar', async () => {
    obtener.mockResolvedValue(COMENTARIOS)
    actualizar.mockResolvedValue({
      ...COMENTARIOS[1]!,
      texto: 'Texto nuevo',
      editado: isoUtcDesdeLocal(11, 10, 11, 50),
    })
    const envoltorio = await montar(7)
    await abrirEdicion(envoltorio)
    await campoEdicion(envoltorio).setValue('Texto nuevo')
    await flushPromises()
    await pedirGuardar(envoltorio)

    await botonDe(envoltorio, GRUPO_GUARDAR, 'Guardar').trigger('click')
    await flushPromises()

    expect(actualizar).toHaveBeenCalledWith('/tareas/7/comentarios/2', { texto: 'Texto nuevo' })
    expect(envoltorio.find('textarea[aria-label="Nuevo texto del comentario"]').exists()).toBe(
      false,
    )
    expect(textosComentarios(envoltorio)).toEqual([
      'Primer comentario',
      'Texto nuevo',
      'sin formato',
    ])
    expect(historial(envoltorio).querySelectorAll('[data-testid="marca-editado"]')).toHaveLength(1)
    expect(document.activeElement).toBe(
      botonPorNombre(envoltorio, `Editar comentario ${REFERENCIA_2}`).element,
    )
    expect(envoltorio.get('[aria-live="polite"]').text()).toBe('Comentario actualizado')
  })

  it('si la API falla muestra una alerta y conserva el texto en edición', async () => {
    obtener.mockResolvedValue(COMENTARIOS)
    actualizar.mockRejectedValue(new ErrorApi(404, 'Comentario no encontrado'))
    const envoltorio = await montar()
    await abrirEdicion(envoltorio)
    await campoEdicion(envoltorio).setValue('Texto nuevo')
    await flushPromises()
    await pedirGuardar(envoltorio)

    await botonDe(envoltorio, GRUPO_GUARDAR, 'Guardar').trigger('click')
    await flushPromises()

    expect(envoltorio.get('[role="alert"]').text()).toContain('Comentario no encontrado')
    expect(envoltorio.find(GRUPO_GUARDAR).exists()).toBe(false)
    const campo = campoEdicion(envoltorio).element as HTMLTextAreaElement
    expect(campo.value).toBe('Texto nuevo')
    expect(document.activeElement).toBe(campo)
  })

  it('Cancelar en la confirmación vuelve al campo con lo escrito', async () => {
    obtener.mockResolvedValue(COMENTARIOS)
    const envoltorio = await montar()
    await abrirEdicion(envoltorio)
    await campoEdicion(envoltorio).setValue('Texto nuevo')
    await flushPromises()
    await pedirGuardar(envoltorio)

    await botonDe(envoltorio, GRUPO_GUARDAR, 'Cancelar').trigger('click')
    await flushPromises()

    expect(envoltorio.find(GRUPO_GUARDAR).exists()).toBe(false)
    const campo = campoEdicion(envoltorio).element as HTMLTextAreaElement
    expect(campo.value).toBe('Texto nuevo')
    expect(document.activeElement).toBe(campo)
    expect(actualizar).not.toHaveBeenCalled()
  })

  it('Escape en la confirmación vuelve al campo sin propagarse', async () => {
    obtener.mockResolvedValue(COMENTARIOS)
    const envoltorio = await montar()
    await abrirEdicion(envoltorio)
    await pedirGuardar(envoltorio)
    const escuchaVentana = vi.fn<(evento: KeyboardEvent) => void>()
    window.addEventListener('keydown', escuchaVentana)

    await envoltorio.get(GRUPO_GUARDAR).trigger('keydown', { key: 'Escape' })
    await flushPromises()
    window.removeEventListener('keydown', escuchaVentana)

    expect(envoltorio.find(GRUPO_GUARDAR).exists()).toBe(false)
    expect(envoltorio.find('textarea[aria-label="Nuevo texto del comentario"]').exists()).toBe(true)
    expect(escuchaVentana).not.toHaveBeenCalled()
    expect(actualizar).not.toHaveBeenCalled()
  })

  it('Cancelar en el formulario restaura el comentario y devuelve el foco al botón de editar', async () => {
    obtener.mockResolvedValue(COMENTARIOS)
    const envoltorio = await montar()
    await abrirEdicion(envoltorio)
    await campoEdicion(envoltorio).setValue('Texto nuevo')
    await flushPromises()

    await botonDe(envoltorio, 'form[aria-label="Editar comentario"]', 'Cancelar').trigger('click')
    await flushPromises()

    expect(envoltorio.find('textarea[aria-label="Nuevo texto del comentario"]').exists()).toBe(
      false,
    )
    expect(historial(envoltorio).textContent).toContain('Línea 1')
    expect(document.activeElement).toBe(
      botonPorNombre(envoltorio, `Editar comentario ${REFERENCIA_2}`).element,
    )
    expect(actualizar).not.toHaveBeenCalled()
  })

  it('Escape en el formulario cancela la edición sin propagarse', async () => {
    obtener.mockResolvedValue(COMENTARIOS)
    const envoltorio = await montar()
    await abrirEdicion(envoltorio)
    const escuchaVentana = vi.fn<(evento: KeyboardEvent) => void>()
    window.addEventListener('keydown', escuchaVentana)

    await campoEdicion(envoltorio).trigger('keydown', { key: 'Escape' })
    await flushPromises()
    window.removeEventListener('keydown', escuchaVentana)

    expect(envoltorio.find('textarea[aria-label="Nuevo texto del comentario"]').exists()).toBe(
      false,
    )
    expect(escuchaVentana).not.toHaveBeenCalled()
    expect(document.activeElement).toBe(
      botonPorNombre(envoltorio, `Editar comentario ${REFERENCIA_2}`).element,
    )
  })
})

describe('ComentariosTarea: eliminar', () => {
  async function pedirEliminar(envoltorio: VueWrapper): Promise<void> {
    await botonPorNombre(envoltorio, `Eliminar comentario ${REFERENCIA_2}`).trigger('click')
    await flushPromises()
  }

  it('pide confirmación en línea antes de llamar a la API', async () => {
    obtener.mockResolvedValue(COMENTARIOS)
    const envoltorio = await montar()

    await pedirEliminar(envoltorio)

    expect(botonDe(envoltorio, GRUPO_ELIMINAR, 'Eliminar').exists()).toBe(true)
    expect(document.activeElement).toBe(botonDe(envoltorio, GRUPO_ELIMINAR, 'Cancelar').element)
    expect(eliminar).not.toHaveBeenCalled()
  })

  it('al confirmar lo borra, lo quita de la lista y lleva el foco al historial', async () => {
    obtener.mockResolvedValue(COMENTARIOS)
    eliminar.mockResolvedValue(undefined)
    const envoltorio = await montar(7)
    await pedirEliminar(envoltorio)

    await botonDe(envoltorio, GRUPO_ELIMINAR, 'Eliminar').trigger('click')
    await flushPromises()

    expect(eliminar).toHaveBeenCalledWith('/tareas/7/comentarios/2')
    expect(textosComentarios(envoltorio)).toEqual(['Primer comentario', 'sin formato'])
    expect(document.activeElement).toBe(historial(envoltorio).parentElement)
    expect(envoltorio.get('[aria-live="polite"]').text()).toBe('Comentario eliminado')
  })

  it('al borrar el último comentario muestra el estado vacío y lleva el foco al campo nuevo', async () => {
    obtener.mockResolvedValue([COMENTARIOS[1]])
    eliminar.mockResolvedValue(undefined)
    const envoltorio = await montar()
    await pedirEliminar(envoltorio)

    await botonDe(envoltorio, GRUPO_ELIMINAR, 'Eliminar').trigger('click')
    await flushPromises()

    expect(envoltorio.text()).toContain('Todavía no hay comentarios.')
    expect(document.activeElement).toBe(campoTexto(envoltorio).element)
  })

  it('Cancelar no llama a la API y devuelve el foco al botón de eliminar', async () => {
    obtener.mockResolvedValue(COMENTARIOS)
    const envoltorio = await montar()
    await pedirEliminar(envoltorio)

    await botonDe(envoltorio, GRUPO_ELIMINAR, 'Cancelar').trigger('click')
    await flushPromises()

    expect(envoltorio.find(GRUPO_ELIMINAR).exists()).toBe(false)
    expect(eliminar).not.toHaveBeenCalled()
    expect(document.activeElement).toBe(
      botonPorNombre(envoltorio, `Eliminar comentario ${REFERENCIA_2}`).element,
    )
  })

  it('Escape cancela la confirmación sin propagarse', async () => {
    obtener.mockResolvedValue(COMENTARIOS)
    const envoltorio = await montar()
    await pedirEliminar(envoltorio)
    const escuchaVentana = vi.fn<(evento: KeyboardEvent) => void>()
    window.addEventListener('keydown', escuchaVentana)

    await envoltorio.get(GRUPO_ELIMINAR).trigger('keydown', { key: 'Escape' })
    await flushPromises()
    window.removeEventListener('keydown', escuchaVentana)

    expect(envoltorio.find(GRUPO_ELIMINAR).exists()).toBe(false)
    expect(escuchaVentana).not.toHaveBeenCalled()
    expect(eliminar).not.toHaveBeenCalled()
  })

  it('si la API falla muestra una alerta y conserva el comentario', async () => {
    obtener.mockResolvedValue(COMENTARIOS)
    eliminar.mockRejectedValue(new ErrorApi(404, 'Comentario no encontrado'))
    const envoltorio = await montar()
    await pedirEliminar(envoltorio)

    await botonDe(envoltorio, GRUPO_ELIMINAR, 'Eliminar').trigger('click')
    await flushPromises()

    expect(envoltorio.get('[role="alert"]').text()).toContain('Comentario no encontrado')
    expect(historial(envoltorio).textContent).toContain('Línea 1')
    expect(document.activeElement).toBe(
      botonPorNombre(envoltorio, `Eliminar comentario ${REFERENCIA_2}`).element,
    )
  })
})

describe('ComentariosTarea: comentarios de una subtarea', () => {
  const RUTA_SUBTAREA = '/tareas/7/subtareas/9/comentarios'

  async function montarSubtarea(): Promise<VueWrapper> {
    contenedor = mount(ComentariosTarea, {
      props: { ruta: RUTA_SUBTAREA, contexto: 'de la subtarea Revisar' },
      attachTo: document.body,
      global: { stubs: { EditorComentario: editorComentarioFalso } },
    })
    await flushPromises()
    return contenedor
  }

  it('carga, crea, edita y elimina usando la ruta recibida', async () => {
    obtener.mockResolvedValue([COMENTARIOS[0]])
    crear.mockResolvedValue({
      id: 5,
      texto: 'Nuevo',
      creado: isoUtcDesdeLocal(4, 3, 10, 0),
      editado: null,
    })
    actualizar.mockResolvedValue({ ...COMENTARIOS[0], texto: 'Cambiado' })
    eliminar.mockResolvedValue(undefined)
    const envoltorio = await montarSubtarea()

    expect(obtener).toHaveBeenCalledWith(RUTA_SUBTAREA)

    await envoltorio
      .get('textarea[aria-label="Escribe un comentario de la subtarea Revisar"]')
      .setValue('Nuevo')
    await flushPromises()
    await envoltorio
      .get('button[aria-label="Enviar comentario de la subtarea Revisar"]')
      .trigger('click')
    await flushPromises()
    expect(crear).toHaveBeenCalledWith(RUTA_SUBTAREA, { texto: 'Nuevo' })

    const editar = envoltorio
      .findAll('button')
      .find((b) => (b.attributes('aria-label') ?? '').startsWith('Editar comentario de las 09:05'))!
    expect(editar.attributes('aria-label')).toMatch(/ de la subtarea Revisar$/)
    await editar.trigger('click')
    await flushPromises()
    const campo = envoltorio.get(
      'textarea[aria-label="Nuevo texto del comentario de la subtarea Revisar"]',
    )
    await campo.setValue('Cambiado')
    await flushPromises()
    await envoltorio
      .get('form[aria-label="Editar comentario de la subtarea Revisar"]')
      .trigger('submit')
    await flushPromises()
    const guardar = envoltorio
      .get(
        '[role="group"][aria-label="¿Guardar los cambios del comentario de la subtarea Revisar?"]',
      )
      .findAll('button')
      .find((b) => b.text() === 'Guardar')!
    await guardar.trigger('click')
    await flushPromises()
    expect(actualizar).toHaveBeenCalledWith(`${RUTA_SUBTAREA}/1`, { texto: 'Cambiado' })

    const borrar = envoltorio
      .findAll('button')
      .find((b) =>
        (b.attributes('aria-label') ?? '').startsWith('Eliminar comentario de las 09:05'),
      )!
    await borrar.trigger('click')
    await flushPromises()
    const confirmar = envoltorio
      .get('[role="group"][aria-label="¿Eliminar el comentario de la subtarea Revisar?"]')
      .findAll('button')
      .find((b) => b.text() === 'Eliminar')!
    await confirmar.trigger('click')
    await flushPromises()
    expect(eliminar).toHaveBeenCalledWith(`${RUTA_SUBTAREA}/1`)
  })

  it('añade el contexto a los nombres accesibles para no repetirlos con los de la tarea', async () => {
    obtener.mockResolvedValue(COMENTARIOS)
    const envoltorio = await montarSubtarea()

    expect(
      envoltorio
        .find('[role="region"][aria-label="Comentarios anteriores de la subtarea Revisar"]')
        .exists(),
    ).toBe(true)
    expect(
      envoltorio.find('[aria-label="Historial de comentarios de la subtarea Revisar"]').exists(),
    ).toBe(true)
    const seccion = envoltorio.get('section').element
    const titulo = document.getElementById(seccion.getAttribute('aria-labelledby')!)
    expect(titulo?.textContent?.replace(/\s+/g, ' ').trim()).toBe(
      'Comentarios de la subtarea Revisar',
    )
    // El texto visible del encabezado sigue siendo "Comentarios".
    expect(titulo?.querySelector('.sr-only')?.textContent?.trim()).toBe('de la subtarea Revisar')
  })

  it('sin contexto los nombres accesibles no cambian', async () => {
    obtener.mockResolvedValue(COMENTARIOS)
    const envoltorio = await montar()

    expect(envoltorio.find('[role="region"][aria-label="Comentarios anteriores"]').exists()).toBe(
      true,
    )
    const seccion = envoltorio.get('section').element
    const titulo = document.getElementById(seccion.getAttribute('aria-labelledby')!)
    expect(titulo?.textContent?.trim()).toBe('Comentarios')
  })

  it('avisa del número de comentarios al cargarlos, al añadir uno y al eliminarlo', async () => {
    obtener.mockResolvedValue([COMENTARIOS[0], COMENTARIOS[1]])
    crear.mockResolvedValue({
      id: 5,
      texto: 'Nuevo',
      creado: isoUtcDesdeLocal(4, 3, 10, 0),
      editado: null,
    })
    eliminar.mockResolvedValue(undefined)
    const envoltorio = await montarSubtarea()
    expect(envoltorio.emitted('actualizados')).toEqual([[2]])

    await envoltorio
      .get('textarea[aria-label="Escribe un comentario de la subtarea Revisar"]')
      .setValue('Nuevo')
    await flushPromises()
    await envoltorio.get('form:not([aria-label])').trigger('submit')
    await flushPromises()
    expect(envoltorio.emitted('actualizados')).toEqual([[2], [3]])

    await envoltorio
      .findAll('button')
      .find((b) =>
        (b.attributes('aria-label') ?? '').startsWith('Eliminar comentario de las 09:05'),
      )!
      .trigger('click')
    await flushPromises()
    await envoltorio
      .get('[role="group"][aria-label="¿Eliminar el comentario de la subtarea Revisar?"]')
      .findAll('button')
      .find((b) => b.text() === 'Eliminar')!
      .trigger('click')
    await flushPromises()
    expect(envoltorio.emitted('actualizados')).toEqual([[2], [3], [2]])
  })
})

describe('ComentariosTarea: con el editor real', () => {
  it('los campos de comentario nuevo y de edición son editores con formato y su nombre accesible', async () => {
    obtener.mockResolvedValue([
      { ...COMENTARIOS[1]!, texto: '<p><strong>Negrita</strong> y normal</p>' },
    ])
    const envoltorio = await montar(7, false)

    const nuevo = envoltorio.get('[role="textbox"][aria-label="Escribe un comentario"]')
    expect(nuevo.attributes('aria-multiline')).toBe('true')
    expect(nuevo.attributes('contenteditable')).toBe('true')
    expect(envoltorio.find('[role="toolbar"] button[aria-label="Negrita"]').exists()).toBe(true)

    await abrirEdicion(envoltorio)
    // Tiptap enfoca al crearse, tras un setTimeout y un fotograma.
    await new Promise((resolver) => setTimeout(() => requestAnimationFrame(resolver)))
    await flushPromises()

    const edicion = envoltorio.get('[role="textbox"][aria-label="Nuevo texto del comentario"]')
    expect(edicion.element.innerHTML).toContain('<strong>Negrita</strong>')
    expect(document.activeElement).toBe(edicion.element)
    const contador = document.getElementById(edicion.attributes('aria-describedby')!)
    expect(contador?.textContent?.trim()).toBe('16/500')
  })
})
