<script setup lang="ts">
import { BellRing } from '@lucide/vue'
import { computed } from 'vue'

import { useAhora } from '@/composables/useAhora'
import { calcularCuentaAtras } from '@/lib/cuentaAtras'
import { isoAFechaLocal } from '@/lib/fechas'

// Aviso de vencimiento próximo:
// - menos de 2 días: una campana naranja que se balancea;
// - menos de 1 día: dos campanas rojas;
// - menos de 4 horas: una campana blanca más grande sobre un círculo rojo que
//   late, con un balanceo más rápido, para marcar que la tarea es urgente.
// No avisa de tareas completadas, con el contador congelado (`congeladaEn`: la
// tarea está completada o en DONE), ya vencidas o sin fecha de vencimiento.
const props = withDefaults(
  defineProps<{
    vencimiento: string | null
    completada: boolean
    congeladaEn?: string | null
  }>(),
  { congeladaEn: null },
)

type Nivel = 'ninguno' | 'menos-de-48h' | 'menos-de-24h' | 'urgente'

const SEGUNDOS_URGENTE = 4 * 60 * 60

const { ahora } = useAhora()

const nivel = computed<Nivel>(() => {
  if (props.completada || props.congeladaEn !== null || props.vencimiento === null) return 'ninguno'
  const cuenta = calcularCuentaAtras(props.vencimiento, ahora.value)
  if (cuenta.nivel === 'menos-de-24h') {
    const fecha = isoAFechaLocal(props.vencimiento)
    const restantes =
      fecha === null ? Infinity : Math.floor((fecha.getTime() - ahora.value.getTime()) / 1000)
    return restantes < SEGUNDOS_URGENTE ? 'urgente' : 'menos-de-24h'
  }
  if (cuenta.nivel === 'menos-de-48h') return 'menos-de-48h'
  return 'ninguno'
})

const numeroCampanas = computed(() => (nivel.value === 'menos-de-24h' ? 2 : 1))

const TEXTOS: Record<Exclude<Nivel, 'ninguno'>, string> = {
  urgente: 'Vence en menos de 4 horas',
  'menos-de-24h': 'Vence en menos de 1 día',
  'menos-de-48h': 'Vence en menos de 2 días',
}
const texto = computed(() => (nivel.value === 'ninguno' ? '' : TEXTOS[nivel.value]))

// Mismos tonos que la cuenta atrás: rojo con menos de 24 h y naranja con
// menos de 48 h, con contraste suficiente en los dos temas.
const color = computed(() =>
  nivel.value === 'menos-de-24h' ? 'text-destructive' : 'text-orange-600 dark:text-orange-400',
)
</script>

<template>
  <span
    v-if="nivel === 'urgente'"
    role="img"
    :aria-label="texto"
    :title="texto"
    data-aviso-vencimiento
    data-urgente
    data-campanas="1"
    class="bg-destructive relative inline-flex size-6 shrink-0 items-center justify-center rounded-full align-middle text-white shadow-sm"
  >
    <span
      aria-hidden="true"
      class="bg-destructive absolute inset-0 rounded-full opacity-60 motion-safe:animate-ping"
    />
    <BellRing
      data-campana
      aria-hidden="true"
      class="motion-safe:animate-campana-urgente relative size-4 origin-top"
      :stroke-width="2.5"
    />
  </span>
  <span
    v-else-if="nivel !== 'ninguno'"
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
