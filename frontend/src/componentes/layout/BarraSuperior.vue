<script setup lang="ts">
import BotonAyuda from './BotonAyuda.vue'
import ConmutadorTema from './ConmutadorTema.vue'
</script>

<template>
  <header class="border-border flex h-12 items-center justify-between border-b px-4">
    <h1 class="text-sm font-semibold">Gestor de Tareas y Conocimiento Personal</h1>
    <div class="flex items-center gap-1">
      <BotonAyuda />
      <ConmutadorTema />
    </div>
  </header>
</template>
