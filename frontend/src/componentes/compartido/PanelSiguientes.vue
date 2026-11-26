<script setup lang="ts">
import { ChevronDown, ChevronUp, GripVertical, Search, X } from '@lucide/vue'
import { createReusableTemplate, useMediaQuery } from '@vueuse/core'
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import BotonFoco from '@/componentes/compartido/BotonFoco.vue'
import BotonSiguientes from '@/componentes/compartido/BotonSiguientes.vue'
import ContadorVencimiento from '@/componentes/compartido/ContadorVencimiento.vue'
import SelectorTareasSiguientes from '@/componentes/compartido/SelectorTareasSiguientes.vue'
import VencimientoCorto from '@/componentes/compartido/VencimientoCorto.vue'
import { Button } from '@/componentes/ui/button'
import { useArrastrarCola } from '@/composables/useArrastrarCola'
import type { Tarea } from '@/api/tipos'
import {
  BORDE_PRIORIDAD,
  CLASE_PILDORA,
  PILDORA_PRIORIDAD,
  clavePrioridad,
} from '@/lib/coloresTarea'
import { estaHibernada, instanteCongelado } from '@/lib/hibernacion'
import { sugerenciasSiguientes } from '@/lib/sugerenciasSiguientes'
import { useTiendaFoco } from '@/stores/foco'
import { useTiendaSiguientes } from '@/stores/siguientes'
import { useTiendaTareas } from '@/stores/tareas'

// Inicio: "A continuación" y "Sugerencias", con tarjetas como las del
// tablero (borde con el color de la prioridad, píldora de prioridad, fecha y
// cuenta atrás). Panel "A continuación": la cola de siguientes, en orden, con
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

// "Buscar tareas" abre el buscador para añadir varias a la cola.
const buscadorAbierto = ref(false)

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

// Tarjeta de una tarea: la del tablero, con el borde izquierdo del color de su
// prioridad (gris claro si no tiene o aún no se han cargado las tareas).
function claseTarjeta(tarea: Tarea | undefined): string {
  return `bg-card text-card-foreground relative rounded-lg border border-l-4 p-3 shadow-xs ${
    BORDE_PRIORIDAD[clavePrioridad(tarea?.prioridad ?? null)]
  }`
}

function clasePildoraPrioridad(prioridad: number): string {
  const clave = clavePrioridad(prioridad)
  return `${CLASE_PILDORA} ${clave === 'sin' ? 'bg-muted text-muted-foreground' : PILDORA_PRIORIDAD[clave]}`
}

const CLASE_TITULO = 'text-base font-semibold'
const CLASE_CRITERIO = 'text-muted-foreground text-sm'

const CLASE_ENLACE =
  'block min-w-0 truncate rounded-sm text-sm font-medium outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50'

onMounted(() => {
  void tiendaSiguientes.cargar()
  void tiendaTareas.cargar()
})
</script>

<template>
  <plantillaDatos v-slot="{ tarea }">
    <span class="text-muted-foreground mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
      <span
        v-if="tarea.prioridad !== null"
        data-prioridad-sugerencia
        :class="clasePildoraPrioridad(tarea.prioridad)"
        >Prioridad {{ tarea.prioridad }}</span
      >
      <span v-if="tarea.fecha_vencimiento" class="flex flex-wrap items-center gap-x-2">
        <span class="sr-only">{{ 'Vencimiento: ' }}</span>
        <VencimientoCorto
          :vencimiento="tarea.fecha_vencimiento"
          :completada="tarea.completada"
          :congelada-en="instanteCongelado(tarea)"
          class="text-foreground"
        />
        <ContadorVencimiento
          :vencimiento="tarea.fecha_vencimiento"
          :congelada-en="instanteCongelado(tarea)"
          :hibernada="estaHibernada(tarea)"
        />
      </span>
      <span v-else data-sin-vencimiento>Sin vencimiento</span>
    </span>
  </plantillaDatos>

  <div class="grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
    <section
      data-panel-siguientes
      aria-labelledby="titulo-siguientes"
      class="grid min-w-0 grid-cols-1 gap-3"
    >
      <div>
        <div class="flex items-center justify-between gap-2">
          <h3 id="titulo-siguientes" :class="CLASE_TITULO">A continuación</h3>
          <Button
            type="button"
            variant="outline"
            size="sm"
            data-buscar-siguientes
            @click="buscadorAbierto = true"
          >
            <Search aria-hidden="true" />Buscar tareas
          </Button>
        </div>
        <p data-criterio-cola :class="CLASE_CRITERIO">
          Las tareas que has elegido, en el orden en que quieres abordarlas: añádelas con «Añadir a
          siguientes» o «Buscar tareas» y ordénalas arrastrándolas o con las flechas. Al ponerlas en
          foco salen de la cola.
        </p>
      </div>
      <p v-if="tiendaSiguientes.error" class="text-destructive text-sm" role="alert">
        {{ tiendaSiguientes.error }}
      </p>

      <p
        v-if="tiendaSiguientes.cola.length === 0"
        class="text-muted-foreground rounded-lg border border-dashed p-4 text-center text-sm"
      >
        No hay tareas en la cola.
      </p>
      <ol v-else class="grid min-w-0 grid-cols-1 gap-2">
        <li
          v-for="(entrada, indice) in tiendaSiguientes.cola"
          :key="entrada.tarea_id"
          data-fila-siguiente
          draggable="true"
          :data-destino="arrastre.destino(indice)"
          :data-arrastrada="arrastre.arrastrada(indice) || undefined"
          :class="[
            claseTarjeta(tareaPorId.get(entrada.tarea_id)),
            'flex flex-wrap items-center gap-1',
            arrastre.arrastrada(indice) && 'opacity-50',
            arrastre.destino(indice) === 'antes' &&
              'after:bg-primary after:absolute after:inset-x-0 after:-top-[5px] after:h-0.5 after:rounded-full',
            arrastre.destino(indice) === 'despues' &&
              'after:bg-primary after:absolute after:inset-x-0 after:-bottom-[5px] after:h-0.5 after:rounded-full',
          ]"
          v-on="arrastre.eventos(indice)"
        >
          <span
            class="text-muted-foreground flex w-8 shrink-0 cursor-grab items-center text-sm tabular-nums"
            title="Arrastra para reordenar"
            ><GripVertical class="size-3.5 shrink-0" aria-hidden="true" />{{ indice + 1 }}.</span
          >
          <!-- En pantallas estrechas los botones bajan a una segunda línea. -->
          <div class="min-w-0 flex-1 max-sm:basis-[calc(100%-2.5rem)]">
            <RouterLink :to="enlace(entrada.tarea_id)" :class="CLASE_ENLACE" draggable="false">{{
              entrada.tarea_nombre
            }}</RouterLink>
            <usarDatos
              v-if="tareaPorId.get(entrada.tarea_id)"
              :tarea="tareaPorId.get(entrada.tarea_id)!"
            />
          </div>
          <span class="flex shrink-0 items-center max-sm:ml-auto">
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
          </span>
        </li>
      </ol>
      <SelectorTareasSiguientes v-model:abierto="buscadorAbierto" />
    </section>

    <section
      data-sugerencias
      aria-labelledby="titulo-sugerencias"
      class="grid min-w-0 grid-cols-1 gap-3"
    >
      <div>
        <h3 id="titulo-sugerencias" :class="CLASE_TITULO">Sugerencias</h3>
        <p data-criterio-sugerencias :class="CLASE_CRITERIO">
          Tareas pendientes que vencen antes; a igual vencimiento, por prioridad y después por
          antigüedad. No incluye las hibernadas, las que están en DONE, las de la cola ni la que
          está en foco.
        </p>
      </div>
      <p
        v-if="sugerencias.length === 0"
        class="text-muted-foreground rounded-lg border border-dashed p-4 text-center text-sm"
      >
        No hay sugerencias.
      </p>
      <ul v-else class="grid min-w-0 grid-cols-1 gap-2">
        <li
          v-for="tarea in sugerencias"
          :key="tarea.id"
          data-sugerencia
          :class="[claseTarjeta(tarea), 'flex items-center gap-2']"
        >
          <div class="min-w-0 flex-1">
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
  </div>
</template>
