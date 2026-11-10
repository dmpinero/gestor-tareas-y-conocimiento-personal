<script setup lang="ts">
import { ChevronRight, ListOrdered } from '@lucide/vue'
import { RouterLink } from 'vue-router'
</script>

<template>
  <section>
    <h2 class="text-xl font-semibold">Ajustes</h2>
    <ul class="mt-4 grid max-w-xl gap-2">
      <li>
        <RouterLink
          to="/ajustes/workflow-oportunidades"
          class="hover:bg-accent focus-visible:ring-ring/50 flex items-center gap-3 rounded-lg border p-4 outline-none focus-visible:ring-[3px]"
        >
          <ListOrdered class="text-muted-foreground size-5 shrink-0" aria-hidden="true" />
          <span class="flex-1">
            <span class="block font-medium">Workflow Oportunidades</span>
            <span class="text-muted-foreground block text-sm">
              Pasos estándar que se realizan en orden en cada oportunidad.
            </span>
          </span>
          <ChevronRight class="text-muted-foreground size-4 shrink-0" aria-hidden="true" />
        </RouterLink>
      </li>
    </ul>
  </section>
</template>
