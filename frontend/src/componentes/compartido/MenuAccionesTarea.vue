<script setup lang="ts">
import {
  CircleStop,
  Ellipsis,
  Eye,
  ListMinus,
  ListPlus,
  Pencil,
  Play,
  Snowflake,
  Target,
  Trash,
} from '@lucide/vue'
import { computed, ref } from 'vue'

import { Button } from '@/componentes/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/componentes/ui/popover'
import { useTiendaFoco } from '@/stores/foco'
import { useTiendaSiguientes } from '@/stores/siguientes'

// Menú "⋯" con las acciones de una fila de la tabla de tareas. Cada acción
// conserva el nombre accesible que tenía como botón suelto. El disparador
// siempre recibe el foco; en pantallas anchas con ratón solo se ve al pasar
// por la fila o al enfocarla (estilos `data-acciones-fila` en main.css).
// Con `tareaId` ofrece también "Trabajar en esta" / "Dejar de trabajar", que
// pone o quita la tarea en foco (como el botón del tablero y del detalle).
// Con `tareaId` y sin `completada`, también "Añadir a siguientes" / "Quitar de
// siguientes" (la cola de "A continuación", como `BotonSiguientes`).
// Con `hibernada` definido ofrece también "Hibernar" (emite `hibernar`, para
// que la vista abra el diálogo del comentario) o, si ya lo está, "Reanudar".
const props = defineProps<{
  nombre: string
  idDisparador: string
  tareaId?: number
  hibernada?: boolean
  completada?: boolean
}>()

const emit = defineEmits<{
  editar: []
  detalle: []
  eliminar: []
  hibernar: []
  reanudar: []
}>()

const abierto = ref(false)
const tiendaFoco = useTiendaFoco()
const enFoco = computed(
  () => props.tareaId !== undefined && tiendaFoco.esTareaEnFoco(props.tareaId),
)
const etiquetaFoco = computed(() => (enFoco.value ? 'Dejar de trabajar' : 'Trabajar en esta'))

function alternarFoco(): void {
  abierto.value = false
  if (props.tareaId === undefined) return
  if (enFoco.value) void tiendaFoco.quitar()
  else void tiendaFoco.fijar(props.tareaId)
}

const tiendaSiguientes = useTiendaSiguientes()
const enCola = computed(
  () => props.tareaId !== undefined && tiendaSiguientes.estaEnCola(props.tareaId),
)
const etiquetaSiguientes = computed(() =>
  enCola.value ? 'Quitar de siguientes' : 'Añadir a siguientes',
)

function alternarSiguientes(): void {
  abierto.value = false
  if (props.tareaId === undefined) return
  if (enCola.value) void tiendaSiguientes.quitar(props.tareaId)
  else void tiendaSiguientes.anadir(props.tareaId)
}

function elegir(accion: 'editar' | 'detalle' | 'eliminar'): void {
  abierto.value = false
  if (accion === 'editar') emit('editar')
  else if (accion === 'detalle') emit('detalle')
  else emit('eliminar')
}

function alternarHibernacion(): void {
  abierto.value = false
  if (props.hibernada) emit('reanudar')
  else emit('hibernar')
}

const CLASE_OPCION =
  'hover:bg-accent hover:text-accent-foreground focus-visible:ring-ring/50 flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm outline-none focus-visible:ring-[3px] [&_svg]:size-4'
</script>

<template>
  <Popover v-model:open="abierto">
    <PopoverTrigger as-child>
      <Button
        :id="props.idDisparador"
        type="button"
        variant="ghost"
        size="icon"
        data-acciones-fila
        :aria-label="`Acciones de la tarea ${props.nombre}`"
        title="Acciones"
      >
        <Ellipsis aria-hidden="true" />
      </Button>
    </PopoverTrigger>
    <PopoverContent align="end" class="w-52 p-1">
      <button
        type="button"
        :class="CLASE_OPCION"
        :aria-label="`Editar tarea ${props.nombre}`"
        @click="elegir('editar')"
      >
        <Pencil aria-hidden="true" />Editar
      </button>
      <button
        type="button"
        :class="CLASE_OPCION"
        :aria-label="`Ver detalle de la tarea ${props.nombre}`"
        @click="elegir('detalle')"
      >
        <Eye aria-hidden="true" />Ver detalle
      </button>
      <button
        v-if="props.tareaId !== undefined"
        type="button"
        :class="CLASE_OPCION"
        :aria-label="`${etiquetaFoco} (${props.nombre})`"
        @click="alternarFoco"
      >
        <CircleStop v-if="enFoco" aria-hidden="true" /><Target v-else aria-hidden="true" />{{
          etiquetaFoco
        }}
      </button>
      <button
        v-if="props.tareaId !== undefined && !props.completada"
        type="button"
        :class="CLASE_OPCION"
        :aria-label="`${etiquetaSiguientes} (${props.nombre})`"
        @click="alternarSiguientes"
      >
        <ListMinus v-if="enCola" aria-hidden="true" /><ListPlus v-else aria-hidden="true" />{{
          etiquetaSiguientes
        }}
      </button>
      <button
        v-if="props.hibernada !== undefined"
        type="button"
        :class="CLASE_OPCION"
        :aria-label="`${props.hibernada ? 'Reanudar' : 'Hibernar'} la tarea ${props.nombre}`"
        @click="alternarHibernacion"
      >
        <Play v-if="props.hibernada" aria-hidden="true" /><Snowflake v-else aria-hidden="true" />{{
          props.hibernada ? 'Reanudar' : 'Hibernar'
        }}
      </button>
      <button
        type="button"
        :class="[CLASE_OPCION, 'text-destructive']"
        :aria-label="`Eliminar la tarea ${props.nombre}`"
        @click="elegir('eliminar')"
      >
        <Trash aria-hidden="true" />Eliminar
      </button>
    </PopoverContent>
  </Popover>
</template>
