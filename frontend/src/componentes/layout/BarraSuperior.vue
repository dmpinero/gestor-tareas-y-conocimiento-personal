<script setup lang="ts">
import BotonAyuda from './BotonAyuda.vue'
import ConmutadorTema from './ConmutadorTema.vue'
import IndicadorFoco from './IndicadorFoco.vue'
</script>

<template>
  <header
    class="bg-card text-card-foreground border-border flex h-12 items-center justify-between gap-3 border-b px-4 shadow-xs"
  >
    <h1 class="min-w-0 truncate text-sm font-semibold">Gestor de Tareas y Conocimiento Personal</h1>
    <div class="flex max-w-[70%] min-w-0 items-center gap-1">
      <IndicadorFoco class="mr-1" />
      <BotonAyuda />
      <ConmutadorTema />
    </div>
  </header>
</template>
