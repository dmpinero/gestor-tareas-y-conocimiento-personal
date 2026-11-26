import type { SolicitudAlta, SolicitudAltaAxasMs3 } from '@/api/altaOportunidades'

/** Mismo mensaje que el script original y que la API. */
export const MENSAJE_CODIGO_PRJ = 'El código debe tener el formato PRJ-XXXXX (5 dígitos).'

/** Campos variables del formulario, tal y como se escriben. */
export interface CamposAlta {
  prj: string
  descripcion: string
  duracion: string
  importe: string
  coste: string
}

export type ErroresAlta = Partial<Record<keyof CamposAlta, string>>

const PATRON_PRJ = /^PRJ-\d{5}$/
const PATRON_ENTERO = /^\d+$/
// Admite coma o punto decimal (10000, 10000,50, 10000.5).
const PATRON_CANTIDAD = /^\d+([.,]\d{1,2})?$/

function aNumero(texto: string): number {
  return Number(texto.trim().replace(',', '.'))
}

function errorCantidad(texto: string, nombre: string): string | undefined {
  if (!texto.trim()) return `${nombre} es obligatorio.`
  if (!PATRON_CANTIDAD.test(texto.trim()))
    return `${nombre} debe ser un número mayor o igual que cero.`
  return undefined
}

/** Duración, importe y coste: las mismas reglas en las dos variantes del alta. */
type CamposComunes = Pick<CamposAlta, 'duracion' | 'importe' | 'coste'>

function validarCamposComunes(campos: CamposComunes): Partial<Record<keyof CamposComunes, string>> {
  const errores: Partial<Record<keyof CamposComunes, string>> = {}
  const duracion = campos.duracion.trim()
  if (!duracion) errores.duracion = 'La duración es obligatoria.'
  else if (!PATRON_ENTERO.test(duracion) || Number(duracion) < 1)
    errores.duracion = 'La duración debe ser un número entero de meses mayor que cero.'
  const importe = errorCantidad(campos.importe, 'El importe total previsto')
  if (importe) errores.importe = importe
  const coste = errorCantidad(campos.coste, 'El coste total previsto')
  if (coste) errores.coste = coste
  return errores
}

export function validarCamposAlta(campos: CamposAlta): ErroresAlta {
  const errores: ErroresAlta = {}
  if (!PATRON_PRJ.test(campos.prj)) errores.prj = MENSAJE_CODIGO_PRJ
  return { ...errores, ...validarCamposComunes(campos) }
}

/** Nombre con el que se creará la oportunidad: "<PRJ> <descripción>". */
export function nombrePrevisto(prj: string, descripcion: string): string {
  const texto = descripcion.trim()
  return texto ? `${prj} ${texto}` : `${prj} + descripción (se buscará en Notion)`
}

/** Cuerpo de la petición a partir de unos campos ya validados. */
export function aSolicitudAlta(campos: CamposAlta): SolicitudAlta {
  return {
    prj: campos.prj,
    descripcion: campos.descripcion.trim() || null,
    duracion: Number(campos.duracion.trim()),
    importe: aNumero(campos.importe),
    coste: aNumero(campos.coste),
  }
}

// --- Alta AXAS MS3 -------------------------------------------------------------

/** Campos variables del alta AXAS MS3, tal y como se escriben. */
export interface CamposAltaAxasMs3 {
  codigo: string
  descripcion: string
  duracion: string
  importe: string
  coste: string
}

export type ErroresAltaAxasMs3 = Partial<Record<keyof CamposAltaAxasMs3, string>>

export const MENSAJE_SIN_CODIGO_SERVICIO = 'Elige o crea un código de servicio.'
export const MENSAJE_SIN_DESCRIPCION = 'La descripción es obligatoria.'

export function validarCamposAxasMs3(campos: CamposAltaAxasMs3): ErroresAltaAxasMs3 {
  const errores: ErroresAltaAxasMs3 = {}
  if (!campos.codigo.trim()) errores.codigo = MENSAJE_SIN_CODIGO_SERVICIO
  if (!campos.descripcion.trim()) errores.descripcion = MENSAJE_SIN_DESCRIPCION
  return { ...errores, ...validarCamposComunes(campos) }
}

/** Nombre de la oportunidad: "AXAS-MS3-EV" + 2 últimos caracteres del código + "-" + descripción. */
export function nombrePrevistoAxasMs3(codigo: string, descripcion: string): string {
  const sufijo = codigo.trim().slice(-2) || 'XX'
  return `AXAS-MS3-EV${sufijo}-${descripcion.trim() || 'descripción'}`
}

export function aSolicitudAltaAxasMs3(campos: CamposAltaAxasMs3): SolicitudAltaAxasMs3 {
  return {
    codigo_servicio: campos.codigo.trim(),
    descripcion: campos.descripcion.trim(),
    duracion: Number(campos.duracion.trim()),
    importe: aNumero(campos.importe),
    coste: aNumero(campos.coste),
  }
}

/** Cada cuánto se consulta el estado del alta en curso. */
export const INTERVALO_SEGUIMIENTO_MS = 1000
