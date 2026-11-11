<script setup lang="ts">
import { MoveRight, Plus } from '@lucide/vue'
import { computed, nextTick, ref } from 'vue'
import { RouterLink } from 'vue-router'

import type { EstadoGrupo, GrupoEstados, Tarea } from '@/api/tipos'
import ContadorVencimiento from '@/componentes/compartido/ContadorVencimiento.vue'
import { Button } from '@/componentes/ui/button'
import { Label } from '@/componentes/ui/label'
import { Popover, PopoverContent, PopoverTrigger } from '@/componentes/ui/popover'
import { formatearFechaHora } from '@/lib/fechas'
import { useTiendaTareas } from '@/stores/tareas'

// Tablero de las tareas de un grupo de estados: una columna por estado, en el
// orden de Ajustes. `tareas` llega ya filtrada y ordenada por quien lo usa.
// Las tarjetas se mueven arrastrándolas o con "Mover a…" (teclado y lectores
// de pantalla); se guarda con `PATCH /tareas/{id}/estado` y la tarjeta se
// recoloca con la respuesta. Abrir el detalle y el alta son cosa del padre.
const props = defineProps<{
  tareas: Tarea[]
  grupos: GrupoEstados[]
  cargandoGrupos?: boolean
}>()
const idGrupo = defineModel<number | null>('idGrupo', { required: true })
const emit = defineEmits<{
  verDetalle: [id: number]
  anadirTarea: [idGrupo: number, idEstado: number]
}>()

const tienda = useTiendaTareas()

// Si el grupo recordado ya no existe, se usa el primero.
const grupoActivo = computed<GrupoEstados | null>(
  () => props.grupos.find((grupo) => grupo.id === idGrupo.value) ?? props.grupos[0] ?? null,
)

const seleccionGrupo = computed<number | null>({
  get: () => grupoActivo.value?.id ?? null,
  set: (id) => {
    idGrupo.value = id
  },
})

const tareasDelGrupo = computed(() =>
  props.tareas.filter((tarea) => tarea.grupo_estados?.id === grupoActivo.value?.id),
)

function tareasEn(estado: EstadoGrupo): Tarea[] {
  return tareasDelGrupo.value.filter((tarea) => tarea.estado?.id === estado.id)
}

function otrosEstados(tarea: Tarea): EstadoGrupo[] {
  return (grupoActivo.value?.estados ?? []).filter((estado) => estado.id !== tarea.estado?.id)
}

function textoTareas(total: number): string {
  return total === 1 ? '1 tarea' : `${total} tareas`
}

function idBotonMover(tarea: Tarea): string {
  return `mover-tarea-${tarea.id}`
}

// --- Mover -----------------------------------------------------------------
const idMenuAbierto = ref<number | null>(null)
const anuncio = ref('')
// Mientras se mueve una tarjeta, el menú no devuelve el foco a su botón: la
// tarjeta cambia de columna y el foco se lleva al botón de la tarjeta nueva.
let moviendo = false

function alCambiarMenu(tarea: Tarea, abierto: boolean): void {
  idMenuAbierto.value = abierto ? tarea.id : null
}

function alDevolverFocoMenu(evento: Event): void {
  if (moviendo) evento.preventDefault()
}

async function mover(tarea: Tarea, estado: EstadoGrupo): Promise<void> {
  moviendo = true
  idMenuAbierto.value = null
  anuncio.value = ''
  const correcto = await tienda.cambiarEstadoTarea(tarea.id, estado.id)
  if (correcto) anuncio.value = `${tarea.nombre} movida a ${estado.nombre}`
  await nextTick()
  // Tanto si se movió como si no, el foco queda en "Mover a…" de la tarjeta.
  document.getElementById(idBotonMover(tarea))?.focus()
  moviendo = false
}

// --- Arrastrar y soltar ------------------------------------------------------
const idArrastrada = ref<number | null>(null)
const idColumnaDestino = ref<number | null>(null)

function alEmpezarArrastre(evento: DragEvent, tarea: Tarea): void {
  idArrastrada.value = tarea.id
  if (evento.dataTransfer) {
    evento.dataTransfer.effectAllowed = 'move'
    evento.dataTransfer.setData('text/plain', String(tarea.id))
  }
}

function alArrastrarSobre(evento: DragEvent, estado: EstadoGrupo): void {
  if (idArrastrada.value === null) return
  evento.preventDefault()
  if (evento.dataTransfer) evento.dataTransfer.dropEffect = 'move'
  idColumnaDestino.value = estado.id
}

function alSalirDeColumna(evento: DragEvent, estado: EstadoGrupo): void {
  // Pasar sobre una tarjeta de la misma columna también lanza `dragleave`.
  const destino = evento.relatedTarget as Node | null
  if (destino && (evento.currentTarget as HTMLElement).contains(destino)) return
  if (idColumnaDestino.value === estado.id) idColumnaDestino.value = null
}

function alSoltar(evento: DragEvent, estado: EstadoGrupo): void {
  evento.preventDefault()
  const tarea = tareasDelGrupo.value.find((t) => t.id === idArrastrada.value)
  terminarArrastre()
  if (tarea && tarea.estado?.id !== estado.id) void mover(tarea, estado)
}

function terminarArrastre(): void {
  idArrastrada.value = null
  idColumnaDestino.value = null
}
</script>

<template>
  <div class="mt-4 flex min-w-0 flex-col gap-4">
    <p
      v-if="!props.cargandoGrupos && props.grupos.length === 0"
      class="text-muted-foreground text-sm"
    >
      Todavía no hay grupos de estados.
      <RouterLink to="/ajustes/grupos-estados" class="text-primary underline underline-offset-4"
        >Crea un grupo de estados en Ajustes</RouterLink
      >
      para ver las tareas en el tablero.
    </p>

    <template v-else-if="grupoActivo">
      <div class="flex max-w-xs flex-col gap-1.5">
        <Label for="tablero-grupo">Grupo del tablero</Label>
        <select
          id="tablero-grupo"
          v-model="seleccionGrupo"
          class="border-input dark:bg-input/30 bg-background focus-visible:border-ring focus-visible:ring-ring/50 h-9 w-full rounded-md border px-3 py-1 text-base shadow-xs outline-none focus-visible:ring-[3px] md:text-sm"
        >
          <option v-for="grupo in props.grupos" :key="grupo.id" :value="grupo.id">
            {{ grupo.nombre }}
          </option>
        </select>
      </div>

      <p v-if="grupoActivo.estados.length === 0" class="text-muted-foreground text-sm">
        Este grupo no tiene estados. Añádelos en
        <RouterLink to="/ajustes/grupos-estados" class="text-primary underline underline-offset-4"
          >Ajustes</RouterLink
        >.
      </p>
      <template v-else>
        <p v-if="tareasDelGrupo.length === 0" class="text-muted-foreground text-sm">
          No hay tareas en este grupo.
        </p>

        <!-- Las columnas desplazan en horizontal dentro de su contenedor, sin
             desbordar la página en pantallas estrechas. -->
        <div class="flex max-w-full gap-3 overflow-x-auto pb-2">
          <section
            v-for="estado in grupoActivo.estados"
            :key="estado.id"
            :aria-label="`Estado ${estado.nombre}`"
            :data-destino="idColumnaDestino === estado.id ? 'true' : undefined"
            :class="[
              'bg-muted/40 flex w-72 shrink-0 flex-col gap-2 rounded-lg border p-2',
              idColumnaDestino === estado.id && 'border-primary ring-primary ring-2',
            ]"
            @dragover="alArrastrarSobre($event, estado)"
            @dragleave="alSalirDeColumna($event, estado)"
            @drop="alSoltar($event, estado)"
          >
            <h3 class="flex items-center gap-2 px-1 text-sm font-semibold">
              <span class="min-w-0 [overflow-wrap:anywhere]">{{ estado.nombre }}</span>
              <span
                data-contador
                aria-hidden="true"
                class="bg-background text-muted-foreground rounded-full border px-2 text-xs"
                >{{ tareasEn(estado).length }}</span
              >
              <span class="sr-only">{{ ` (${textoTareas(tareasEn(estado).length)})` }}</span>
            </h3>

            <ul :aria-label="`Tareas en ${estado.nombre}`" class="flex flex-col gap-2">
              <li
                v-for="tarea in tareasEn(estado)"
                :key="tarea.id"
                data-tarjeta
                draggable="true"
                :class="[
                  'bg-background relative flex flex-col gap-2 rounded-md border p-3 shadow-xs',
                  idArrastrada === tarea.id && 'opacity-50',
                ]"
                @dragstart="alEmpezarArrastre($event, tarea)"
                @dragend="terminarArrastre"
              >
                <button
                  type="button"
                  data-nombre-tarjeta
                  class="focus-visible:ring-ring/50 line-clamp-2 rounded-sm text-left text-sm font-medium outline-none [overflow-wrap:anywhere] hover:underline focus-visible:ring-[3px]"
                  :class="tarea.completada ? 'line-through' : ''"
                  @click="emit('verDetalle', tarea.id)"
                >
                  {{ tarea.nombre }}
                </button>

                <p
                  v-if="tarea.asignados.length > 0"
                  class="text-muted-foreground text-xs [overflow-wrap:anywhere]"
                >
                  <span class="sr-only">{{ 'Asignado a: ' }}</span
                  >{{ tarea.asignados.join(', ') }}
                </p>

                <p v-if="tarea.fecha_vencimiento" class="text-xs">
                  <span class="sr-only">{{ 'Vencimiento: ' }}</span
                  >{{ formatearFechaHora(tarea.fecha_vencimiento) }}
                  <ContadorVencimiento :vencimiento="tarea.fecha_vencimiento" class="block" />
                </p>

                <ul
                  v-if="tarea.etiquetas.length > 0"
                  aria-label="Etiquetas"
                  class="flex flex-wrap gap-1"
                >
                  <li
                    v-for="etiqueta in tarea.etiquetas"
                    :key="etiqueta"
                    class="bg-secondary text-secondary-foreground inline-flex max-w-full rounded-md border px-2 py-0.5 text-xs font-medium [overflow-wrap:anywhere]"
                  >
                    {{ etiqueta }}
                  </li>
                </ul>

                <Popover
                  :open="idMenuAbierto === tarea.id"
                  @update:open="(abierto: boolean) => alCambiarMenu(tarea, abierto)"
                >
                  <PopoverTrigger as-child>
                    <Button
                      :id="idBotonMover(tarea)"
                      type="button"
                      variant="outline"
                      size="sm"
                      class="self-start"
                      :aria-label="`Mover a… (${tarea.nombre})`"
                    >
                      <MoveRight aria-hidden="true" />
                      Mover a…
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent
                    align="start"
                    class="w-56 p-2"
                    data-menu-mover
                    @close-auto-focus="alDevolverFocoMenu"
                  >
                    <p :id="`menu-mover-${tarea.id}`" class="px-2 py-1 text-sm font-medium">
                      Mover a
                    </p>
                    <ul
                      v-if="otrosEstados(tarea).length > 0"
                      :aria-labelledby="`menu-mover-${tarea.id}`"
                      class="flex flex-col"
                    >
                      <li v-for="destino in otrosEstados(tarea)" :key="destino.id">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          class="w-full justify-start"
                          @click="mover(tarea, destino)"
                          >{{ destino.nombre }}</Button
                        >
                      </li>
                    </ul>
                    <p v-else class="text-muted-foreground px-2 py-1 text-sm">
                      No hay otros estados en el grupo.
                    </p>
                  </PopoverContent>
                </Popover>
              </li>
            </ul>

            <Button
              type="button"
              variant="ghost"
              size="sm"
              class="justify-start"
              :aria-label="`Añadir tarea en ${estado.nombre}`"
              @click="emit('anadirTarea', grupoActivo.id, estado.id)"
            >
              <Plus aria-hidden="true" />
              Añadir tarea
            </Button>
          </section>
        </div>
      </template>
    </template>

    <p class="sr-only" aria-live="polite" data-anuncio-tablero>{{ anuncio }}</p>
  </div>
</template>
