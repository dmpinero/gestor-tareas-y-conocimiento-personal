<script setup lang="ts">
import { computed } from 'vue'
import type { GrupoEstados, Subtarea, Tarea } from '@/api/tipos'
import type { SeleccionRelacionada } from '@/composables/useTareasRelacionadas'
import { RELACIONES, textosRelacion } from '@/lib/tareasRelacionadas'
import { instanteCongelado } from '@/lib/hibernacion'
import {
  CLASE_PILDORA,
  PILDORA_PRIORIDAD,
  clavePrioridad,
  colorEtiqueta,
  pildoraEstado,
} from '@/lib/coloresTarea'
import AvatarPersona from '@/componentes/compartido/AvatarPersona.vue'
import VencimientoCorto from '@/componentes/compartido/VencimientoCorto.vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/componentes/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/componentes/ui/table'

// Ventana con las tareas (y, para persona y prioridad, las subtareas) que
// comparten lo pulsado. Las tablas siguen el estilo del listado: cabecera gris,
// filas alternas, las mismas píldoras de color y la fila entera pulsable.
// `grupos` da el color de cada estado según su posición en su grupo.
const props = withDefaults(
  defineProps<{
    seleccion: SeleccionRelacionada | null
    tareas: Tarea[]
    grupos?: GrupoEstados[]
  }>(),
  { grupos: () => [] },
)

const emit = defineEmits<{
  cerrar: []
  verTarea: [id: number]
}>()

const tareasRelacionadas = computed<Tarea[]>(() => {
  const seleccion = props.seleccion
  if (seleccion === null) return []
  const { coincide } = RELACIONES[seleccion.tipo]
  return props.tareas.filter((tarea) => coincide(tarea, seleccion.nombre))
})

// Persona y prioridad también se dan en subtareas: tienen su propia sección.
const relacionSubtareas = computed(() =>
  props.seleccion === null ? undefined : RELACIONES[props.seleccion.tipo].subtareas,
)

const subtareasRelacionadas = computed<{ subtarea: Subtarea; tarea: Tarea }[]>(() => {
  const seleccion = props.seleccion
  const relacion = relacionSubtareas.value
  if (seleccion === null || relacion === undefined) return []
  return props.tareas.flatMap((tarea) =>
    tarea.subtareas
      .filter((subtarea) => relacion.coincide(subtarea, seleccion.nombre))
      .map((subtarea) => ({ subtarea, tarea })),
  )
})

const titulo = computed(() => {
  const seleccion = props.seleccion
  return seleccion === null ? '' : RELACIONES[seleccion.tipo].titulo(seleccion.nombre)
})

const textos = computed(() => {
  const seleccion = props.seleccion
  return seleccion === null
    ? { descripcion: '', vacio: '' }
    : textosRelacion(seleccion.tipo, seleccion.nombre)
})

function clasePildoraPrioridad(prioridad: number): string {
  const clave = clavePrioridad(prioridad)
  return clave === 'sin' ? CLASE_PILDORA : `${CLASE_PILDORA} ${PILDORA_PRIORIDAD[clave]}`
}

function clasePildoraEstado(tarea: Tarea): string {
  const estados = props.grupos.find((grupo) => grupo.id === tarea.grupo_estados?.id)?.estados ?? []
  const indice = estados.findIndex((estado) => estado.id === tarea.estado?.id)
  return `${CLASE_PILDORA} ${pildoraEstado(indice, estados.length)}`
}

const CLASE_FILA = 'cursor-pointer hover:bg-blue-100/60 dark:hover:bg-blue-950/60'
function claseFila(indice: number, tachada: boolean): string {
  return [CLASE_FILA, indice % 2 === 1 && 'bg-muted/40', tachada && 'line-through']
    .filter(Boolean)
    .join(' ')
}

// Pulsar la fila abre la tarea; el botón del nombre lo hace con el teclado.
function alPulsarFila(evento: MouseEvent, id: number): void {
  if (evento.target instanceof Element && evento.target.closest('button')) return
  emit('verTarea', id)
}

const CLASE_NOMBRE =
  'focus-visible:ring-ring/50 rounded-sm text-left font-medium outline-none [overflow-wrap:anywhere] hover:underline focus-visible:ring-[3px]'
const CLASE_CONTADOR =
  'bg-muted text-muted-foreground inline-flex min-w-6 justify-center rounded-full px-2 py-0.5 text-xs font-semibold'
const CLASE_MARCO = 'bg-card text-card-foreground overflow-hidden rounded-xl border shadow-xs'
</script>

<template>
  <Dialog :open="props.seleccion !== null" @update:open="(abierto) => !abierto && emit('cerrar')">
    <DialogContent class="max-h-[85vh] gap-6 overflow-y-auto sm:max-w-4xl">
      <DialogHeader>
        <DialogTitle class="text-xl [overflow-wrap:anywhere]">{{ titulo }}</DialogTitle>
        <DialogDescription>{{ textos.descripcion }}</DialogDescription>
      </DialogHeader>

      <section class="grid gap-3">
        <h3 class="flex items-center gap-2 text-sm font-semibold">
          Tareas
          <!-- Un solo texto oculto: varios trozos se leían "( 5 )". -->
          <span :class="CLASE_CONTADOR"
            ><span aria-hidden="true">{{ tareasRelacionadas.length }}</span
            ><span class="sr-only">{{ ` (${tareasRelacionadas.length})` }}</span></span
          >
        </h3>
        <div v-if="tareasRelacionadas.length > 0" :class="CLASE_MARCO">
          <Table data-tabla="Tareas">
            <caption class="sr-only">
              Tareas
            </caption>
            <TableHeader class="bg-muted">
              <TableRow class="bg-muted hover:bg-muted">
                <TableHead>Nombre</TableHead>
                <TableHead>Prioridad</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Subestado</TableHead>
                <TableHead>Vencimiento</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow
                v-for="(tarea, indice) in tareasRelacionadas"
                :key="tarea.id"
                :class="claseFila(indice, tarea.completada)"
                @click="alPulsarFila($event, tarea.id)"
              >
                <TableCell class="min-w-48 whitespace-normal">
                  <button
                    type="button"
                    :class="CLASE_NOMBRE"
                    :aria-label="`Abrir la tarea ${tarea.nombre}`"
                    @click="emit('verTarea', tarea.id)"
                  >
                    {{ tarea.nombre }}
                  </button>
                </TableCell>
                <TableCell>
                  <span
                    v-if="tarea.prioridad !== null"
                    :class="clasePildoraPrioridad(tarea.prioridad)"
                    >{{ tarea.prioridad }}</span
                  >
                  <template v-else>—</template>
                </TableCell>
                <TableCell>
                  <span v-if="tarea.estado" :class="clasePildoraEstado(tarea)">{{
                    tarea.estado.nombre
                  }}</span>
                  <template v-else>—</template>
                </TableCell>
                <TableCell>
                  <span
                    v-if="tarea.subestado"
                    :class="`${CLASE_PILDORA} ${colorEtiqueta(tarea.subestado)}`"
                    >{{ tarea.subestado }}</span
                  >
                  <template v-else>—</template>
                </TableCell>
                <TableCell>
                  <VencimientoCorto
                    v-if="tarea.fecha_vencimiento"
                    :vencimiento="tarea.fecha_vencimiento"
                    :completada="tarea.completada"
                    :congelada-en="instanteCongelado(tarea)"
                  />
                  <template v-else>—</template>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
        <p
          v-else
          class="text-muted-foreground rounded-xl border border-dashed p-6 text-center text-sm"
        >
          {{ textos.vacio }}
        </p>
      </section>

      <section v-if="relacionSubtareas" class="grid gap-3">
        <h3 class="flex items-center gap-2 text-sm font-semibold">
          Subtareas
          <!-- Un solo texto oculto: varios trozos se leían "( 5 )". -->
          <span :class="CLASE_CONTADOR"
            ><span aria-hidden="true">{{ subtareasRelacionadas.length }}</span
            ><span class="sr-only">{{ ` (${subtareasRelacionadas.length})` }}</span></span
          >
        </h3>
        <div v-if="subtareasRelacionadas.length > 0" :class="CLASE_MARCO">
          <Table data-tabla="Subtareas">
            <caption class="sr-only">
              Subtareas
            </caption>
            <TableHeader class="bg-muted">
              <TableRow class="bg-muted hover:bg-muted">
                <TableHead>Subtarea</TableHead>
                <TableHead>Tarea</TableHead>
                <TableHead>Persona</TableHead>
                <TableHead>Prioridad</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow
                v-for="({ subtarea, tarea }, indice) in subtareasRelacionadas"
                :key="subtarea.id"
                :class="claseFila(indice, subtarea.resuelta)"
                @click="alPulsarFila($event, tarea.id)"
              >
                <TableCell class="min-w-40 whitespace-normal">
                  <button
                    type="button"
                    :class="CLASE_NOMBRE"
                    :aria-label="`Abrir la tarea ${tarea.nombre} (subtarea ${subtarea.nombre})`"
                    @click="emit('verTarea', tarea.id)"
                  >
                    {{ subtarea.nombre }}
                  </button>
                </TableCell>
                <TableCell class="text-muted-foreground min-w-40 whitespace-normal">{{
                  tarea.nombre
                }}</TableCell>
                <TableCell>
                  <AvatarPersona v-if="subtarea.asignado" :nombre="subtarea.asignado" />
                  <template v-else>—</template>
                </TableCell>
                <TableCell>
                  <span
                    v-if="subtarea.prioridad !== null"
                    :class="clasePildoraPrioridad(subtarea.prioridad)"
                    >{{ subtarea.prioridad }}</span
                  >
                  <template v-else>—</template>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
        <p
          v-else
          class="text-muted-foreground rounded-xl border border-dashed p-6 text-center text-sm"
        >
          {{ relacionSubtareas.vacio }}
        </p>
      </section>
    </DialogContent>
  </Dialog>
</template>
