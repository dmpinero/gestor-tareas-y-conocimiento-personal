<script setup lang="ts">
import { ArrowDown, ArrowLeft, ArrowUp, GripVertical, Pencil, Trash2 } from '@lucide/vue'
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'

import type { PasoWorkflow, Workflow } from '@/api/tipos'
import DialogoConfirmacion from '@/componentes/compartido/DialogoConfirmacion.vue'
import { Button } from '@/componentes/ui/button'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'
import { useTiendaWorkflows } from '@/stores/workflows'

// Workflows de Ajustes: cada uno es una secuencia de pasos que se copian como
// subtareas, en orden, en las tareas que lo usan.
const LONGITUD_MAXIMA = 50
const ID_WORKFLOW_NUEVO = 'nombre-workflow-nuevo'

const tienda = useTiendaWorkflows()
const workflows = computed(() => tienda.workflows)

onMounted(() => {
  void tienda.cargar()
})

function idPasoNuevo(workflow: Workflow): string {
  return `paso-nuevo-${workflow.id}`
}

// Devuelve el mensaje de error del nombre recortado, o `null` si es válido.
function validarNombre(nombre: string, que: 'workflow' | 'paso'): string | null {
  if (nombre.length === 0) return `El nombre del ${que} es obligatorio.`
  if (nombre.length > LONGITUD_MAXIMA) {
    return `El nombre del ${que} no puede superar los ${LONGITUD_MAXIMA} caracteres.`
  }
  return null
}

async function enfocarPorId(id: string): Promise<void> {
  await nextTick()
  document.getElementById(id)?.focus()
}

// --- Alta de workflows y pasos ----------------------------------------------
const nombreWorkflowNuevo = ref('')
const errorWorkflowNuevo = ref<string | null>(null)
const guardandoWorkflow = ref(false)

async function anadirWorkflow(): Promise<void> {
  const nombre = nombreWorkflowNuevo.value.trim()
  errorWorkflowNuevo.value = validarNombre(nombre, 'workflow')
  if (errorWorkflowNuevo.value) return
  guardandoWorkflow.value = true
  const correcto = await tienda.crear(nombre)
  guardandoWorkflow.value = false
  if (correcto) nombreWorkflowNuevo.value = ''
}

const nombresPasoNuevo = reactive<Record<number, string>>({})
const erroresPasoNuevo = reactive<Record<number, string | null>>({})

async function anadirPaso(workflow: Workflow): Promise<void> {
  const nombre = (nombresPasoNuevo[workflow.id] ?? '').trim()
  erroresPasoNuevo[workflow.id] = validarNombre(nombre, 'paso')
  if (erroresPasoNuevo[workflow.id]) return
  if (await tienda.anadirPaso(workflow.id, nombre)) nombresPasoNuevo[workflow.id] = ''
}

// --- Renombrar en línea ----------------------------------------------------
type Edicion = { tipo: 'workflow'; id: number } | { tipo: 'paso'; id: number }
const edicion = ref<Edicion | null>(null)
const nombreEditando = ref('')
const errorEdicion = ref<string | null>(null)

function editando(tipo: Edicion['tipo'], id: number): boolean {
  return edicion.value?.tipo === tipo && edicion.value.id === id
}

async function empezarEdicion(tipo: Edicion['tipo'], id: number, nombre: string): Promise<void> {
  edicion.value = { tipo, id }
  nombreEditando.value = nombre
  errorEdicion.value = null
  await enfocarPorId(`nombre-${tipo}-${id}`)
}

function cancelarEdicion(): void {
  edicion.value = null
  errorEdicion.value = null
}

async function guardarWorkflow(workflow: Workflow): Promise<void> {
  const nombre = nombreEditando.value.trim()
  errorEdicion.value = validarNombre(nombre, 'workflow')
  if (errorEdicion.value) return
  if (await tienda.renombrar(workflow.id, nombre)) edicion.value = null
}

async function guardarPaso(workflow: Workflow, paso: PasoWorkflow): Promise<void> {
  const nombre = nombreEditando.value.trim()
  errorEdicion.value = validarNombre(nombre, 'paso')
  if (errorEdicion.value) return
  if (await tienda.renombrarPaso(workflow.id, paso.id, nombre)) edicion.value = null
}

// --- Eliminar, con confirmación --------------------------------------------
// El elemento que abrió la confirmación desaparece al borrar: el foco va al
// campo de alta correspondiente en vez de perderse en el <body>.
const workflowAEliminar = ref<Workflow | null>(null)
const pasoAEliminar = ref<{ workflow: Workflow; paso: PasoWorkflow } | null>(null)
const procesando = ref(false)
const errorDialogo = ref<string | null>(null)
let destinoFoco: string | null = null

const DESCRIPCION_ELIMINAR_WORKFLOW =
  'Las tareas con este workflow quedarán sin workflow y conservarán sus subtareas. Sus pasos también se eliminarán.'

const descripcionEliminarPaso = computed(
  () => `Los pasos siguientes de ${pasoAEliminar.value?.workflow.nombre ?? ''} se renumerarán.`,
)

function pedirEliminarWorkflow(workflow: Workflow): void {
  errorDialogo.value = null
  workflowAEliminar.value = workflow
}

function pedirEliminarPaso(workflow: Workflow, paso: PasoWorkflow): void {
  errorDialogo.value = null
  pasoAEliminar.value = { workflow, paso }
}

function alCambiarConfirmacion(abierta: boolean): void {
  if (abierta || procesando.value) return
  workflowAEliminar.value = null
  pasoAEliminar.value = null
}

async function terminarEliminacion(correcto: boolean, destino: string): Promise<void> {
  if (!correcto) {
    errorDialogo.value = tienda.error
    return
  }
  destinoFoco = destino
  workflowAEliminar.value = null
  pasoAEliminar.value = null
  // Por si la confirmación no devuelve el foco (p. ej. sin animación).
  await enfocarPorId(destino)
}

async function confirmarEliminarWorkflow(): Promise<void> {
  const workflow = workflowAEliminar.value
  if (!workflow || procesando.value) return
  procesando.value = true
  const correcto = await tienda.eliminar(workflow.id)
  procesando.value = false
  await terminarEliminacion(correcto, ID_WORKFLOW_NUEVO)
}

async function confirmarEliminarPaso(): Promise<void> {
  const seleccion = pasoAEliminar.value
  if (!seleccion || procesando.value) return
  procesando.value = true
  const correcto = await tienda.eliminarPaso(seleccion.workflow.id, seleccion.paso.id)
  procesando.value = false
  await terminarEliminacion(correcto, idPasoNuevo(seleccion.workflow))
}

function alDevolverFoco(evento: Event): void {
  if (destinoFoco === null) return
  evento.preventDefault()
  document.getElementById(destinoFoco)?.focus()
  destinoFoco = null
}

// --- Ordenar pasos (botones y arrastrar) -----------------------------------
const reordenando = ref(false)
const anuncio = ref('')
const arrastre = ref<{ idWorkflow: number; indice: number } | null>(null)
const destinoArrastre = ref<{ idWorkflow: number; indice: number } | null>(null)

// Tras mover con los botones, el foco vuelve al mismo botón del paso movido
// (o al otro si ya está en un extremo); el botón se desactiva mientras se
// guarda y el navegador mandaba el foco al <body>.
async function enfocarBotonDeMover(
  workflow: string,
  paso: string,
  accion: 'Subir' | 'Bajar',
): Promise<void> {
  await nextTick()
  const otra = accion === 'Subir' ? 'Bajar' : 'Subir'
  for (const etiqueta of [
    `${accion} paso ${paso} de ${workflow}`,
    `${otra} paso ${paso} de ${workflow}`,
  ]) {
    const boton = [...document.querySelectorAll<HTMLButtonElement>('button[aria-label]')].find(
      (b) => b.getAttribute('aria-label') === etiqueta && !b.disabled,
    )
    if (boton) {
      boton.focus()
      return
    }
  }
}

async function mover(
  workflow: Workflow,
  origen: number,
  destino: number,
  accion?: 'Subir' | 'Bajar',
): Promise<void> {
  const paso = workflow.pasos[origen]
  if (!paso || origen === destino || destino < 0 || destino >= workflow.pasos.length) return
  const ids = workflow.pasos.map((p) => p.id)
  ids.splice(origen, 1)
  ids.splice(destino, 0, paso.id)
  anuncio.value = ''
  reordenando.value = true
  const correcto = await tienda.reordenarPasos(workflow.id, ids)
  reordenando.value = false
  if (!correcto) return
  const actualizado = tienda.workflows.find((w) => w.id === workflow.id)
  const movido = actualizado?.pasos.find((p) => p.id === paso.id)
  if (!actualizado || !movido) return
  anuncio.value = `${movido.nombre} movido a la posición ${movido.numero}`
  if (accion) await enfocarBotonDeMover(actualizado.nombre, movido.nombre, accion)
}

function alEmpezarArrastre(evento: DragEvent, workflow: Workflow, indice: number): void {
  arrastre.value = { idWorkflow: workflow.id, indice }
  if (evento.dataTransfer) {
    evento.dataTransfer.effectAllowed = 'move'
    evento.dataTransfer.setData('text/plain', String(workflow.pasos[indice]?.id ?? ''))
  }
}

// Solo se puede soltar sobre pasos del mismo workflow.
function alArrastrarSobre(evento: DragEvent, workflow: Workflow, indice: number): void {
  if (arrastre.value?.idWorkflow !== workflow.id) return
  evento.preventDefault()
  if (evento.dataTransfer) evento.dataTransfer.dropEffect = 'move'
  destinoArrastre.value = { idWorkflow: workflow.id, indice }
}

function alSalirDeFila(workflow: Workflow, indice: number): void {
  const actual = destinoArrastre.value
  if (actual?.idWorkflow === workflow.id && actual.indice === indice) destinoArrastre.value = null
}

function alSoltar(evento: DragEvent, workflow: Workflow, indice: number): void {
  evento.preventDefault()
  const origen = arrastre.value
  terminarArrastre()
  if (origen?.idWorkflow === workflow.id) void mover(workflow, origen.indice, indice)
}

function terminarArrastre(): void {
  arrastre.value = null
  destinoArrastre.value = null
}

// Dónde se pinta la línea de destino: antes de la fila si el paso sube y
// después si baja, que es donde quedará al soltarlo.
function posicionDestino(workflow: Workflow, indice: number): 'antes' | 'despues' | undefined {
  const origen = arrastre.value
  const destino = destinoArrastre.value
  if (!origen || !destino || origen.idWorkflow !== workflow.id) return undefined
  if (destino.idWorkflow !== workflow.id) return undefined
  if (destino.indice !== indice || origen.indice === indice) return undefined
  return indice < origen.indice ? 'antes' : 'despues'
}

function esArrastrado(workflow: Workflow, indice: number): boolean {
  return arrastre.value?.idWorkflow === workflow.id && arrastre.value.indice === indice
}
</script>

<template>
  <section class="max-w-3xl">
    <RouterLink
      to="/ajustes"
      class="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 text-sm"
    >
      <ArrowLeft class="size-4" aria-hidden="true" />
      Volver a Ajustes
    </RouterLink>
    <h2 class="mt-2 text-xl font-semibold">Workflows</h2>
    <p class="text-muted-foreground mt-1 text-sm">
      Pasos que se realizan en orden y que se añaden como subtareas a las tareas con ese workflow.
      Arrastra un paso o usa los botones Subir y Bajar para cambiar su orden.
    </p>

    <form
      aria-label="Añadir workflow"
      class="mt-6 flex flex-wrap items-end gap-2"
      novalidate
      @submit.prevent="anadirWorkflow"
    >
      <div class="grid min-w-0 flex-1 gap-1.5">
        <Label :for="ID_WORKFLOW_NUEVO">Nombre del workflow</Label>
        <Input
          :id="ID_WORKFLOW_NUEVO"
          v-model="nombreWorkflowNuevo"
          required
          :maxlength="LONGITUD_MAXIMA"
          autocomplete="off"
          :aria-invalid="errorWorkflowNuevo ? true : undefined"
        />
      </div>
      <Button type="submit" :disabled="guardandoWorkflow">Añadir workflow</Button>
    </form>
    <p v-if="errorWorkflowNuevo" class="text-destructive mt-2 text-sm" role="alert">
      {{ errorWorkflowNuevo }}
    </p>

    <p v-if="tienda.error" class="text-destructive mt-4 text-sm" role="alert">{{ tienda.error }}</p>

    <p v-if="!tienda.cargando && workflows.length === 0" class="text-muted-foreground mt-6 text-sm">
      Todavía no hay workflows.
    </p>

    <ul v-else class="mt-6 grid gap-4" aria-label="Workflows">
      <li
        v-for="workflow in workflows"
        :key="workflow.id"
        data-workflow
        class="bg-background grid gap-3 rounded-lg border p-4"
      >
        <form
          v-if="editando('workflow', workflow.id)"
          :aria-label="`Renombrar workflow ${workflow.nombre}`"
          class="flex flex-wrap items-center gap-2"
          novalidate
          @submit.prevent="guardarWorkflow(workflow)"
        >
          <Input
            :id="`nombre-workflow-${workflow.id}`"
            v-model="nombreEditando"
            class="min-w-0 flex-1"
            required
            :maxlength="LONGITUD_MAXIMA"
            autocomplete="off"
            :aria-label="`Nuevo nombre del workflow ${workflow.nombre}`"
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
        <div v-else class="flex flex-wrap items-center gap-2">
          <h3 class="min-w-0 flex-1 text-base font-semibold break-words">{{ workflow.nombre }}</h3>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            :aria-label="`Renombrar workflow ${workflow.nombre}`"
            @click="empezarEdicion('workflow', workflow.id, workflow.nombre)"
          >
            <Pencil aria-hidden="true" />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            :aria-label="`Eliminar workflow ${workflow.nombre}`"
            @click="pedirEliminarWorkflow(workflow)"
          >
            <Trash2 aria-hidden="true" />
          </Button>
        </div>

        <p v-if="workflow.pasos.length === 0" class="text-muted-foreground text-sm">
          Este workflow todavía no tiene pasos.
        </p>
        <ol v-else class="grid gap-2" :aria-label="`Pasos de ${workflow.nombre}`">
          <li
            v-for="(paso, indice) in workflow.pasos"
            :key="paso.id"
            data-paso
            :data-destino="posicionDestino(workflow, indice)"
            :draggable="editando('paso', paso.id) ? 'false' : 'true'"
            :class="[
              'bg-background flex items-center gap-2 rounded-md border p-2',
              esArrastrado(workflow, indice) && 'opacity-50',
              posicionDestino(workflow, indice) === 'antes' && 'border-t-primary border-t-4',
              posicionDestino(workflow, indice) === 'despues' && 'border-b-primary border-b-4',
            ]"
            @dragstart="alEmpezarArrastre($event, workflow, indice)"
            @dragover="alArrastrarSobre($event, workflow, indice)"
            @dragleave="alSalirDeFila(workflow, indice)"
            @drop="alSoltar($event, workflow, indice)"
            @dragend="terminarArrastre"
          >
            <span data-asa class="text-muted-foreground cursor-grab px-1" aria-hidden="true">
              <GripVertical class="size-4" />
            </span>

            <form
              v-if="editando('paso', paso.id)"
              :aria-label="`Renombrar paso ${paso.nombre} de ${workflow.nombre}`"
              class="flex flex-1 flex-wrap items-center gap-2"
              novalidate
              @submit.prevent="guardarPaso(workflow, paso)"
            >
              <span class="tabular-nums">{{ paso.numero }}.</span>
              <Input
                :id="`nombre-paso-${paso.id}`"
                v-model="nombreEditando"
                class="min-w-0 flex-1"
                required
                :maxlength="LONGITUD_MAXIMA"
                autocomplete="off"
                :aria-label="`Nuevo nombre del paso ${paso.nombre} de ${workflow.nombre}`"
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
                :aria-label="`Subir paso ${paso.nombre} de ${workflow.nombre}`"
                :disabled="indice === 0 || reordenando"
                @click="mover(workflow, indice, indice - 1, 'Subir')"
              >
                <ArrowUp aria-hidden="true" />
              </Button>
              <Button
                type="button"
                size="icon"
                variant="ghost"
                :aria-label="`Bajar paso ${paso.nombre} de ${workflow.nombre}`"
                :disabled="indice === workflow.pasos.length - 1 || reordenando"
                @click="mover(workflow, indice, indice + 1, 'Bajar')"
              >
                <ArrowDown aria-hidden="true" />
              </Button>
              <Button
                type="button"
                size="icon"
                variant="ghost"
                :aria-label="`Renombrar paso ${paso.nombre} de ${workflow.nombre}`"
                @click="empezarEdicion('paso', paso.id, paso.nombre)"
              >
                <Pencil aria-hidden="true" />
              </Button>
              <Button
                type="button"
                size="icon"
                variant="ghost"
                :aria-label="`Eliminar paso ${paso.nombre} de ${workflow.nombre}`"
                @click="pedirEliminarPaso(workflow, paso)"
              >
                <Trash2 aria-hidden="true" />
              </Button>
            </template>
          </li>
        </ol>

        <form
          :aria-label="`Añadir paso a ${workflow.nombre}`"
          class="flex flex-wrap items-end gap-2"
          novalidate
          @submit.prevent="anadirPaso(workflow)"
        >
          <div class="grid min-w-0 flex-1 gap-1.5">
            <Label :for="idPasoNuevo(workflow)">Nuevo paso</Label>
            <Input
              :id="idPasoNuevo(workflow)"
              v-model="nombresPasoNuevo[workflow.id]"
              required
              :maxlength="LONGITUD_MAXIMA"
              autocomplete="off"
              :aria-label="`Nuevo paso de ${workflow.nombre}`"
              :aria-invalid="erroresPasoNuevo[workflow.id] ? true : undefined"
            />
          </div>
          <Button type="submit" variant="outline" :aria-label="`Añadir paso a ${workflow.nombre}`"
            >Añadir paso</Button
          >
          <p
            v-if="erroresPasoNuevo[workflow.id]"
            class="text-destructive w-full text-sm"
            role="alert"
          >
            {{ erroresPasoNuevo[workflow.id] }}
          </p>
        </form>
      </li>
    </ul>

    <p class="sr-only" aria-live="polite">{{ anuncio }}</p>

    <DialogoConfirmacion
      :abierto="workflowAEliminar !== null"
      :titulo="`¿Eliminar el workflow ${workflowAEliminar?.nombre ?? ''}?`"
      :descripcion="DESCRIPCION_ELIMINAR_WORKFLOW"
      texto-confirmar="Eliminar"
      :procesando="procesando"
      :error="errorDialogo"
      @update:abierto="alCambiarConfirmacion"
      @confirmar="confirmarEliminarWorkflow"
      @cierre-foco="alDevolverFoco"
    />

    <DialogoConfirmacion
      :abierto="pasoAEliminar !== null"
      :titulo="`¿Eliminar el paso ${pasoAEliminar?.paso.nombre ?? ''}?`"
      :descripcion="descripcionEliminarPaso"
      texto-confirmar="Eliminar"
      :procesando="procesando"
      :error="errorDialogo"
      @update:abierto="alCambiarConfirmacion"
      @confirmar="confirmarEliminarPaso"
      @cierre-foco="alDevolverFoco"
    />
  </section>
</template>
