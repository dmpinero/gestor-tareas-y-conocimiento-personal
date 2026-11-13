<script setup lang="ts">
/**
 * Histórico de comentarios de una tarea, de una subtarea o de un paso de un
 * workflow: lista cronológica
 * agrupada por día y un campo para añadir comentarios nuevos (también con
 * Ctrl/Cmd+Enter). Cada comentario se puede editar o eliminar en línea, con
 * confirmación.
 *
 * `ruta` es el recurso de la colección (`/tareas/5/comentarios`,
 * `/tareas/5/subtareas/9/comentarios` o `/workflows/2/pasos/7/comentarios`); carga sus datos al montarse y cada vez
 * que cambia. `contexto` (p. ej. "de la subtarea Revisar") se añade a los
 * nombres accesibles para que no se repitan si hay varios históricos a la vez.
 * Emite `actualizados` con el número de comentarios tras cargarlos, añadir o
 * eliminar uno.
 */
import { Pencil, SendHorizontal, Trash } from '@lucide/vue'
import { computed, nextTick, ref, useId, useTemplateRef, watch } from 'vue'

import { clienteApi, ErrorApi } from '@/api/cliente'
import { Button } from '@/componentes/ui/button'
import { Textarea } from '@/componentes/ui/textarea'
import {
  agruparComentariosPorDia,
  formatearEdicionComentario,
  type Comentario,
  type ComentarioMostrado,
} from '@/lib/comentarios'

const LONGITUD_MAXIMA = 500
const ERROR_TEXTO_VACIO = 'El comentario no puede estar vacío.'

const props = defineProps<{
  ruta: string
  contexto?: string
}>()
const emit = defineEmits<{ actualizados: [total: number] }>()

// Sufijo de los nombres accesibles: vacío si no hay contexto.
const sufijo = computed(() => (props.contexto ? ` ${props.contexto}` : ''))

const idBase = useId()
const idTitulo = `${idBase}-titulo`
const idContador = `${idBase}-contador`
const idCampo = `${idBase}-campo`

const comentarios = ref<Comentario[]>([])
const cargando = ref(false)
const errorCarga = ref<string | null>(null)
const texto = ref('')
const enviando = ref(false)
const errorEnvio = ref<string | null>(null)
const anuncio = ref('')

const contenedorHistorial = useTemplateRef<HTMLElement>('contenedorHistorial')

const grupos = computed(() => agruparComentariosPorDia(comentarios.value))
const puedeEnviar = computed(() => texto.value.trim() !== '' && !enviando.value)

function mensajeDe(error: unknown): string {
  if (error instanceof ErrorApi || error instanceof Error) return error.message
  return String(error)
}

async function desplazarAlFinal(): Promise<void> {
  await nextTick()
  const elemento = contenedorHistorial.value
  if (!elemento) return
  try {
    elemento.scrollTop = elemento.scrollHeight
  } catch {
    // Algunos entornos (p. ej. jsdom) no implementan el desplazamiento.
  }
}

// Cada carga recibe un número; solo la más reciente puede escribir el estado,
// para que la respuesta tardía de otra tarea no pise la actual.
let cargaActual = 0

async function cargar(ruta: string): Promise<void> {
  const numeroCarga = ++cargaActual
  cargando.value = true
  errorCarga.value = null
  errorEnvio.value = null
  cerrarAcciones()
  comentarios.value = []
  try {
    const datos = await clienteApi.obtener<Comentario[]>(ruta)
    if (numeroCarga !== cargaActual) return
    comentarios.value = datos
    emit('actualizados', datos.length)
  } catch (error) {
    if (numeroCarga !== cargaActual) return
    errorCarga.value = mensajeDe(error)
  } finally {
    if (numeroCarga === cargaActual) cargando.value = false
  }
  if (numeroCarga === cargaActual) await desplazarAlFinal()
}

async function enviar(): Promise<void> {
  if (!puedeEnviar.value) return
  const ruta = props.ruta
  enviando.value = true
  errorEnvio.value = null
  anuncio.value = ''
  try {
    const nuevo = await clienteApi.crear<Comentario>(ruta, { texto: texto.value })
    if (ruta !== props.ruta) return
    comentarios.value = [...comentarios.value, nuevo]
    emit('actualizados', comentarios.value.length)
    texto.value = ''
    anuncio.value = 'Comentario añadido'
    await desplazarAlFinal()
    // Al vaciarse el campo el botón se desactiva y, si tenía el foco, este caía
    // en el <body>: se devuelve al campo para seguir escribiendo.
    document.getElementById(idCampo)?.focus()
  } catch (error) {
    if (ruta !== props.ruta) return
    errorEnvio.value = mensajeDe(error)
  } finally {
    enviando.value = false
  }
}

function alPulsarTecla(evento: KeyboardEvent): void {
  if (evento.key !== 'Enter' || !(evento.ctrlKey || evento.metaKey)) return
  evento.preventDefault()
  void enviar()
}

// --- Editar y eliminar, con confirmación en línea -------------------------
// Se confirma dentro del propio comentario y no con otra modal: el detalle ya
// es una modal y anidar otra complica el foco y el Escape. Solo hay una acción
// abierta a la vez; abrir otra descarta la anterior.
const idEditando = ref<number | null>(null)
const textoEdicion = ref('')
const confirmandoEdicion = ref(false)
const idConfirmandoEliminar = ref<number | null>(null)
const procesando = ref(false)
// Error de la última acción sobre un comentario, junto a él.
const errorAccion = ref<{ id: number; mensaje: string } | null>(null)

const idCampoEdicion = `${idBase}-edicion`
const idContadorEdicion = `${idBase}-contador-edicion`
const idCancelarConfirmacion = `${idBase}-cancelar-confirmacion`

function idBotonEditar(id: number): string {
  return `${idBase}-editar-${id}`
}

function idBotonEliminar(id: number): string {
  return `${idBase}-eliminar-${id}`
}

function descripcionEdicion(editado: string): string {
  return formatearEdicionComentario(editado)
}

function cerrarAcciones(): void {
  idEditando.value = null
  textoEdicion.value = ''
  confirmandoEdicion.value = false
  idConfirmandoEliminar.value = null
  errorAccion.value = null
}

async function enfocar(id: string): Promise<void> {
  await nextTick()
  document.getElementById(id)?.focus()
}

async function abrirEdicion(comentario: ComentarioMostrado): Promise<void> {
  cerrarAcciones()
  idEditando.value = comentario.id
  textoEdicion.value = comentario.texto
  await enfocar(idCampoEdicion)
}

async function cancelarEdicion(id: number): Promise<void> {
  cerrarAcciones()
  await enfocar(idBotonEditar(id))
}

async function pedirConfirmacionEdicion(id: number): Promise<void> {
  if (procesando.value) return
  if (textoEdicion.value.trim() === '') {
    errorAccion.value = { id, mensaje: ERROR_TEXTO_VACIO }
    return
  }
  errorAccion.value = null
  confirmandoEdicion.value = true
  await enfocar(idCancelarConfirmacion)
}

async function volverAEdicion(): Promise<void> {
  confirmandoEdicion.value = false
  await enfocar(idCampoEdicion)
}

async function confirmarEdicion(id: number): Promise<void> {
  if (procesando.value) return
  const ruta = props.ruta
  procesando.value = true
  anuncio.value = ''
  try {
    const editado = await clienteApi.actualizar<Comentario>(`${ruta}/${id}`, {
      texto: textoEdicion.value,
    })
    if (ruta !== props.ruta) return
    comentarios.value = comentarios.value.map((comentario) =>
      comentario.id === id ? editado : comentario,
    )
    anuncio.value = 'Comentario actualizado'
    await cancelarEdicion(id)
  } catch (error) {
    if (ruta !== props.ruta) return
    // Se conserva el texto en edición para poder reintentar.
    errorAccion.value = { id, mensaje: `No se pudo guardar el comentario: ${mensajeDe(error)}` }
    await volverAEdicion()
  } finally {
    procesando.value = false
  }
}

async function pedirConfirmacionEliminar(comentario: ComentarioMostrado): Promise<void> {
  cerrarAcciones()
  idConfirmandoEliminar.value = comentario.id
  await enfocar(idCancelarConfirmacion)
}

async function cancelarEliminar(id: number): Promise<void> {
  cerrarAcciones()
  await enfocar(idBotonEliminar(id))
}

async function confirmarEliminar(id: number): Promise<void> {
  if (procesando.value) return
  const ruta = props.ruta
  procesando.value = true
  anuncio.value = ''
  try {
    await clienteApi.eliminar<void>(`${ruta}/${id}`)
    if (ruta !== props.ruta) return
    cerrarAcciones()
    comentarios.value = comentarios.value.filter((comentario) => comentario.id !== id)
    emit('actualizados', comentarios.value.length)
    anuncio.value = 'Comentario eliminado'
    await nextTick()
    // El comentario ya no está: el foco pasa al historial o, si se ha quedado
    // vacío, al campo de comentario nuevo (nunca al <body>).
    ;(contenedorHistorial.value ?? document.getElementById(idCampo))?.focus()
  } catch (error) {
    if (ruta !== props.ruta) return
    idConfirmandoEliminar.value = null
    errorAccion.value = { id, mensaje: `No se pudo eliminar el comentario: ${mensajeDe(error)}` }
    await enfocar(idBotonEliminar(id))
  } finally {
    procesando.value = false
  }
}
// Al final: la carga inmediata usa el estado de las acciones declarado arriba.
watch(() => props.ruta, cargar, { immediate: true })
</script>

<template>
  <section :aria-labelledby="idTitulo" class="flex min-h-0 flex-col gap-3">
    <h3 :id="idTitulo" class="text-base font-semibold">
      Comentarios<span v-if="props.contexto" class="sr-only">{{ sufijo }}</span>
    </h3>

    <p v-if="cargando" class="text-muted-foreground text-sm">Cargando comentarios…</p>
    <p v-else-if="errorCarga" class="text-destructive text-sm" role="alert">
      No se pudieron cargar los comentarios: {{ errorCarga }}
    </p>
    <p v-else-if="comentarios.length === 0" class="text-muted-foreground text-sm">
      Todavía no hay comentarios.
    </p>
    <!-- Enfocable y con nombre: con muchos comentarios se desplaza y debe poder
         recorrerse con el teclado (axe `scrollable-region-focusable`). -->
    <div
      v-else
      ref="contenedorHistorial"
      class="max-h-96 overflow-y-auto pr-1"
      role="region"
      :aria-label="`Comentarios anteriores${sufijo}`"
      tabindex="0"
    >
      <ol :aria-label="`Historial de comentarios${sufijo}`" class="flex flex-col gap-4">
        <li v-for="grupo in grupos" :key="grupo.clave" class="flex flex-col gap-2">
          <h4
            :id="`${idBase}-dia-${grupo.clave}`"
            class="text-muted-foreground border-b pb-1 text-xs font-medium first-letter:uppercase"
          >
            {{ grupo.etiqueta }}
          </h4>
          <ol :aria-labelledby="`${idBase}-dia-${grupo.clave}`" class="flex flex-col gap-2">
            <li
              v-for="comentario in grupo.comentarios"
              :key="comentario.id"
              class="bg-muted/50 rounded-md px-3 py-2"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="text-muted-foreground text-xs">
                  <time :datetime="comentario.creado">{{ comentario.hora }}</time>
                  <span
                    v-if="comentario.editado"
                    data-testid="marca-editado"
                    class="ml-1"
                    :title="`Editado el ${descripcionEdicion(comentario.editado)}`"
                    >(editado<span class="sr-only">
                      el {{ descripcionEdicion(comentario.editado) }}</span
                    >)</span
                  >
                </span>
                <div v-if="idEditando !== comentario.id" class="flex gap-1">
                  <Button
                    :id="idBotonEditar(comentario.id)"
                    variant="ghost"
                    size="icon"
                    class="size-7"
                    :aria-label="`Editar comentario ${comentario.referencia}${sufijo}`"
                    @click="abrirEdicion(comentario)"
                  >
                    <Pencil aria-hidden="true" />
                  </Button>
                  <Button
                    :id="idBotonEliminar(comentario.id)"
                    variant="ghost"
                    size="icon"
                    class="size-7"
                    :aria-label="`Eliminar comentario ${comentario.referencia}${sufijo}`"
                    @click="pedirConfirmacionEliminar(comentario)"
                  >
                    <Trash aria-hidden="true" />
                  </Button>
                </div>
              </div>

              <form
                v-if="idEditando === comentario.id"
                class="mt-1 flex flex-col gap-1"
                :aria-label="`Editar comentario${sufijo}`"
                novalidate
                @submit.prevent="pedirConfirmacionEdicion(comentario.id)"
                @keydown.esc.stop.prevent="cancelarEdicion(comentario.id)"
              >
                <Textarea
                  :id="idCampoEdicion"
                  v-model="textoEdicion"
                  :aria-label="`Nuevo texto del comentario${sufijo}`"
                  :maxlength="LONGITUD_MAXIMA"
                  :aria-describedby="idContadorEdicion"
                  :aria-invalid="errorAccion?.mensaje === ERROR_TEXTO_VACIO ? 'true' : undefined"
                  :readonly="confirmandoEdicion"
                  rows="3"
                />
                <span :id="idContadorEdicion" class="text-muted-foreground self-end text-xs">
                  {{ textoEdicion.length }}/{{ LONGITUD_MAXIMA }}
                </span>
                <div
                  v-if="confirmandoEdicion"
                  role="group"
                  :aria-label="`¿Guardar los cambios del comentario${sufijo}?`"
                  class="flex flex-wrap items-center justify-end gap-2"
                  @keydown.esc.stop.prevent="volverAEdicion"
                >
                  <span class="text-sm" aria-hidden="true"
                    >¿Guardar los cambios del comentario?</span
                  >
                  <Button
                    type="button"
                    size="sm"
                    :disabled="procesando"
                    @click="confirmarEdicion(comentario.id)"
                    >Guardar</Button
                  >
                  <Button
                    :id="idCancelarConfirmacion"
                    type="button"
                    variant="outline"
                    size="sm"
                    @click="volverAEdicion"
                    >Cancelar</Button
                  >
                </div>
                <div v-else class="flex justify-end gap-2">
                  <Button type="submit" size="sm">Guardar</Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    @click="cancelarEdicion(comentario.id)"
                    >Cancelar</Button
                  >
                </div>
              </form>
              <p v-else class="text-sm break-words whitespace-pre-wrap">{{ comentario.texto }}</p>

              <div
                v-if="idConfirmandoEliminar === comentario.id"
                role="group"
                :aria-label="`¿Eliminar el comentario${sufijo}?`"
                class="mt-1 flex flex-wrap items-center justify-end gap-2"
                @keydown.esc.stop.prevent="cancelarEliminar(comentario.id)"
              >
                <span class="text-sm" aria-hidden="true">¿Eliminar el comentario?</span>
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  :disabled="procesando"
                  @click="confirmarEliminar(comentario.id)"
                  >Eliminar</Button
                >
                <Button
                  :id="idCancelarConfirmacion"
                  type="button"
                  variant="outline"
                  size="sm"
                  @click="cancelarEliminar(comentario.id)"
                  >Cancelar</Button
                >
              </div>
              <span
                v-if="errorAccion?.id === comentario.id"
                role="alert"
                class="text-destructive mt-1 block text-sm"
                >{{ errorAccion.mensaje }}</span
              >
            </li>
          </ol>
        </li>
      </ol>
    </div>

    <form class="flex flex-col gap-1" @submit.prevent="enviar">
      <div class="flex items-end gap-2">
        <Textarea
          :id="idCampo"
          v-model="texto"
          :aria-label="`Escribe un comentario${sufijo}`"
          placeholder="Escribe un comentario"
          :maxlength="LONGITUD_MAXIMA"
          :aria-describedby="idContador"
          rows="2"
          @keydown="alPulsarTecla"
        />
        <Button
          type="submit"
          size="icon"
          :aria-label="`Enviar comentario${sufijo}`"
          :disabled="!puedeEnviar"
        >
          <SendHorizontal aria-hidden="true" />
        </Button>
      </div>
      <p :id="idContador" class="text-muted-foreground self-end text-xs">
        {{ texto.length }}/{{ LONGITUD_MAXIMA }}
      </p>
      <p v-if="errorEnvio" class="text-destructive text-sm" role="alert">
        No se pudo enviar el comentario: {{ errorEnvio }}
      </p>
    </form>

    <p class="sr-only" aria-live="polite">{{ anuncio }}</p>
  </section>
</template>
