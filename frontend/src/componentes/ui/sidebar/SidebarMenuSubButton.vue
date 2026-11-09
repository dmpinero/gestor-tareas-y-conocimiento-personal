<script setup lang="ts">
import { Primitive } from 'reka-ui'
import { cn } from '@/lib/utils'

interface PropiedadesSidebarMenuSubButton {
  asChild?: boolean
  isActive?: boolean
  class?: string
}

const props = withDefaults(defineProps<PropiedadesSidebarMenuSubButton>(), {
  asChild: false,
  isActive: false,
})
</script>

<template>
  <Primitive
    :as="asChild ? 'template' : 'a'"
    :as-child="asChild"
    data-slot="sidebar-menu-sub-button"
    :data-active="isActive"
    :class="
      cn(
        'flex h-7 min-w-0 items-center gap-2 overflow-hidden rounded-md px-2 text-sm outline-hidden hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:ring-2 disabled:pointer-events-none disabled:opacity-50 [&>svg]:size-4 [&>svg]:shrink-0',
        'data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground',
        'group-data-[collapsible=icon]:hidden',
        props.class,
      )
    "
  >
    <slot />
  </Primitive>
</template>
