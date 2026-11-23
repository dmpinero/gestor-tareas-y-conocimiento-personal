// Reglas del nombre de un código de servicio (p. ej. «AXAS0024»), las mismas que
// aplica la API: de 2 a 20 caracteres sin los espacios de los extremos y sin
// espacios interiores. Las comparten la página de Ajustes y el alta de
// oportunidades AXAS MS3.
export const MIN_CODIGO_SERVICIO = 2
export const MAX_CODIGO_SERVICIO = 20
export const ERROR_CODIGO_SERVICIO_CORTO = `El código de servicio debe tener al menos ${MIN_CODIGO_SERVICIO} caracteres.`
export const ERROR_CODIGO_SERVICIO_LARGO = `El código de servicio no puede superar los ${MAX_CODIGO_SERVICIO} caracteres.`
export const ERROR_CODIGO_SERVICIO_CON_ESPACIOS =
  'El código de servicio no puede contener espacios.'

/** Código recortado y válido, o el mensaje de error que explica por qué no. */
export function validarCodigoServicio(nombre: string): { nombre: string } | { error: string } {
  const recortado = nombre.trim()
  if (recortado.length < MIN_CODIGO_SERVICIO) return { error: ERROR_CODIGO_SERVICIO_CORTO }
  if (recortado.length > MAX_CODIGO_SERVICIO) return { error: ERROR_CODIGO_SERVICIO_LARGO }
  if (/\s/.test(recortado)) return { error: ERROR_CODIGO_SERVICIO_CON_ESPACIOS }
  return { nombre: recortado }
}
