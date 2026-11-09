import { defineStore } from 'pinia'
import { ref } from 'vue'

import { clienteApi } from '@/api/cliente'
import type { DatosTarea, Tarea } from '@/api/tipos'

export const useTiendaTareas = defineStore('tareas', () => {
  const tareas = ref<Tarea[]>([])
  const cargando = ref(false)
  const error = ref<string | null>(null)

  async function cargar(): Promise<void> {
    cargando.value = true
    error.value = null
    try {
      tareas.value = await clienteApi.obtener<Tarea[]>('/tareas')
    } catch (motivo) {
      error.value = (motivo as Error).message
    } finally {
      cargando.value = false
    }
  }

  async function crear(datos: DatosTarea): Promise<void> {
    const tarea = await clienteApi.crear<Tarea>('/tareas', datos)
    tareas.value.push(tarea)
  }

  async function actualizar(id: number, datos: DatosTarea): Promise<void> {
    const tarea = await clienteApi.actualizar<Tarea>(`/tareas/${id}`, datos)
    const indice = tareas.value.findIndex((t) => t.id === id)
    if (indice !== -1) tareas.value[indice] = tarea
  }

  return { tareas, cargando, error, cargar, crear, actualizar }
})
