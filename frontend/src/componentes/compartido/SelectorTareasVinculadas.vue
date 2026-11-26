<script setup lang="ts">
import { computed } from 'vue'

import type { Tarea } from '@/api/tipos'
import DialogoElegirTareas from '@/componentes/compartido/DialogoElegirTareas.vue'
import { useTiendaTareas } from '@/stores/tareas'

// Diálogo para vincular `tarea` con una o varias tareas más: ofrece las demás
// tareas del almacén (sin ella ni las ya vinculadas) y "Relacionar (n)" las
// vincula todas de una vez (ver `DialogoElegirTareas`).
const props = defineProps<{ tarea: Tarea; abierto: boolean }>()
const emit = defineEmits<{ 'update:abierto': [abierto: boolean] }>()

const tienda = useTiendaTareas()

const disponibles = computed(() =>
  tienda.tareas.filter(
    (otra) => otra.id !== props.tarea.id && !props.tarea.vinculadas.includes(otra.id),
  ),
)

async function vincular(ids: number[]): Promise<string | null> {
  const hecho = await tienda.vincularTareas(
    props.tarea.id,
    [...ids].sort((a, b) => a - b),
  )
  return hecho ? null : tienda.error
}
</script>

<template>
  <DialogoElegirTareas
    :abierto="props.abierto"
    :titulo="`Relacionar tareas con ${props.tarea.nombre}`"
    descripcion="Elige una o varias tareas. Cada una mostrará también esta tarea entre sus tareas relacionadas."
    etiqueta-lista="Tareas que se pueden relacionar"
    texto-accion="Relacionar"
    texto-sin-tareas="No quedan tareas por relacionar."
    :id-buscador="`buscar-vinculadas-${props.tarea.id}`"
    :tareas="disponibles"
    :confirmar="vincular"
    @update:abierto="emit('update:abierto', $event)"
  />
</template>
