<script setup lang="ts">
import { computed } from 'vue'

import { calcularCuentaAtras, type NivelCuentaAtras } from '@/lib/cuentaAtras'
import { useAhora } from '@/composables/useAhora'

// Cuenta atrás hasta `vencimiento` (ISO sin zona horaria, en hora local) que
// se actualiza cada segundo con el reloj compartido.
const props = defineProps<{ vencimiento: string }>()

const { ahora } = useAhora()

const cuentaAtras = computed(() => calcularCuentaAtras(props.vencimiento, ahora.value))

// Rojo con menos de 24 h (o vencida), naranja entre 24 y 48 h y verde con 48 h
// o más. Los tonos de naranja y verde cambian en modo oscuro para mantener el
// contraste WCAG AA sobre el fondo de cada tema.
const COLOR_POR_NIVEL: Record<NivelCuentaAtras, string> = {
  vencida: 'text-destructive',
  'menos-de-24h': 'text-destructive',
  'menos-de-48h': 'text-orange-700 dark:text-orange-400',
  holgada: 'text-green-700 dark:text-green-400',
}
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
    class="tabular-nums"
    :class="COLOR_POR_NIVEL[cuentaAtras.nivel]"
    >{{ cuentaAtras.texto }}</span
  >
</template>
