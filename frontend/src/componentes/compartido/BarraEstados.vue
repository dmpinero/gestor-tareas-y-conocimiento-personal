<script setup lang="ts">
import { computed } from 'vue'

// Barra apilada con la proporción de tareas en cada estado del tablero, en el
// color de su columna. El reparto se lee también como texto en su nombre
// accesible; los estados sin tareas no aparecen.
const props = defineProps<{
  // Estados en el orden del grupo, con sus tareas y el relleno de su color.
  estados: { id: number; nombre: string; cantidad: number; relleno: string }[]
  // Nombre del grupo de estados.
  titulo: string
}>()

const segmentos = computed(() => {
  const total = props.estados.reduce((suma, estado) => suma + estado.cantidad, 0)
  return props.estados
    .filter((estado) => estado.cantidad > 0)
    .map((estado) => ({
      ...estado,
      porcentaje: (estado.cantidad / total) * 100,
      texto: `${estado.nombre}, ${estado.cantidad} ${estado.cantidad === 1 ? 'tarea' : 'tareas'}`,
    }))
})

const etiqueta = computed(
  () =>
    `Distribución de estados en ${props.titulo}: ${
      segmentos.value.length === 0
        ? 'sin tareas'
        : segmentos.value.map((segmento) => segmento.texto).join('; ')
    }`,
)
</script>

<template>
  <div
    data-testid="barra-estados"
    role="img"
    :aria-label="etiqueta"
    :title="etiqueta"
    class="bg-muted flex h-3 w-full overflow-hidden rounded-full"
  >
    <span
      v-for="segmento in segmentos"
      :key="segmento.id"
      :data-estado="segmento.nombre"
      :class="segmento.relleno"
      :style="{ width: `${segmento.porcentaje}%` }"
    />
  </div>
</template>
