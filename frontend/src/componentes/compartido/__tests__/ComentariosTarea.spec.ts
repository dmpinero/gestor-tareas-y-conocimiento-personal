import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

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

let contenedor: VueWrapper | null = null

async function montar(idTarea = 7): Promise<VueWrapper> {
  contenedor = mount(ComentariosTarea, { props: { idTarea }, attachTo: document.body })
  await flushPromises()
  return contenedor
}

function historial(envoltorio: VueWrapper): HTMLElement {
  return envoltorio.get('[aria-label="Historial de comentarios"]').element as HTMLElement
}

function campoTexto(envoltorio: VueWrapper) {
  return envoltorio.get('textarea[aria-label="Escribe un comentario"]')
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

    await envoltorio.setProps({ idTarea: 8 })
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

    await envoltorio.setProps({ idTarea: 8 })
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
      fila.querySelector('p')!.textContent,
    ])
    expect(filas).toEqual([
      ['09:05', 'Primer comentario'],
      ['18:30', 'Línea 1\nLínea 2'],
      ['08:00', '<b>sin formato</b>'],
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

  it('respeta los saltos de línea del texto', async () => {
    obtener.mockResolvedValue(COMENTARIOS)

    const envoltorio = await montar()

    const parrafos = historial(envoltorio).querySelectorAll('li li p')
    expect(parrafos[1]!.classList.contains('whitespace-pre-wrap')).toBe(true)
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

  it('desactiva el botón con el campo vacío o solo con espacios', async () => {
    obtener.mockResolvedValue([])
    const envoltorio = await montar()

    expect(botonEnviar(envoltorio).attributes('disabled')).toBeDefined()
    await escribir(envoltorio, '   \n ')
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
    const filas = [...historial(envoltorio).querySelectorAll('li li p')].map((p) => p.textContent)
    expect(filas).toEqual(['Primer comentario', 'Hola'])
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
    expect(campo.value).toBe('Línea 1\nLínea 2')
    expect(campo.maxLength).toBe(500)
    expect(document.activeElement).toBe(campo)
    const contador = document.getElementById(campo.getAttribute('aria-describedby')!)
    expect(contador?.textContent?.trim()).toBe('15/500')
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
    await campoEdicion(envoltorio).setValue('  \n ')
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
    const textos = [...historial(envoltorio).querySelectorAll('li li p')].map((p) => p.textContent)
    expect(textos).toEqual(['Primer comentario', 'Texto nuevo', '<b>sin formato</b>'])
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
    const textos = [...historial(envoltorio).querySelectorAll('li li p')].map((p) => p.textContent)
    expect(textos).toEqual(['Primer comentario', '<b>sin formato</b>'])
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
