import type { SolicitudAlta } from '@/api/altaOportunidades'

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

export function validarCamposAlta(campos: CamposAlta): ErroresAlta {
  const errores: ErroresAlta = {}
  if (!PATRON_PRJ.test(campos.prj)) errores.prj = MENSAJE_CODIGO_PRJ
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

/** Cada cuánto se consulta el estado del alta en curso. */
export const INTERVALO_SEGUIMIENTO_MS = 1000
