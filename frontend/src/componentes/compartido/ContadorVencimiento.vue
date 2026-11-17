<script setup lang="ts">
import { Pause } from '@lucide/vue'
import { computed } from 'vue'

import { calcularCuentaAtras, type NivelCuentaAtras } from '@/lib/cuentaAtras'
import { useAhora } from '@/composables/useAhora'

// Cuenta atrás hasta `vencimiento` (ISO sin zona horaria, en hora local) que
// se actualiza cada segundo con el reloj compartido.
//
// Con `congeladaEn` (instante en UTC de la API, "YYYY-MM-DDTHH:MM:SSZ") la tarea
// está completada o en DONE: el contador queda parado en lo que faltaba (o hacía
// que venció) en ese instante, sin color de urgencia y con un icono de pausa. Al
// quitarlo vuelve a contar en vivo desde el vencimiento.
const props = withDefaults(defineProps<{ vencimiento: string; congeladaEn?: string | null }>(), {
  congeladaEn: null,
})

const { ahora } = useAhora()

const congelado = computed(() => props.congeladaEn !== null)

const cuentaAtras = computed(() =>
  calcularCuentaAtras(
    props.vencimiento,
    // Congelado, no depende del reloj: no se recalcula cada segundo.
    props.congeladaEn !== null ? new Date(props.congeladaEn) : ahora.value,
  ),
)

// Rojo con menos de 24 h (o vencida), naranja entre 24 y 48 h y verde con 48 h
// o más. Los tonos de naranja y verde cambian en modo oscuro para mantener el
// contraste WCAG AA sobre el fondo de cada tema. Congelado, el tono atenuado del
// tema, que también lo mantiene.
const COLOR_POR_NIVEL: Record<NivelCuentaAtras, string> = {
  vencida: 'text-destructive',
  'menos-de-24h': 'text-destructive',
  'menos-de-48h': 'text-orange-700 dark:text-orange-400',
  holgada: 'text-green-700 dark:text-green-400',
}
const color = computed(() =>
  congelado.value ? 'text-muted-foreground' : COLOR_POR_NIVEL[cuentaAtras.value.nivel],
)
</script>

<template>
  <!--
    El rol `timer` lleva `aria-live="off"` implícito: los lectores de pantalla
    leen el texto al llegar a él, pero no anuncian cada segundo.
  -->
  <span
    role="timer"
    data-testid="contador-vencimiento"
    :data-vencida="cuentaAtras.vencida"
    :data-nivel="cuentaAtras.nivel"
    :data-congelado="congelado || undefined"
    :title="congelado ? 'Contador detenido: la tarea está completada o en DONE' : undefined"
    class="tabular-nums"
    :class="[color, congelado && 'inline-flex items-center gap-1']"
    ><Pause
      v-if="congelado"
      data-icono-pausa
      aria-hidden="true"
      class="size-3 shrink-0"
      :stroke-width="2.5"
    /><span data-testid="contador-texto">{{ cuentaAtras.texto }}</span
    ><span v-if="congelado" class="sr-only">{{ ' (contador detenido)' }}</span></span
  >
</template>
