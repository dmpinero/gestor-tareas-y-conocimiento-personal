<script setup lang="ts">
import { Link2, X } from '@lucide/vue'
import { computed, ref } from 'vue'

import type { Tarea } from '@/api/tipos'
import SelectorTareasVinculadas from '@/componentes/compartido/SelectorTareasVinculadas.vue'
import { Button } from '@/componentes/ui/button'
import { useTiendaTareas } from '@/stores/tareas'

// "Tareas relacionadas" del detalle: las tareas vinculadas con `tarea` (la
// relación es simétrica). Cada nombre es un botón que emite `verTarea` para
// abrir su detalle; las completadas van tachadas. Junto a cada una, "Quitar
// relación" deshace el vínculo en ambos sentidos. "Relacionar tareas" abre el
// selector para vincular una o varias más. Los nombres salen del almacén de
// tareas; un fallo al quitar queda en `tienda.error`, que muestra el detalle.
const props = defineProps<{ tarea: Tarea }>()
const emit = defineEmits<{ verTarea: [id: number] }>()

const tienda = useTiendaTareas()
const selectorAbierto = ref(false)
const idTitulo = computed(() => `tareas-vinculadas-${props.tarea.id}-titulo`)

const vinculadas = computed(() =>
  props.tarea.vinculadas
    .map((id) => tienda.tareas.find((otra) => otra.id === id))
    .filter((otra): otra is Tarea => otra !== undefined),
)

function quitar(otra: Tarea): void {
  void tienda.desvincularTarea(props.tarea.id, otra.id)
}
</script>

<template>
  <section data-testid="tareas-vinculadas" :aria-labelledby="idTitulo" class="flex flex-col gap-3">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h3 :id="idTitulo" class="text-base font-semibold">Tareas relacionadas</h3>
      <Button type="button" variant="outline" size="sm" @click="selectorAbierto = true">
        <Link2 aria-hidden="true" />
        Relacionar tareas
      </Button>
    </div>

    <ul v-if="vinculadas.length > 0" class="flex flex-col gap-1">
      <li v-for="otra in vinculadas" :key="otra.id" class="flex items-center gap-2">
        <button
          type="button"
          data-vinculada
          class="focus-visible:ring-ring/50 min-w-0 flex-1 rounded-sm px-1 py-0.5 text-left text-sm underline-offset-4 outline-none hover:underline focus-visible:ring-[3px] [overflow-wrap:anywhere]"
          @click="emit('verTarea', otra.id)"
        >
          <span :class="otra.completada ? 'text-muted-foreground line-through' : ''">{{
            otra.nombre
          }}</span>
          <span v-if="otra.completada" class="sr-only"> (completada)</span>
        </button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          class="text-muted-foreground size-8 shrink-0"
          :aria-label="`Quitar relación con ${otra.nombre}`"
          title="Quitar relación"
          @click="quitar(otra)"
        >
          <X aria-hidden="true" />
        </Button>
      </li>
    </ul>
    <p v-else class="text-muted-foreground text-sm">Esta tarea no tiene tareas relacionadas.</p>

    <SelectorTareasVinculadas v-model:abierto="selectorAbierto" :tarea="props.tarea" />
  </section>
</template>
