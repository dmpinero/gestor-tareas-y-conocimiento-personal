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

const RUTA_SUGERENCIAS = '/sugerencias'

/** Sugerencias elegidas por el usuario, en orden, sin las tareas completadas. */
export function obtenerSugerenciasElegidas(): Promise<TareaSiguiente[]> {
  return clienteApi.obtener<TareaSiguiente[]>(RUTA_SUGERENCIAS)
}

/** Añade la tarea al final de las sugerencias elegidas; si estaba en la cola
 * de siguientes, el servidor la saca de ella. */
export function anadirSugerenciaElegida(tareaId: number): Promise<TareaSiguiente[]> {
  return clienteApi.crear<TareaSiguiente[]>(RUTA_SUGERENCIAS, { tarea_id: tareaId })
}

/** Saca la tarea de las sugerencias elegidas (si no estaba, no cambia nada). */
export function quitarSugerenciaElegida(tareaId: number): Promise<TareaSiguiente[]> {
  return clienteApi.eliminar<TareaSiguiente[]>(`${RUTA_SUGERENCIAS}/${tareaId}`)
}
