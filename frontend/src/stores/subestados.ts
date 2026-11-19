import { defineStore } from 'pinia'
import { ref } from 'vue'

import { clienteApi } from '@/api/cliente'
import type { ElementoCatalogo } from '@/api/tipos'

const RUTA = '/subestados'

function porNombre(a: ElementoCatalogo, b: ElementoCatalogo): number {
  return a.nombre.localeCompare(b.nombre, 'es', { sensitivity: 'base' })
}

// Catálogo de subestados de Ajustes (como el de etiquetas, pero se gestiona
// aquí). Las acciones que cambian datos devuelven `true` si la API respondió
// bien; si falla, guardan el mensaje en `error` y dejan la lista como estaba.
export const useTiendaSubestados = defineStore('subestados', () => {
  const subestados = ref<ElementoCatalogo[]>([])
  const cargando = ref(false)
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

  async function cargar(): Promise<void> {
    cargando.value = true
    await ejecutar(async () => {
      subestados.value = await clienteApi.obtener<ElementoCatalogo[]>(RUTA)
    })
    cargando.value = false
  }

  function crear(nombre: string): Promise<boolean> {
    return ejecutar(async () => {
      const subestado = await clienteApi.crear<ElementoCatalogo>(RUTA, { nombre })
      subestados.value = [...subestados.value, subestado].sort(porNombre)
    })
  }

  function renombrar(id: number, nombre: string): Promise<boolean> {
    return ejecutar(async () => {
      const subestado = await clienteApi.actualizar<ElementoCatalogo>(`${RUTA}/${id}`, { nombre })
      subestados.value = subestados.value
        .map((actual) => (actual.id === id ? subestado : actual))
        .sort(porNombre)
    })
  }

  // Las tareas con este subestado quedan sin subestado en el servidor.
  function eliminar(id: number): Promise<boolean> {
    return ejecutar(async () => {
      await clienteApi.eliminar<void>(`${RUTA}/${id}`)
      subestados.value = subestados.value.filter((subestado) => subestado.id !== id)
    })
  }

  return { subestados, cargando, error, cargar, crear, renombrar, eliminar }
})
