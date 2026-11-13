import { defineStore } from 'pinia'
import { ref } from 'vue'

import { clienteApi } from '@/api/cliente'
import type { Workflow } from '@/api/tipos'

const RUTA = '/workflows'

// Workflows de Ajustes, que también usa el formulario de tareas. Las acciones
// que cambian datos devuelven `true` si la API respondió bien; si falla,
// guardan el mensaje en `error` y dejan la lista como estaba. Las acciones
// sobre pasos reemplazan el workflow con el que devuelve la API.
export const useTiendaWorkflows = defineStore('workflows', () => {
  const workflows = ref<Workflow[]>([])
  const cargando = ref(false)
  const error = ref<string | null>(null)

  function conPasosOrdenados(workflow: Workflow): Workflow {
    return { ...workflow, pasos: [...workflow.pasos].sort((a, b) => a.numero - b.numero) }
  }

  function reemplazar(workflow: Workflow): void {
    const ordenado = conPasosOrdenados(workflow)
    workflows.value = workflows.value.map((actual) =>
      actual.id === workflow.id ? ordenado : actual,
    )
  }

  async function obtenerTodos(): Promise<Workflow[]> {
    return (await clienteApi.obtener<Workflow[]>(RUTA)).map(conPasosOrdenados)
  }

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

  async function cargar(): Promise<void> {
    cargando.value = true
    await ejecutar(async () => {
      workflows.value = await obtenerTodos()
    })
    cargando.value = false
  }

  function crear(nombre: string): Promise<boolean> {
    return ejecutar(async () => {
      const workflow = await clienteApi.crear<Workflow>(RUTA, { nombre })
      workflows.value = [...workflows.value, conPasosOrdenados(workflow)]
    })
  }

  function renombrar(id: number, nombre: string): Promise<boolean> {
    return ejecutar(async () => {
      reemplazar(await clienteApi.actualizar<Workflow>(`${RUTA}/${id}`, { nombre }))
    })
  }

  // Las tareas del workflow quedan sin workflow en el servidor y conservan sus
  // subtareas.
  function eliminar(id: number): Promise<boolean> {
    return ejecutar(async () => {
      await clienteApi.eliminar<void>(`${RUTA}/${id}`)
      workflows.value = workflows.value.filter((workflow) => workflow.id !== id)
    })
  }

  function anadirPaso(idWorkflow: number, nombre: string): Promise<boolean> {
    return ejecutar(async () => {
      reemplazar(await clienteApi.crear<Workflow>(`${RUTA}/${idWorkflow}/pasos`, { nombre }))
    })
  }

  function renombrarPaso(idWorkflow: number, idPaso: number, nombre: string): Promise<boolean> {
    return ejecutar(async () => {
      reemplazar(
        await clienteApi.actualizar<Workflow>(`${RUTA}/${idWorkflow}/pasos/${idPaso}`, { nombre }),
      )
    })
  }

  // El borrado renumera los pasos siguientes en el servidor. Si la respuesta
  // no trae el workflow (204), se recarga la lista para mostrar los números
  // que este ha asignado.
  function eliminarPaso(idWorkflow: number, idPaso: number): Promise<boolean> {
    return ejecutar(async () => {
      const workflow = await clienteApi.eliminar<Workflow | undefined>(
        `${RUTA}/${idWorkflow}/pasos/${idPaso}`,
      )
      if (workflow) reemplazar(workflow)
      else workflows.value = await obtenerTodos()
    })
  }

  function reordenarPasos(idWorkflow: number, ids: number[]): Promise<boolean> {
    return ejecutar(async () => {
      reemplazar(await clienteApi.actualizar<Workflow>(`${RUTA}/${idWorkflow}/orden`, { ids }))
    })
  }

  return {
    workflows,
    cargando,
    error,
    cargar,
    crear,
    renombrar,
    eliminar,
    anadirPaso,
    renombrarPaso,
    eliminarPaso,
    reordenarPasos,
  }
})
