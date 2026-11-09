<script setup lang="ts">
import { Primitive } from 'reka-ui'
import { cn } from '@/lib/utils'

const props = withDefaults(defineProps<{ asChild?: boolean; class?: string }>(), {
  asChild: false,
})
</script>

<template>
  <Primitive
    :as="asChild ? 'template' : 'button'"
    :as-child="asChild"
    data-slot="sidebar-menu-action"
    :class="
      cn(
        'text-sidebar-foreground ring-sidebar-ring hover:bg-sidebar-accent hover:text-sidebar-accent-foreground absolute top-1.5 right-1 flex aspect-square w-5 items-center justify-center rounded-md p-0 outline-hidden transition-transform focus-visible:ring-2 [&>svg]:size-4 [&>svg]:shrink-0',
        'group-data-[collapsible=icon]:hidden',
        props.class,
      )
    "
  >
    <slot />
  </Primitive>
</template>
