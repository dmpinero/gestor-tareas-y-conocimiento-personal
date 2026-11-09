<script setup lang="ts">
import { Label, type LabelProps } from 'reka-ui'
import { cn } from '@/lib/utils'

interface PropiedadesLabel extends LabelProps {
  class?: string
}

const props = defineProps<PropiedadesLabel>()
</script>

<template>
  <Label
    data-slot="label"
    v-bind="props"
    :class="
      cn(
        'flex select-none items-center gap-2 text-sm leading-none font-medium peer-disabled:cursor-not-allowed peer-disabled:opacity-50 group-data-[disabled=true]:pointer-events-none group-data-[disabled=true]:opacity-50',
        props.class,
      )
    "
  >
    <slot />
  </Label>
</template>
