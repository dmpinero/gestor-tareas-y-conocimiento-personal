<script setup lang="ts">
import { History } from '@lucide/vue'
import { useRouter } from 'vue-router'

import { Button } from '@/componentes/ui/button'

import BotonAyuda from './BotonAyuda.vue'
import ConmutadorTema from './ConmutadorTema.vue'
import IndicadorFoco from './IndicadorFoco.vue'

// El reloj abre el historial de foco; se ve siempre, haya foco o no.
const router = useRouter()
</script>

<template>
  <header
    class="bg-card text-card-foreground border-border flex h-12 items-center justify-between gap-3 border-b px-4 shadow-xs"
  >
    <h1 class="min-w-0 truncate text-sm font-semibold">Gestor de Tareas y Conocimiento Personal</h1>
    <div class="flex max-w-[70%] min-w-0 shrink-0 items-center gap-1">
      <IndicadorFoco class="mr-1" />
      <Button
        variant="ghost"
        size="icon"
        aria-label="Historial de foco"
        title="Historial de foco"
        @click="router.push('/foco/historial')"
      >
        <History class="size-4" aria-hidden="true" />
      </Button>
      <BotonAyuda />
      <ConmutadorTema />
    </div>
  </header>
</template>
