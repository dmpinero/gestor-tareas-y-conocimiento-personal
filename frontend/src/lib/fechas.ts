/**
 * Utilidades para la fecha y hora de las tareas.
 *
 * La API trabaja con ISO 8601 sin zona horaria (`YYYY-MM-DDTHH:MM:SS`) y el
 * formulario y el listado con `dd/mm/aaaa hh:mm:ss`, siempre en hora local.
 */

/** Patrón nativo (`<input pattern>`) del formato `dd/mm/aaaa hh:mm:ss`. */
export const PATRON_FECHA_HORA = '\\d{2}/\\d{2}/\\d{4} \\d{2}:\\d{2}:\\d{2}'

const EXPRESION_ISO = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/
const EXPRESION_FECHA_HORA = /^(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2}):(\d{2})$/

function dosCifras(numero: number): string {
  return String(numero).padStart(2, '0')
}

/**
 * Formatea un `Date` (en hora local) o una cadena ISO sin zona horaria como
 * `dd/mm/aaaa hh:mm:ss`. La cadena ISO se lee tal cual, sin convertir de zona.
 * Una cadena que no sea ISO se devuelve sin cambios.
 */
export function formatearFechaHora(valor: Date | string): string {
  if (typeof valor === 'string') {
    const partes = EXPRESION_ISO.exec(valor)
    if (!partes) return valor
    const [, anio, mes, dia, hora, minuto, segundo] = partes
    return `${dia}/${mes}/${anio} ${hora}:${minuto}:${segundo}`
  }
  const fecha = `${dosCifras(valor.getDate())}/${dosCifras(valor.getMonth() + 1)}/${valor.getFullYear()}`
  const hora = `${dosCifras(valor.getHours())}:${dosCifras(valor.getMinutes())}:${dosCifras(valor.getSeconds())}`
  return `${fecha} ${hora}`
}

/**
 * Convierte `dd/mm/aaaa hh:mm:ss` a ISO sin zona horaria
 * (`YYYY-MM-DDTHH:MM:SS`). Devuelve `null` si el texto no tiene ese formato
 * o la fecha no existe (p. ej. `31/02/2026` o `25:00:00`).
 */
export function aFechaHoraIso(texto: string): string | null {
  const partes = EXPRESION_FECHA_HORA.exec(texto.trim())
  if (!partes) return null
  const [dia, mes, anio, hora, minuto, segundo] = partes.slice(1) as [
    string,
    string,
    string,
    string,
    string,
    string,
  ]
  const [d, m, a, h, min, s] = [dia, mes, anio, hora, minuto, segundo].map(Number) as [
    number,
    number,
    number,
    number,
    number,
    number,
  ]
  if (h > 23 || min > 59 || s > 59) return null
  // `Date` desborda los días imposibles al mes siguiente; si no coinciden los
  // componentes, la fecha no existe.
  const fecha = new Date(a, m - 1, d)
  if (fecha.getFullYear() !== a || fecha.getMonth() !== m - 1 || fecha.getDate() !== d) {
    return null
  }
  return `${anio}-${mes}-${dia}T${hora}:${minuto}:${segundo}`
}
