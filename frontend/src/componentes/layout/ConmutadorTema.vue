<script setup lang="ts">
import { Moon, Sun } from '@lucide/vue'
import { computed } from 'vue'
import { useModoOscuro } from '@/composables/useModoOscuro'
import { Button } from '@/componentes/ui/button'

const { temaActual, alternar } = useModoOscuro()

const esOscuro = computed(() => temaActual.value === 'oscuro')
const etiqueta = computed(() => (esOscuro.value ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'))
</script>

<template>
  <Button
    variant="ghost"
    size="icon"
    role="switch"
    :aria-checked="esOscuro"
    :aria-label="etiqueta"
    @click="alternar"
  >
    <Sun v-if="esOscuro" class="size-4" />
    <Moon v-else class="size-4" />
  </Button>
</template>
