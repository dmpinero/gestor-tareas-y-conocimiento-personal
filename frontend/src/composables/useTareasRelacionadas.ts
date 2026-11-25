import { inject, provide, ref, type InjectionKey, type Ref } from 'vue'
import type { TipoRelacion } from '@/lib/tareasRelacionadas'

export type { TipoRelacion }

export interface SeleccionRelacionada {
  tipo: TipoRelacion
  nombre: string
}

type AbrirRelacionadas = (tipo: TipoRelacion, nombre: string) => void

const CLAVE_ABRIR: InjectionKey<AbrirRelacionadas> = Symbol('abrirTareasRelacionadas')

/**
 * Lo usa la vista que pinta el modal de tareas relacionadas: guarda la etiqueta,
 * persona, estado, etc. elegido y deja a sus descendientes abrir el modal.
 */
export function useProveedorTareasRelacionadas(): {
  seleccion: Ref<SeleccionRelacionada | null>
  cerrar: () => void
} {
  const seleccion = ref<SeleccionRelacionada | null>(null)
  provide(CLAVE_ABRIR, (tipo, nombre) => {
    seleccion.value = { tipo, nombre }
  })
  return {
    seleccion,
    cerrar: () => {
      seleccion.value = null
    },
  }
}

/** `null` cuando ninguna vista antecesora ofrece el modal. */
export function useAbrirTareasRelacionadas(): AbrirRelacionadas | null {
  return inject(CLAVE_ABRIR, null)
}
