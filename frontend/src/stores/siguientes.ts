import { defineStore } from 'pinia'
import { ref } from 'vue'

import {
  anadirSiguiente,
  anadirSugerenciaElegida,
  obtenerSiguientes,
  obtenerSugerenciasElegidas,
  quitarSiguiente,
  quitarSugerenciaElegida,
  reordenarSiguientes,
} from '@/api/siguientes'
import type { ClaveEntradaSiguiente, TareaSiguiente } from '@/api/tipos'
import { useTiendaFoco } from '@/stores/foco'
import { useTiendaTareas } from '@/stores/tareas'

// Cola de siguientes ("A continuación"): tareas o subtareas elegidas para
// después del foco actual, en orden. Cada entrada se identifica por
// (`tarea_id`, `subtarea_id`); las acciones reciben el id de la tarea y, para
// una subtarea, el suyo (sin él, la tarea entera). Como las demás tiendas, las acciones devuelven `true` si la
// API respondió bien; si falla, guardan el mensaje en `error` y la cola se
// queda como estaba.
//
// También guarda las sugerencias elegidas por el usuario (`elegidas`), que van
// antes que las automáticas. Una entrada está como mucho en una de las dos
// listas: el servidor la mueve al añadirla a la otra y la tienda lo refleja
// quitándola localmente de la lista que no devolvió.
export const useTiendaSiguientes = defineStore('siguientes', () => {
  const cola = ref<TareaSiguiente[]>([])
  const elegidas = ref<TareaSiguiente[]>([])
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

  // Una entrada es una tarea entera (`subtarea_id` `null`) o una subtarea suya.
  function clave(tareaId: number, subtareaId: number | null): ClaveEntradaSiguiente {
    return { tarea_id: tareaId, subtarea_id: subtareaId }
  }

  function esEntrada(entrada: ClaveEntradaSiguiente, buscada: ClaveEntradaSiguiente): boolean {
    return entrada.tarea_id === buscada.tarea_id && entrada.subtarea_id === buscada.subtarea_id
  }

  function sinEntrada(lista: TareaSiguiente[], buscada: ClaveEntradaSiguiente): TareaSiguiente[] {
    return lista.filter((entrada) => !esEntrada(entrada, buscada))
  }

  function anadir(tareaId: number, subtareaId: number | null = null): Promise<boolean> {
    return ejecutar(async () => {
      cola.value = await anadirSiguiente(tareaId, subtareaId)
      elegidas.value = sinEntrada(elegidas.value, clave(tareaId, subtareaId))
    })
  }

  // Un id suelto es la tarea entera.
  function aClave(entrada: number | ClaveEntradaSiguiente): ClaveEntradaSiguiente {
    return typeof entrada === 'number' ? clave(entrada, null) : entrada
  }

  // Añade varias, una tras otra y en el orden dado (cada una al final). Se
  // detiene en el primer fallo, con las anteriores ya añadidas.
  async function anadirVarias(entradas: (number | ClaveEntradaSiguiente)[]): Promise<boolean> {
    for (const entrada of entradas.map(aClave)) {
      if (!(await anadir(entrada.tarea_id, entrada.subtarea_id))) return false
    }
    return true
  }

  function cargarElegidas(): Promise<boolean> {
    return ejecutar(async () => {
      elegidas.value = await obtenerSugerenciasElegidas()
    })
  }

  /** La añade al final de las sugerencias elegidas (si estaba en la cola, sale
   * de ella). La ✕ de una fila de la cola en Inicio usa esta acción. */
  function anadirElegida(tareaId: number, subtareaId: number | null = null): Promise<boolean> {
    return ejecutar(async () => {
      elegidas.value = await anadirSugerenciaElegida(tareaId, subtareaId)
      cola.value = sinEntrada(cola.value, clave(tareaId, subtareaId))
    })
  }

  // Como `anadirVarias`, para las sugerencias elegidas.
  async function anadirElegidas(entradas: (number | ClaveEntradaSiguiente)[]): Promise<boolean> {
    for (const entrada of entradas.map(aClave)) {
      if (!(await anadirElegida(entrada.tarea_id, entrada.subtarea_id))) return false
    }
    return true
  }

  function quitarElegida(tareaId: number, subtareaId: number | null = null): Promise<boolean> {
    return ejecutar(async () => {
      elegidas.value = await quitarSugerenciaElegida(tareaId, subtareaId)
    })
  }

  function estaElegida(tareaId: number, subtareaId: number | null = null): boolean {
    return elegidas.value.some((entrada) => esEntrada(entrada, clave(tareaId, subtareaId)))
  }

  function reordenar(entradas: ClaveEntradaSiguiente[]): Promise<boolean> {
    return ejecutar(async () => {
      cola.value = await reordenarSiguientes(entradas)
    })
  }

  function clavesCola(): ClaveEntradaSiguiente[] {
    return cola.value.map((entrada) => clave(entrada.tarea_id, entrada.subtarea_id))
  }

  // Intercambia la entrada con su vecina (`desplazamiento` -1 sube, +1 baja). En
  // un extremo, o si no está en la cola, no pide nada.
  function mover(buscada: ClaveEntradaSiguiente, desplazamiento: -1 | 1): Promise<boolean> {
    const claves = clavesCola()
    const indice = claves.findIndex((entrada) => esEntrada(entrada, buscada))
    const destino = indice + desplazamiento
    if (indice === -1 || destino < 0 || destino >= claves.length) return Promise.resolve(true)
    ;[claves[indice], claves[destino]] = [claves[destino]!, claves[indice]!]
    return reordenar(claves)
  }

  // Lleva la entrada a la posición `destino` de la cola (al arrastrarla). A su
  // misma posición, o si no está en la cola, no pide nada.
  function moverA(
    tareaId: number,
    destino: number,
    subtareaId: number | null = null,
  ): Promise<boolean> {
    const claves = clavesCola()
    const indice = claves.findIndex((entrada) => esEntrada(entrada, clave(tareaId, subtareaId)))
    if (indice === -1 || indice === destino || destino < 0 || destino >= claves.length) {
      return Promise.resolve(true)
    }
    const [movida] = claves.splice(indice, 1)
    claves.splice(destino, 0, movida!)
    return reordenar(claves)
  }

  function subir(tareaId: number, subtareaId: number | null = null): Promise<boolean> {
    return mover(clave(tareaId, subtareaId), -1)
  }

  function bajar(tareaId: number, subtareaId: number | null = null): Promise<boolean> {
    return mover(clave(tareaId, subtareaId), 1)
  }

  function quitar(tareaId: number, subtareaId: number | null = null): Promise<boolean> {
    return ejecutar(async () => {
      cola.value = await quitarSiguiente(tareaId, subtareaId)
    })
  }

  function estaEnCola(tareaId: number, subtareaId: number | null = null): boolean {
    return cola.value.some((entrada) => esEntrada(entrada, clave(tareaId, subtareaId)))
  }

  /** Fija el foco en la primera de la cola, tarea o subtarea (el servidor la
   * saca de ella), y recarga la cola. Con la cola vacía no hace nada y devuelve
   * `false`. */
  async function pasarALaSiguiente(): Promise<boolean> {
    const primera = cola.value[0]
    if (!primera) return false
    const tiendaFoco = useTiendaFoco()
    if (!(await tiendaFoco.fijar(primera.tarea_id, primera.subtarea_id))) {
      error.value = tiendaFoco.error
      return false
    }
    return cargar()
  }

  function quitarLocalmente(quitarDe: (entrada: TareaSiguiente) => boolean): void {
    cola.value = cola.value.filter((entrada) => !quitarDe(entrada))
    elegidas.value = elegidas.value.filter((entrada) => !quitarDe(entrada))
  }

  // El servidor saca las entradas de la tarea (y de sus subtareas) al borrarla
  // y no muestra las de una tarea completada; esta lo refleja sin volver a
  // pedirlas.
  function olvidarTarea(tareaId: number): void {
    quitarLocalmente((entrada) => entrada.tarea_id === tareaId)
  }

  // Igual con una subtarea borrada o resuelta.
  function olvidarSubtarea(subtareaId: number): void {
    quitarLocalmente((entrada) => entrada.subtarea_id === subtareaId)
  }

  // Reflejan sin repetir código en cada componente lo que el servidor ya hace
  // con la cola y las elegidas: poner en foco una subtarea saca su entrada y la
  // de su tarea entera; una tarea entera, solo la suya. Borrar una tarea o una
  // subtarea saca sus entradas, y no se muestran las de tareas completadas ni
  // las subtareas resueltas (volver a dejarlas pendientes las devuelve a su
  // sitio, por eso se recarga).
  useTiendaFoco().$onAction(({ name, args, after }) => {
    if (name !== 'fijar') return
    const tareaId = args[0] as number
    const subtareaId = (args[1] as number | null | undefined) ?? null
    after((bien) => {
      if (!bien) return
      quitarLocalmente(
        (entrada) =>
          esEntrada(entrada, clave(tareaId, null)) ||
          (subtareaId !== null && esEntrada(entrada, clave(tareaId, subtareaId))),
      )
    })
  })
  function recargarListas(): void {
    void cargar()
    void cargarElegidas()
  }
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
        else recargarListas()
      })
    } else if (name === 'eliminarSubtarea') {
      const subtareaId = args[1] as number
      after((bien) => {
        if (bien) olvidarSubtarea(subtareaId)
      })
    } else if (name === 'alternarSubtarea') {
      const subtareaId = args[1] as number
      after((bien) => {
        if (!bien) return
        const subtarea = tiendaTareas.tareas
          .find((t) => t.id === tareaId)
          ?.subtareas.find((s) => s.id === subtareaId)
        if (!subtarea) return
        if (subtarea.resuelta) olvidarSubtarea(subtareaId)
        else recargarListas()
      })
    }
  })

  return {
    cola,
    elegidas,
    error,
    cargar,
    anadir,
    anadirVarias,
    cargarElegidas,
    anadirElegida,
    anadirElegidas,
    quitarElegida,
    estaElegida,
    reordenar,
    moverA,
    subir,
    bajar,
    quitar,
    estaEnCola,
    pasarALaSiguiente,
    olvidarTarea,
    olvidarSubtarea,
  }
})
