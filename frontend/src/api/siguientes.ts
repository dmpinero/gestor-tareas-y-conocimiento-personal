import { clienteApi } from '@/api/cliente'
import type { ClaveEntradaSiguiente, TareaSiguiente } from '@/api/tipos'

const RUTA = '/siguientes'
const RUTA_SUGERENCIAS = '/sugerencias'

// Cuerpo de los `POST`: `subtarea_id` solo si la entrada es una subtarea.
function cuerpoEntrada(tareaId: number, subtareaId: number | null) {
  return subtareaId === null
    ? { tarea_id: tareaId }
    : { tarea_id: tareaId, subtarea_id: subtareaId }
}

// Ruta de los `DELETE`: sin `subtarea_id`, la entrada de la tarea entera.
function rutaEntrada(base: string, tareaId: number, subtareaId: number | null): string {
  return subtareaId === null ? `${base}/${tareaId}` : `${base}/${tareaId}?subtarea_id=${subtareaId}`
}

/** Cola de siguientes en orden, sin las tareas completadas ni las subtareas
 * resueltas. */
export function obtenerSiguientes(): Promise<TareaSiguiente[]> {
  return clienteApi.obtener<TareaSiguiente[]>(RUTA)
}

/** Añade la tarea (o su subtarea) al final de la cola (si ya estaba, no cambia
 * nada). */
export function anadirSiguiente(
  tareaId: number,
  subtareaId: number | null = null,
): Promise<TareaSiguiente[]> {
  return clienteApi.crear<TareaSiguiente[]>(RUTA, cuerpoEntrada(tareaId, subtareaId))
}

/** Reordena la cola visible: `entradas` debe tener exactamente sus entradas. */
export function reordenarSiguientes(entradas: ClaveEntradaSiguiente[]): Promise<TareaSiguiente[]> {
  return clienteApi.actualizar<TareaSiguiente[]>(RUTA, { entradas })
}

/** Saca la tarea (o su subtarea) de la cola (si no estaba, no cambia nada). */
export function quitarSiguiente(
  tareaId: number,
  subtareaId: number | null = null,
): Promise<TareaSiguiente[]> {
  return clienteApi.eliminar<TareaSiguiente[]>(rutaEntrada(RUTA, tareaId, subtareaId))
}

/** Sugerencias elegidas por el usuario, en orden, sin las tareas completadas ni
 * las subtareas resueltas. */
export function obtenerSugerenciasElegidas(): Promise<TareaSiguiente[]> {
  return clienteApi.obtener<TareaSiguiente[]>(RUTA_SUGERENCIAS)
}

/** Añade la tarea (o su subtarea) al final de las sugerencias elegidas; si
 * estaba en la cola de siguientes, el servidor la saca de ella. */
export function anadirSugerenciaElegida(
  tareaId: number,
  subtareaId: number | null = null,
): Promise<TareaSiguiente[]> {
  return clienteApi.crear<TareaSiguiente[]>(RUTA_SUGERENCIAS, cuerpoEntrada(tareaId, subtareaId))
}

/** Saca la tarea (o su subtarea) de las sugerencias elegidas (si no estaba, no
 * cambia nada). */
export function quitarSugerenciaElegida(
  tareaId: number,
  subtareaId: number | null = null,
): Promise<TareaSiguiente[]> {
  return clienteApi.eliminar<TareaSiguiente[]>(rutaEntrada(RUTA_SUGERENCIAS, tareaId, subtareaId))
}
