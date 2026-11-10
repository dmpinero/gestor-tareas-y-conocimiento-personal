<script setup lang="ts">
import { Check } from '@lucide/vue'
import {
  CheckboxIndicator,
  CheckboxRoot,
  type CheckboxRootEmits,
  type CheckboxRootProps,
  useForwardPropsEmits,
} from 'reka-ui'
import { computed, type HTMLAttributes } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps<CheckboxRootProps & { class?: HTMLAttributes['class'] }>()
const emits = defineEmits<CheckboxRootEmits>()

const delegatedProps = computed(() => {
  const { class: clase, ...delegated } = props
  void clase
  return delegated
})

const forwarded = useForwardPropsEmits(delegatedProps, emits)
</script>

<template>
  <CheckboxRoot
    data-slot="checkbox"
    v-bind="forwarded"
    :class="
      cn(
        'peer border-input bg-background data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground data-[state=checked]:border-primary focus-visible:ring-ring/50 size-4 shrink-0 rounded-[4px] border shadow-xs outline-none focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50',
        props.class,
      )
    "
  >
    <CheckboxIndicator
      data-slot="checkbox-indicator"
      class="flex items-center justify-center text-current"
    >
      <Check class="size-3.5" />
    </CheckboxIndicator>
  </CheckboxRoot>
</template>
