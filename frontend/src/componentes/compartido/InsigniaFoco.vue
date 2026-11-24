<script setup lang="ts">
// Marca la tarea o subtarea en la que se está trabajando ahora: un punto
// violeta que late suave (quieto si se prefiere reducir el movimiento) y el
// texto "En foco".
</script>

<template>
  <span
    data-insignia-foco
    class="inline-flex shrink-0 items-center gap-1 rounded-full bg-violet-100 px-1.5 py-0.5 text-xs font-medium text-violet-800 dark:bg-violet-950 dark:text-violet-200"
  >
    <span aria-hidden="true" class="size-2 rounded-full bg-violet-500 motion-safe:animate-pulse" />
    En foco
  </span>
</template>
