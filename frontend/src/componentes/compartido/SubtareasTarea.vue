<script setup lang="ts">
import { Circle, CircleCheck, Plus, Trash } from '@lucide/vue'
import { computed, nextTick, reactive, ref } from 'vue'

import type { DatosSubtarea, Subtarea, Tarea } from '@/api/tipos'
import { Button } from '@/componentes/ui/button'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/componentes/ui/table'
import { useTiendaTareas } from '@/stores/tareas'

// Subtareas de una tarea: listado, alta en línea, marcar como resuelta y
// eliminar. Lee y escribe a través del almacén de tareas; la tarea actualizada
// llega de vuelta por `tarea` (el almacén la reemplaza con la respuesta). Los
// fallos de la API quedan en `tienda.error`, que muestra el detalle.
const props = defineProps<{ tarea: Tarea }>()

const tienda = useTiendaTareas()

const MAX_NOMBRE = 200
const MAX_PERSONA = 100
const VACIO = '—'
const ERROR_NOMBRE_OBLIGATORIO = 'El nombre de la subtarea es obligatorio.'
const ERROR_NOMBRE_LARGO = `El nombre de la subtarea no puede superar ${MAX_NOMBRE} caracteres.`
const ERROR_PERSONA_LARGA = `La persona asignada no puede superar ${MAX_PERSONA} caracteres.`
const ERROR_PRIORIDAD = 'La prioridad debe ser un número entero del 1 al 5.'

const idBase = computed(() => `subtareas-tarea-${props.tarea.id}`)

const sinResolver = computed(
  () => props.tarea.subtareas.filter((subtarea) => !subtarea.resuelta).length,
)

function textoOVacio(valor: string | number | null): string {
  return valor === null || valor === '' ? VACIO : String(valor)
}

async function alternar(subtarea: Subtarea): Promise<void> {
  await tienda.alternarSubtarea(props.tarea.id, subtarea.id)
}

// --- Eliminar, con confirmación en la propia fila -------------------------
// Se confirma en línea y no con otra modal: el detalle ya es una modal y
// anidar otra complica el foco y el Escape.
const idConfirmando = ref<number | null>(null)

function idBotonEliminar(subtarea: Subtarea): string {
  return `${idBase.value}-eliminar-${subtarea.id}`
}

async function pedirConfirmacion(subtarea: Subtarea): Promise<void> {
  idConfirmando.value = subtarea.id
  await nextTick()
  document.getElementById(`${idBase.value}-cancelar-eliminar`)?.focus()
}

async function cancelarEliminacion(subtarea: Subtarea): Promise<void> {
  idConfirmando.value = null
  await nextTick()
  document.getElementById(idBotonEliminar(subtarea))?.focus()
}

async function confirmarEliminacion(subtarea: Subtarea): Promise<void> {
  const eliminada = await tienda.eliminarSubtarea(props.tarea.id, subtarea.id)
  idConfirmando.value = null
  await nextTick()
  // Si se borró, la fila ya no está: el foco pasa al botón de añadir (o al
  // primer campo si la fila de alta está abierta).
  const destino = eliminada
    ? (document.getElementById(`${idBase.value}-nombre`) ??
      document.getElementById(`${idBase.value}-anadir`))
    : document.getElementById(idBotonEliminar(subtarea))
  destino?.focus()
}

// --- Alta en línea --------------------------------------------------------
// Tras guardar, la fila se vacía y sigue abierta con el foco en Nombre para
// encadenar varias subtareas seguidas; Cancelar o Escape la cierran.
const anadiendo = ref(false)
const guardando = ref(false)
const errorAlta = ref<string | null>(null)
// La prioridad llega como número desde el `<input type="number">`, o como
// cadena vacía si se deja en blanco.
const formulario = reactive<{
  nombre: string
  asignado: string
  prioridad: string | number | null
}>({ nombre: '', asignado: '', prioridad: '' })

function vaciarFormulario(): void {
  formulario.nombre = ''
  formulario.asignado = ''
  formulario.prioridad = ''
  errorAlta.value = null
}

async function enfocarNombre(): Promise<void> {
  await nextTick()
  document.getElementById(`${idBase.value}-nombre`)?.focus()
}

async function abrirAlta(): Promise<void> {
  vaciarFormulario()
  anadiendo.value = true
  await enfocarNombre()
}

async function cancelarAlta(): Promise<void> {
  anadiendo.value = false
  vaciarFormulario()
  await nextTick()
  document.getElementById(`${idBase.value}-anadir`)?.focus()
}

function validar(): DatosSubtarea | { error: string } {
  const nombre = formulario.nombre.trim()
  if (nombre === '') return { error: ERROR_NOMBRE_OBLIGATORIO }
  if (nombre.length > MAX_NOMBRE) return { error: ERROR_NOMBRE_LARGO }
  const datos: DatosSubtarea = { nombre }

  const asignado = formulario.asignado.trim()
  if (asignado.length > MAX_PERSONA) return { error: ERROR_PERSONA_LARGA }
  if (asignado !== '') datos.asignado = asignado

  if (formulario.prioridad !== null && formulario.prioridad !== '') {
    const prioridad = Number(formulario.prioridad)
    if (!Number.isInteger(prioridad) || prioridad < 1 || prioridad > 5) {
      return { error: ERROR_PRIORIDAD }
    }
    datos.prioridad = prioridad
  }
  return datos
}

async function guardar(): Promise<void> {
  if (guardando.value) return
  const resultado = validar()
  if ('error' in resultado) {
    errorAlta.value = resultado.error
    return
  }
  errorAlta.value = null
  guardando.value = true
  try {
    const creada = await tienda.crearSubtarea(props.tarea.id, resultado)
    // Si falla se conserva lo escrito; el mensaje queda en `tienda.error`.
    if (creada) {
      vaciarFormulario()
      await enfocarNombre()
    }
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <section :aria-labelledby="`${idBase}-titulo`">
    <div class="mb-3 flex items-baseline gap-2">
      <h3 :id="`${idBase}-titulo`" class="text-base font-semibold">Subtareas</h3>
      <span data-testid="contador-subtareas" class="text-muted-foreground text-sm"
        >{{ sinResolver }} sin resolver</span
      >
    </div>

    <Table v-if="props.tarea.subtareas.length > 0" data-testid="tabla-subtareas">
      <TableHeader>
        <TableRow>
          <TableHead>Nombre</TableHead>
          <TableHead>Persona asignada</TableHead>
          <TableHead>Prioridad</TableHead>
          <TableHead><span class="sr-only">Acciones</span></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow v-for="subtarea in props.tarea.subtareas" :key="subtarea.id">
          <TableCell class="whitespace-normal">
            <div class="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                class="size-8"
                :aria-pressed="subtarea.resuelta ? 'true' : 'false'"
                :aria-label="`Marcar como resuelta la subtarea ${subtarea.nombre}`"
                @click="alternar(subtarea)"
              >
                <CircleCheck v-if="subtarea.resuelta" class="text-success" aria-hidden="true" />
                <Circle v-else aria-hidden="true" />
              </Button>
              <span
                class="[overflow-wrap:anywhere]"
                :class="subtarea.resuelta ? 'text-muted-foreground line-through' : ''"
                >{{ subtarea.nombre }}</span
              >
            </div>
          </TableCell>
          <TableCell class="whitespace-normal">
            <span
              class="[overflow-wrap:anywhere]"
              :class="subtarea.resuelta ? 'text-muted-foreground line-through' : ''"
              >{{ textoOVacio(subtarea.asignado) }}</span
            >
          </TableCell>
          <TableCell>
            <span :class="subtarea.resuelta ? 'text-muted-foreground line-through' : ''">{{
              textoOVacio(subtarea.prioridad)
            }}</span>
          </TableCell>
          <TableCell class="text-right">
            <div
              v-if="idConfirmando === subtarea.id"
              role="group"
              :aria-label="`¿Eliminar la subtarea ${subtarea.nombre}?`"
              class="flex items-center justify-end gap-2"
              @keydown.esc.stop.prevent="cancelarEliminacion(subtarea)"
            >
              <Button variant="destructive" size="sm" @click="confirmarEliminacion(subtarea)"
                >Eliminar</Button
              >
              <Button
                :id="`${idBase}-cancelar-eliminar`"
                variant="outline"
                size="sm"
                @click="cancelarEliminacion(subtarea)"
                >Cancelar</Button
              >
            </div>
            <Button
              v-else
              :id="idBotonEliminar(subtarea)"
              variant="ghost"
              size="icon"
              class="size-8"
              :aria-label="`Eliminar subtarea ${subtarea.nombre}`"
              @click="pedirConfirmacion(subtarea)"
            >
              <Trash aria-hidden="true" />
            </Button>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
    <p v-else class="text-muted-foreground text-sm">Esta tarea no tiene subtareas.</p>

    <form
      v-if="anadiendo"
      class="mt-3 grid gap-3 sm:grid-cols-[1fr_12rem_7rem_auto] sm:items-end"
      novalidate
      @submit.prevent="guardar"
      @keydown.esc.stop.prevent="cancelarAlta"
    >
      <div class="flex flex-col gap-1.5">
        <Label :for="`${idBase}-nombre`">Nombre de la subtarea</Label>
        <Input
          :id="`${idBase}-nombre`"
          v-model="formulario.nombre"
          :maxlength="MAX_NOMBRE"
          required
          :aria-invalid="errorAlta === ERROR_NOMBRE_OBLIGATORIO ? 'true' : undefined"
          :aria-describedby="errorAlta ? `${idBase}-error` : undefined"
        />
      </div>
      <div class="flex flex-col gap-1.5">
        <Label :for="`${idBase}-asignado`">Persona asignada</Label>
        <Input
          :id="`${idBase}-asignado`"
          v-model="formulario.asignado"
          :maxlength="MAX_PERSONA"
          :list="`${idBase}-personas`"
          autocomplete="off"
        />
        <datalist :id="`${idBase}-personas`">
          <option v-for="persona in tienda.personas" :key="persona" :value="persona" />
        </datalist>
      </div>
      <div class="flex flex-col gap-1.5">
        <Label :for="`${idBase}-prioridad`">Prioridad de la subtarea</Label>
        <Input
          :id="`${idBase}-prioridad`"
          v-model="formulario.prioridad"
          type="number"
          min="1"
          max="5"
          step="1"
          :aria-invalid="errorAlta === ERROR_PRIORIDAD ? 'true' : undefined"
        />
      </div>
      <div class="flex gap-2">
        <Button type="submit" :disabled="guardando">Guardar</Button>
        <Button type="button" variant="outline" @click="cancelarAlta">Cancelar</Button>
      </div>
      <p
        v-if="errorAlta"
        :id="`${idBase}-error`"
        role="alert"
        class="text-destructive text-sm sm:col-span-4"
      >
        {{ errorAlta }}
      </p>
    </form>
    <Button
      v-else
      :id="`${idBase}-anadir`"
      variant="outline"
      size="sm"
      class="mt-3"
      @click="abrirAlta"
    >
      <Plus aria-hidden="true" />
      Añadir subtarea
    </Button>
  </section>
</template>
