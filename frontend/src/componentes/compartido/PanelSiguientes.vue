<script setup lang="ts">
import { ChevronDown, ChevronUp, GripVertical, X } from '@lucide/vue'
import { createReusableTemplate, useMediaQuery } from '@vueuse/core'
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'

import BotonFoco from '@/componentes/compartido/BotonFoco.vue'
import BotonSiguientes from '@/componentes/compartido/BotonSiguientes.vue'
import ContadorVencimiento from '@/componentes/compartido/ContadorVencimiento.vue'
import { Button } from '@/componentes/ui/button'
import { useArrastrarCola } from '@/composables/useArrastrarCola'
import type { Tarea } from '@/api/tipos'
import { estaHibernada, instanteCongelado } from '@/lib/hibernacion'
import { sugerenciasSiguientes } from '@/lib/sugerenciasSiguientes'
import { useTiendaFoco } from '@/stores/foco'
import { useTiendaSiguientes } from '@/stores/siguientes'
import { useTiendaTareas } from '@/stores/tareas'

// Panel "A continuación" de Inicio: la cola de siguientes, en orden, con
// "Trabajar en esta", subir, bajar y quitar en cada fila; debajo, sugerencias
// calculadas con las tareas cargadas (ver `sugerenciasSiguientes`) para
// añadirlas al final de la cola, cada una con su cuenta atrás hasta el
// vencimiento y su prioridad, que son el porqué de su orden (el criterio se
// explica bajo el título). Al montarse carga la cola y las tareas.
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

// Las filas de la cola también se reordenan arrastrándolas con el ratón.
const arrastre = useArrastrarCola()

// Cuenta atrás (parada si la tarea está hibernada o en DONE) y prioridad, en
// las filas de la cola y en las sugerencias.
const [plantillaDatos, usarDatos] = createReusableTemplate<{ tarea: Tarea }>()

// Datos de cada tarea de la cola (las tareas pueden no haberse cargado aún).
const tareaPorId = computed(() => new Map(tiendaTareas.tareas.map((t) => [t.id, t])))

// En pantallas estrechas «Añadir a siguientes» queda en solo icono, para que
// quepa el nombre.
const ancha = useMediaQuery('(min-width: 640px)')

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
  <plantillaDatos v-slot="{ tarea }">
    <span class="flex flex-wrap items-center gap-x-3 text-sm">
      <ContadorVencimiento
        v-if="tarea.fecha_vencimiento"
        :vencimiento="tarea.fecha_vencimiento"
        :congelada-en="instanteCongelado(tarea)"
        :hibernada="estaHibernada(tarea)"
      />
      <span v-else data-sin-vencimiento class="text-muted-foreground">Sin vencimiento</span>
      <span v-if="tarea.prioridad !== null" data-prioridad-sugerencia class="text-muted-foreground"
        >Prioridad {{ tarea.prioridad }}</span
      >
    </span>
  </plantillaDatos>
  <section data-panel-siguientes aria-labelledby="titulo-siguientes" class="rounded-lg border p-4">
    <h3 id="titulo-siguientes" class="text-lg font-semibold">A continuación</h3>
    <p data-criterio-cola class="text-muted-foreground mt-1 text-xs">
      Las tareas que has elegido, en el orden en que quieres abordarlas: añádelas con «Añadir a
      siguientes» y ordénalas arrastrándolas o con las flechas. Al ponerlas en foco salen de la
      cola.
    </p>
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
        draggable="true"
        :data-destino="arrastre.destino(indice)"
        :data-arrastrada="arrastre.arrastrada(indice) || undefined"
        :class="[
          'flex flex-wrap items-center gap-1 border-y-2 border-y-transparent py-1.5',
          arrastre.arrastrada(indice) && 'opacity-50',
          arrastre.destino(indice) === 'antes' && 'border-t-primary',
          arrastre.destino(indice) === 'despues' && 'border-b-primary',
        ]"
        v-on="arrastre.eventos(indice)"
      >
        <span
          class="text-muted-foreground flex w-8 shrink-0 cursor-grab items-center justify-end text-sm tabular-nums"
          title="Arrastra para reordenar"
          ><GripVertical class="size-3.5 shrink-0" aria-hidden="true" />{{ indice + 1 }}.</span
        >
        <!-- En pantallas estrechas los botones bajan a una segunda línea. -->
        <div class="flex min-w-0 flex-1 flex-col max-sm:basis-[calc(100%-2.5rem)]">
          <RouterLink :to="enlace(entrada.tarea_id)" :class="CLASE_ENLACE" draggable="false">{{
            entrada.tarea_nombre
          }}</RouterLink>
          <usarDatos
            v-if="tareaPorId.get(entrada.tarea_id)"
            :tarea="tareaPorId.get(entrada.tarea_id)!"
          />
        </div>
        <BotonFoco
          class="max-sm:ml-auto"
          :tarea-id="entrada.tarea_id"
          :nombre="entrada.tarea_nombre"
          compacto
        />
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
    <p data-criterio-sugerencias class="text-muted-foreground mt-1 text-xs">
      Tareas pendientes que vencen antes; a igual vencimiento, por prioridad y después por
      antigüedad. No incluye las hibernadas, las que están en DONE, las de la cola ni la que está en
      foco.
    </p>
    <p v-if="sugerencias.length === 0" class="text-muted-foreground mt-2 text-sm">
      No hay sugerencias.
    </p>
    <ul v-else class="mt-2 divide-y">
      <li
        v-for="tarea in sugerencias"
        :key="tarea.id"
        data-sugerencia
        class="flex items-center gap-2 py-1.5"
      >
        <div class="flex min-w-0 flex-1 flex-col">
          <RouterLink :to="enlace(tarea.id)" :class="CLASE_ENLACE">{{ tarea.nombre }}</RouterLink>
          <usarDatos :tarea="tarea" />
        </div>
        <BotonSiguientes
          class="shrink-0"
          :tarea-id="tarea.id"
          :nombre="tarea.nombre"
          :compacto="!ancha"
        />
      </li>
    </ul>
  </section>
</template>
