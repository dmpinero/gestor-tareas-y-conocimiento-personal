<script setup lang="ts">
import { cn } from '@/lib/utils'

const props = defineProps<{ class?: string }>()
</script>

<template>
  <div data-slot="sheet-header" :class="cn('flex flex-col gap-1.5 p-4', props.class)">
    <slot />
  </div>
</template>
