<script setup lang="ts">
import { computed, watch } from 'vue'

import type { ClaveEntradaSiguiente } from '@/api/tipos'
import DialogoElegirTareas, {
  type AccionEleccion,
  type ElementoEleccion,
} from '@/componentes/compartido/DialogoElegirTareas.vue'
import { textoTareaYSubtarea } from '@/lib/foco'
import { useTiendaSiguientes } from '@/stores/siguientes'
import { useTiendaTareas } from '@/stores/tareas'

// Buscador para añadir una o varias tareas o subtareas a "A continuación" (la
// cola de siguientes) o a las sugerencias elegidas, al final y en el orden en
// que se marcaron (ver `DialogoElegirTareas`). Ofrece las tareas pendientes y
// sus subtareas sin resolver, estas como «Tarea › Subtarea» (la búsqueda
// encuentra por el nombre de cualquiera de las dos). Las que ya están en una
// lista llevan una nota con cuál, y cada acción se salta las que ya están en su
// destino (añadir a una lista una que está en la otra la mueve). Como se abre
// también desde la barra superior, en cualquier página, si las tareas no están
// cargadas las pide al abrirse.
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

function nota(entrada: ClaveEntradaSiguiente): string | null {
  if (tiendaSiguientes.estaEnCola(entrada.tarea_id, entrada.subtarea_id)) {
    return 'En A continuación'
  }
  if (tiendaSiguientes.estaElegida(entrada.tarea_id, entrada.subtarea_id)) return 'En sugerencias'
  return null
}

function elemento(
  valor: ClaveEntradaSiguiente,
  tareaNombre: string,
  subtareaNombre: string | null,
): ElementoEleccion<ClaveEntradaSiguiente> {
  return {
    clave: `${valor.tarea_id}-${valor.subtarea_id ?? ''}`,
    valor,
    nombre: textoTareaYSubtarea(tareaNombre, subtareaNombre),
    nota: nota(valor),
  }
}

const elementos = computed(() =>
  tiendaTareas.tareas
    .filter((tarea) => !tarea.completada)
    .flatMap((tarea) => [
      elemento({ tarea_id: tarea.id, subtarea_id: null }, tarea.nombre, null),
      ...tarea.subtareas
        .filter((subtarea) => !subtarea.resuelta)
        .map((subtarea) =>
          elemento({ tarea_id: tarea.id, subtarea_id: subtarea.id }, tarea.nombre, subtarea.nombre),
        ),
    ]),
)

function resultado(bien: boolean): string | null {
  return bien ? null : tiendaSiguientes.error
}

const acciones: AccionEleccion<ClaveEntradaSiguiente>[] = [
  {
    clave: 'siguientes',
    texto: 'A continuación',
    yaIncluida: (entrada) => tiendaSiguientes.estaEnCola(entrada.tarea_id, entrada.subtarea_id),
    confirmar: async (entradas) => resultado(await tiendaSiguientes.anadirVarias(entradas)),
  },
  {
    clave: 'sugerencias',
    texto: 'Sugerencias',
    yaIncluida: (entrada) => tiendaSiguientes.estaElegida(entrada.tarea_id, entrada.subtarea_id),
    confirmar: async (entradas) => resultado(await tiendaSiguientes.anadirElegidas(entradas)),
  },
]
</script>

<template>
  <DialogoElegirTareas
    :abierto="props.abierto"
    titulo="Añadir a siguientes"
    descripcion="Elige una o varias tareas o subtareas y añádelas a «A continuación» o a «Sugerencias». Se añadirán al final, en el orden en que las marques."
    etiqueta-lista="Tareas que se pueden añadir"
    texto-sin-tareas="No quedan tareas por añadir."
    id-buscador="buscar-siguientes"
    :elementos="elementos"
    :acciones="acciones"
    @update:abierto="emit('update:abierto', $event)"
  />
</template>
