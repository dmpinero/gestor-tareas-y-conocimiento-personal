<script setup lang="ts">
import { BookOpen, RefreshCw, Search, Send, SquarePen } from '@lucide/vue'
import { computed, nextTick, onMounted, ref, watch } from 'vue'

import {
  agruparPorPagina,
  esUrlWeb,
  segmentosResaltados,
} from '@/componentes/conocimiento/busqueda'
import RespuestaMarkdown from '@/componentes/conocimiento/RespuestaMarkdown.vue'
import { Alerta } from '@/componentes/ui/alerta'
import { Button } from '@/componentes/ui/button'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'
import { Textarea } from '@/componentes/ui/textarea'
import { formatearFechaHora } from '@/lib/fechas'
import {
  LONGITUD_MAXIMA_BUSQUEDA,
  LONGITUD_MAXIMA_MENSAJE,
  useTiendaConocimiento,
} from '@/stores/conocimiento'

const SIN_RESULTADOS = 'No he encontrado nada sobre eso en tus notas de Notion.'

const tienda = useTiendaConocimiento()

const busqueda = ref('')
const pregunta = ref('')
const lista = ref<HTMLElement | null>(null)

const faltaNotion = computed(() => tienda.estado !== null && !tienda.estado.configurado.notion)
// El chat (con Claude) solo aparece si el backend tiene ANTHROPIC_API_KEY; sin
// ella, Conocimiento es solo el buscador y no avisa de esa clave.
const hayChat = computed(() => tienda.estado?.configurado.anthropic === true)
const nuncaSincronizado = computed(
  () => tienda.estado !== null && tienda.estado.ultima_sincronizacion === null,
)
const puedeBuscar = computed(() => !tienda.buscando && busqueda.value.trim() !== '')
const paginasEncontradas = computed(() =>
  tienda.resultados ? agruparPorPagina(tienda.resultados) : [],
)

function segmentos(texto: string) {
  return segmentosResaltados(texto, tienda.consultaBuscada)
}

async function buscar(): Promise<void> {
  if (!puedeBuscar.value) return
  await tienda.buscar(busqueda.value)
}

const puedeSincronizar = computed(
  () => tienda.estado?.configurado.notion === true && !tienda.sincronizando,
)
const puedeEnviar = computed(
  () => hayChat.value && !tienda.enviando && pregunta.value.trim() !== '',
)

function plural(cantidad: number, singular: string, plural: string): string {
  return `${cantidad} ${cantidad === 1 ? singular : plural}`
}

const ultimaSincronizacion = computed(() => {
  const instante = tienda.estado?.ultima_sincronizacion
  return instante ? formatearFechaHora(new Date(instante)) : 'nunca'
})

const resumenSincronizacion = computed(() => {
  const r = tienda.resultadoSincronizacion
  if (!r) return null
  return `Sincronizado: ${r.nuevas} nuevas, ${r.actualizadas} actualizadas, ${r.eliminadas} eliminadas.`
})

async function enviar(): Promise<void> {
  if (!puedeEnviar.value) return
  const texto = pregunta.value
  pregunta.value = ''
  await tienda.preguntar(texto)
}

// Enter envía; Shift+Enter (o mientras se compone un carácter con IME) hace
// un salto de línea normal.
function alPulsarTecla(evento: KeyboardEvent): void {
  if (evento.key !== 'Enter' || evento.shiftKey || evento.isComposing) return
  evento.preventDefault()
  void enviar()
}

// Lleva la lista al último mensaje cuando llega uno nuevo o crece la respuesta.
watch(
  () => {
    const ultimo = tienda.conversacion[tienda.conversacion.length - 1]
    return [tienda.conversacion.length, ultimo?.texto.length, ultimo?.fuentes?.length]
  },
  async () => {
    await nextTick()
    if (lista.value) lista.value.scrollTop = lista.value.scrollHeight
  },
)

onMounted(() => {
  void tienda.cargarEstado()
})
</script>

<template>
  <section class="flex flex-col gap-4">
    <h2 class="text-xl font-semibold">Conocimiento</h2>

    <div
      data-testid="estado-conocimiento"
      class="bg-card text-card-foreground flex flex-col gap-3 rounded-lg border p-4 shadow-xs"
    >
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div class="flex min-w-0 items-start gap-3">
          <BookOpen
            class="mt-0.5 size-5 shrink-0 text-cyan-600 dark:text-cyan-400"
            aria-hidden="true"
          />
          <div class="min-w-0 text-sm">
            <p v-if="tienda.estado" class="font-medium">
              {{ plural(tienda.estado.paginas, 'página', 'páginas') }} de Notion ({{
                plural(tienda.estado.fragmentos, 'fragmento', 'fragmentos')
              }})
            </p>
            <p v-if="tienda.estado" class="text-muted-foreground">
              Última sincronización: {{ ultimaSincronizacion }}
            </p>
            <p v-else-if="!tienda.error" class="text-muted-foreground">Cargando…</p>
          </div>
        </div>
        <Button
          variant="outline"
          :disabled="!puedeSincronizar"
          data-testid="boton-sincronizar"
          @click="tienda.sincronizar()"
        >
          <RefreshCw :class="{ 'animate-spin': tienda.sincronizando }" aria-hidden="true" />
          {{ tienda.sincronizando ? 'Sincronizando…' : 'Sincronizar con Notion' }}
        </Button>
      </div>

      <Alerta v-if="faltaNotion" variant="aviso" data-testid="falta-notion">
        Falta configurar NOTION_TOKEN en backend/.env
      </Alerta>

      <p
        v-if="resumenSincronizacion"
        data-testid="resultado-sincronizacion"
        role="status"
        class="text-sm"
      >
        {{ resumenSincronizacion }}
      </p>
      <p v-if="tienda.error" class="text-destructive text-sm" role="alert">{{ tienda.error }}</p>
    </div>

    <div
      data-testid="buscador-conocimiento"
      class="bg-card text-card-foreground flex flex-col gap-3 rounded-lg border p-4 shadow-xs"
    >
      <form class="flex flex-col gap-2" role="search" @submit.prevent="buscar">
        <Label for="busqueda-conocimiento">Buscar en tus notas</Label>
        <div class="flex items-center gap-2">
          <Input
            id="busqueda-conocimiento"
            v-model="busqueda"
            type="search"
            :maxlength="LONGITUD_MAXIMA_BUSQUEDA"
            autocomplete="off"
          />
          <Button type="submit" :disabled="!puedeBuscar" data-testid="boton-buscar">
            <Search aria-hidden="true" />
            Buscar
          </Button>
        </div>
      </form>

      <p
        v-if="nuncaSincronizado"
        data-testid="invitar-sincronizar"
        class="text-muted-foreground text-sm"
      >
        Aún no has sincronizado tus notas: pulsa «Sincronizar con Notion» para poder buscar en
        ellas.
      </p>
      <p v-if="tienda.errorBusqueda" class="text-destructive text-sm" role="alert">
        {{ tienda.errorBusqueda }}
      </p>

      <div
        data-testid="resultados-busqueda"
        aria-live="polite"
        :aria-busy="tienda.buscando ? 'true' : 'false'"
      >
        <p
          v-if="tienda.resultados !== null && tienda.resultados.length === 0"
          data-testid="sin-resultados"
          class="text-muted-foreground py-4 text-center text-sm"
        >
          {{ SIN_RESULTADOS }}
        </p>
        <ul v-else-if="paginasEncontradas.length > 0" class="flex flex-col gap-3">
          <li
            v-for="pagina in paginasEncontradas"
            :key="pagina.pagina_id"
            data-testid="resultado-pagina"
            class="flex flex-col gap-2 rounded-md border p-3"
          >
            <h3 class="text-sm font-semibold break-words">
              <a
                v-if="esUrlWeb(pagina.url)"
                :href="pagina.url"
                target="_blank"
                rel="noopener noreferrer"
                class="text-primary underline underline-offset-2"
                >{{ pagina.titulo }}</a
              >
              <template v-else>{{ pagina.titulo }}</template>
            </h3>
            <p
              v-for="fragmento in pagina.fragmentos"
              :key="fragmento.orden"
              data-testid="fragmento-resultado"
              class="text-muted-foreground text-sm break-words whitespace-pre-wrap"
            >
              <template v-for="(segmento, i) in segmentos(fragmento.texto)" :key="i"
                ><mark
                  v-if="segmento.resaltado"
                  class="text-foreground rounded-sm bg-yellow-200 px-0.5 dark:bg-yellow-500/40"
                  >{{ segmento.texto }}</mark
                ><template v-else>{{ segmento.texto }}</template></template
              >
            </p>
          </li>
        </ul>
      </div>
    </div>

    <div
      v-if="hayChat"
      data-testid="chat-conocimiento"
      class="bg-card text-card-foreground flex min-h-0 flex-col rounded-lg border shadow-xs"
    >
      <div class="flex items-center justify-between gap-2 border-b px-4 py-2">
        <h3 class="text-sm font-semibold">Chat</h3>
        <Button
          variant="ghost"
          size="sm"
          data-testid="nueva-conversacion"
          @click="tienda.nuevaConversacion()"
        >
          <SquarePen aria-hidden="true" />
          Nueva conversación
        </Button>
      </div>

      <div
        ref="lista"
        data-testid="conversacion-conocimiento"
        aria-live="polite"
        :aria-busy="tienda.enviando ? 'true' : 'false'"
        aria-label="Conversación"
        class="max-h-[60vh] min-h-40 overflow-y-auto px-4 py-3"
      >
        <p
          v-if="tienda.conversacion.length === 0"
          class="text-muted-foreground py-6 text-center text-sm"
        >
          Pregunta lo que quieras sobre tus notas de Notion.
        </p>
        <ol v-else class="flex flex-col gap-3">
          <li
            v-for="(mensaje, indice) in tienda.conversacion"
            :key="indice"
            :data-rol="mensaje.rol"
            :class="[
              'max-w-[85%] rounded-lg px-3 py-2 text-sm',
              mensaje.rol === 'usuario'
                ? 'bg-primary text-primary-foreground self-end whitespace-pre-wrap break-words'
                : 'bg-muted text-foreground self-start',
            ]"
          >
            <span class="sr-only">{{ mensaje.rol === 'usuario' ? 'Tú:' : 'Respuesta:' }}</span>
            <template v-if="mensaje.rol === 'usuario'">{{ mensaje.texto }}</template>
            <template v-else>
              <RespuestaMarkdown v-if="mensaje.texto !== ''" :texto="mensaje.texto" />
              <p v-else class="text-muted-foreground">Buscando en tus notas…</p>
              <p
                v-if="mensaje.fuentes && mensaje.fuentes.length > 0"
                data-testid="fuentes-respuesta"
                class="text-muted-foreground mt-2 border-t pt-2 text-xs"
              >
                Fuentes:
                <template v-for="(fuente, i) in mensaje.fuentes" :key="fuente.pagina_id">
                  <span v-if="!esUrlWeb(fuente.url)">{{ fuente.titulo }}</span>
                  <a
                    v-else
                    :href="fuente.url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="text-primary underline underline-offset-2"
                    >{{ fuente.titulo }}</a
                  ><span v-if="i < mensaje.fuentes.length - 1">, </span>
                </template>
              </p>
            </template>
          </li>
        </ol>
      </div>

      <form class="flex flex-col gap-2 border-t px-4 py-3" @submit.prevent="enviar">
        <p v-if="tienda.errorChat" class="text-destructive text-sm" role="alert">
          {{ tienda.errorChat }}
        </p>
        <Label for="pregunta-conocimiento">Pregunta</Label>
        <div class="flex items-end gap-2">
          <Textarea
            id="pregunta-conocimiento"
            v-model="pregunta"
            :maxlength="LONGITUD_MAXIMA_MENSAJE"
            rows="2"
            class="max-h-48"
            @keydown="alPulsarTecla"
          />
          <Button type="submit" :disabled="!puedeEnviar" data-testid="boton-enviar">
            <Send aria-hidden="true" />
            Enviar
          </Button>
        </div>
      </form>
    </div>
  </section>
</template>
