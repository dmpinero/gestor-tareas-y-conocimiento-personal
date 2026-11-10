<script setup lang="ts">
import { computed } from 'vue'

import { calcularCuentaAtras } from '@/lib/cuentaAtras'
import { useAhora } from '@/composables/useAhora'

// Cuenta atrás hasta `vencimiento` (ISO sin zona horaria, en hora local) que
// se actualiza cada segundo con el reloj compartido.
const props = defineProps<{ vencimiento: string }>()

const { ahora } = useAhora()

const cuentaAtras = computed(() => calcularCuentaAtras(props.vencimiento, ahora.value))
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
    class="tabular-nums"
    :class="cuentaAtras.vencida ? 'text-destructive' : 'text-muted-foreground'"
    >{{ cuentaAtras.texto }}</span
  >
</template>
