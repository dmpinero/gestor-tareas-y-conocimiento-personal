import { defineStore } from 'pinia'
import { ref } from 'vue'

import { clienteApi } from '@/api/cliente'
import type { DatosTarea, ElementoCatalogo, Tarea } from '@/api/tipos'

export const useTiendaTareas = defineStore('tareas', () => {
  const tareas = ref<Tarea[]>([])
  const cargando = ref(false)
  const error = ref<string | null>(null)
  // Nombres de los catálogos compartidos, para sugerirlos en el formulario.
  const etiquetas = ref<string[]>([])
  const personas = ref<string[]>([])

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

  // Los catálogos solo alimentan sugerencias: si fallan se conservan los que
  // ya hubiera, sin bloquear el listado ni el guardado de la tarea.
  async function cargarCatalogos(): Promise<void> {
    try {
      const [listaEtiquetas, listaPersonas] = await Promise.all([
        clienteApi.obtener<ElementoCatalogo[]>('/etiquetas'),
        clienteApi.obtener<ElementoCatalogo[]>('/personas'),
      ])
      etiquetas.value = listaEtiquetas.map((elemento) => elemento.nombre)
      personas.value = listaPersonas.map((elemento) => elemento.nombre)
    } catch {
      // Sin sugerencias nuevas; el formulario sigue permitiendo escribirlas.
    }
  }

  async function crear(datos: DatosTarea): Promise<void> {
    const tarea = await clienteApi.crear<Tarea>('/tareas', datos)
    tareas.value.push(tarea)
    // Guardar puede haber dado de alta etiquetas o personas nuevas.
    await cargarCatalogos()
  }

  async function actualizar(id: number, datos: DatosTarea): Promise<void> {
    const tarea = await clienteApi.actualizar<Tarea>(`/tareas/${id}`, datos)
    const indice = tareas.value.findIndex((t) => t.id === id)
    if (indice !== -1) tareas.value[indice] = tarea
    await cargarCatalogos()
  }

  // Cambia la tarea entre pendiente y completada. Se invoca desde un botón de
  // la tabla, sin formulario donde mostrar el fallo: si la API falla se guarda
  // el mensaje en `error` y la lista se queda como estaba.
  async function alternarCompletada(id: number): Promise<void> {
    const actual = tareas.value.find((t) => t.id === id)
    if (!actual) return
    error.value = null
    try {
      const tarea = await clienteApi.parchear<Tarea>(`/tareas/${id}/completada`, {
        completada: !actual.completada,
      })
      const indice = tareas.value.findIndex((t) => t.id === id)
      if (indice !== -1) tareas.value[indice] = tarea
    } catch (motivo) {
      error.value = (motivo as Error).message
    }
  }

  // Cambia un paso del workflow de una oportunidad entre hecho y pendiente.
  // Como `alternarCompletada`: si la API falla se guarda el mensaje en `error`
  // y la tarea se queda como estaba.
  async function alternarPasoTarea(idTarea: number, idPaso: number): Promise<void> {
    const paso = tareas.value
      .find((t) => t.id === idTarea)
      ?.pasos_oportunidad.find((p) => p.id === idPaso)
    if (!paso) return
    error.value = null
    try {
      const tarea = await clienteApi.parchear<Tarea>(`/tareas/${idTarea}/pasos/${idPaso}`, {
        hecho: !paso.hecho,
      })
      const indice = tareas.value.findIndex((t) => t.id === idTarea)
      if (indice !== -1) tareas.value[indice] = tarea
    } catch (motivo) {
      error.value = (motivo as Error).message
    }
  }

  return {
    tareas,
    cargando,
    error,
    etiquetas,
    personas,
    cargar,
    cargarCatalogos,
    crear,
    actualizar,
    alternarCompletada,
    alternarPasoTarea,
  }
})
