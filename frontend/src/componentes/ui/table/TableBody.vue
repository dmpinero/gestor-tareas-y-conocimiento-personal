<script setup lang="ts">
import { cn } from '@/lib/utils'

const props = defineProps<{ class?: string }>()
</script>

<template>
  <tbody
    data-slot="table-body"
    :class="cn('[&_tr:last-child]:border-0 [&_tr:nth-child(even)]:bg-muted/30', props.class)"
  >
    <slot />
  </tbody>
</template>
