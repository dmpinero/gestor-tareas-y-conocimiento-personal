<script setup lang="ts">
import { RouterView } from 'vue-router'
import { SidebarInset, SidebarProvider } from '@/componentes/ui/sidebar'
import BarraLateral from '@/componentes/layout/BarraLateral.vue'
import BarraSuperior from '@/componentes/layout/BarraSuperior.vue'
import BarraEstado from '@/componentes/layout/BarraEstado.vue'
</script>

<template>
  <SidebarProvider>
    <BarraLateral />
    <SidebarInset>
      <BarraSuperior />
      <main class="min-w-0 flex-1 overflow-y-auto p-6 pb-12">
        <RouterView />
      </main>
    </SidebarInset>
  </SidebarProvider>
  <BarraEstado />
</template>
