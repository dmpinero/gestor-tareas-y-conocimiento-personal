<script setup lang="ts">
import { Primitive } from 'reka-ui'
import { computed } from 'vue'
import { cn } from '@/lib/utils'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/componentes/ui/tooltip'
import { useSidebar } from './useSidebar'

interface PropiedadesSidebarMenuButton {
  asChild?: boolean
  isActive?: boolean
  tooltip?: string
  class?: string
}

const props = withDefaults(defineProps<PropiedadesSidebarMenuButton>(), {
  asChild: false,
  isActive: false,
})

const { estado, esMovil } = useSidebar()

const mostrarTooltip = computed(
  () => Boolean(props.tooltip) && estado.value === 'colapsado' && !esMovil.value,
)
</script>

<template>
  <TooltipProvider v-if="tooltip">
    <Tooltip :delay-duration="0">
      <TooltipTrigger as-child>
        <Primitive
          :as="asChild ? 'template' : 'button'"
          :as-child="asChild"
          data-slot="sidebar-menu-button"
          :data-active="isActive"
          :class="
            cn(
              'peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left text-sm outline-hidden transition-[width,height,padding] hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:ring-2 disabled:pointer-events-none disabled:opacity-50 [&>svg]:size-4 [&>svg]:shrink-0',
              'data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground',
              'group-data-[collapsible=icon]:size-8! group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:p-2 group-data-[collapsible=icon]:[&>span]:hidden',
              props.class,
            )
          "
        >
          <slot />
        </Primitive>
      </TooltipTrigger>
      <TooltipContent v-if="mostrarTooltip" side="left">
        {{ tooltip }}
      </TooltipContent>
    </Tooltip>
  </TooltipProvider>

  <Primitive
    v-else
    :as="asChild ? 'template' : 'button'"
    :as-child="asChild"
    data-slot="sidebar-menu-button"
    :data-active="isActive"
    :class="
      cn(
        'peer/menu-button flex w-full items-center gap-2 overflow-hidden rounded-md p-2 text-left text-sm outline-hidden transition-[width,height,padding] hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:ring-2 disabled:pointer-events-none disabled:opacity-50 [&>svg]:size-4 [&>svg]:shrink-0',
        'data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-sidebar-accent-foreground',
        'group-data-[collapsible=icon]:size-8! group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:p-2 group-data-[collapsible=icon]:[&>span]:hidden',
        props.class,
      )
    "
  >
    <slot />
  </Primitive>
</template>
