<script setup lang="ts">
import { cn } from '@/lib/utils'

const props = defineProps<{ class?: string }>()
</script>

<template>
  <main
    data-slot="sidebar-inset"
    :class="cn('bg-background relative flex w-full min-w-0 flex-1 flex-col', props.class)"
  >
    <slot />
  </main>
</template>
