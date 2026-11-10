<script setup lang="ts">
import { CollapsibleContent, type CollapsibleContentProps } from 'reka-ui'

defineProps<CollapsibleContentProps>()
</script>

<template>
  <CollapsibleContent data-slot="collapsible-content" v-bind="$props" class="overflow-hidden">
    <slot />
  </CollapsibleContent>
</template>
