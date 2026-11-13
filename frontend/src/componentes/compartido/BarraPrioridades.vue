<script setup lang="ts">
import { computed } from 'vue'

import { CLAVES_PRIORIDAD, RELLENO_PRIORIDAD, clavePrioridad } from '@/lib/coloresTarea'

// Barra apilada con la proporción de tareas de cada prioridad. El reparto se
// lee también como texto en su nombre accesible.
const props = defineProps<{
  prioridades: (number | null)[]
  // Nombre del conjunto de tareas, p. ej. el del grupo ("Pendientes").
  titulo: string
}>()

const segmentos = computed(() => {
  const total = props.prioridades.length
  return CLAVES_PRIORIDAD.map((clave) => {
    const cantidad = props.prioridades.filter((p) => clavePrioridad(p) === clave).length
    return {
      clave,
      cantidad,
      porcentaje: total === 0 ? 0 : (cantidad / total) * 100,
      texto: `${clave === 'sin' ? 'sin prioridad' : `prioridad ${clave}`}, ${cantidad} ${
        cantidad === 1 ? 'tarea' : 'tareas'
      }`,
    }
  }).filter((segmento) => segmento.cantidad > 0)
})

const etiqueta = computed(
  () =>
    `Distribución de prioridades en ${props.titulo}: ${segmentos.value
      .map((segmento) => segmento.texto)
      .join('; ')}`,
)
</script>

<template>
  <div
    data-testid="barra-prioridades"
    role="img"
    :aria-label="etiqueta"
    :title="etiqueta"
    class="bg-muted flex h-2.5 w-full min-w-16 overflow-hidden rounded-full"
  >
    <span
      v-for="segmento in segmentos"
      :key="segmento.clave"
      :data-prioridad="segmento.clave"
      :class="RELLENO_PRIORIDAD[segmento.clave]"
      :style="{ width: `${segmento.porcentaje}%` }"
    />
  </div>
</template>
