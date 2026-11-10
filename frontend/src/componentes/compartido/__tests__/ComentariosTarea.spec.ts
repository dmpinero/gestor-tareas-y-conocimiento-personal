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
    },
  }
})

const obtener = vi.mocked(clienteApi.obtener)
const crear = vi.mocked(clienteApi.crear)

// Marca UTC con `Z` (como la envía la API) de una hora local dada, para que
// los tests no dependan de la zona horaria.
function isoUtcDesdeLocal(mes: number, dia: number, hora: number, minuto: number): string {
  return new Date(2026, mes - 1, dia, hora, minuto, 5).toISOString().replace(/\.\d{3}Z$/, 'Z')
}

const COMENTARIOS: Comentario[] = [
  { id: 1, texto: 'Primer comentario', creado: isoUtcDesdeLocal(4, 1, 9, 5) },
  { id: 2, texto: 'Línea 1\nLínea 2', creado: isoUtcDesdeLocal(4, 1, 18, 30) },
  { id: 3, texto: '<b>sin formato</b>', creado: isoUtcDesdeLocal(4, 2, 8, 0) },
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
      set: (valor: number) => asignaciones.push(valor),
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
    const nuevo: Comentario = { id: 9, texto: 'Hola', creado: isoUtcDesdeLocal(11, 10, 11, 45) }
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

  it('el primer comentario sustituye al estado vacío', async () => {
    obtener.mockResolvedValue([])
    crear.mockResolvedValue({ id: 9, texto: 'Hola', creado: isoUtcDesdeLocal(11, 10, 11, 45) })
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
    crear.mockResolvedValue({ id: 9, texto: 'Hola', creado: isoUtcDesdeLocal(11, 10, 11, 45) })
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
