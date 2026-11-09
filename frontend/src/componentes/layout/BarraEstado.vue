<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { obtenerUltimaVersion } from '@/api/github'

const version = ref<string | null>(null)

onMounted(async () => {
  try {
    version.value = await obtenerUltimaVersion()
  } catch {
    // Sin conexión con GitHub (offline, límite de peticiones...): se omite el
    // número de versión en vez de romper la barra de estado.
    version.value = null
  }
})
</script>

<template>
  <footer
    class="bg-background border-border fixed inset-x-0 bottom-0 z-40 flex h-9 items-center justify-end gap-1 border-t px-3 text-xs"
  >
    <span v-if="version" class="text-muted-foreground">v{{ version }}</span>
  </footer>
</template>
