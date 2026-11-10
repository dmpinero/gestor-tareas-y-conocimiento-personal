import { dosCifras, isoAFechaLocal } from '@/lib/fechas'

/** Texto de la cuenta atrás hasta el vencimiento y si la tarea ya venció. */
export interface CuentaAtras {
  texto: string
  vencida: boolean
}

const SEGUNDOS_POR_MINUTO = 60
const SEGUNDOS_POR_HORA = 60 * SEGUNDOS_POR_MINUTO
const SEGUNDOS_POR_DIA = 24 * SEGUNDOS_POR_HORA

/**
 * Calcula cuánto falta para `vencimientoIso` (ISO sin zona horaria, en hora
 * local) desde `ahora`, o cuánto hace que venció.
 *
 * - Antes del vencimiento: `Vence en [d d ]hh h mm min ss s`.
 * - Desde el instante exacto del vencimiento: `Vencida hace [d d ]hh h mm min`,
 *   sin segundos y con los minutos truncados.
 *
 * Los días solo aparecen si hay al menos uno y no se rellenan con ceros.
 */
export function calcularCuentaAtras(vencimientoIso: string, ahora: Date): CuentaAtras {
  const vencimiento = isoAFechaLocal(vencimientoIso)
  if (vencimiento === null) return { texto: vencimientoIso, vencida: false }

  // Se trabaja en segundos completos: las milésimas de `ahora` no cuentan
  // como un segundo más pendiente.
  const restantes = Math.floor((vencimiento.getTime() - ahora.getTime()) / 1000)
  const vencida = restantes <= 0
  const total = Math.abs(restantes)

  const dias = Math.floor(total / SEGUNDOS_POR_DIA)
  const horas = Math.floor((total % SEGUNDOS_POR_DIA) / SEGUNDOS_POR_HORA)
  const minutos = Math.floor((total % SEGUNDOS_POR_HORA) / SEGUNDOS_POR_MINUTO)
  const segundos = total % SEGUNDOS_POR_MINUTO

  const prefijoDias = dias >= 1 ? `${dias} d ` : ''
  const horasYMinutos = `${dosCifras(horas)} h ${dosCifras(minutos)} min`
  if (vencida) return { texto: `Vencida hace ${prefijoDias}${horasYMinutos}`, vencida }
  return { texto: `Vence en ${prefijoDias}${horasYMinutos} ${dosCifras(segundos)} s`, vencida }
}
