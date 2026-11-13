<script setup lang="ts">
import { ChevronRight, Kanban, ListOrdered } from '@lucide/vue'
import { RouterLink } from 'vue-router'
</script>

<template>
  <section>
    <h2 class="text-xl font-semibold">Ajustes</h2>
    <ul class="mt-4 grid max-w-xl gap-2">
      <li>
        <RouterLink
          to="/ajustes/workflows"
          class="bg-card hover:bg-accent focus-visible:ring-ring/50 flex items-center gap-3 rounded-lg border p-4 shadow-xs outline-none focus-visible:ring-[3px]"
        >
          <ListOrdered class="text-muted-foreground size-5 shrink-0" aria-hidden="true" />
          <span class="flex-1">
            <span class="block font-medium">Workflows</span>
            <span class="text-muted-foreground block text-sm">
              Pasos que se realizan en orden y se añaden como subtareas a las tareas.
            </span>
          </span>
          <ChevronRight class="text-muted-foreground size-4 shrink-0" aria-hidden="true" />
        </RouterLink>
      </li>
      <li>
        <RouterLink
          to="/ajustes/grupos-estados"
          class="bg-card hover:bg-accent focus-visible:ring-ring/50 flex items-center gap-3 rounded-lg border p-4 shadow-xs outline-none focus-visible:ring-[3px]"
        >
          <Kanban class="text-muted-foreground size-5 shrink-0" aria-hidden="true" />
          <span class="flex-1">
            <span class="block font-medium">Grupos de estados</span>
            <span class="text-muted-foreground block text-sm">
              Estados entre los que se mueven las tareas en el tablero.
            </span>
          </span>
          <ChevronRight class="text-muted-foreground size-4 shrink-0" aria-hidden="true" />
        </RouterLink>
      </li>
    </ul>
  </section>
</template>
