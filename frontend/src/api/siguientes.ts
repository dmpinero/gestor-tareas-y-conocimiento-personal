import { clienteApi } from '@/api/cliente'
import type { TareaSiguiente } from '@/api/tipos'

const RUTA = '/siguientes'

/** Cola de siguientes en orden, sin las tareas completadas. */
export function obtenerSiguientes(): Promise<TareaSiguiente[]> {
  return clienteApi.obtener<TareaSiguiente[]>(RUTA)
}

/** Añade la tarea al final de la cola (si ya estaba, no cambia nada). */
export function anadirSiguiente(tareaId: number): Promise<TareaSiguiente[]> {
  return clienteApi.crear<TareaSiguiente[]>(RUTA, { tarea_id: tareaId })
}

/** Reordena la cola visible: `ids` debe tener exactamente sus tareas. */
export function reordenarSiguientes(ids: number[]): Promise<TareaSiguiente[]> {
  return clienteApi.actualizar<TareaSiguiente[]>(RUTA, { ids })
}

/** Saca la tarea de la cola (si no estaba, no cambia nada). */
export function quitarSiguiente(tareaId: number): Promise<TareaSiguiente[]> {
  return clienteApi.eliminar<TareaSiguiente[]>(`${RUTA}/${tareaId}`)
}
