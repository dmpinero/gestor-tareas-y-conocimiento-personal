import { clienteApi, urlRecurso } from './cliente'

/**
 * Alta automática de oportunidades. La sirve el servicio "automatizador"
 * (Playwright) bajo `/alta-oportunidades`; los valores fijos vienen de una
 * configuración local fuera de git.
 */

export interface Asignacion {
  nombre: string
  porcentaje: string
}

export interface ValoresFijosAlta {
  perfil: string
  cliente: string
  grupo: string
  tipo: string
  segmentacion: string
  fase: string
  probabilidad: string
  dias_fecha_limite: number
  tipo_servicio: string
  lineas_negocio: Asignacion[]
  comunidades: Asignacion[]
}

/** Respuesta de `GET /alta-oportunidades/configuracion`. Si la configuración
 * local falta o no es válida, `valores` es `null` y `error` explica por qué. */
export interface ResumenConfiguracionAlta {
  valores: ValoresFijosAlta | null
  error: string | null
  /** Hoy + días de la configuración, en dd/mm/aaaa. */
  fecha_limite: string | null
  /** Hoy + 1 mes, en dd/mm/aaaa. */
  fecha_inicio: string
  /** Nombre de la entrada del menú (de la configuración local o el predeterminado). */
  nombre_menu: string
}

/** Cuerpo de `POST /alta-oportunidades/ejecucion`. */
export interface SolicitudAlta {
  prj: string
  /** `null` para buscarla en Notion. */
  descripcion: string | null
  duracion: number
  importe: number
  coste: number
}

export type TipoPreguntaAlta = 'inicio_sesion' | 'duplicado' | 'intervencion_manual' | 'guardar'

export interface PreguntaAlta {
  id: number
  tipo: TipoPreguntaAlta
  mensaje: string
  detalle: string | null
  /** Vacía cuando solo hay que actuar en la ventana del navegador. */
  opciones: { valor: string; etiqueta: string }[]
}

export type EstadoEjecucionAlta = 'en_curso' | 'guardada' | 'no_guardada' | 'error'

export interface EjecucionAlta {
  id: string
  prj: string
  estado: EstadoEjecucionAlta
  terminada: boolean
  pasos: string[]
  pregunta: PreguntaAlta | null
  mensaje_final: string | null
  hay_captura: boolean
}

const RUTA = '/alta-oportunidades'

export function obtenerConfiguracionAlta(): Promise<ResumenConfiguracionAlta> {
  return clienteApi.obtener<ResumenConfiguracionAlta>(`${RUTA}/configuracion`)
}

export function lanzarAlta(solicitud: SolicitudAlta): Promise<EjecucionAlta> {
  return clienteApi.crear<EjecucionAlta>(`${RUTA}/ejecucion`, solicitud)
}

/** Estado del último alta; rechaza con `ErrorApi` 404 si no se ha lanzado ninguno. */
export function obtenerEjecucionAlta(): Promise<EjecucionAlta> {
  return clienteApi.obtener<EjecucionAlta>(`${RUTA}/ejecucion`)
}

export function responderPreguntaAlta(idPregunta: number, valor: string): Promise<EjecucionAlta> {
  return clienteApi.crear<EjecucionAlta>(`${RUTA}/ejecucion/respuesta`, {
    id_pregunta: idPregunta,
    valor,
  })
}

/** URL de la captura PNG del resultado guardado de la ejecución indicada. */
export function urlCapturaAlta(idEjecucion: string): string {
  return `${urlRecurso(`${RUTA}/ejecucion/captura`)}?ejecucion=${encodeURIComponent(idEjecucion)}`
}
