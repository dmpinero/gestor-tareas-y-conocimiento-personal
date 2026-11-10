import { defineStore } from 'pinia'
import { ref } from 'vue'

import { clienteApi } from '@/api/cliente'
import type { PasoWorkflow } from '@/api/tipos'

const RUTA = '/workflow-oportunidades/pasos'

// Pasos del workflow estándar de las oportunidades. Las acciones que cambian
// datos devuelven `true` si la API respondió bien; si falla, guardan el
// mensaje en `error` y dejan la lista como estaba.
export const useTiendaWorkflowOportunidades = defineStore('workflowOportunidades', () => {
  const pasos = ref<PasoWorkflow[]>([])
  const cargando = ref(false)
  const error = ref<string | null>(null)

  function ordenarPorNumero(lista: PasoWorkflow[]): PasoWorkflow[] {
    return [...lista].sort((a, b) => a.numero - b.numero)
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
      pasos.value = ordenarPorNumero(await clienteApi.obtener<PasoWorkflow[]>(RUTA))
    })
    cargando.value = false
  }

  function crear(nombre: string): Promise<boolean> {
    return ejecutar(async () => {
      const paso = await clienteApi.crear<PasoWorkflow>(RUTA, { nombre })
      pasos.value = ordenarPorNumero([...pasos.value, paso])
    })
  }

  function renombrar(id: number, nombre: string): Promise<boolean> {
    return ejecutar(async () => {
      const paso = await clienteApi.actualizar<PasoWorkflow>(`${RUTA}/${id}`, { nombre })
      pasos.value = pasos.value.map((actual) => (actual.id === id ? paso : actual))
    })
  }

  // El borrado renumera los pasos siguientes en el servidor; se recarga la
  // lista para mostrar los números que este ha asignado.
  function eliminar(id: number): Promise<boolean> {
    return ejecutar(async () => {
      await clienteApi.eliminar<void>(`${RUTA}/${id}`)
      pasos.value = ordenarPorNumero(await clienteApi.obtener<PasoWorkflow[]>(RUTA))
    })
  }

  function reordenar(ids: number[]): Promise<boolean> {
    return ejecutar(async () => {
      pasos.value = ordenarPorNumero(
        await clienteApi.actualizar<PasoWorkflow[]>(`${RUTA}/orden`, { ids }),
      )
    })
  }

  return { pasos, cargando, error, cargar, crear, renombrar, eliminar, reordenar }
})
