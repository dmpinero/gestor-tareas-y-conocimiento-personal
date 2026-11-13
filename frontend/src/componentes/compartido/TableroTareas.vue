<script setup lang="ts">
import { ListTree, MessageSquare, MoveRight, Plus } from '@lucide/vue'
import { computed, nextTick, ref } from 'vue'
import { RouterLink } from 'vue-router'

import type { EstadoGrupo, GrupoEstados, Tarea } from '@/api/tipos'
import AvatarPersona from '@/componentes/compartido/AvatarPersona.vue'
import BarraEstados from '@/componentes/compartido/BarraEstados.vue'
import AvisoVencimiento from '@/componentes/compartido/AvisoVencimiento.vue'
import ContadorVencimiento from '@/componentes/compartido/ContadorVencimiento.vue'
import NombreRelacionado from '@/componentes/compartido/NombreRelacionado.vue'
import VencimientoCorto from '@/componentes/compartido/VencimientoCorto.vue'
import { Button } from '@/componentes/ui/button'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'
import { Popover, PopoverContent, PopoverTrigger } from '@/componentes/ui/popover'
import {
  CLASE_PILDORA,
  colorEstadoTablero,
  colorEtiqueta,
  type ColorEstadoTablero,
} from '@/lib/coloresTarea'
import { MAX_NOMBRE_SUBTAREA, validarNombreSubtarea } from '@/lib/subtareas'
import { useTiendaTareas } from '@/stores/tareas'

// Tablero de las tareas de un grupo de estados: una columna por estado, en el
// orden de Ajustes. `tareas` llega ya filtrada y ordenada por quien lo usa.
// Las tarjetas se mueven arrastrándolas o con "Mover a…" (teclado y lectores
// de pantalla); se guarda con `PATCH /tareas/{id}/estado` y la tarjeta se
// recoloca con la respuesta. Abrir el detalle y el alta son cosa del padre.
// Cada columna lleva una cabecera del color de su estado (por posición, como
// la píldora de la tabla) y una barra resume cuántas tareas hay en cada uno.
// Las subtareas se despliegan bajo su tarjeta, donde también se añaden.
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

function colorDe(estado: EstadoGrupo): ColorEstadoTablero {
  const estados = grupoActivo.value?.estados ?? []
  return colorEstadoTablero(
    estados.findIndex((e) => e.id === estado.id),
    estados.length,
  )
}

const estadosBarra = computed(() =>
  (grupoActivo.value?.estados ?? []).map((estado) => ({
    id: estado.id,
    nombre: estado.nombre,
    cantidad: tareasEn(estado).length,
    relleno: colorDe(estado).relleno,
  })),
)

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

// --- Subtareas bajo la tarjeta -------------------------------------------
// Se pueden desplegar las de varias tarjetas a la vez. El alta rápida (solo
// el nombre) es de una en una; tras guardar sigue abierta y vacía para
// encadenar otra. Los fallos de la API quedan en `tienda.error`, que muestra
// la vista.
const idsDesplegadas = ref(new Set<number>())
const idAltaAbierta = ref<number | null>(null)
const nombreNueva = ref('')
const errorNueva = ref<string | null>(null)
const guardandoNueva = ref(false)

function idPanelSubtareas(tarea: Tarea): string {
  return `subtareas-tablero-${tarea.id}`
}

function idCampoSubtarea(tarea: Tarea): string {
  return `nombre-subtarea-tablero-${tarea.id}`
}

function idBotonAgregar(tarea: Tarea): string {
  return `agregar-subtarea-tablero-${tarea.id}`
}

function alternarSubtareas(tarea: Tarea): void {
  if (idsDesplegadas.value.has(tarea.id)) {
    idsDesplegadas.value.delete(tarea.id)
    if (idAltaAbierta.value === tarea.id) idAltaAbierta.value = null
  } else {
    idsDesplegadas.value.add(tarea.id)
  }
}

async function enfocarCampoSubtarea(tarea: Tarea): Promise<void> {
  await nextTick()
  document.getElementById(idCampoSubtarea(tarea))?.focus()
}

async function abrirAltaSubtarea(tarea: Tarea): Promise<void> {
  nombreNueva.value = ''
  errorNueva.value = null
  idAltaAbierta.value = tarea.id
  await enfocarCampoSubtarea(tarea)
}

async function cancelarAltaSubtarea(tarea: Tarea): Promise<void> {
  idAltaAbierta.value = null
  errorNueva.value = null
  await nextTick()
  document.getElementById(idBotonAgregar(tarea))?.focus()
}

async function guardarSubtarea(tarea: Tarea): Promise<void> {
  if (guardandoNueva.value) return
  const resultado = validarNombreSubtarea(nombreNueva.value)
  if ('error' in resultado) {
    errorNueva.value = resultado.error
    return
  }
  errorNueva.value = null
  guardandoNueva.value = true
  try {
    // Si falla se conserva lo escrito.
    if (await tienda.crearSubtarea(tarea.id, { nombre: resultado.nombre })) {
      nombreNueva.value = ''
      await enfocarCampoSubtarea(tarea)
    }
  } finally {
    guardandoNueva.value = false
  }
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
      <div class="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div class="flex w-full max-w-xs flex-col gap-1.5">
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
        <div v-if="grupoActivo.estados.length > 0" class="w-full pb-3 sm:w-64">
          <BarraEstados :estados="estadosBarra" :titulo="grupoActivo.nombre" />
        </div>
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
             desbordar la página en pantallas estrechas. `relative` hace que los
             textos sr-only (posición absoluta) de las columnas se recorten aquí:
             sin él se posicionaban respecto a un antecesor fuera del scroll y
             ensanchaban la página. -->
        <div class="relative flex max-w-full items-start gap-3 overflow-x-auto pb-2">
          <section
            v-for="estado in grupoActivo.estados"
            :key="estado.id"
            :aria-label="`Estado ${estado.nombre}`"
            :data-destino="idColumnaDestino === estado.id ? 'true' : undefined"
            :class="[
              'bg-muted relative flex w-72 shrink-0 flex-col rounded-lg border',
              idColumnaDestino === estado.id && 'ring-primary ring-2',
            ]"
            @dragover="alArrastrarSobre($event, estado)"
            @dragleave="alSalirDeColumna($event, estado)"
            @drop="alSoltar($event, estado)"
          >
            <h3
              :class="[
                'flex items-center gap-2 rounded-t-lg px-3 py-2 text-sm font-semibold',
                colorDe(estado).cabecera,
              ]"
            >
              <span class="min-w-0 [overflow-wrap:anywhere]">{{ estado.nombre }}</span>
              <span data-contador aria-hidden="true" class="font-normal">{{
                tareasEn(estado).length
              }}</span>
              <span class="sr-only">{{ ` (${textoTareas(tareasEn(estado).length)})` }}</span>
            </h3>

            <div class="flex flex-col gap-2 p-2">
              <ul :aria-label="`Tareas en ${estado.nombre}`" class="flex flex-col gap-2">
                <li v-for="tarea in tareasEn(estado)" :key="tarea.id" class="flex flex-col">
                  <div
                    data-tarjeta
                    draggable="true"
                    :class="[
                      'bg-card text-card-foreground relative flex flex-col gap-2 rounded-lg border p-3 shadow-xs',
                      idArrastrada === tarea.id && 'opacity-50',
                    ]"
                    @dragstart="alEmpezarArrastre($event, tarea)"
                    @dragend="terminarArrastre"
                  >
                    <div class="flex items-start justify-between gap-2">
                      <button
                        type="button"
                        data-nombre-tarjeta
                        class="focus-visible:ring-ring/50 line-clamp-2 rounded-sm text-left text-sm font-medium outline-none [overflow-wrap:anywhere] hover:underline focus-visible:ring-[3px]"
                        :class="tarea.completada ? 'line-through' : ''"
                        @click="emit('verDetalle', tarea.id)"
                      >
                        {{ tarea.nombre }}
                      </button>
                      <AvisoVencimiento
                        class="mt-0.5"
                        :vencimiento="tarea.fecha_vencimiento"
                        :completada="tarea.completada"
                      />
                    </div>

                    <div
                      v-if="tarea.asignados.length > 0 || tarea.fecha_vencimiento"
                      class="text-muted-foreground flex flex-wrap items-center gap-x-3 gap-y-1 text-xs"
                    >
                      <ul
                        v-if="tarea.asignados.length > 0"
                        aria-label="Asignados"
                        class="flex -space-x-1.5"
                      >
                        <li v-for="persona in tarea.asignados" :key="persona" class="flex">
                          <NombreRelacionado tipo="persona" :nombre="persona" class="rounded-full">
                            <AvatarPersona :nombre="persona" />
                          </NombreRelacionado>
                        </li>
                      </ul>
                      <span
                        v-if="tarea.fecha_vencimiento"
                        class="flex flex-wrap items-center gap-x-2"
                      >
                        <span class="sr-only">{{ 'Vencimiento: ' }}</span>
                        <VencimientoCorto
                          :vencimiento="tarea.fecha_vencimiento"
                          :completada="tarea.completada"
                          class="text-foreground"
                        />
                        <ContadorVencimiento :vencimiento="tarea.fecha_vencimiento" />
                      </span>
                    </div>

                    <ul
                      v-if="tarea.etiquetas.length > 0"
                      aria-label="Etiquetas"
                      class="flex flex-wrap gap-1"
                    >
                      <li
                        v-for="etiqueta in tarea.etiquetas"
                        :key="etiqueta"
                        :class="`${CLASE_PILDORA} ${colorEtiqueta(etiqueta)} [overflow-wrap:anywhere]`"
                      >
                        <NombreRelacionado tipo="etiqueta" :nombre="etiqueta" />
                      </li>
                    </ul>

                    <div class="-mx-1 -mb-1 flex items-center gap-1">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        class="text-muted-foreground size-8"
                        :aria-label="`Comentarios de ${tarea.nombre}`"
                        :title="`Comentarios de ${tarea.nombre}`"
                        @click="emit('verDetalle', tarea.id)"
                      >
                        <MessageSquare aria-hidden="true" />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        class="text-muted-foreground gap-1 px-2"
                        :aria-label="`${tarea.subtareas.length} subtareas de ${tarea.nombre}`"
                        :title="`${tarea.subtareas.length} subtareas de ${tarea.nombre}`"
                        :aria-expanded="idsDesplegadas.has(tarea.id)"
                        :aria-controls="
                          idsDesplegadas.has(tarea.id) ? idPanelSubtareas(tarea) : undefined
                        "
                        @click="alternarSubtareas(tarea)"
                      >
                        {{ tarea.subtareas.length }}
                        <ListTree aria-hidden="true" />
                      </Button>

                      <Popover
                        :open="idMenuAbierto === tarea.id"
                        @update:open="(abierto: boolean) => alCambiarMenu(tarea, abierto)"
                      >
                        <PopoverTrigger as-child>
                          <Button
                            :id="idBotonMover(tarea)"
                            type="button"
                            variant="ghost"
                            size="sm"
                            class="text-muted-foreground ml-auto px-2"
                            :aria-label="`Mover a… (${tarea.nombre})`"
                          >
                            <MoveRight aria-hidden="true" />
                            Mover a…
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent
                          align="end"
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
                    </div>
                  </div>

                  <!-- Subtareas: tarjetas sangradas bajo la tarea, unidas por
                       una línea que baja desde la tarjeta. -->
                  <div
                    v-if="idsDesplegadas.has(tarea.id)"
                    :id="idPanelSubtareas(tarea)"
                    class="border-border ml-4 flex flex-col gap-1.5 border-l-2 pt-1.5 pl-3"
                  >
                    <ul
                      v-if="tarea.subtareas.length > 0"
                      :aria-label="`Subtareas de ${tarea.nombre}`"
                      class="flex flex-col gap-1.5"
                    >
                      <li
                        v-for="subtarea in tarea.subtareas"
                        :key="subtarea.id"
                        class="before:border-border relative before:absolute before:top-1/2 before:-left-3 before:w-3 before:border-t-2"
                      >
                        <div
                          class="bg-card text-card-foreground flex items-center gap-2 rounded-md border px-2.5 py-1.5 shadow-xs"
                        >
                          <button
                            type="button"
                            data-nombre-subtarea
                            class="focus-visible:ring-ring/50 min-w-0 flex-1 rounded-sm text-left text-sm outline-none [overflow-wrap:anywhere] hover:underline focus-visible:ring-[3px]"
                            :class="subtarea.resuelta ? 'text-muted-foreground line-through' : ''"
                            @click="emit('verDetalle', tarea.id)"
                          >
                            {{ subtarea.nombre
                            }}<span v-if="subtarea.resuelta" class="sr-only">{{
                              ' (resuelta)'
                            }}</span>
                          </button>
                          <NombreRelacionado
                            v-if="subtarea.asignado"
                            tipo="persona"
                            :nombre="subtarea.asignado"
                            class="rounded-full"
                          >
                            <AvatarPersona :nombre="subtarea.asignado" />
                          </NombreRelacionado>
                        </div>
                      </li>
                    </ul>

                    <form
                      v-if="idAltaAbierta === tarea.id"
                      class="flex flex-col gap-1.5"
                      novalidate
                      @submit.prevent="guardarSubtarea(tarea)"
                    >
                      <Label :for="idCampoSubtarea(tarea)" class="sr-only"
                        >Nombre de la subtarea</Label
                      >
                      <Input
                        :id="idCampoSubtarea(tarea)"
                        v-model="nombreNueva"
                        name="nombre-subtarea"
                        placeholder="Nombre de la subtarea"
                        autocomplete="off"
                        :maxlength="MAX_NOMBRE_SUBTAREA"
                        :aria-invalid="errorNueva ? 'true' : undefined"
                        :aria-describedby="
                          errorNueva ? `${idCampoSubtarea(tarea)}-error` : undefined
                        "
                        class="bg-card h-8"
                        @keydown.esc.prevent.stop="cancelarAltaSubtarea(tarea)"
                      />
                      <p
                        v-if="errorNueva"
                        :id="`${idCampoSubtarea(tarea)}-error`"
                        role="alert"
                        class="text-destructive text-xs"
                      >
                        {{ errorNueva }}
                      </p>
                      <div class="flex gap-1">
                        <Button
                          type="submit"
                          size="sm"
                          :disabled="guardandoNueva"
                          aria-label="Guardar subtarea"
                          >Guardar</Button
                        >
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          aria-label="Cancelar subtarea"
                          @click="cancelarAltaSubtarea(tarea)"
                          >Cancelar</Button
                        >
                      </div>
                    </form>
                    <Button
                      v-else
                      :id="idBotonAgregar(tarea)"
                      type="button"
                      variant="ghost"
                      size="sm"
                      class="text-muted-foreground justify-start px-2"
                      :aria-label="`Agregar subtarea a ${tarea.nombre}`"
                      @click="abrirAltaSubtarea(tarea)"
                    >
                      <Plus aria-hidden="true" />
                      Agregar subtarea
                    </Button>
                  </div>
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
            </div>
          </section>
        </div>
      </template>
    </template>

    <p class="sr-only" aria-live="polite" data-anuncio-tablero>{{ anuncio }}</p>
  </div>
</template>
