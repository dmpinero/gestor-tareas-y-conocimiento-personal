<script setup lang="ts">
import { type VariantesAlerta, variantesAlerta } from '.'
import { cn } from '@/lib/utils'

const props = withDefaults(
  defineProps<{
    variant?: VariantesAlerta['variant']
    class?: string
  }>(),
  { variant: 'default' },
)
</script>

<template>
  <div
    role="status"
    :data-variante="props.variant"
    :class="cn(variantesAlerta({ variant: props.variant }), props.class)"
  >
    <slot />
  </div>
</template>
