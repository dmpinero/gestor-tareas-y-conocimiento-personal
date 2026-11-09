<script setup lang="ts">
import { PanelLeftClose, PanelLeftOpen } from '@lucide/vue'
import { computed } from 'vue'
import { cn } from '@/lib/utils'
import { Button } from '@/componentes/ui/button'
import { useSidebar } from './useSidebar'

const props = defineProps<{ class?: string }>()

const { estado, alternar } = useSidebar()

const colapsado = computed(() => estado.value === 'colapsado')
</script>

<template>
  <Button
    data-slot="sidebar-trigger"
    variant="ghost"
    size="icon"
    :class="cn('size-7', props.class)"
    :aria-label="colapsado ? 'Expandir panel de navegación' : 'Contraer panel de navegación'"
    @click="alternar"
  >
    <PanelLeftOpen v-if="colapsado" class="size-4" />
    <PanelLeftClose v-else class="size-4" />
  </Button>
</template>
