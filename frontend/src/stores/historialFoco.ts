import { defineStore } from 'pinia'
import { ref } from 'vue'

import { obtenerHistorialFoco } from '@/api/foco'
import type { EntradaHistorialFoco } from '@/api/tipos'
import { limitesDiaLocal } from '@/lib/foco'

// Historial de foco que muestra la página `/foco/historial`: un día local o
// todo. Las acciones devuelven `true` si la API respondió bien; si falla, el
// mensaje queda en `error` y las entradas se vacían. Si se piden dos cargas
// seguidas (p. ej. al pasar días deprisa), solo cuenta la última.
export const useTiendaHistorialFoco = defineStore('historialFoco', () => {
  const entradas = ref<EntradaHistorialFoco[]>([])
  const cargando = ref(false)
  const error = ref<string | null>(null)
  let ultimaPeticion = 0

  async function cargar(rango?: { desde: string; hasta: string }): Promise<boolean> {
    const peticion = ++ultimaPeticion
    cargando.value = true
    error.value = null
    try {
      const recibidas = await obtenerHistorialFoco(rango)
      if (peticion === ultimaPeticion) entradas.value = recibidas
      return true
    } catch (motivo) {
      if (peticion === ultimaPeticion) {
        error.value = (motivo as Error).message
        entradas.value = []
      }
      return false
    } finally {
      if (peticion === ultimaPeticion) cargando.value = false
    }
  }

  /** Entradas que empezaron en el día local `dia` (`YYYY-MM-DD`). */
  function cargarDia(dia: string): Promise<boolean> {
    return cargar(limitesDiaLocal(dia))
  }

  function cargarTodo(): Promise<boolean> {
    return cargar()
  }

  return { entradas, cargando, error, cargarDia, cargarTodo }
})
