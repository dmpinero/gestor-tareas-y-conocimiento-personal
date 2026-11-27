import { defineStore } from 'pinia'
import { ref } from 'vue'

import * as api from '@/api/conocimiento'
import type {
  EstadoConocimiento,
  FuenteConocimiento,
  MensajeConocimiento,
  ResultadoBusquedaConocimiento,
  ResultadoSincronizacion,
} from '@/api/conocimiento'
import type { RolMensajeConocimiento } from '@/api/tipos'

/** Máximo de mensajes de historial que admite `POST /conocimiento/preguntar`. */
export const MAXIMO_MENSAJES_HISTORIAL = 20
/** Máximo de caracteres por mensaje que admite la API. */
export const LONGITUD_MAXIMA_MENSAJE = 4000
/** Máximo de caracteres de una búsqueda que admite `GET /conocimiento/buscar`. */
export const LONGITUD_MAXIMA_BUSQUEDA = 200

/** Un mensaje de la conversación tal como se muestra. */
export interface MensajeConversacion {
  rol: RolMensajeConocimiento
  texto: string
  /** Solo en las respuestas: las páginas de Notion citadas. */
  fuentes?: FuenteConocimiento[]
}

function esCancelacion(motivo: unknown): boolean {
  return motivo instanceof DOMException && motivo.name === 'AbortError'
}

// Conocimiento (buscador y chat con las notas de Notion). Como las demás
// tiendas, las acciones devuelven `true` si la API respondió bien; si falla,
// guardan el mensaje en `error` (estado y sincronización), `errorBusqueda`
// (búsquedas) o `errorChat` (preguntas).
//
// La conversación vive solo en la pestaña: no se guarda en la BD. A la API se
// le manda el historial reciente (como mucho 20 mensajes, sin respuestas
// vacías y cada uno de hasta 4000 caracteres) en cada pregunta.
export const useTiendaConocimiento = defineStore('conocimiento', () => {
  const estado = ref<EstadoConocimiento | null>(null)
  const sincronizando = ref(false)
  const resultadoSincronizacion = ref<ResultadoSincronizacion | null>(null)
  const error = ref<string | null>(null)
  const conversacion = ref<MensajeConversacion[]>([])
  const enviando = ref(false)
  const errorChat = ref<string | null>(null)
  let controlador: AbortController | null = null
  /** Resultados de la última búsqueda (`null` si aún no se ha buscado). */
  const resultados = ref<ResultadoBusquedaConocimiento[] | null>(null)
  /** La búsqueda (recortada) que dio `resultados`, para resaltar sus palabras. */
  const consultaBuscada = ref('')
  const buscando = ref(false)
  const errorBusqueda = ref<string | null>(null)
  let ultimaBusqueda = 0

  async function ejecutar(accion: () => Promise<void>): Promise<boolean> {
    error.value = null
    try {
      await accion()
      return true
    } catch (motivo) {
      error.value = (motivo as Error).message
      return false
    }
  }

  function cargarEstado(): Promise<boolean> {
    return ejecutar(async () => {
      estado.value = await api.obtenerEstado()
    })
  }

  async function sincronizar(): Promise<boolean> {
    if (sincronizando.value) return false
    sincronizando.value = true
    resultadoSincronizacion.value = null
    try {
      return await ejecutar(async () => {
        const resultado = await api.sincronizar()
        resultadoSincronizacion.value = resultado
        if (estado.value) {
          estado.value = {
            ...estado.value,
            paginas: resultado.paginas,
            fragmentos: resultado.fragmentos,
            ultima_sincronizacion: resultado.ultima_sincronizacion,
          }
        }
      })
    } finally {
      sincronizando.value = false
    }
  }

  /** Busca en las notas sin IA. Si se lanza otra búsqueda antes de que esta
   * responda, solo cuenta la última. */
  async function buscar(texto: string): Promise<boolean> {
    const consulta = texto.trim()
    if (consulta === '') return false
    const propia = ++ultimaBusqueda
    buscando.value = true
    errorBusqueda.value = null
    try {
      const encontrados = await api.buscar(consulta)
      if (propia !== ultimaBusqueda) return false
      resultados.value = encontrados
      consultaBuscada.value = consulta
      return true
    } catch (motivo) {
      if (propia !== ultimaBusqueda) return false
      errorBusqueda.value = (motivo as Error).message
      return false
    } finally {
      if (propia === ultimaBusqueda) buscando.value = false
    }
  }

  function historialParaEnviar(): MensajeConocimiento[] {
    return conversacion.value
      .filter((mensaje) => mensaje.texto !== '')
      .map(({ rol, texto }) => ({ rol, texto: texto.slice(0, LONGITUD_MAXIMA_MENSAJE) }))
      .slice(-MAXIMO_MENSAJES_HISTORIAL)
  }

  async function preguntar(texto: string): Promise<boolean> {
    const pregunta = texto.trim()
    if (pregunta === '' || enviando.value) return false

    errorChat.value = null
    conversacion.value.push({ rol: 'usuario', texto: pregunta })
    const mensajes = historialParaEnviar()
    conversacion.value.push({ rol: 'asistente', texto: '', fuentes: [] })
    // El objeto reactivo (no el literal) para que cada delta se pinte.
    const respuesta = conversacion.value[conversacion.value.length - 1]!
    const propio = new AbortController()
    controlador = propio
    enviando.value = true
    try {
      await api.preguntar(mensajes, {
        signal: propio.signal,
        onFuentes: (fuentes) => {
          if (!propio.signal.aborted) respuesta.fuentes = fuentes
        },
        onTexto: (delta) => {
          if (!propio.signal.aborted) respuesta.texto += delta
        },
      })
      return true
    } catch (motivo) {
      if (propio.signal.aborted || esCancelacion(motivo)) return false
      errorChat.value = (motivo as Error).message
      if (respuesta.texto === '') {
        conversacion.value = conversacion.value.filter((mensaje) => mensaje !== respuesta)
      }
      return false
    } finally {
      if (controlador === propio) {
        controlador = null
        enviando.value = false
      }
    }
  }

  /** Cancela la pregunta en curso (si hay) y empieza de cero. */
  function nuevaConversacion(): void {
    controlador?.abort()
    controlador = null
    enviando.value = false
    errorChat.value = null
    conversacion.value = []
  }

  return {
    estado,
    sincronizando,
    resultadoSincronizacion,
    error,
    conversacion,
    enviando,
    errorChat,
    resultados,
    consultaBuscada,
    buscando,
    errorBusqueda,
    cargarEstado,
    sincronizar,
    buscar,
    preguntar,
    nuevaConversacion,
  }
})
