// Reglas del nombre de una subtarea, compartidas por el detalle de la tarea y
// el alta rápida del tablero: obligatorio y de 1 a 200 caracteres sin los
// espacios de los extremos.
export const MAX_NOMBRE_SUBTAREA = 200
export const ERROR_NOMBRE_SUBTAREA_OBLIGATORIO = 'El nombre de la subtarea es obligatorio.'
export const ERROR_NOMBRE_SUBTAREA_LARGO = `El nombre de la subtarea no puede superar ${MAX_NOMBRE_SUBTAREA} caracteres.`

/** Nombre recortado y válido, o el mensaje de error que explica por qué no. */
export function validarNombreSubtarea(nombre: string): { nombre: string } | { error: string } {
  const recortado = nombre.trim()
  if (recortado === '') return { error: ERROR_NOMBRE_SUBTAREA_OBLIGATORIO }
  if (recortado.length > MAX_NOMBRE_SUBTAREA) return { error: ERROR_NOMBRE_SUBTAREA_LARGO }
  return { nombre: recortado }
}
