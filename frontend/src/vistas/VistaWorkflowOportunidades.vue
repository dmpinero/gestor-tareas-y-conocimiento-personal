<script setup lang="ts">
import { ArrowDown, ArrowLeft, ArrowUp, GripVertical, Pencil, Trash2 } from '@lucide/vue'
import { computed, nextTick, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import type { PasoWorkflow } from '@/api/tipos'
import { Button } from '@/componentes/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/componentes/ui/dialog'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'
import { useTiendaWorkflowOportunidades } from '@/stores/workflowOportunidades'

const LONGITUD_MAXIMA = 50

const tienda = useTiendaWorkflowOportunidades()

const nombreNuevo = ref('')
const errorFormulario = ref<string | null>(null)
const guardando = ref(false)

const idEditando = ref<number | null>(null)
const nombreEditando = ref('')
const errorEdicion = ref<string | null>(null)

const pasoAEliminar = ref<PasoWorkflow | null>(null)

const reordenando = ref(false)
const anuncio = ref('')
const indiceArrastrado = ref<number | null>(null)
const indiceDestino = ref<number | null>(null)

const pasos = computed(() => tienda.pasos)

onMounted(() => {
  void tienda.cargar()
})

// Devuelve el mensaje de error del nombre recortado, o `null` si es válido.
function validarNombre(nombre: string): string | null {
  if (nombre.length === 0) return 'El nombre del paso es obligatorio.'
  if (nombre.length > LONGITUD_MAXIMA) {
    return `El nombre del paso no puede superar los ${LONGITUD_MAXIMA} caracteres.`
  }
  return null
}

async function anadirPaso(): Promise<void> {
  const nombre = nombreNuevo.value.trim()
  errorFormulario.value = validarNombre(nombre)
  if (errorFormulario.value) return
  guardando.value = true
  const correcto = await tienda.crear(nombre)
  guardando.value = false
  if (correcto) nombreNuevo.value = ''
}

async function empezarEdicion(paso: PasoWorkflow): Promise<void> {
  idEditando.value = paso.id
  nombreEditando.value = paso.nombre
  errorEdicion.value = null
  await nextTick()
  document.getElementById(`nombre-paso-${paso.id}`)?.focus()
}

function cancelarEdicion(): void {
  idEditando.value = null
  errorEdicion.value = null
}

async function guardarEdicion(paso: PasoWorkflow): Promise<void> {
  const nombre = nombreEditando.value.trim()
  errorEdicion.value = validarNombre(nombre)
  if (errorEdicion.value) return
  if (await tienda.renombrar(paso.id, nombre)) idEditando.value = null
}

function alCambiarConfirmacion(abierto: boolean): void {
  if (!abierto) pasoAEliminar.value = null
}

async function confirmarEliminacion(): Promise<void> {
  const paso = pasoAEliminar.value
  if (!paso) return
  pasoAEliminar.value = null
  await tienda.eliminar(paso.id)
}

// Mueve el paso de `origen` a la posición `destino` (índices de la lista),
// guarda el nuevo orden y anuncia la posición final a los lectores de pantalla.
async function mover(origen: number, destino: number): Promise<void> {
  const lista = pasos.value
  const paso = lista[origen]
  if (!paso || origen === destino || destino < 0 || destino >= lista.length) return
  const ids = lista.map((p) => p.id)
  ids.splice(origen, 1)
  ids.splice(destino, 0, paso.id)
  anuncio.value = ''
  reordenando.value = true
  const correcto = await tienda.reordenar(ids)
  reordenando.value = false
  if (!correcto) return
  const movido = tienda.pasos.find((p) => p.id === paso.id)
  if (movido) anuncio.value = `${movido.nombre} movido a la posición ${movido.numero}`
}

function alEmpezarArrastre(evento: DragEvent, indice: number): void {
  indiceArrastrado.value = indice
  if (evento.dataTransfer) {
    evento.dataTransfer.effectAllowed = 'move'
    evento.dataTransfer.setData('text/plain', String(pasos.value[indice]?.id ?? ''))
  }
}

function alArrastrarSobre(evento: DragEvent, indice: number): void {
  if (indiceArrastrado.value === null) return
  evento.preventDefault()
  if (evento.dataTransfer) evento.dataTransfer.dropEffect = 'move'
  indiceDestino.value = indice
}

function alSalirDeFila(indice: number): void {
  if (indiceDestino.value === indice) indiceDestino.value = null
}

function alSoltar(evento: DragEvent, indice: number): void {
  evento.preventDefault()
  const origen = indiceArrastrado.value
  terminarArrastre()
  if (origen !== null) void mover(origen, indice)
}

function terminarArrastre(): void {
  indiceArrastrado.value = null
  indiceDestino.value = null
}

// Dónde se pinta la línea de destino: antes de la fila si el paso sube y
// después si baja, que es donde quedará al soltarlo.
function posicionDestino(indice: number): 'antes' | 'despues' | undefined {
  const origen = indiceArrastrado.value
  if (origen === null || indiceDestino.value !== indice || origen === indice) return undefined
  return indice < origen ? 'antes' : 'despues'
}
</script>

<template>
  <section class="max-w-2xl">
    <RouterLink
      to="/ajustes"
      class="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 text-sm"
    >
      <ArrowLeft class="size-4" aria-hidden="true" />
      Volver a Ajustes
    </RouterLink>
    <h2 class="mt-2 text-xl font-semibold">Workflow Oportunidades</h2>
    <p class="text-muted-foreground mt-1 text-sm">
      Pasos estándar que se realizan en orden en cada oportunidad. Arrastra un paso o usa los
      botones Subir y Bajar para cambiar su orden.
    </p>

    <form
      aria-label="Añadir paso"
      class="mt-6 flex flex-wrap items-end gap-2"
      novalidate
      @submit.prevent="anadirPaso"
    >
      <div class="grid min-w-0 flex-1 gap-1.5">
        <Label for="nombre-paso-nuevo">Nombre del paso</Label>
        <Input
          id="nombre-paso-nuevo"
          v-model="nombreNuevo"
          required
          :maxlength="LONGITUD_MAXIMA"
          autocomplete="off"
          :aria-invalid="errorFormulario ? true : undefined"
        />
      </div>
      <Button type="submit" :disabled="guardando">Añadir paso</Button>
    </form>
    <p v-if="errorFormulario" class="text-destructive mt-2 text-sm" role="alert">
      {{ errorFormulario }}
    </p>

    <p v-if="tienda.error" class="text-destructive mt-4 text-sm" role="alert">{{ tienda.error }}</p>

    <p v-if="!tienda.cargando && pasos.length === 0" class="text-muted-foreground mt-6 text-sm">
      Todavía no hay pasos en el workflow.
    </p>

    <ol v-else class="mt-6 grid gap-2" aria-label="Pasos del workflow">
      <li
        v-for="(paso, indice) in pasos"
        :key="paso.id"
        data-paso
        :data-destino="posicionDestino(indice)"
        :draggable="idEditando === paso.id ? 'false' : 'true'"
        :class="[
          'bg-background flex items-center gap-2 rounded-lg border p-2',
          indiceArrastrado === indice && 'opacity-50',
          posicionDestino(indice) === 'antes' && 'border-t-primary border-t-4',
          posicionDestino(indice) === 'despues' && 'border-b-primary border-b-4',
        ]"
        @dragstart="alEmpezarArrastre($event, indice)"
        @dragover="alArrastrarSobre($event, indice)"
        @dragleave="alSalirDeFila(indice)"
        @drop="alSoltar($event, indice)"
        @dragend="terminarArrastre"
      >
        <span data-asa class="text-muted-foreground cursor-grab px-1" aria-hidden="true">
          <GripVertical class="size-4" />
        </span>

        <form
          v-if="idEditando === paso.id"
          :aria-label="`Renombrar paso ${paso.nombre}`"
          class="flex flex-1 flex-wrap items-center gap-2"
          novalidate
          @submit.prevent="guardarEdicion(paso)"
        >
          <span class="tabular-nums">{{ paso.numero }}.</span>
          <Input
            :id="`nombre-paso-${paso.id}`"
            v-model="nombreEditando"
            class="min-w-0 flex-1"
            required
            :maxlength="LONGITUD_MAXIMA"
            autocomplete="off"
            :aria-label="`Nuevo nombre del paso ${paso.nombre}`"
            :aria-invalid="errorEdicion ? true : undefined"
            @keydown.esc="cancelarEdicion"
          />
          <Button type="submit" size="sm">Guardar</Button>
          <Button type="button" size="sm" variant="outline" @click="cancelarEdicion">
            Cancelar
          </Button>
          <p v-if="errorEdicion" class="text-destructive w-full text-sm" role="alert">
            {{ errorEdicion }}
          </p>
        </form>

        <template v-else>
          <span data-texto-paso class="min-w-0 flex-1 break-words">
            {{ paso.numero }}. {{ paso.nombre }}
          </span>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            :aria-label="`Subir paso ${paso.nombre}`"
            :disabled="indice === 0 || reordenando"
            @click="mover(indice, indice - 1)"
          >
            <ArrowUp aria-hidden="true" />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            :aria-label="`Bajar paso ${paso.nombre}`"
            :disabled="indice === pasos.length - 1 || reordenando"
            @click="mover(indice, indice + 1)"
          >
            <ArrowDown aria-hidden="true" />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            :aria-label="`Renombrar paso ${paso.nombre}`"
            @click="empezarEdicion(paso)"
          >
            <Pencil aria-hidden="true" />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            :aria-label="`Eliminar paso ${paso.nombre}`"
            @click="pasoAEliminar = paso"
          >
            <Trash2 aria-hidden="true" />
          </Button>
        </template>
      </li>
    </ol>

    <p class="sr-only" aria-live="polite">{{ anuncio }}</p>

    <Dialog :open="pasoAEliminar !== null" @update:open="alCambiarConfirmacion">
      <DialogContent sin-aspa>
        <DialogHeader>
          <DialogTitle>Eliminar paso</DialogTitle>
          <DialogDescription>
            ¿Seguro que quieres eliminar el paso «{{ pasoAEliminar?.nombre }}»? Los pasos siguientes
            se renumerarán.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button type="button" variant="outline" @click="pasoAEliminar = null">Cancelar</Button>
          <Button type="button" variant="destructive" @click="confirmarEliminacion">
            Eliminar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </section>
</template>
