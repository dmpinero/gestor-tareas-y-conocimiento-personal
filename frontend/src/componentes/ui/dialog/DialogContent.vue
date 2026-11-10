<script setup lang="ts">
import { X } from '@lucide/vue'
import {
  DialogClose,
  DialogContent,
  DialogPortal,
  type DialogContentEmits,
  type DialogContentProps,
  useForwardPropsEmits,
} from 'reka-ui'
import { computed, type HTMLAttributes } from 'vue'
import { cn } from '@/lib/utils'
import DialogOverlay from './DialogOverlay.vue'

const props = defineProps<
  DialogContentProps & {
    class?: HTMLAttributes['class']
    // Para modales de operación en curso que no deben poder cerrarse
    // mientras se ejecutan (p. ej. un borrado en bloque o una importación):
    // oculta la X y bloquea el cierre por Escape o por click fuera.
    sinCerrar?: boolean
    // Oculta solo la X de la esquina, para modales que ya tienen su propio
    // botón "Cerrar" visible (y así el nombre accesible no se repite).
    sinAspa?: boolean
  }
>()
const emits = defineEmits<DialogContentEmits>()

const delegatedProps = computed(() => {
  const { class: clase, sinCerrar: descartado, sinAspa: sinX, ...delegated } = props
  void clase
  void descartado
  void sinX
  return delegated
})

const forwarded = useForwardPropsEmits(delegatedProps, emits)
</script>

<template>
  <DialogPortal>
    <DialogOverlay />
    <DialogContent
      data-slot="dialog-content"
      v-bind="forwarded"
      :class="
        cn(
          'bg-background data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 fixed top-[50%] left-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 rounded-lg border p-6 shadow-lg duration-200',
          props.class,
        )
      "
      @escape-key-down="(evento) => props.sinCerrar && evento.preventDefault()"
      @pointer-down-outside="(evento) => props.sinCerrar && evento.preventDefault()"
      @interact-outside="(evento) => props.sinCerrar && evento.preventDefault()"
    >
      <slot />
      <DialogClose
        v-if="!props.sinCerrar && !props.sinAspa"
        class="ring-offset-background focus:ring-ring data-[state=open]:bg-accent absolute top-4 right-4 rounded-xs opacity-70 transition-opacity hover:opacity-100 focus:ring-2 focus:ring-offset-2 focus:outline-hidden disabled:pointer-events-none"
      >
        <X class="size-4" />
        <span class="sr-only">Cerrar</span>
      </DialogClose>
    </DialogContent>
  </DialogPortal>
</template>
