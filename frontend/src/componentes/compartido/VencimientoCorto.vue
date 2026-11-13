<script setup lang="ts">
import { CircleAlert, CircleCheck } from '@lucide/vue'
import { computed } from 'vue'

import { useAhora } from '@/composables/useAhora'
import { calcularCuentaAtras } from '@/lib/cuentaAtras'
import { formatearFechaCorta, formatearFechaHora } from '@/lib/fechas'

// Vencimiento corto para la tabla ("13 nov"), con un ✓ si la tarea está
// completada o un ! rojo si ya venció. La fecha y hora completas quedan en el
// title y en el texto para lectores de pantalla.
const props = defineProps<{ vencimiento: string; completada: boolean }>()

const { ahora } = useAhora()

const icono = computed<'completada' | 'vencida' | undefined>(() => {
  if (props.completada) return 'completada'
  return calcularCuentaAtras(props.vencimiento, ahora.value).vencida ? 'vencida' : undefined
})
const fechaCompleta = computed(() => formatearFechaHora(props.vencimiento))
</script>

<template>
  <span
    data-testid="vencimiento-corto"
    :data-icono="icono"
    class="inline-flex items-center gap-1 whitespace-nowrap"
  >
    <CircleCheck
      v-if="icono === 'completada'"
      class="size-3.5 shrink-0 text-emerald-700 dark:text-emerald-400"
      aria-hidden="true"
    />
    <CircleAlert
      v-else-if="icono === 'vencida'"
      class="text-destructive size-3.5 shrink-0"
      aria-hidden="true"
    />
    <time :datetime="props.vencimiento" :title="fechaCompleta"
      ><span aria-hidden="true">{{ formatearFechaCorta(props.vencimiento) }}</span
      ><span class="sr-only">{{ fechaCompleta }}</span></time
    >
  </span>
</template>
