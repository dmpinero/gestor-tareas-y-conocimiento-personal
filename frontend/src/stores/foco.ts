import { defineStore } from 'pinia'
import { ref } from 'vue'

import { fijarFoco, obtenerFoco, quitarFoco } from '@/api/foco'
import type { Foco } from '@/api/tipos'

// Tarea o subtarea en la que se está trabajando ahora. Solo hay una: fijar
// otra la sustituye. Como las demás tiendas, las acciones devuelven `true` si
// la API respondió bien; si falla, guardan el mensaje en `error` y el foco se
// queda como estaba.
export const useTiendaFoco = defineStore('foco', () => {
  const foco = ref<Foco | null>(null)
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
      foco.value = await obtenerFoco()
    })
  }

  function fijar(tareaId: number, subtareaId: number | null = null): Promise<boolean> {
    return ejecutar(async () => {
      foco.value = await fijarFoco({ tarea_id: tareaId, subtarea_id: subtareaId })
    })
  }

  function quitar(): Promise<boolean> {
    return ejecutar(async () => {
      await quitarFoco()
      foco.value = null
    })
  }

  // El servidor quita el foco al borrar su tarea o subtarea; estas lo reflejan
  // sin volver a pedirlo.
  function olvidarTarea(tareaId: number): void {
    if (foco.value?.tarea_id === tareaId) foco.value = null
  }

  function olvidarSubtarea(subtareaId: number): void {
    if (foco.value?.subtarea_id === subtareaId) foco.value = null
  }

  /** `true` solo si el foco es la tarea entera, no una de sus subtareas. */
  function esTareaEnFoco(tareaId: number): boolean {
    return foco.value?.tarea_id === tareaId && foco.value.subtarea_id === null
  }

  function esSubtareaEnFoco(subtareaId: number): boolean {
    return foco.value !== null && foco.value.subtarea_id === subtareaId
  }

  /** `true` si el foco es la tarea o una de sus subtareas. */
  function tareaContieneFoco(tareaId: number): boolean {
    return foco.value?.tarea_id === tareaId
  }

  return {
    foco,
    error,
    cargar,
    fijar,
    quitar,
    olvidarTarea,
    olvidarSubtarea,
    esTareaEnFoco,
    esSubtareaEnFoco,
    tareaContieneFoco,
  }
})
