<script setup lang="ts">
/**
 * Histórico de comentarios de una tarea: lista cronológica agrupada por día
 * y un campo para añadir comentarios nuevos (también con Ctrl/Cmd+Enter).
 *
 * Carga sus propios datos al montarse y cada vez que cambia `idTarea`; el
 * estado vive en el componente porque solo lo usa el detalle de una tarea.
 */
import { SendHorizontal } from '@lucide/vue'
import { computed, nextTick, ref, useId, useTemplateRef, watch } from 'vue'

import { clienteApi, ErrorApi } from '@/api/cliente'
import { Button } from '@/componentes/ui/button'
import { Textarea } from '@/componentes/ui/textarea'
import { agruparComentariosPorDia, type Comentario } from '@/lib/comentarios'

const LONGITUD_MAXIMA = 500

const props = defineProps<{
  idTarea: number
}>()

const idBase = useId()
const idTitulo = `${idBase}-titulo`
const idContador = `${idBase}-contador`

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

async function cargar(idTarea: number): Promise<void> {
  const numeroCarga = ++cargaActual
  cargando.value = true
  errorCarga.value = null
  errorEnvio.value = null
  comentarios.value = []
  try {
    const datos = await clienteApi.obtener<Comentario[]>(`/tareas/${idTarea}/comentarios`)
    if (numeroCarga !== cargaActual) return
    comentarios.value = datos
  } catch (error) {
    if (numeroCarga !== cargaActual) return
    errorCarga.value = mensajeDe(error)
  } finally {
    if (numeroCarga === cargaActual) cargando.value = false
  }
  if (numeroCarga === cargaActual) await desplazarAlFinal()
}

watch(() => props.idTarea, cargar, { immediate: true })

async function enviar(): Promise<void> {
  if (!puedeEnviar.value) return
  const idTarea = props.idTarea
  enviando.value = true
  errorEnvio.value = null
  anuncio.value = ''
  try {
    const nuevo = await clienteApi.crear<Comentario>(`/tareas/${idTarea}/comentarios`, {
      texto: texto.value,
    })
    if (idTarea !== props.idTarea) return
    comentarios.value = [...comentarios.value, nuevo]
    texto.value = ''
    anuncio.value = 'Comentario añadido'
    await desplazarAlFinal()
  } catch (error) {
    if (idTarea !== props.idTarea) return
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
</script>

<template>
  <section :aria-labelledby="idTitulo" class="flex min-h-0 flex-col gap-3">
    <h3 :id="idTitulo" class="text-base font-semibold">Comentarios</h3>

    <p v-if="cargando" class="text-muted-foreground text-sm">Cargando comentarios…</p>
    <p v-else-if="errorCarga" class="text-destructive text-sm" role="alert">
      No se pudieron cargar los comentarios: {{ errorCarga }}
    </p>
    <p v-else-if="comentarios.length === 0" class="text-muted-foreground text-sm">
      Todavía no hay comentarios.
    </p>
    <div v-else ref="contenedorHistorial" class="max-h-96 overflow-y-auto pr-1">
      <ol aria-label="Historial de comentarios" class="flex flex-col gap-4">
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
              <time :datetime="comentario.creado" class="text-muted-foreground text-xs">{{
                comentario.hora
              }}</time>
              <p class="text-sm break-words whitespace-pre-wrap">{{ comentario.texto }}</p>
            </li>
          </ol>
        </li>
      </ol>
    </div>

    <form class="flex flex-col gap-1" @submit.prevent="enviar">
      <div class="flex items-end gap-2">
        <Textarea
          v-model="texto"
          aria-label="Escribe un comentario"
          placeholder="Escribe un comentario"
          :maxlength="LONGITUD_MAXIMA"
          :aria-describedby="idContador"
          rows="2"
          @keydown="alPulsarTecla"
        />
        <Button type="submit" size="icon" aria-label="Enviar comentario" :disabled="!puedeEnviar">
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
