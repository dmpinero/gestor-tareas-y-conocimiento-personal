<script setup lang="ts">
import { ChevronDown, ChevronUp, X } from '@lucide/vue'
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'

import BotonFoco from '@/componentes/compartido/BotonFoco.vue'
import BotonSiguientes from '@/componentes/compartido/BotonSiguientes.vue'
import { Button } from '@/componentes/ui/button'
import { sugerenciasSiguientes } from '@/lib/sugerenciasSiguientes'
import { useTiendaFoco } from '@/stores/foco'
import { useTiendaSiguientes } from '@/stores/siguientes'
import { useTiendaTareas } from '@/stores/tareas'

// Panel "A continuación" de Inicio: la cola de siguientes, en orden, con
// "Trabajar en esta", subir, bajar y quitar en cada fila; debajo, sugerencias
// calculadas con las tareas cargadas (ver `sugerenciasSiguientes`) para
// añadirlas al final de la cola. Al montarse carga la cola y las tareas.
const tiendaSiguientes = useTiendaSiguientes()
const tiendaTareas = useTiendaTareas()
const tiendaFoco = useTiendaFoco()

const sugerencias = computed(() =>
  sugerenciasSiguientes(
    tiendaTareas.tareas,
    tiendaSiguientes.cola.map((entrada) => entrada.tarea_id),
    tiendaFoco.foco?.tarea_id ?? null,
  ),
)

function enlace(tareaId: number) {
  return { path: '/tareas', query: { tarea: String(tareaId) } }
}

const CLASE_ENLACE =
  'min-w-0 flex-1 truncate rounded-sm font-medium outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50'

onMounted(() => {
  void tiendaSiguientes.cargar()
  void tiendaTareas.cargar()
})
</script>

<template>
  <section data-panel-siguientes aria-labelledby="titulo-siguientes" class="rounded-lg border p-4">
    <h3 id="titulo-siguientes" class="text-lg font-semibold">A continuación</h3>
    <p v-if="tiendaSiguientes.error" class="text-destructive mt-2 text-sm" role="alert">
      {{ tiendaSiguientes.error }}
    </p>

    <p v-if="tiendaSiguientes.cola.length === 0" class="text-muted-foreground mt-2 text-sm">
      No hay tareas en la cola.
    </p>
    <ol v-else class="mt-2 divide-y">
      <li
        v-for="(entrada, indice) in tiendaSiguientes.cola"
        :key="entrada.tarea_id"
        data-fila-siguiente
        class="flex items-center gap-1 py-1"
      >
        <span class="text-muted-foreground w-6 shrink-0 text-right text-sm tabular-nums"
          >{{ indice + 1 }}.</span
        >
        <RouterLink :to="enlace(entrada.tarea_id)" :class="CLASE_ENLACE">{{
          entrada.tarea_nombre
        }}</RouterLink>
        <BotonFoco :tarea-id="entrada.tarea_id" :nombre="entrada.tarea_nombre" compacto />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          class="text-muted-foreground size-8"
          :aria-label="`Subir ${entrada.tarea_nombre}`"
          title="Subir"
          :disabled="indice === 0"
          @click="tiendaSiguientes.subir(entrada.tarea_id)"
        >
          <ChevronUp aria-hidden="true" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          class="text-muted-foreground size-8"
          :aria-label="`Bajar ${entrada.tarea_nombre}`"
          title="Bajar"
          :disabled="indice === tiendaSiguientes.cola.length - 1"
          @click="tiendaSiguientes.bajar(entrada.tarea_id)"
        >
          <ChevronDown aria-hidden="true" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          class="text-muted-foreground size-8"
          :aria-label="`Quitar ${entrada.tarea_nombre} de siguientes`"
          title="Quitar de siguientes"
          @click="tiendaSiguientes.quitar(entrada.tarea_id)"
        >
          <X aria-hidden="true" />
        </Button>
      </li>
    </ol>

    <h4 class="mt-4 text-sm font-semibold">Sugerencias</h4>
    <p v-if="sugerencias.length === 0" class="text-muted-foreground mt-2 text-sm">
      No hay sugerencias.
    </p>
    <ul v-else class="mt-2 divide-y">
      <li
        v-for="tarea in sugerencias"
        :key="tarea.id"
        data-sugerencia
        class="flex flex-wrap items-center gap-2 py-1"
      >
        <RouterLink :to="enlace(tarea.id)" :class="CLASE_ENLACE">{{ tarea.nombre }}</RouterLink>
        <BotonSiguientes :tarea-id="tarea.id" :nombre="tarea.nombre" />
      </li>
    </ul>
  </section>
</template>
