import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { clienteApi, ErrorApi } from '@/api/cliente'
import {
  buscar,
  crearLectorSse,
  obtenerEstado,
  preguntar,
  sincronizar,
  type EventoSse,
} from '@/api/conocimiento'
import type { FuenteConocimiento } from '@/api/tipos'

vi.mock('@/api/cliente', async (original) => ({
  ...(await original()),
  clienteApi: {
    obtener: vi.fn<(...args: unknown[]) => unknown>(),
    crear: vi.fn<(...args: unknown[]) => unknown>(),
  },
}))

/** Respuesta `text/event-stream` que entrega el cuerpo en los trozos dados. */
function respuestaSse(trozos: string[], estado = 200): Response {
  const codificador = new TextEncoder()
  const cuerpo = new ReadableStream<Uint8Array>({
    start(controlador) {
      for (const trozo of trozos) controlador.enqueue(codificador.encode(trozo))
      controlador.close()
    },
  })
  return new Response(cuerpo, {
    status: estado,
    headers: { 'Content-Type': 'text/event-stream' },
  })
}

const FUENTE: FuenteConocimiento = {
  pagina_id: 'abc',
  titulo: 'Recetas',
  url: 'https://www.notion.so/abc',
}

describe('crearLectorSse', () => {
  it('separa los eventos aunque las líneas lleguen partidas entre trozos', () => {
    const eventos: EventoSse[] = []
    const lector = crearLectorSse((evento) => eventos.push(evento))
    lector.anadir('event: tex')
    lector.anadir('to\ndata: {"delta"')
    lector.anadir(': "Hola"}\n')
    lector.anadir('\nevent: fin\r\ndata: {}\r\n\r\n')
    expect(eventos).toEqual([
      { evento: 'texto', datos: '{"delta": "Hola"}' },
      { evento: 'fin', datos: '{}' },
    ])
  })

  it('un "\\r\\n" partido entre dos trozos no cierra el evento antes de tiempo', () => {
    const eventos: EventoSse[] = []
    const lector = crearLectorSse((evento) => eventos.push(evento))
    lector.anadir('event: texto\r')
    lector.anadir('\ndata: a\r')
    lector.anadir('\n\r')
    lector.anadir('\n')
    expect(eventos).toEqual([{ evento: 'texto', datos: 'a' }])
  })

  it('une varias líneas data con saltos de línea e ignora comentarios', () => {
    const eventos: EventoSse[] = []
    const lector = crearLectorSse((evento) => eventos.push(evento))
    lector.anadir(': ping\n\nevent: texto\ndata: a\ndata: b\n\n')
    expect(eventos).toEqual([{ evento: 'texto', datos: 'a\nb' }])
  })

  it('sin línea event, el evento es "message"', () => {
    const eventos: EventoSse[] = []
    const lector = crearLectorSse((evento) => eventos.push(evento))
    lector.anadir('data: x\n\n')
    expect(eventos).toEqual([{ evento: 'message', datos: 'x' }])
  })
})

describe('obtenerEstado y sincronizar', () => {
  beforeEach(() => vi.clearAllMocks())

  it('obtenerEstado pide GET /conocimiento/estado', async () => {
    vi.mocked(clienteApi.obtener).mockResolvedValue({ paginas: 1 })
    await expect(obtenerEstado()).resolves.toEqual({ paginas: 1 })
    expect(clienteApi.obtener).toHaveBeenCalledWith('/conocimiento/estado')
  })

  it('sincronizar pide POST /conocimiento/sincronizar', async () => {
    vi.mocked(clienteApi.crear).mockResolvedValue({ nuevas: 2 })
    await expect(sincronizar()).resolves.toEqual({ nuevas: 2 })
    expect(clienteApi.crear).toHaveBeenCalledWith('/conocimiento/sincronizar', {})
  })
})

describe('buscar', () => {
  beforeEach(() => vi.clearAllMocks())

  it('pide GET /conocimiento/buscar con la búsqueda codificada en la URL', async () => {
    const resultados = [
      { pagina_id: 'p', titulo: 'T', url: 'https://n.so/p', fragmento: 'f', orden: 0 },
    ]
    vi.mocked(clienteApi.obtener).mockResolvedValue(resultados)
    await expect(buscar('paella & arroz?')).resolves.toEqual(resultados)
    expect(clienteApi.obtener).toHaveBeenCalledWith('/conocimiento/buscar?q=paella+%26+arroz%3F')
  })

  it('envía el límite si se indica', async () => {
    vi.mocked(clienteApi.obtener).mockResolvedValue([])
    await buscar('paella', 5)
    expect(clienteApi.obtener).toHaveBeenCalledWith('/conocimiento/buscar?q=paella&limite=5')
  })
})

describe('preguntar', () => {
  const fetchOriginal = globalThis.fetch

  afterEach(() => {
    globalThis.fetch = fetchOriginal
  })

  it('envía el historial y entrega fuentes y deltas en orden hasta fin', async () => {
    const espia = vi
      .fn<typeof fetch>()
      .mockResolvedValue(
        respuestaSse([
          `event: fuentes\ndata: ${JSON.stringify([FUENTE])}\n\n`,
          'event: texto\ndata: {"delta": "Ho',
          'la"}\n\nevent: texto\ndata: {"delta": " mundo"}\n\n',
          'event: fin\ndata: {}\n\n',
        ]),
      )
    globalThis.fetch = espia
    const onFuentes = vi.fn()
    const onTexto = vi.fn()
    const mensajes = [{ rol: 'usuario' as const, texto: '¿Qué hay?' }]

    await preguntar(mensajes, { onFuentes, onTexto })

    const [url, opciones] = espia.mock.calls[0]!
    expect(url).toBe('/api/v1/conocimiento/preguntar')
    expect(opciones?.method).toBe('POST')
    expect(JSON.parse(String(opciones?.body))).toEqual({ mensajes })
    expect((opciones?.headers as Record<string, string>)['Content-Type']).toBe('application/json')
    expect(onFuentes).toHaveBeenCalledWith([FUENTE])
    expect(onTexto.mock.calls).toEqual([['Hola'], [' mundo']])
  })

  it('un evento error rechaza con su detalle', async () => {
    globalThis.fetch = vi
      .fn<typeof fetch>()
      .mockResolvedValue(
        respuestaSse([
          'event: texto\ndata: {"delta": "a"}\n\nevent: error\ndata: {"detalle": "Falló Claude"}\n\n',
        ]),
      )
    const onTexto = vi.fn()
    await expect(
      preguntar([{ rol: 'usuario', texto: 'x' }], { onFuentes: vi.fn(), onTexto }),
    ).rejects.toThrow('Falló Claude')
    expect(onTexto).toHaveBeenCalledWith('a')
  })

  it('si el flujo se corta sin fin, rechaza', async () => {
    globalThis.fetch = vi
      .fn<typeof fetch>()
      .mockResolvedValue(respuestaSse(['event: texto\ndata: {"delta": "a"}\n\n']))
    await expect(
      preguntar([{ rol: 'usuario', texto: 'x' }], { onFuentes: vi.fn(), onTexto: vi.fn() }),
    ).rejects.toThrow('La respuesta se cortó antes de terminar.')
  })

  it('una respuesta HTTP de error rechaza con ErrorApi y su detalle', async () => {
    globalThis.fetch = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({ detalle: 'Falta configurar ANTHROPIC_API_KEY en backend/.env' }),
        {
          status: 503,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    )
    const promesa = preguntar([{ rol: 'usuario', texto: 'x' }], {
      onFuentes: vi.fn(),
      onTexto: vi.fn(),
    })
    await expect(promesa).rejects.toBeInstanceOf(ErrorApi)
    await expect(promesa).rejects.toMatchObject({
      estado: 503,
      message: 'Falta configurar ANTHROPIC_API_KEY en backend/.env',
    })
  })

  it('pasa la señal de cancelación a fetch', async () => {
    const espia = vi
      .fn<typeof fetch>()
      .mockResolvedValue(respuestaSse(['event: fin\ndata: {}\n\n']))
    globalThis.fetch = espia
    const controlador = new AbortController()
    await preguntar([{ rol: 'usuario', texto: 'x' }], {
      onFuentes: vi.fn(),
      onTexto: vi.fn(),
      signal: controlador.signal,
    })
    expect(espia.mock.calls[0]![1]?.signal).toBe(controlador.signal)
  })
})
