import { ref } from 'vue'

import { useTiendaSiguientes } from '@/stores/siguientes'

/**
 * Reordenar la cola de siguientes arrastrando sus filas con el ratón (arrastre
 * nativo, como los estados de un grupo). `eventos(indice)` se pone en cada fila
 * (con `draggable="true"`); `destino(indice)` dice si se pinta la línea de
 * destino antes o después de la fila (donde quedará la entrada al soltarla) y
 * `arrastrada(indice)` si es la fila que se arrastra. Al soltar guarda el nuevo
 * orden con `moverA` de la tienda.
 */
export function useArrastrarCola() {
  const tienda = useTiendaSiguientes()
  const origen = ref<number | null>(null)
  const sobre = ref<number | null>(null)

  function terminar(): void {
    origen.value = null
    sobre.value = null
  }

  function eventos(indice: number) {
    return {
      dragstart(evento: DragEvent) {
        origen.value = indice
        if (evento.dataTransfer) {
          evento.dataTransfer.effectAllowed = 'move'
          const entrada = tienda.cola[indice]
          evento.dataTransfer.setData(
            'text/plain',
            entrada ? `${entrada.tarea_id}-${entrada.subtarea_id ?? ''}` : '',
          )
        }
      },
      dragover(evento: DragEvent) {
        if (origen.value === null) return
        evento.preventDefault()
        if (evento.dataTransfer) evento.dataTransfer.dropEffect = 'move'
        sobre.value = indice
      },
      dragleave() {
        if (sobre.value === indice) sobre.value = null
      },
      drop(evento: DragEvent) {
        evento.preventDefault()
        const desde = origen.value
        terminar()
        const entrada = desde === null ? undefined : tienda.cola[desde]
        if (entrada) void tienda.moverA(entrada.tarea_id, indice, entrada.subtarea_id)
      },
      dragend: terminar,
    }
  }

  function destino(indice: number): 'antes' | 'despues' | undefined {
    if (origen.value === null || sobre.value !== indice || origen.value === indice) return undefined
    return indice < origen.value ? 'antes' : 'despues'
  }

  function arrastrada(indice: number): boolean {
    return origen.value === indice
  }

  return { eventos, destino, arrastrada }
}
