import type { EntradaHistorialFoco, Foco } from '@/api/tipos'

const MS_POR_MINUTO = 60_000

/**
 * Tiempo que se lleva trabajando desde `desde` (ISO 8601; sin zona se lee en
 * hora local) hasta `ahora`: `< 1 min`, `N min`, `N h M min`, o `N h` si los
 * minutos son 0.
 */
export function formatearTiempoFoco(desde: string, ahora: Date): string {
  return formatearDuracionFoco(ahora.getTime() - new Date(desde).getTime())
}

/** Una duración en milisegundos con los mismos tramos que `formatearTiempoFoco`. */
export function formatearDuracionFoco(ms: number): string {
  const minutos = Math.floor(ms / MS_POR_MINUTO)
  if (!(minutos >= 1)) return '< 1 min'
  if (minutos < 60) return `${minutos} min`
  const horas = Math.floor(minutos / 60)
  const resto = minutos % 60
  return resto === 0 ? `${horas} h` : `${horas} h ${resto} min`
}

/** Nombre del elemento en foco: la tarea, o `Tarea › Subtarea`. */
export function textoFoco(foco: Foco): string {
  return foco.subtarea_id === null || foco.subtarea_nombre === null
    ? foco.tarea_nombre
    : `${foco.tarea_nombre} › ${foco.subtarea_nombre}`
}

/** Nombre de una entrada del historial: la tarea, o `Tarea › Subtarea` (también
 * si la subtarea se borró, con su último nombre). */
export function textoEntradaHistorial(
  entrada: Pick<EntradaHistorialFoco, 'tarea_nombre' | 'subtarea_nombre'>,
): string {
  return entrada.subtarea_nombre === null
    ? entrada.tarea_nombre
    : `${entrada.tarea_nombre} › ${entrada.subtarea_nombre}`
}

// --- Días locales (`YYYY-MM-DD`) del historial -----------------------------------

const dosCifras = (n: number): string => String(n).padStart(2, '0')

/** El día local de `fecha` como `YYYY-MM-DD`. */
export function fechaLocal(fecha: Date): string {
  return `${fecha.getFullYear()}-${dosCifras(fecha.getMonth() + 1)}-${dosCifras(fecha.getDate())}`
}

/** Medianoche local del día `YYYY-MM-DD` (se supone válido). */
function medianocheLocal(dia: string): Date {
  const [anio = 0, mes = 1, diaMes = 1] = dia.split('-').map(Number)
  return new Date(anio, mes - 1, diaMes)
}

/** `dia` si es una fecha `YYYY-MM-DD` real; si no, `null`. */
export function normalizarFechaLocal(dia: unknown): string | null {
  if (typeof dia !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(dia)) return null
  return fechaLocal(medianocheLocal(dia)) === dia ? dia : null
}

/** El día `dias` días después (o antes, si es negativo) de `dia`. */
export function desplazarDia(dia: string, dias: number): string {
  const fecha = medianocheLocal(dia)
  fecha.setDate(fecha.getDate() + dias)
  return fechaLocal(fecha)
}

/** Del inicio del día local al del siguiente, como instantes ISO en UTC. */
export function limitesDiaLocal(dia: string): { desde: string; hasta: string } {
  return {
    desde: medianocheLocal(dia).toISOString(),
    hasta: medianocheLocal(desplazarDia(dia, 1)).toISOString(),
  }
}

/** Hora local `HH:MM` de un instante ISO. */
export function horaLocal(instante: string): string {
  const fecha = new Date(instante)
  return `${dosCifras(fecha.getHours())}:${dosCifras(fecha.getMinutes())}`
}
