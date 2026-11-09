<script setup lang="ts">
import { Primitive, type PrimitiveProps } from 'reka-ui'
import { type VariantesBoton, variantesBoton } from '.'
import { cn } from '@/lib/utils'

interface PropiedadesBoton extends PrimitiveProps {
  variant?: VariantesBoton['variant']
  size?: VariantesBoton['size']
  class?: string
}

const props = withDefaults(defineProps<PropiedadesBoton>(), {
  as: 'button',
})
</script>

<template>
  <Primitive
    :as="as"
    :as-child="asChild"
    :class="cn(variantesBoton({ variant, size }), props.class)"
  >
    <slot />
  </Primitive>
</template>
