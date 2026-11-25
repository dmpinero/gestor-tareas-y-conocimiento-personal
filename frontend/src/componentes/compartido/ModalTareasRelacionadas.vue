<script setup lang="ts">
import { computed } from 'vue'
import type { Subtarea, Tarea } from '@/api/tipos'
import type { SeleccionRelacionada } from '@/composables/useTareasRelacionadas'
import { RELACIONES, textosRelacion } from '@/lib/tareasRelacionadas'
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

// Persona y prioridad también se dan en subtareas: tienen su propia sección.
const relacionSubtareas = computed(() =>
  props.seleccion === null ? undefined : RELACIONES[props.seleccion.tipo].subtareas,
)

const tareasRelacionadas = computed<Tarea[]>(() => {
  const seleccion = props.seleccion
  if (seleccion === null) return []
  const { coincide } = RELACIONES[seleccion.tipo]
  return props.tareas.filter((tarea) => coincide(tarea, seleccion.nombre))
})

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

const CLASE_ELEMENTO =
  'focus-visible:ring-ring/50 w-full rounded-md px-2 py-1.5 text-left text-sm outline-none [overflow-wrap:anywhere] hover:bg-accent focus-visible:ring-[3px]'
</script>

<template>
  <Dialog :open="props.seleccion !== null" @update:open="(abierto) => !abierto && emit('cerrar')">
    <DialogContent class="max-h-[80vh] overflow-y-auto">
      <DialogHeader>
        <DialogTitle class="[overflow-wrap:anywhere]">{{ titulo }}</DialogTitle>
        <DialogDescription>{{ textos.descripcion }}</DialogDescription>
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
        <p v-else class="text-muted-foreground text-sm">{{ textos.vacio }}</p>
      </section>

      <section v-if="relacionSubtareas" class="grid gap-2">
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
        <p v-else class="text-muted-foreground text-sm">{{ relacionSubtareas.vacio }}</p>
      </section>
    </DialogContent>
  </Dialog>
</template>
