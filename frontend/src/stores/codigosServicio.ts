import { defineStore } from 'pinia'
import { ref } from 'vue'

import { clienteApi } from '@/api/cliente'
import type { CodigoServicio } from '@/api/tipos'

const RUTA = '/codigos-servicio'

function porNombre(a: CodigoServicio, b: CodigoServicio): number {
  return a.nombre.localeCompare(b.nombre, 'es', { sensitivity: 'base' })
}

// Catálogo de códigos de servicio del alta de oportunidades AXAS MS3 (como el de
// subestados). Si una acción falla, guarda el mensaje en `error` y deja la lista
// como estaba. `crear` devuelve el código creado (o `null`) para que quien lo da
// de alta pueda seleccionarlo; `renombrar` y `eliminar` devuelven si fue bien.
export const useTiendaCodigosServicio = defineStore('codigosServicio', () => {
  const codigos = ref<CodigoServicio[]>([])
  const cargando = ref(false)
  const error = ref<string | null>(null)

  async function ejecutar<T>(accion: () => Promise<T>): Promise<T | null> {
    error.value = null
    try {
      return await accion()
    } catch (motivo) {
      error.value = (motivo as Error).message
      return null
    }
  }

  async function cargar(): Promise<void> {
    cargando.value = true
    await ejecutar(async () => {
      codigos.value = await clienteApi.obtener<CodigoServicio[]>(RUTA)
    })
    cargando.value = false
  }

  function crear(nombre: string): Promise<CodigoServicio | null> {
    return ejecutar(async () => {
      const codigo = await clienteApi.crear<CodigoServicio>(RUTA, { nombre })
      codigos.value = [...codigos.value, codigo].sort(porNombre)
      return codigo
    })
  }

  async function renombrar(id: number, nombre: string): Promise<boolean> {
    const resultado = await ejecutar(async () => {
      const codigo = await clienteApi.actualizar<CodigoServicio>(`${RUTA}/${id}`, { nombre })
      codigos.value = codigos.value
        .map((actual) => (actual.id === id ? codigo : actual))
        .sort(porNombre)
      return true
    })
    return resultado === true
  }

  async function eliminar(id: number): Promise<boolean> {
    const resultado = await ejecutar(async () => {
      await clienteApi.eliminar<void>(`${RUTA}/${id}`)
      codigos.value = codigos.value.filter((codigo) => codigo.id !== id)
      return true
    })
    return resultado === true
  }

  return { codigos, cargando, error, cargar, crear, renombrar, eliminar }
})
