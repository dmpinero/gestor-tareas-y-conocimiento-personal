import { defineStore } from 'pinia'
import { ref } from 'vue'

import { clienteApi } from '@/api/cliente'
import type {
  DatosEdicionSubtarea,
  DatosSubtarea,
  DatosTarea,
  ElementoCatalogo,
  Tarea,
} from '@/api/tipos'

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

  function reemplazarTarea(tarea: Tarea): void {
    const indice = tareas.value.findIndex((t) => t.id === tarea.id)
    if (indice !== -1) tareas.value[indice] = tarea
  }

  // Borra la tarea (con sus subtareas y comentarios). Como las acciones de
  // subtareas, si la API falla guarda el mensaje en `error`, la lista se queda
  // como estaba y devuelve `false`.
  async function eliminarTarea(id: number): Promise<boolean> {
    error.value = null
    try {
      await clienteApi.eliminar<void>(`/tareas/${id}`)
    } catch (motivo) {
      error.value = (motivo as Error).message
      return false
    }
    tareas.value = tareas.value.filter((tarea) => tarea.id !== id)
    return true
  }

  // Los comentarios de una subtarea se cargan y guardan en su propio
  // componente; este ajusta el número que muestra la lista de subtareas sin
  // volver a pedir la tarea.
  function fijarComentariosSubtarea(idTarea: number, idSubtarea: number, total: number): void {
    const subtarea = tareas.value
      .find((t) => t.id === idTarea)
      ?.subtareas.find((s) => s.id === idSubtarea)
    if (subtarea) subtarea.comentarios = total
  }

  // Las acciones de subtareas se lanzan desde el detalle de la tarea. Como
  // `alternarCompletada`, si la API falla guardan el mensaje en `error` y la
  // tarea se queda como estaba; devuelven `true` si la operación se hizo, para
  // que el formulario sepa si limpiarse.
  async function crearSubtarea(idTarea: number, datos: DatosSubtarea): Promise<boolean> {
    error.value = null
    try {
      reemplazarTarea(await clienteApi.crear<Tarea>(`/tareas/${idTarea}/subtareas`, datos))
    } catch (motivo) {
      error.value = (motivo as Error).message
      return false
    }
    // La persona asignada puede ser nueva en el catálogo.
    await cargarCatalogos()
    return true
  }

  async function editarSubtarea(
    idTarea: number,
    idSubtarea: number,
    datos: DatosEdicionSubtarea,
  ): Promise<boolean> {
    error.value = null
    try {
      reemplazarTarea(
        await clienteApi.actualizar<Tarea>(`/tareas/${idTarea}/subtareas/${idSubtarea}`, datos),
      )
    } catch (motivo) {
      error.value = (motivo as Error).message
      return false
    }
    // Como al crearla, la persona asignada puede ser nueva en el catálogo.
    await cargarCatalogos()
    return true
  }

  async function alternarSubtarea(idTarea: number, idSubtarea: number): Promise<boolean> {
    const subtarea = tareas.value
      .find((t) => t.id === idTarea)
      ?.subtareas.find((s) => s.id === idSubtarea)
    if (!subtarea) return false
    error.value = null
    try {
      reemplazarTarea(
        await clienteApi.parchear<Tarea>(`/tareas/${idTarea}/subtareas/${idSubtarea}/resuelta`, {
          resuelta: !subtarea.resuelta,
        }),
      )
      return true
    } catch (motivo) {
      error.value = (motivo as Error).message
      return false
    }
  }

  async function eliminarSubtarea(idTarea: number, idSubtarea: number): Promise<boolean> {
    error.value = null
    try {
      reemplazarTarea(
        await clienteApi.eliminar<Tarea>(`/tareas/${idTarea}/subtareas/${idSubtarea}`),
      )
      return true
    } catch (motivo) {
      error.value = (motivo as Error).message
      return false
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
    eliminarTarea,
    fijarComentariosSubtarea,
    crearSubtarea,
    editarSubtarea,
    alternarSubtarea,
    eliminarSubtarea,
  }
})
