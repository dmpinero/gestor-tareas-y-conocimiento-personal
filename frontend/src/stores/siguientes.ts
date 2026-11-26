import { defineStore } from 'pinia'
import { ref } from 'vue'

import {
  anadirSiguiente,
  obtenerSiguientes,
  quitarSiguiente,
  reordenarSiguientes,
} from '@/api/siguientes'
import type { TareaSiguiente } from '@/api/tipos'
import { useTiendaFoco } from '@/stores/foco'
import { useTiendaTareas } from '@/stores/tareas'

// Cola de siguientes ("A continuación"): tareas elegidas para después del foco
// actual, en orden. Como las demás tiendas, las acciones devuelven `true` si la
// API respondió bien; si falla, guardan el mensaje en `error` y la cola se
// queda como estaba.
export const useTiendaSiguientes = defineStore('siguientes', () => {
  const cola = ref<TareaSiguiente[]>([])
  const error = ref<string | null>(null)

  async function ejecutar(accion: () => Promise<void>): Promise<boolean> {
    error.value = null
    try {
      await accion()
      return true
    } catch (motivo) {
      error.value = (motivo as Error).message
      return false
    }
  }

  function cargar(): Promise<boolean> {
    return ejecutar(async () => {
      cola.value = await obtenerSiguientes()
    })
  }

  function anadir(tareaId: number): Promise<boolean> {
    return ejecutar(async () => {
      cola.value = await anadirSiguiente(tareaId)
    })
  }

  function reordenar(ids: number[]): Promise<boolean> {
    return ejecutar(async () => {
      cola.value = await reordenarSiguientes(ids)
    })
  }

  // Intercambia la tarea con su vecina (`desplazamiento` -1 sube, +1 baja). En
  // un extremo, o si no está en la cola, no pide nada.
  function mover(tareaId: number, desplazamiento: -1 | 1): Promise<boolean> {
    const ids = cola.value.map((entrada) => entrada.tarea_id)
    const indice = ids.indexOf(tareaId)
    const destino = indice + desplazamiento
    if (indice === -1 || destino < 0 || destino >= ids.length) return Promise.resolve(true)
    ;[ids[indice], ids[destino]] = [ids[destino]!, ids[indice]!]
    return reordenar(ids)
  }

  function subir(tareaId: number): Promise<boolean> {
    return mover(tareaId, -1)
  }

  function bajar(tareaId: number): Promise<boolean> {
    return mover(tareaId, 1)
  }

  function quitar(tareaId: number): Promise<boolean> {
    return ejecutar(async () => {
      cola.value = await quitarSiguiente(tareaId)
    })
  }

  function estaEnCola(tareaId: number): boolean {
    return cola.value.some((entrada) => entrada.tarea_id === tareaId)
  }

  /** Fija el foco en la primera de la cola (el servidor la saca de ella) y
   * recarga la cola. Con la cola vacía no hace nada y devuelve `false`. */
  async function pasarALaSiguiente(): Promise<boolean> {
    const primera = cola.value[0]
    if (!primera) return false
    const tiendaFoco = useTiendaFoco()
    if (!(await tiendaFoco.fijar(primera.tarea_id))) {
      error.value = tiendaFoco.error
      return false
    }
    return cargar()
  }

  // El servidor la saca de la cola al borrarla; esta lo refleja sin volver a
  // pedirla.
  function olvidarTarea(tareaId: number): void {
    cola.value = cola.value.filter((entrada) => entrada.tarea_id !== tareaId)
  }

  // Reflejan sin repetir código en cada componente lo que el servidor ya hace
  // con la cola: poner en foco una tarea (o una subtarea suya) o borrarla la
  // saca, y la cola no muestra las completadas (reabrirla la devuelve a su
  // sitio, por eso se recarga).
  useTiendaFoco().$onAction(({ name, args, after }) => {
    if (name !== 'fijar') return
    after((bien) => {
      if (bien) olvidarTarea(args[0] as number)
    })
  })
  const tiendaTareas = useTiendaTareas()
  tiendaTareas.$onAction(({ name, args, after }) => {
    const tareaId = args[0] as number
    if (name === 'eliminarTarea') {
      after((bien) => {
        if (bien) olvidarTarea(tareaId)
      })
    } else if (name === 'alternarCompletada') {
      after(() => {
        const tarea = tiendaTareas.tareas.find((t) => t.id === tareaId)
        if (!tarea || tiendaTareas.error) return
        if (tarea.completada) olvidarTarea(tareaId)
        else void cargar()
      })
    }
  })

  return {
    cola,
    error,
    cargar,
    anadir,
    reordenar,
    subir,
    bajar,
    quitar,
    estaEnCola,
    pasarALaSiguiente,
    olvidarTarea,
  }
})
