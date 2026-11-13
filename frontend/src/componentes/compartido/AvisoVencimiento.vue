<script setup lang="ts">
import { BellRing } from '@lucide/vue'
import { computed } from 'vue'

import { useAhora } from '@/composables/useAhora'
import { calcularCuentaAtras } from '@/lib/cuentaAtras'

// Aviso de vencimiento próximo: una campana que se balancea cuando a la tarea
// le quedan menos de 2 días y dos campanas cuando le queda menos de 1 día. No
// avisa de tareas completadas, ya vencidas o sin fecha de vencimiento.
const props = defineProps<{
  vencimiento: string | null
  completada: boolean
}>()

const { ahora } = useAhora()

const numeroCampanas = computed<0 | 1 | 2>(() => {
  if (props.completada || props.vencimiento === null) return 0
  const { nivel } = calcularCuentaAtras(props.vencimiento, ahora.value)
  if (nivel === 'menos-de-24h') return 2
  if (nivel === 'menos-de-48h') return 1
  return 0
})

const texto = computed(() =>
  numeroCampanas.value === 2 ? 'Vence en menos de 1 día' : 'Vence en menos de 2 días',
)

// Mismos tonos que la cuenta atrás: rojo con menos de 24 h y naranja con
// menos de 48 h, con contraste suficiente en los dos temas.
const color = computed(() =>
  numeroCampanas.value === 2 ? 'text-destructive' : 'text-orange-600 dark:text-orange-400',
)
</script>

<template>
  <span
    v-if="numeroCampanas > 0"
    role="img"
    :aria-label="texto"
    :title="texto"
    data-aviso-vencimiento
    :data-campanas="numeroCampanas"
    class="inline-flex shrink-0 items-center align-middle"
    :class="color"
  >
    <BellRing
      v-for="indice in numeroCampanas"
      :key="indice"
      data-campana
      aria-hidden="true"
      class="motion-safe:animate-campana size-4 origin-top"
      :class="indice === 2 && '-ml-1.5 [animation-delay:-0.6s]'"
    />
  </span>
</template>
