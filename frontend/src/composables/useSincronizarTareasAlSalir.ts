import { ref, type Ref } from 'vue'
import { onBeforeRouteLeave, useRouter } from 'vue-router'

import type { CambiosDeLasTareas } from '@/api/tipos'

/** Cambios pendientes de las tareas de un workflow editado en la visita. */
export interface CambiosDeWorkflow {
  idWorkflow: number
  nombre: string
  cambios: CambiosDeLasTareas
}

export interface OpcionesSincronizacion {
  /** Cambios pendientes de las tareas del workflow, sin modificar nada. */
  consultar: (idWorkflow: number) => Promise<CambiosDeLasTareas>
  /** Aplica los cambios pendientes de las tareas del workflow. */
  sincronizar: (idWorkflow: number) => Promise<CambiosDeLasTareas>
  /** Nombre actual del workflow, para mostrarlo en la pregunta. */
  nombreDe: (idWorkflow: number) => string | undefined
}

/**
 * Al salir de la página (con cualquier navegación), pregunta si se ponen al
 * día las tareas no completadas de los workflows cuyos pasos se han editado en
 * esta visita (`marcarEditado`). Antes consulta sus cambios pendientes: si no
 * hay ninguno, sale sin preguntar. Si los hay, cancela la navegación y abre la
 * pregunta (`abierto`, con `pendientes`): "Actualizar" aplica los cambios y
 * después sale (si falla, deja el mensaje en `error` y no sale); "Salir sin
 * actualizar" sale sin cambiar nada, y cerrar la pregunta se queda en la
 * página. Nada se modifica sin confirmarlo.
 *
 * Un workflow cuyos cambios no se pueden consultar (p. ej. porque se ha
 * eliminado) se omite: nunca impide salir.
 */
export interface SincronizacionAlSalir {
  abierto: Ref<boolean>
  pendientes: Ref<CambiosDeWorkflow[]>
  procesando: Ref<boolean>
  error: Ref<string | null>
  marcarEditado: (idWorkflow: number) => void
  olvidar: (idWorkflow: number) => void
  actualizar: () => Promise<void>
  salirSinActualizar: () => void
  alCambiarApertura: (abierto: boolean) => void
}

export function useSincronizarTareasAlSalir(
  opciones: OpcionesSincronizacion,
): SincronizacionAlSalir {
  const router = useRouter()
  const editados = new Set<number>()
  const abierto = ref(false)
  const pendientes = ref<CambiosDeWorkflow[]>([])
  const procesando = ref(false)
  const error = ref<string | null>(null)
  let destino: string | null = null
  let salidaAutorizada = false

  async function consultarPendientes(): Promise<CambiosDeWorkflow[]> {
    const resultados = await Promise.allSettled(
      [...editados].map(async (idWorkflow) => ({
        idWorkflow,
        nombre: opciones.nombreDe(idWorkflow) ?? '',
        cambios: await opciones.consultar(idWorkflow),
      })),
    )
    return resultados
      .filter((r) => r.status === 'fulfilled')
      .map((r) => r.value)
      .filter((p) => p.cambios.tareas.length > 0)
  }

  onBeforeRouteLeave(async (hacia) => {
    if (salidaAutorizada || editados.size === 0) return true
    if (abierto.value) return false
    const encontrados = await consultarPendientes()
    if (encontrados.length === 0) return true
    pendientes.value = encontrados
    destino = hacia.fullPath
    error.value = null
    abierto.value = true
    return false
  })

  function salir(): void {
    const ruta = destino
    salidaAutorizada = true
    editados.clear()
    abierto.value = false
    destino = null
    if (ruta !== null) void router.push(ruta)
  }

  async function actualizar(): Promise<void> {
    if (procesando.value) return
    procesando.value = true
    error.value = null
    try {
      // Repetirlo no cambia nada: si falla a medias, se puede volver a intentar.
      for (const pendiente of pendientes.value) await opciones.sincronizar(pendiente.idWorkflow)
    } catch (motivo) {
      error.value = (motivo as Error).message
      return
    } finally {
      procesando.value = false
    }
    salir()
  }

  function salirSinActualizar(): void {
    if (!procesando.value) salir()
  }

  function alCambiarApertura(abrir: boolean): void {
    if (abrir || procesando.value) return
    abierto.value = false
    destino = null
  }

  return {
    abierto,
    pendientes,
    procesando,
    error,
    marcarEditado: (idWorkflow) => {
      editados.add(idWorkflow)
    },
    olvidar: (idWorkflow) => {
      editados.delete(idWorkflow)
    },
    actualizar,
    salirSinActualizar,
    alCambiarApertura,
  }
}
