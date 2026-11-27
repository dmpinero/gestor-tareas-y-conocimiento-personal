import { clienteApi, ErrorApi, urlRecurso } from '@/api/cliente'
import type {
  EstadoConocimiento,
  FuenteConocimiento,
  MensajeConocimiento,
  ResultadoBusquedaConocimiento,
  ResultadoSincronizacion,
} from '@/api/tipos'

export type {
  EstadoConocimiento,
  FuenteConocimiento,
  MensajeConocimiento,
  ResultadoBusquedaConocimiento,
  ResultadoSincronizacion,
} from '@/api/tipos'

export function obtenerEstado(): Promise<EstadoConocimiento> {
  return clienteApi.obtener<EstadoConocimiento>('/conocimiento/estado')
}

export function sincronizar(): Promise<ResultadoSincronizacion> {
  return clienteApi.crear<ResultadoSincronizacion>('/conocimiento/sincronizar', {})
}

/**
 * Busca en las notas de Notion ya sincronizadas, sin IA (`GET /conocimiento/buscar`):
 * los trozos que coinciden, del más al menos relevante. Sin `limite`, la API
 * devuelve 20 como mucho.
 */
export function buscar(q: string, limite?: number): Promise<ResultadoBusquedaConocimiento[]> {
  const parametros = new URLSearchParams({ q })
  if (limite !== undefined) parametros.set('limite', String(limite))
  return clienteApi.obtener<ResultadoBusquedaConocimiento[]>(`/conocimiento/buscar?${parametros}`)
}

/** Un evento de un flujo `text/event-stream`: su nombre y sus datos sin analizar. */
export interface EventoSse {
  evento: string
  datos: string
}

/**
 * Lector incremental de `text/event-stream`: se le van pasando los trozos de
 * texto tal como llegan (una línea puede quedar partida entre dos) y llama a
 * `alEvento` con cada evento completo (terminado en línea en blanco).
 */
export function crearLectorSse(alEvento: (evento: EventoSse) => void) {
  let pendiente = ''
  let nombre = ''
  let datos: string[] = []

  function procesarLinea(linea: string): void {
    if (linea === '') {
      if (datos.length > 0) alEvento({ evento: nombre || 'message', datos: datos.join('\n') })
      nombre = ''
      datos = []
      return
    }
    if (linea.startsWith(':')) return
    const separador = linea.indexOf(':')
    const campo = separador < 0 ? linea : linea.slice(0, separador)
    let valor = separador < 0 ? '' : linea.slice(separador + 1)
    if (valor.startsWith(' ')) valor = valor.slice(1)
    if (campo === 'event') nombre = valor
    else if (campo === 'data') datos.push(valor)
  }

  return {
    anadir(trozo: string): void {
      pendiente += trozo
      // Un "\r" final puede ser la primera mitad de un "\r\n" partido: se
      // guarda para el trozo siguiente en vez de tomarlo como fin de línea.
      const corte = pendiente.endsWith('\r') ? pendiente.length - 1 : pendiente.length
      const lineas = pendiente.slice(0, corte).split(/\r\n|\r|\n/)
      // La última puede estar a medias.
      pendiente = (lineas.pop() ?? '') + pendiente.slice(corte)
      for (const linea of lineas) procesarLinea(linea)
    },
  }
}

export interface OpcionesPreguntar {
  /** Las páginas citadas; llega antes que el texto. */
  onFuentes: (fuentes: FuenteConocimiento[]) => void
  /** Cada trozo nuevo del texto de la respuesta. */
  onTexto: (delta: string) => void
  signal?: AbortSignal
}

async function mensajeDeError(respuesta: Response): Promise<string> {
  try {
    const datos = await respuesta.json()
    if (typeof datos.detalle === 'string') return datos.detalle
    if (typeof datos.detail === 'string') return datos.detail
    if (Array.isArray(datos.detail)) {
      return datos.detail.map((error: { msg?: string }) => error.msg).join('; ')
    }
  } catch {
    // El cuerpo no era JSON; se usa el texto del estado HTTP.
  }
  return respuesta.statusText
}

/**
 * Envía la conversación a `POST /conocimiento/preguntar` y va entregando la
 * respuesta en streaming (SSE). Se resuelve con el evento `fin`; se rechaza con
 * `ErrorApi` si la API responde con error HTTP, con el `detalle` de un evento
 * `error`, o si el flujo se corta antes de `fin`. Con `signal` se cancela.
 */
export async function preguntar(
  mensajes: MensajeConocimiento[],
  { onFuentes, onTexto, signal }: OpcionesPreguntar,
): Promise<void> {
  const respuesta = await fetch(urlRecurso('/conocimiento/preguntar'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({ mensajes }),
    signal,
  })
  if (!respuesta.ok) {
    throw new ErrorApi(respuesta.status, await mensajeDeError(respuesta))
  }
  if (!respuesta.body) throw new Error('La respuesta se cortó antes de terminar.')

  let terminado = false
  let errorFlujo: string | null = null
  const lector = crearLectorSse(({ evento, datos }) => {
    if (terminado || errorFlujo !== null) return
    if (evento === 'fuentes') onFuentes(JSON.parse(datos) as FuenteConocimiento[])
    else if (evento === 'texto') onTexto((JSON.parse(datos) as { delta: string }).delta)
    else if (evento === 'fin') terminado = true
    else if (evento === 'error') {
      errorFlujo = (JSON.parse(datos) as { detalle?: string }).detalle ?? 'Error desconocido.'
    }
  })

  const decodificador = new TextDecoder()
  const flujo = respuesta.body.getReader()
  try {
    while (!terminado && errorFlujo === null) {
      const { done, value } = await flujo.read()
      if (done) break
      lector.anadir(decodificador.decode(value, { stream: true }))
    }
    lector.anadir(decodificador.decode() + '\n\n')
  } finally {
    if (terminado || errorFlujo !== null) void flujo.cancel().catch(() => {})
  }

  if (errorFlujo !== null) throw new ErrorApi(respuesta.status, errorFlujo)
  if (!terminado) throw new Error('La respuesta se cortó antes de terminar.')
}
