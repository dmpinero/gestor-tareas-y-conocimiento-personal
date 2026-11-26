<script setup lang="ts">
import { computed, watch } from 'vue'

import type { Tarea } from '@/api/tipos'
import DialogoElegirTareas, {
  type AccionEleccion,
} from '@/componentes/compartido/DialogoElegirTareas.vue'
import { useTiendaSiguientes } from '@/stores/siguientes'
import { useTiendaTareas } from '@/stores/tareas'

// Buscador para añadir una o varias tareas a "A continuación" (la cola de
// siguientes) o a las sugerencias elegidas, al final y en el orden en que se
// marcaron (ver `DialogoElegirTareas`). Ofrece todas las pendientes: las que
// ya están en una lista llevan una nota con cuál, y cada acción se salta las
// que ya están en su destino (añadir a una lista una que está en la otra la
// mueve). Como se abre también desde la barra superior, en cualquier página, si
// las tareas no están cargadas las pide al abrirse.
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

const disponibles = computed(() => tiendaTareas.tareas.filter((tarea) => !tarea.completada))

function nota(tarea: Tarea): string | null {
  if (tiendaSiguientes.estaEnCola(tarea.id)) return 'En A continuación'
  if (tiendaSiguientes.estaElegida(tarea.id)) return 'En sugerencias'
  return null
}

function resultado(bien: boolean): string | null {
  return bien ? null : tiendaSiguientes.error
}

const acciones: AccionEleccion[] = [
  {
    clave: 'siguientes',
    texto: 'A continuación',
    yaIncluida: (id) => tiendaSiguientes.estaEnCola(id),
    confirmar: async (ids) => resultado(await tiendaSiguientes.anadirVarias(ids)),
  },
  {
    clave: 'sugerencias',
    texto: 'Sugerencias',
    yaIncluida: (id) => tiendaSiguientes.estaElegida(id),
    confirmar: async (ids) => resultado(await tiendaSiguientes.anadirElegidas(ids)),
  },
]
</script>

<template>
  <DialogoElegirTareas
    :abierto="props.abierto"
    titulo="Añadir a siguientes"
    descripcion="Elige una o varias tareas y añádelas a «A continuación» o a «Sugerencias». Se añadirán al final, en el orden en que las marques."
    etiqueta-lista="Tareas que se pueden añadir"
    texto-sin-tareas="No quedan tareas por añadir."
    id-buscador="buscar-siguientes"
    :tareas="disponibles"
    :acciones="acciones"
    :nota="nota"
    @update:abierto="emit('update:abierto', $event)"
  />
</template>
