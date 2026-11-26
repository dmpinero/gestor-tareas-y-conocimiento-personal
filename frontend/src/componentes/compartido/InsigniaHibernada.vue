<script setup lang="ts">
import { Snowflake } from '@lucide/vue'

import NombreRelacionado from '@/componentes/compartido/NombreRelacionado.vue'

// Marca una tarea hibernada: su reloj de vencimiento está parado hasta que se
// reanude. Lleva el texto "Hibernada" (no solo el color) con tonos que
// mantienen el contraste en los dos temas. Dentro de una vista con el modal de
// tareas relacionadas, pulsarla lista todas las hibernadas.
</script>

<template>
  <NombreRelacionado tipo="hibernada" nombre="Hibernada" class="inline-flex shrink-0 rounded-full">
    <span
      data-insignia-hibernada
      class="inline-flex shrink-0 items-center gap-1 rounded-full bg-sky-100 px-1.5 py-0.5 text-xs font-medium text-sky-900 dark:bg-sky-950 dark:text-sky-100"
    >
      <Snowflake aria-hidden="true" class="size-3 shrink-0" :stroke-width="2.5" />
      Hibernada
    </span>
  </NombreRelacionado>
</template>
