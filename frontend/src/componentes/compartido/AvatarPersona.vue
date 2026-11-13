<script setup lang="ts">
import { computed } from 'vue'

import { colorAvatar, inicialesDe } from '@/lib/coloresTarea'

// Círculo con las iniciales de una persona, con un color estable derivado de
// su nombre. El nombre completo va en el tooltip y como texto para lectores de
// pantalla.
const props = defineProps<{ nombre: string }>()

const iniciales = computed(() => inicialesDe(props.nombre))
</script>

<template>
  <span
    data-testid="avatar-persona"
    :title="props.nombre"
    class="ring-background inline-flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ring-2 select-none"
    :class="colorAvatar(props.nombre)"
  >
    <span aria-hidden="true">{{ iniciales }}</span>
    <span class="sr-only">{{ props.nombre }}</span>
  </span>
</template>
