<script setup lang="ts">
import { Circle, CircleCheck, MessageSquare, Pencil, Plus, Trash } from '@lucide/vue'
import { createReusableTemplate, useElementSize } from '@vueuse/core'
import { computed, nextTick, reactive, ref, useTemplateRef } from 'vue'

import type { DatosEdicionSubtarea, DatosSubtarea, Subtarea, Tarea } from '@/api/tipos'
import ComentariosTarea from '@/componentes/compartido/ComentariosTarea.vue'
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

// Subtareas de una tarea: listado, alta en línea, edición en línea (con
// confirmación), marcar como resuelta, eliminar (con confirmación) y un panel
// de comentarios por subtarea. Lee y escribe a través del almacén de tareas; la tarea actualizada
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
const idPersonas = computed(() => `${idBase.value}-personas`)

// --- Tabla o tarjetas según el ancho disponible ---------------------------
// La tabla necesita unos 380 px con la columna de acciones (más si los nombres
// son largos); por debajo de 32rem (512 px) se desborda o queda justa, así que
// se pasa a una lista de tarjetas. Se mide el contenedor y no la ventana: en el
// detalle, la columna de comentarios estrecha el hueco aunque la ventana sea
// ancha. Se pinta una sola de las dos vistas (v-if) para no duplicar controles
// ni nombres accesibles. Sin medida (ancho 0, p. ej. en jsdom) se usa la tabla.
const ANCHO_MINIMO_TABLA = 512
const raiz = useTemplateRef<HTMLElement>('raiz')
const { width: ancho } = useElementSize(raiz, undefined, { box: 'border-box' })
const enTarjetas = computed(() => ancho.value > 0 && ancho.value < ANCHO_MINIMO_TABLA)

// Piezas compartidas por la tabla y las tarjetas, para no duplicar el marcado.
const plantillaAlternar = createReusableTemplate<{ subtarea: Subtarea }>()
const plantillaAcciones = createReusableTemplate<{ subtarea: Subtarea }>()
const plantillaEdicion = createReusableTemplate<{ subtarea: Subtarea }>()
const plantillaComentarios = createReusableTemplate<{ subtarea: Subtarea }>()

function claseResuelta(subtarea: Subtarea): string {
  return subtarea.resuelta ? 'text-muted-foreground line-through' : ''
}

const sinResolver = computed(
  () => props.tarea.subtareas.filter((subtarea) => !subtarea.resuelta).length,
)

function textoOVacio(valor: string | number | null): string {
  return valor === null || valor === '' ? VACIO : String(valor)
}

async function alternar(subtarea: Subtarea): Promise<void> {
  await tienda.alternarSubtarea(props.tarea.id, subtarea.id)
}

// --- Comentarios de cada subtarea -----------------------------------------
// Se despliegan bajo la subtarea (una fila a todo lo ancho en la tabla, una
// sección dentro de la tarjeta), de una en una. El histórico se carga y guarda
// en su propio componente; cuando cambia el número de comentarios, el almacén
// ajusta el de la subtarea para que el botón lo refleje sin pedir la tarea.
const idComentariosAbiertos = ref<number | null>(null)

function idPanelComentarios(subtarea: Subtarea): string {
  return `${idBase.value}-comentarios-${subtarea.id}`
}

function alternarComentarios(subtarea: Subtarea): void {
  idComentariosAbiertos.value = idComentariosAbiertos.value === subtarea.id ? null : subtarea.id
}

function alActualizarComentarios(subtarea: Subtarea, total: number): void {
  tienda.fijarComentariosSubtarea(props.tarea.id, subtarea.id, total)
}

// --- Eliminar, con confirmación en la propia fila -------------------------
// Se confirma en línea y no con otra modal: el detalle ya es una modal y
// anidar otra complica el foco y el Escape.
const idConfirmando = ref<number | null>(null)

function idBotonEliminar(subtarea: Subtarea): string {
  return `${idBase.value}-eliminar-${subtarea.id}`
}

async function pedirConfirmacion(subtarea: Subtarea): Promise<void> {
  cerrarEdicion()
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
  if (eliminada && idComentariosAbiertos.value === subtarea.id) idComentariosAbiertos.value = null
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
interface FormularioSubtarea {
  nombre: string
  asignado: string
  prioridad: string | number | null
}
const formulario = reactive<FormularioSubtarea>({ nombre: '', asignado: '', prioridad: '' })

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

// Mismas reglas para el alta y la edición.
function validar(campos: FormularioSubtarea): DatosSubtarea | { error: string } {
  const nombre = campos.nombre.trim()
  if (nombre === '') return { error: ERROR_NOMBRE_OBLIGATORIO }
  if (nombre.length > MAX_NOMBRE) return { error: ERROR_NOMBRE_LARGO }
  const datos: DatosSubtarea = { nombre }

  const asignado = campos.asignado.trim()
  if (asignado.length > MAX_PERSONA) return { error: ERROR_PERSONA_LARGA }
  if (asignado !== '') datos.asignado = asignado

  if (campos.prioridad !== null && campos.prioridad !== '') {
    const prioridad = Number(campos.prioridad)
    if (!Number.isInteger(prioridad) || prioridad < 1 || prioridad > 5) {
      return { error: ERROR_PRIORIDAD }
    }
    datos.prioridad = prioridad
  }
  return datos
}

async function guardar(): Promise<void> {
  if (guardando.value) return
  const resultado = validar(formulario)
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

// --- Edición en línea, con confirmación ----------------------------------
// La fila se convierte en un formulario relleno. "Guardar" valida y pide
// confirmación en la propia fila; solo al confirmar se envía el reemplazo
// completo (persona o prioridad vacías se envían como `null` para vaciarlas).
// Cancelar o Escape en la confirmación vuelven al formulario; en el formulario
// cierran la edición y devuelven el foco al botón de editar.
const idEditando = ref<number | null>(null)
const confirmandoEdicion = ref(false)
const guardandoEdicion = ref(false)
const errorEdicion = ref<string | null>(null)
const edicion = reactive<FormularioSubtarea>({ nombre: '', asignado: '', prioridad: '' })
let datosEdicion: DatosEdicionSubtarea | null = null

function idBotonEditar(idSubtarea: number): string {
  return `${idBase.value}-editar-${idSubtarea}`
}

function idCampoEdicion(subtarea: Subtarea, campo: 'nombre' | 'asignado' | 'prioridad'): string {
  return `${idBase.value}-edicion-${subtarea.id}-${campo}`
}

function cerrarEdicion(): void {
  idEditando.value = null
  confirmandoEdicion.value = false
  errorEdicion.value = null
  datosEdicion = null
}

async function enfocarNombreEdicion(subtarea: Subtarea): Promise<void> {
  await nextTick()
  document.getElementById(idCampoEdicion(subtarea, 'nombre'))?.focus()
}

async function abrirEdicion(subtarea: Subtarea): Promise<void> {
  idConfirmando.value = null
  cerrarEdicion()
  edicion.nombre = subtarea.nombre
  edicion.asignado = subtarea.asignado ?? ''
  edicion.prioridad = subtarea.prioridad ?? ''
  idEditando.value = subtarea.id
  await enfocarNombreEdicion(subtarea)
}

async function cancelarEdicion(subtarea: Subtarea): Promise<void> {
  cerrarEdicion()
  await nextTick()
  document.getElementById(idBotonEditar(subtarea.id))?.focus()
}

async function pedirConfirmacionEdicion(): Promise<void> {
  if (guardandoEdicion.value) return
  const resultado = validar(edicion)
  if ('error' in resultado) {
    errorEdicion.value = resultado.error
    return
  }
  errorEdicion.value = null
  datosEdicion = {
    nombre: resultado.nombre,
    asignado: resultado.asignado ?? null,
    prioridad: resultado.prioridad ?? null,
  }
  confirmandoEdicion.value = true
  await nextTick()
  document.getElementById(`${idBase.value}-cancelar-guardar`)?.focus()
}

async function volverAEdicion(subtarea: Subtarea): Promise<void> {
  confirmandoEdicion.value = false
  await enfocarNombreEdicion(subtarea)
}

async function confirmarEdicion(subtarea: Subtarea): Promise<void> {
  if (guardandoEdicion.value || !datosEdicion) return
  guardandoEdicion.value = true
  try {
    const editada = await tienda.editarSubtarea(props.tarea.id, subtarea.id, datosEdicion)
    if (editada) {
      await cancelarEdicion(subtarea)
    } else {
      // Se conserva lo escrito; el mensaje queda en `tienda.error`.
      await volverAEdicion(subtarea)
    }
  } finally {
    guardandoEdicion.value = false
  }
}
</script>

<template>
  <section ref="raiz" class="@container" :aria-labelledby="`${idBase}-titulo`">
    <plantillaAlternar.define v-slot="{ subtarea }">
      <Button
        variant="ghost"
        size="icon"
        class="size-8 shrink-0"
        :aria-pressed="subtarea.resuelta ? 'true' : 'false'"
        :aria-label="`Marcar como resuelta la subtarea ${subtarea.nombre}`"
        @click="alternar(subtarea)"
      >
        <CircleCheck v-if="subtarea.resuelta" class="text-success" aria-hidden="true" />
        <Circle v-else aria-hidden="true" />
      </Button>
    </plantillaAlternar.define>

    <plantillaAcciones.define v-slot="{ subtarea }">
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
      <div v-else class="flex items-center justify-end gap-1">
        <Button
          variant="ghost"
          size="sm"
          class="h-8 gap-1 px-2"
          :aria-label="`Comentarios de la subtarea ${subtarea.nombre}`"
          :aria-expanded="idComentariosAbiertos === subtarea.id ? 'true' : 'false'"
          :aria-controls="idPanelComentarios(subtarea)"
          @click="alternarComentarios(subtarea)"
        >
          <MessageSquare aria-hidden="true" />
          <span v-if="subtarea.comentarios > 0" data-testid="numero-comentarios-subtarea">{{
            subtarea.comentarios
          }}</span>
        </Button>
        <Button
          :id="idBotonEditar(subtarea.id)"
          variant="ghost"
          size="icon"
          class="size-8"
          :aria-label="`Editar subtarea ${subtarea.nombre}`"
          @click="abrirEdicion(subtarea)"
        >
          <Pencil aria-hidden="true" />
        </Button>
        <Button
          :id="idBotonEliminar(subtarea)"
          variant="ghost"
          size="icon"
          class="size-8"
          :aria-label="`Eliminar subtarea ${subtarea.nombre}`"
          @click="pedirConfirmacion(subtarea)"
        >
          <Trash aria-hidden="true" />
        </Button>
      </div>
    </plantillaAcciones.define>

    <!-- Las columnas dependen del ancho del contenedor (@lg = 32rem), no de la
         ventana: en un hueco estrecho los campos se apilan a todo lo ancho. -->
    <plantillaComentarios.define v-slot="{ subtarea }">
      <div :id="idPanelComentarios(subtarea)" data-testid="comentarios-subtarea">
        <ComentariosTarea
          :ruta="`/tareas/${props.tarea.id}/subtareas/${subtarea.id}/comentarios`"
          :contexto="`de la subtarea ${subtarea.nombre}`"
          @actualizados="(total) => alActualizarComentarios(subtarea, total)"
        />
      </div>
    </plantillaComentarios.define>

    <plantillaEdicion.define v-slot="{ subtarea }">
      <form
        class="grid gap-3 @lg:grid-cols-[1fr_12rem_7rem] @lg:items-end"
        :aria-label="`Editar subtarea ${subtarea.nombre}`"
        novalidate
        @submit.prevent="pedirConfirmacionEdicion"
        @keydown.esc.stop.prevent="cancelarEdicion(subtarea)"
      >
        <div class="flex min-w-0 flex-col gap-1.5">
          <Label :for="idCampoEdicion(subtarea, 'nombre')"
            >Nuevo nombre de la subtarea {{ subtarea.nombre }}</Label
          >
          <Input
            :id="idCampoEdicion(subtarea, 'nombre')"
            v-model="edicion.nombre"
            :maxlength="MAX_NOMBRE"
            required
            :readonly="confirmandoEdicion"
            :aria-invalid="errorEdicion === ERROR_NOMBRE_OBLIGATORIO ? 'true' : undefined"
            :aria-describedby="errorEdicion ? `${idBase}-error-edicion` : undefined"
          />
        </div>
        <div class="flex min-w-0 flex-col gap-1.5">
          <Label :for="idCampoEdicion(subtarea, 'asignado')"
            >Nueva persona asignada de la subtarea {{ subtarea.nombre }}</Label
          >
          <Input
            :id="idCampoEdicion(subtarea, 'asignado')"
            v-model="edicion.asignado"
            :maxlength="MAX_PERSONA"
            :list="idPersonas"
            autocomplete="off"
            :readonly="confirmandoEdicion"
          />
        </div>
        <div class="flex min-w-0 flex-col gap-1.5">
          <Label :for="idCampoEdicion(subtarea, 'prioridad')"
            >Nueva prioridad de la subtarea {{ subtarea.nombre }}</Label
          >
          <Input
            :id="idCampoEdicion(subtarea, 'prioridad')"
            v-model="edicion.prioridad"
            type="number"
            min="1"
            max="5"
            step="1"
            :readonly="confirmandoEdicion"
            :aria-invalid="errorEdicion === ERROR_PRIORIDAD ? 'true' : undefined"
          />
        </div>
        <div
          v-if="confirmandoEdicion"
          role="group"
          :aria-label="`¿Guardar los cambios de la subtarea ${subtarea.nombre}?`"
          class="flex flex-wrap items-center gap-2 @lg:col-span-3"
          @keydown.esc.stop.prevent="volverAEdicion(subtarea)"
        >
          <span class="text-sm [overflow-wrap:anywhere]" aria-hidden="true"
            >¿Guardar los cambios de la subtarea {{ subtarea.nombre }}?</span
          >
          <Button
            type="button"
            size="sm"
            :disabled="guardandoEdicion"
            @click="confirmarEdicion(subtarea)"
            >Guardar</Button
          >
          <Button
            :id="`${idBase}-cancelar-guardar`"
            type="button"
            variant="outline"
            size="sm"
            @click="volverAEdicion(subtarea)"
            >Cancelar</Button
          >
        </div>
        <div v-else class="flex gap-2 @lg:col-span-3">
          <Button type="submit" size="sm">Guardar</Button>
          <Button type="button" variant="outline" size="sm" @click="cancelarEdicion(subtarea)"
            >Cancelar</Button
          >
        </div>
        <p
          v-if="errorEdicion"
          :id="`${idBase}-error-edicion`"
          role="alert"
          class="text-destructive text-sm @lg:col-span-3"
        >
          {{ errorEdicion }}
        </p>
      </form>
    </plantillaEdicion.define>

    <div class="mb-3 flex items-baseline gap-2">
      <h3 :id="`${idBase}-titulo`" class="text-base font-semibold">Subtareas</h3>
      <span data-testid="contador-subtareas" class="text-muted-foreground text-sm"
        >{{ sinResolver }} sin resolver</span
      >
    </div>

    <p v-if="props.tarea.subtareas.length === 0" class="text-muted-foreground text-sm">
      Esta tarea no tiene subtareas.
    </p>
    <ul v-else-if="enTarjetas" data-testid="tarjetas-subtareas" class="grid gap-2">
      <li
        v-for="subtarea in props.tarea.subtareas"
        :key="subtarea.id"
        data-testid="tarjeta-subtarea"
        class="min-w-0 rounded-md border p-3"
      >
        <plantillaEdicion.reuse v-if="idEditando === subtarea.id" :subtarea="subtarea" />
        <template v-else>
          <div class="flex items-center gap-2">
            <plantillaAlternar.reuse :subtarea="subtarea" />
            <span
              data-testid="nombre-subtarea"
              class="min-w-0 font-medium [overflow-wrap:anywhere]"
              :class="claseResuelta(subtarea)"
              >{{ subtarea.nombre }}</span
            >
          </div>
          <dl class="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
            <dt class="text-muted-foreground">Persona asignada</dt>
            <dd class="min-w-0">
              <span class="[overflow-wrap:anywhere]" :class="claseResuelta(subtarea)">{{
                textoOVacio(subtarea.asignado)
              }}</span>
            </dd>
            <dt class="text-muted-foreground">Prioridad</dt>
            <dd>
              <span :class="claseResuelta(subtarea)">{{ textoOVacio(subtarea.prioridad) }}</span>
            </dd>
          </dl>
          <div class="mt-2">
            <plantillaAcciones.reuse :subtarea="subtarea" />
          </div>
        </template>
        <div v-if="idComentariosAbiertos === subtarea.id" class="mt-3 border-t pt-3">
          <plantillaComentarios.reuse :subtarea="subtarea" />
        </div>
      </li>
    </ul>
    <Table v-else data-testid="tabla-subtareas">
      <TableHeader>
        <TableRow>
          <TableHead>Nombre</TableHead>
          <TableHead>Persona asignada</TableHead>
          <TableHead>Prioridad</TableHead>
          <TableHead><span class="sr-only">Acciones</span></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <template v-for="subtarea in props.tarea.subtareas" :key="subtarea.id">
          <TableRow>
            <TableCell v-if="idEditando === subtarea.id" colspan="4" class="whitespace-normal">
              <plantillaEdicion.reuse :subtarea="subtarea" />
            </TableCell>
            <template v-else>
              <TableCell class="whitespace-normal">
                <div class="flex items-center gap-2">
                  <plantillaAlternar.reuse :subtarea="subtarea" />
                  <span class="[overflow-wrap:anywhere]" :class="claseResuelta(subtarea)">{{
                    subtarea.nombre
                  }}</span>
                </div>
              </TableCell>
              <TableCell class="whitespace-normal">
                <span class="[overflow-wrap:anywhere]" :class="claseResuelta(subtarea)">{{
                  textoOVacio(subtarea.asignado)
                }}</span>
              </TableCell>
              <TableCell>
                <span :class="claseResuelta(subtarea)">{{ textoOVacio(subtarea.prioridad) }}</span>
              </TableCell>
              <TableCell class="text-right">
                <plantillaAcciones.reuse :subtarea="subtarea" />
              </TableCell>
            </template>
          </TableRow>
          <TableRow v-if="idComentariosAbiertos === subtarea.id">
            <TableCell colspan="4" class="bg-muted/30 whitespace-normal">
              <plantillaComentarios.reuse :subtarea="subtarea" />
            </TableCell>
          </TableRow>
        </template>
      </TableBody>
    </Table>

    <!-- Sugerencias de personas compartidas por la fila de alta y la de edición. -->
    <datalist :id="idPersonas">
      <option v-for="persona in tienda.personas" :key="persona" :value="persona" />
    </datalist>

    <!-- Cuatro columnas solo con hueco de sobra (@2xl = 42rem); si no, apilado. -->
    <form
      v-if="anadiendo"
      class="mt-3 grid gap-3 @2xl:grid-cols-[1fr_12rem_7rem_auto] @2xl:items-end"
      novalidate
      @submit.prevent="guardar"
      @keydown.esc.stop.prevent="cancelarAlta"
    >
      <div class="flex min-w-0 flex-col gap-1.5">
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
      <div class="flex min-w-0 flex-col gap-1.5">
        <Label :for="`${idBase}-asignado`">Persona asignada</Label>
        <Input
          :id="`${idBase}-asignado`"
          v-model="formulario.asignado"
          :maxlength="MAX_PERSONA"
          :list="idPersonas"
          autocomplete="off"
        />
      </div>
      <div class="flex min-w-0 flex-col gap-1.5">
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
        class="text-destructive text-sm @2xl:col-span-4"
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
