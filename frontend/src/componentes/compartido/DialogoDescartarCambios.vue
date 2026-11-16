<script setup lang="ts">
import DialogoConfirmacion from '@/componentes/compartido/DialogoConfirmacion.vue'

// Confirmación de descartar los cambios sin guardar al cerrar una modal con
// datos. "Descartar" emite `descartar`; "Seguir editando" y Escape la cierran
// (`update:abierto`). Se usa junto a `useConfirmarDescarte`.
const props = defineProps<{ abierto: boolean }>()
const emit = defineEmits<{
  'update:abierto': [abierto: boolean]
  descartar: []
  cierreFoco: [evento: Event]
}>()
</script>

<template>
  <DialogoConfirmacion
    :abierto="props.abierto"
    titulo="¿Descartar los cambios?"
    descripcion="Los datos que has introducido se perderán."
    texto-confirmar="Descartar"
    texto-cancelar="Seguir editando"
    @update:abierto="(abierto) => emit('update:abierto', abierto)"
    @confirmar="emit('descartar')"
    @cierre-foco="(evento) => emit('cierreFoco', evento)"
  />
</template>
