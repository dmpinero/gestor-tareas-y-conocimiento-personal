import { clienteApi } from '@/api/cliente'
import type { DatosFoco, Foco } from '@/api/tipos'

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
