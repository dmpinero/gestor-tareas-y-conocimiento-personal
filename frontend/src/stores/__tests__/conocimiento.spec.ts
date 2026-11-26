import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as api from '@/api/conocimiento'
import type {
  EstadoConocimiento,
  MensajeConocimiento,
  OpcionesPreguntar,
  ResultadoSincronizacion,
} from '@/api/conocimiento'
import { useTiendaConocimiento } from '@/stores/conocimiento'

vi.mock('@/api/conocimiento', async (original) => ({
  ...(await original()),
  obtenerEstado: vi.fn(),
  sincronizar: vi.fn(),
  preguntar: vi.fn(),
}))

const ESTADO: EstadoConocimiento = {
  configurado: { notion: true, anthropic: true },
  paginas: 3,
  fragmentos: 10,
  ultima_sincronizacion: null,
}

const RESULTADO: ResultadoSincronizacion = {
  paginas: 5,
  fragmentos: 20,
  nuevas: 2,
  actualizadas: 1,
  eliminadas: 0,
  ultima_sincronizacion: '2026-11-26T10:00:00Z',
}

const FUENTE = { pagina_id: 'p1', titulo: 'Recetas', url: 'https://www.notion.so/p1' }

describe('useTiendaConocimiento', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('cargarEstado guarda el estado', async () => {
    vi.mocked(api.obtenerEstado).mockResolvedValue(ESTADO)
    const tienda = useTiendaConocimiento()
    expect(await tienda.cargarEstado()).toBe(true)
    expect(tienda.estado).toEqual(ESTADO)
  })

  it('sincronizar guarda el resultado y actualiza recuentos y fecha', async () => {
    vi.mocked(api.obtenerEstado).mockResolvedValue(ESTADO)
    let resolver!: (valor: ResultadoSincronizacion) => void
    vi.mocked(api.sincronizar).mockReturnValue(new Promise((r) => (resolver = r)))
    const tienda = useTiendaConocimiento()
    await tienda.cargarEstado()

    const promesa = tienda.sincronizar()
    expect(tienda.sincronizando).toBe(true)
    resolver(RESULTADO)
    expect(await promesa).toBe(true)

    expect(tienda.sincronizando).toBe(false)
    expect(tienda.resultadoSincronizacion).toEqual(RESULTADO)
    expect(tienda.estado).toMatchObject({
      paginas: 5,
      fragmentos: 20,
      ultima_sincronizacion: '2026-11-26T10:00:00Z',
    })
  })

  it('si sincronizar falla guarda el error y no cambia el estado', async () => {
    vi.mocked(api.obtenerEstado).mockResolvedValue(ESTADO)
    vi.mocked(api.sincronizar).mockRejectedValue(new Error('Notion no responde'))
    const tienda = useTiendaConocimiento()
    await tienda.cargarEstado()

    expect(await tienda.sincronizar()).toBe(false)
    expect(tienda.error).toBe('Notion no responde')
    expect(tienda.sincronizando).toBe(false)
    expect(tienda.estado).toEqual(ESTADO)
  })

  it('preguntar añade la pregunta y una respuesta que crece con los deltas y lleva sus fuentes', async () => {
    vi.mocked(api.preguntar).mockImplementation(async (_mensajes, opciones) => {
      opciones.onFuentes([FUENTE])
      opciones.onTexto('Ho')
      opciones.onTexto('la')
    })
    const tienda = useTiendaConocimiento()

    expect(await tienda.preguntar('  ¿Qué hay?  ')).toBe(true)

    expect(api.preguntar).toHaveBeenCalledWith(
      [{ rol: 'usuario', texto: '¿Qué hay?' }],
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
    expect(tienda.conversacion).toEqual([
      { rol: 'usuario', texto: '¿Qué hay?' },
      { rol: 'asistente', texto: 'Hola', fuentes: [FUENTE] },
    ])
    expect(tienda.enviando).toBe(false)
  })

  it('mientras llega la respuesta, enviando es true y el texto ya se ve', async () => {
    let terminar!: () => void
    vi.mocked(api.preguntar).mockImplementation((_m, opciones) => {
      opciones.onTexto('Parcial')
      return new Promise<void>((r) => (terminar = r))
    })
    const tienda = useTiendaConocimiento()
    const promesa = tienda.preguntar('Hola')
    expect(tienda.enviando).toBe(true)
    expect(tienda.conversacion[1]?.texto).toBe('Parcial')
    terminar()
    await promesa
    expect(tienda.enviando).toBe(false)
  })

  it('envía el historial anterior en el formato del contrato', async () => {
    vi.mocked(api.preguntar).mockImplementation(async (_m, opciones) => {
      opciones.onTexto('R1')
    })
    const tienda = useTiendaConocimiento()
    await tienda.preguntar('P1')
    await tienda.preguntar('P2')
    expect(vi.mocked(api.preguntar).mock.calls[1]![0]).toEqual([
      { rol: 'usuario', texto: 'P1' },
      { rol: 'asistente', texto: 'R1' },
      { rol: 'usuario', texto: 'P2' },
    ])
  })

  it('envía como mucho los 20 mensajes más recientes', async () => {
    vi.mocked(api.preguntar).mockImplementation(async (_m, opciones) => {
      opciones.onTexto('R')
    })
    const tienda = useTiendaConocimiento()
    for (let i = 1; i <= 11; i++) await tienda.preguntar(`P${i}`)
    const enviados = vi.mocked(api.preguntar).mock.calls[10]![0] as MensajeConocimiento[]
    expect(enviados).toHaveLength(20)
    expect(enviados[0]).toEqual({ rol: 'asistente', texto: 'R' })
    expect(enviados[enviados.length - 1]).toEqual({ rol: 'usuario', texto: 'P11' })
    // La conversación visible conserva todo.
    expect(tienda.conversacion).toHaveLength(22)
  })

  it('recorta a 4000 caracteres las respuestas largas que reenvía en el historial', async () => {
    vi.mocked(api.preguntar).mockImplementationOnce(async (_m, opciones) => {
      opciones.onTexto('x'.repeat(5000))
    })
    vi.mocked(api.preguntar).mockResolvedValueOnce(undefined)
    const tienda = useTiendaConocimiento()
    await tienda.preguntar('P1')
    await tienda.preguntar('P2')
    const enviados = vi.mocked(api.preguntar).mock.calls[1]![0] as MensajeConocimiento[]
    expect(enviados[1]!.texto).toHaveLength(4000)
    expect(tienda.conversacion[1]!.texto).toHaveLength(5000)
  })

  it('no envía preguntas vacías ni mientras hay otra en curso', async () => {
    vi.mocked(api.preguntar).mockReturnValue(new Promise<void>(() => {}))
    const tienda = useTiendaConocimiento()
    expect(await tienda.preguntar('   ')).toBe(false)
    void tienda.preguntar('Una')
    expect(await tienda.preguntar('Otra')).toBe(false)
    expect(api.preguntar).toHaveBeenCalledTimes(1)
  })

  it('si la pregunta falla guarda el error y quita la respuesta vacía', async () => {
    vi.mocked(api.preguntar).mockRejectedValue(new Error('Falló Claude'))
    const tienda = useTiendaConocimiento()
    expect(await tienda.preguntar('Hola')).toBe(false)
    expect(tienda.errorChat).toBe('Falló Claude')
    expect(tienda.conversacion).toEqual([{ rol: 'usuario', texto: 'Hola' }])
    expect(tienda.enviando).toBe(false)
  })

  it('no reenvía respuestas vacías en el historial', async () => {
    vi.mocked(api.preguntar).mockRejectedValueOnce(new Error('x'))
    vi.mocked(api.preguntar).mockResolvedValueOnce(undefined)
    const tienda = useTiendaConocimiento()
    await tienda.preguntar('P1')
    await tienda.preguntar('P2')
    expect(vi.mocked(api.preguntar).mock.calls[1]![0]).toEqual([
      { rol: 'usuario', texto: 'P1' },
      { rol: 'usuario', texto: 'P2' },
    ])
  })

  it('nuevaConversacion cancela la petición en curso y vacía la conversación', async () => {
    let opcionesRecibidas!: OpcionesPreguntar
    vi.mocked(api.preguntar).mockImplementation((_m, opciones) => {
      opcionesRecibidas = opciones
      return new Promise<void>((_r, rechazar) => {
        opciones.signal?.addEventListener('abort', () =>
          rechazar(new DOMException('Abortado', 'AbortError')),
        )
      })
    })
    const tienda = useTiendaConocimiento()
    const promesa = tienda.preguntar('Hola')

    tienda.nuevaConversacion()

    expect(opcionesRecibidas.signal?.aborted).toBe(true)
    expect(tienda.conversacion).toEqual([])
    expect(tienda.enviando).toBe(false)
    expect(await promesa).toBe(false)
    expect(tienda.errorChat).toBeNull()
    expect(tienda.conversacion).toEqual([])
  })

  it('los deltas que lleguen tras nuevaConversacion no reaparecen', async () => {
    let opcionesRecibidas!: OpcionesPreguntar
    vi.mocked(api.preguntar).mockImplementation((_m, opciones) => {
      opcionesRecibidas = opciones
      return new Promise<void>(() => {})
    })
    const tienda = useTiendaConocimiento()
    void tienda.preguntar('Hola')
    tienda.nuevaConversacion()
    opcionesRecibidas.onTexto('tarde')
    opcionesRecibidas.onFuentes([FUENTE])
    expect(tienda.conversacion).toEqual([])
  })
})
