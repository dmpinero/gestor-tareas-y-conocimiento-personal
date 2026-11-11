import { defineStore } from 'pinia'
import { ref } from 'vue'

import { clienteApi } from '@/api/cliente'
import type { GrupoEstados } from '@/api/tipos'

const RUTA = '/grupos-estados'

// Grupos de estados de Ajustes, que también usan el formulario de tareas y el
// tablero. Las acciones que cambian datos devuelven `true` si la API respondió
// bien; si falla, guardan el mensaje en `error` y dejan la lista como estaba.
// Las acciones sobre estados reemplazan el grupo con el que devuelve la API.
export const useTiendaGruposEstados = defineStore('gruposEstados', () => {
  const grupos = ref<GrupoEstados[]>([])
  const cargando = ref(false)
  const error = ref<string | null>(null)

  function conEstadosOrdenados(grupo: GrupoEstados): GrupoEstados {
    return { ...grupo, estados: [...grupo.estados].sort((a, b) => a.posicion - b.posicion) }
  }

  function reemplazar(grupo: GrupoEstados): void {
    const ordenado = conEstadosOrdenados(grupo)
    grupos.value = grupos.value.map((actual) => (actual.id === grupo.id ? ordenado : actual))
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
      grupos.value = (await clienteApi.obtener<GrupoEstados[]>(RUTA)).map(conEstadosOrdenados)
    })
    cargando.value = false
  }

  function crear(nombre: string): Promise<boolean> {
    return ejecutar(async () => {
      const grupo = await clienteApi.crear<GrupoEstados>(RUTA, { nombre })
      grupos.value = [...grupos.value, conEstadosOrdenados(grupo)]
    })
  }

  function renombrar(id: number, nombre: string): Promise<boolean> {
    return ejecutar(async () => {
      reemplazar(await clienteApi.actualizar<GrupoEstados>(`${RUTA}/${id}`, { nombre }))
    })
  }

  // Las tareas del grupo quedan sin grupo en el servidor.
  function eliminar(id: number): Promise<boolean> {
    return ejecutar(async () => {
      await clienteApi.eliminar<void>(`${RUTA}/${id}`)
      grupos.value = grupos.value.filter((grupo) => grupo.id !== id)
    })
  }

  function anadirEstado(idGrupo: number, nombre: string): Promise<boolean> {
    return ejecutar(async () => {
      reemplazar(await clienteApi.crear<GrupoEstados>(`${RUTA}/${idGrupo}/estados`, { nombre }))
    })
  }

  function renombrarEstado(idGrupo: number, idEstado: number, nombre: string): Promise<boolean> {
    return ejecutar(async () => {
      reemplazar(
        await clienteApi.actualizar<GrupoEstados>(`${RUTA}/${idGrupo}/estados/${idEstado}`, {
          nombre,
        }),
      )
    })
  }

  // Si el estado tiene tareas, el servidor exige `moverA`: otro estado del
  // mismo grupo al que pasarlas.
  function eliminarEstado(idGrupo: number, idEstado: number, moverA?: number): Promise<boolean> {
    const consulta = moverA === undefined ? '' : `?mover_a=${moverA}`
    return ejecutar(async () => {
      reemplazar(
        await clienteApi.eliminar<GrupoEstados>(
          `${RUTA}/${idGrupo}/estados/${idEstado}${consulta}`,
        ),
      )
    })
  }

  function reordenarEstados(idGrupo: number, ids: number[]): Promise<boolean> {
    return ejecutar(async () => {
      reemplazar(await clienteApi.actualizar<GrupoEstados>(`${RUTA}/${idGrupo}/orden`, { ids }))
    })
  }

  return {
    grupos,
    cargando,
    error,
    cargar,
    crear,
    renombrar,
    eliminar,
    anadirEstado,
    renombrarEstado,
    eliminarEstado,
    reordenarEstados,
  }
})
