<script setup lang="ts">
import { ref, watch } from 'vue'

import type { Tarea } from '@/api/tipos'
import { tieneContenidoComentario } from '@/lib/htmlComentario'
import { useTiendaTareas } from '@/stores/tareas'
import DialogoConfirmacion from '@/componentes/compartido/DialogoConfirmacion.vue'
import EditorComentario from '@/componentes/compartido/EditorComentario.vue'

// Diálogo para hibernar `tarea` con un comentario opcional. Está abierto
// mientras `tarea` no sea null. Un comentario sin texto visible se envía como
// null (sin comentario). Si la API falla, el diálogo sigue abierto con el
// error; si acierta, emite `hibernada` (indicando si llevaba comentario, para
// que quien muestre los comentarios los recargue) y `cerrar`.
const props = defineProps<{ tarea: Tarea | null }>()
const emit = defineEmits<{ cerrar: []; hibernada: [conComentario: boolean] }>()

const tiendaTareas = useTiendaTareas()
const comentario = ref('')
const procesando = ref(false)
const error = ref<string | null>(null)
// El título conserva el nombre mientras el diálogo se cierra (animación de
// salida), en vez de quedarse en "Hibernar la tarea " sin nombre.
const nombre = ref(props.tarea?.nombre ?? '')

watch(
  () => props.tarea,
  (tarea) => {
    if (tarea === null) return
    nombre.value = tarea.nombre
    comentario.value = ''
    error.value = null
  },
)

function alCambiarApertura(abierto: boolean): void {
  if (!abierto && !procesando.value) emit('cerrar')
}

async function confirmar(): Promise<void> {
  const tarea = props.tarea
  if (tarea === null || procesando.value) return
  const texto = tieneContenidoComentario(comentario.value) ? comentario.value : null
  procesando.value = true
  error.value = null
  const hecho = await tiendaTareas.hibernar(tarea.id, texto)
  procesando.value = false
  if (!hecho) {
    error.value = tiendaTareas.error
    return
  }
  emit('hibernada', texto !== null)
  emit('cerrar')
}
</script>

<template>
  <DialogoConfirmacion
    :abierto="props.tarea !== null"
    :titulo="`Hibernar la tarea ${nombre}`"
    descripcion="El contador de vencimiento se detiene hasta que la reanudes; al reanudarla, el vencimiento se retrasa el tiempo que haya estado hibernada. Si escribes un comentario, se añadirá a los comentarios de la tarea."
    texto-confirmar="Hibernar"
    confirmar-sin-peligro
    :procesando="procesando"
    :error="error"
    @update:abierto="alCambiarApertura"
    @confirmar="confirmar"
  >
    <EditorComentario
      v-model="comentario"
      etiqueta="Comentario (opcional)"
      placeholder="Comentario (opcional)"
      :solo-lectura="procesando"
      @enviar="confirmar"
    />
  </DialogoConfirmacion>
</template>
