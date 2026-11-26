<script setup lang="ts">
import { computed, watch } from 'vue'

import DialogoElegirTareas from '@/componentes/compartido/DialogoElegirTareas.vue'
import { useTiendaSiguientes } from '@/stores/siguientes'
import { useTiendaTareas } from '@/stores/tareas'

// Buscador para añadir una o varias tareas a la cola de "A continuación":
// ofrece las pendientes que aún no están en la cola y "Añadir (n)" las pone al
// final, en el orden en que se marcaron (ver `DialogoElegirTareas`). Como se
// abre también desde la barra superior, en cualquier página, si las tareas no
// están cargadas las pide al abrirse.
const props = defineProps<{ abierto: boolean }>()
const emit = defineEmits<{ 'update:abierto': [abierto: boolean] }>()

const tiendaTareas = useTiendaTareas()
const tiendaSiguientes = useTiendaSiguientes()

watch(
  () => props.abierto,
  (abierto) => {
    if (abierto && tiendaTareas.tareas.length === 0) void tiendaTareas.cargar()
  },
  { immediate: true },
)

const disponibles = computed(() =>
  tiendaTareas.tareas.filter(
    (tarea) => !tarea.completada && !tiendaSiguientes.estaEnCola(tarea.id),
  ),
)

async function anadir(ids: number[]): Promise<string | null> {
  return (await tiendaSiguientes.anadirVarias(ids)) ? null : tiendaSiguientes.error
}
</script>

<template>
  <DialogoElegirTareas
    :abierto="props.abierto"
    titulo="Añadir a siguientes"
    descripcion="Elige una o varias tareas. Se añadirán al final de la cola, en el orden en que las marques."
    etiqueta-lista="Tareas que se pueden añadir"
    texto-accion="Añadir"
    texto-sin-tareas="No quedan tareas por añadir."
    id-buscador="buscar-siguientes"
    :tareas="disponibles"
    :confirmar="anadir"
    @update:abierto="emit('update:abierto', $event)"
  />
</template>
