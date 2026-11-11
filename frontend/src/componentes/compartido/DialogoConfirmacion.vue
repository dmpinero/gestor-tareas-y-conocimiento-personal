<script setup lang="ts">
import {
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogOverlay,
  AlertDialogPortal,
  AlertDialogRoot,
  AlertDialogTitle,
} from 'reka-ui'

import { Button } from '@/componentes/ui/button'

// Confirmación de una acción destructiva (role="alertdialog"). Al abrirse, el
// foco va a "Cancelar"; Escape y "Cancelar" la cierran (`update:abierto`). Un
// clic fuera no la cierra. "Confirmar" emite `confirmar` y no la cierra: quien
// la usa cierra al terminar o deja el fallo en `error`, que se muestra dentro.
// `cierreFoco` reenvía el evento de devolución del foco al cerrar, para que
// quien la usa pueda llevarlo a otro sitio (`preventDefault`) si el elemento
// que la abrió ya no existe. El contenido por defecto (slot) va bajo la
// descripción, p. ej. para elegir una opción antes de confirmar.
const props = defineProps<{
  abierto: boolean
  titulo: string
  descripcion: string
  textoConfirmar: string
  procesando?: boolean
  error?: string | null
}>()
const emit = defineEmits<{
  'update:abierto': [abierto: boolean]
  confirmar: []
  cierreFoco: [evento: Event]
}>()
</script>

<template>
  <AlertDialogRoot
    :open="props.abierto"
    @update:open="(abierto) => emit('update:abierto', abierto)"
  >
    <AlertDialogPortal>
      <AlertDialogOverlay
        data-slot="dialog-overlay"
        class="data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 fixed inset-0 z-50 bg-black/50"
      />
      <AlertDialogContent
        data-slot="alert-dialog-content"
        class="bg-background data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 fixed top-[50%] left-[50%] z-50 grid w-[calc(100%-2rem)] max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 rounded-lg border p-6 shadow-lg duration-200"
        @close-auto-focus="(evento: Event) => emit('cierreFoco', evento)"
      >
        <div class="flex flex-col gap-2 text-center sm:text-left">
          <AlertDialogTitle class="text-lg leading-none font-semibold [overflow-wrap:anywhere]">{{
            props.titulo
          }}</AlertDialogTitle>
          <AlertDialogDescription class="text-muted-foreground text-sm">{{
            props.descripcion
          }}</AlertDialogDescription>
        </div>
        <slot />
        <p v-if="props.error" class="text-destructive text-sm" role="alert">{{ props.error }}</p>
        <div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <AlertDialogCancel as-child>
            <Button type="button" variant="outline">Cancelar</Button>
          </AlertDialogCancel>
          <Button
            type="button"
            variant="destructive"
            :disabled="props.procesando"
            @click="emit('confirmar')"
            >{{ props.textoConfirmar }}</Button
          >
        </div>
      </AlertDialogContent>
    </AlertDialogPortal>
  </AlertDialogRoot>
</template>
