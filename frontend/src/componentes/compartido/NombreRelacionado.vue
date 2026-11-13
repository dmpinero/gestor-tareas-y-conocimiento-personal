<script setup lang="ts">
import { computed } from 'vue'
import { useAbrirTareasRelacionadas, type TipoRelacion } from '@/composables/useTareasRelacionadas'

// Nombre de una etiqueta o persona que, dentro de una vista que ofrece el modal
// de tareas relacionadas, se pulsa para abrirlo. Fuera de ella es solo texto.
// El contenido visible puede cambiarse por la ranura (p. ej. un avatar); el
// nombre accesible es siempre el mismo.
const props = defineProps<{
  tipo: TipoRelacion
  nombre: string
}>()

const abrir = useAbrirTareasRelacionadas()

const etiquetaAccesible = computed(() =>
  props.tipo === 'etiqueta'
    ? `Ver tareas con la etiqueta ${props.nombre}`
    : `Ver tareas y subtareas de ${props.nombre}`,
)
</script>

<template>
  <button
    v-if="abrir"
    type="button"
    data-nombre-relacionado
    :aria-label="etiquetaAccesible"
    :title="etiquetaAccesible"
    class="focus-visible:ring-ring/50 cursor-pointer rounded-sm text-left outline-none [overflow-wrap:anywhere] hover:underline focus-visible:ring-[3px]"
    @click.stop="abrir(props.tipo, props.nombre)"
  >
    <slot>{{ props.nombre }}</slot>
  </button>
  <span v-else
    ><slot>{{ props.nombre }}</slot></span
  >
</template>
