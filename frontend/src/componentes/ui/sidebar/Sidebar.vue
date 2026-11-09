<script setup lang="ts">
import { cn } from '@/lib/utils'
import { Sheet, SheetContent } from '@/componentes/ui/sheet'
import { useSidebar } from './useSidebar'

interface PropiedadesSidebar {
  side?: 'left' | 'right'
  collapsible?: 'icon' | 'none'
  class?: string
}

const props = withDefaults(defineProps<PropiedadesSidebar>(), {
  side: 'left',
  collapsible: 'icon',
})

const { estado, abiertoEnMovil, esMovil } = useSidebar()
</script>

<template>
  <Sheet v-if="esMovil" v-model:open="abiertoEnMovil">
    <SheetContent
      data-slot="sidebar"
      data-sidebar="sidebar"
      data-mobile="true"
      :side="props.side"
      class="bg-sidebar text-sidebar-foreground w-(--sidebar-width) p-0 [&>button]:hidden"
    >
      <div class="flex h-full w-full flex-col">
        <slot />
      </div>
    </SheetContent>
  </Sheet>

  <div
    v-else
    class="text-sidebar-foreground group peer hidden md:block"
    :data-state="estado"
    :data-collapsible="estado === 'colapsado' ? props.collapsible : ''"
    :data-side="props.side"
  >
    <div
      :class="
        cn(
          'relative h-svh w-(--sidebar-width) bg-transparent transition-[width] duration-200 ease-linear',
          'group-data-[collapsible=icon]:w-(--sidebar-width-icon)',
        )
      "
    />
    <div
      :class="
        cn(
          'fixed inset-y-0 z-10 hidden h-svh w-(--sidebar-width) transition-[left,right,width] duration-200 ease-linear md:flex',
          props.side === 'left'
            ? 'left-0 group-data-[collapsible=icon]:w-(--sidebar-width-icon)'
            : 'right-0 group-data-[collapsible=icon]:w-(--sidebar-width-icon)',
          props.class,
        )
      "
    >
      <div
        data-slot="sidebar"
        data-sidebar="sidebar"
        :class="
          cn(
            'bg-sidebar flex h-full w-full flex-col',
            props.side === 'left' ? 'border-r' : 'border-l',
          )
        "
      >
        <slot />
      </div>
    </div>
  </div>
</template>
