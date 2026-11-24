import { clienteApi } from '@/api/cliente'
import type { DatosFoco, EntradaHistorialFoco, Foco } from '@/api/tipos'

const RUTA = '/foco'

export async function obtenerFoco(): Promise<Foco | null> {
  return (await clienteApi.obtener<Foco | null>(RUTA)) ?? null
}

export function fijarFoco(datos: DatosFoco): Promise<Foco> {
  return clienteApi.actualizar<Foco>(RUTA, datos)
}

export function quitarFoco(): Promise<void> {
  return clienteApi.eliminar<void>(RUTA)
}

/** Historial de foco, el más reciente primero. Con `rango` (instantes ISO en
 * UTC) solo las entradas cuyo `desde` cae en `[desde, hasta)`. */
export function obtenerHistorialFoco(rango?: {
  desde: string
  hasta: string
}): Promise<EntradaHistorialFoco[]> {
  const consulta = rango ? `?${new URLSearchParams(rango)}` : ''
  return clienteApi.obtener<EntradaHistorialFoco[]>(`${RUTA}/historial${consulta}`)
}
