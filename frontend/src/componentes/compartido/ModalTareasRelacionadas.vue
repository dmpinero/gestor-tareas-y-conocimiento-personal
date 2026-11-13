<script setup lang="ts">
import { computed } from 'vue'
import type { Subtarea, Tarea } from '@/api/tipos'
import type { SeleccionRelacionada } from '@/composables/useTareasRelacionadas'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/componentes/ui/dialog'

const props = defineProps<{
  seleccion: SeleccionRelacionada | null
  tareas: Tarea[]
}>()

const emit = defineEmits<{
  cerrar: []
  verTarea: [id: number]
}>()

const esPersona = computed(() => props.seleccion?.tipo === 'persona')

const tareasRelacionadas = computed<Tarea[]>(() => {
  const seleccion = props.seleccion
  if (seleccion === null) return []
  return props.tareas.filter((tarea) =>
    (seleccion.tipo === 'etiqueta' ? tarea.etiquetas : tarea.asignados).includes(seleccion.nombre),
  )
})

// Las subtareas solo tienen persona asignada, no etiquetas.
const subtareasRelacionadas = computed<{ subtarea: Subtarea; tarea: Tarea }[]>(() => {
  const seleccion = props.seleccion
  if (seleccion === null || seleccion.tipo !== 'persona') return []
  return props.tareas.flatMap((tarea) =>
    tarea.subtareas
      .filter((subtarea) => subtarea.asignado === seleccion.nombre)
      .map((subtarea) => ({ subtarea, tarea })),
  )
})

const titulo = computed(() => {
  const seleccion = props.seleccion
  if (seleccion === null) return ''
  return `${seleccion.tipo === 'etiqueta' ? 'Etiqueta' : 'Persona'}: ${seleccion.nombre}`
})

const descripcion = computed(() =>
  esPersona.value
    ? 'Tareas y subtareas asignadas a esta persona.'
    : 'Tareas que llevan esta etiqueta.',
)

const CLASE_ELEMENTO =
  'focus-visible:ring-ring/50 w-full rounded-md px-2 py-1.5 text-left text-sm outline-none [overflow-wrap:anywhere] hover:bg-accent focus-visible:ring-[3px]'
</script>

<template>
  <Dialog :open="props.seleccion !== null" @update:open="(abierto) => !abierto && emit('cerrar')">
    <DialogContent class="max-h-[80vh] overflow-y-auto">
      <DialogHeader>
        <DialogTitle class="[overflow-wrap:anywhere]">{{ titulo }}</DialogTitle>
        <DialogDescription>{{ descripcion }}</DialogDescription>
      </DialogHeader>

      <section class="grid gap-2">
        <h3 class="text-sm font-semibold">Tareas ({{ tareasRelacionadas.length }})</h3>
        <ul v-if="tareasRelacionadas.length > 0" aria-label="Tareas" class="grid gap-1">
          <li v-for="tarea in tareasRelacionadas" :key="tarea.id">
            <button
              type="button"
              :class="[CLASE_ELEMENTO, tarea.completada && 'line-through']"
              :aria-label="`Abrir la tarea ${tarea.nombre}`"
              @click="emit('verTarea', tarea.id)"
            >
              {{ tarea.nombre }}
            </button>
          </li>
        </ul>
        <p v-else class="text-muted-foreground text-sm">
          {{
            esPersona
              ? 'No hay tareas asignadas a esta persona.'
              : 'No hay tareas con esta etiqueta.'
          }}
        </p>
      </section>

      <section v-if="esPersona" class="grid gap-2">
        <h3 class="text-sm font-semibold">Subtareas ({{ subtareasRelacionadas.length }})</h3>
        <ul v-if="subtareasRelacionadas.length > 0" aria-label="Subtareas" class="grid gap-1">
          <li v-for="{ subtarea, tarea } in subtareasRelacionadas" :key="subtarea.id">
            <button
              type="button"
              :class="CLASE_ELEMENTO"
              :aria-label="`Abrir la tarea ${tarea.nombre} (subtarea ${subtarea.nombre})`"
              @click="emit('verTarea', tarea.id)"
            >
              <span class="block" :class="subtarea.resuelta && 'line-through'">{{
                subtarea.nombre
              }}</span>
              <span class="text-muted-foreground block text-xs">Tarea: {{ tarea.nombre }}</span>
            </button>
          </li>
        </ul>
        <p v-else class="text-muted-foreground text-sm">
          No hay subtareas asignadas a esta persona.
        </p>
      </section>
    </DialogContent>
  </Dialog>
</template>
