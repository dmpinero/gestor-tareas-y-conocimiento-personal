<script setup lang="ts">
import { Maximize, ZoomIn, ZoomOut } from '@lucide/vue'
import { useElementSize } from '@vueuse/core'
import { computed, ref, useTemplateRef, watch } from 'vue'

import type { Tarea } from '@/api/tipos'
import { Button } from '@/componentes/ui/button'
import { CLAVES_PRIORIDAD, clavePrioridad, type ClavePrioridad } from '@/lib/coloresTarea'
import { cajaVisible, disponerRed } from '@/lib/disposicionRed'
import {
  TIPOS_NODO_PROPIO,
  TIPOS_UNION,
  construirRed,
  vecinosDe,
  type NodoRed,
  type TipoNodoPropio,
  type TipoUnion,
} from '@/lib/redTareas'

// Red de tareas: cada tarea es un círculo con el color de su prioridad y cada
// etiqueta, persona, subestado u oportunidad que comparten dos o más tareas es
// un nodo propio al que se unen; las relacionadas se unen entre sí. `tareas`
// llega ya filtrada por quien lo usa; abrir el detalle es cosa del padre.
const props = defineProps<{ tareas: Tarea[] }>()
const emit = defineEmits<{ verDetalle: [id: number] }>()

// --- Uniones visibles (se recuerdan en este navegador) ---
const CLAVE_UNIONES = 'gestor-tareas:uniones-red'
const ETIQUETA_UNION: Record<TipoUnion, string> = {
  relacionadas: 'Relacionadas',
  etiquetas: 'Etiquetas',
  personas: 'Personas',
  subestados: 'Subestados',
  oportunidades: 'Oportunidades',
}

function leerUniones(): TipoUnion[] {
  try {
    const guardadas: unknown = JSON.parse(localStorage.getItem(CLAVE_UNIONES) ?? 'null')
    if (Array.isArray(guardadas)) {
      return TIPOS_UNION.filter((union) => guardadas.includes(union))
    }
  } catch {
    // Una preferencia ilegible muestra todas las uniones.
  }
  return [...TIPOS_UNION]
}

const uniones = ref<TipoUnion[]>(leerUniones())
watch(uniones, (valor) => {
  try {
    localStorage.setItem(
      CLAVE_UNIONES,
      JSON.stringify(TIPOS_UNION.filter((union) => valor.includes(union))),
    )
  } catch {
    // Sin almacenamiento, la preferencia dura lo que la página.
  }
})

// --- Red y disposición ---
const red = computed(() => construirRed(props.tareas, uniones.value))
const vecinos = computed(() => vecinosDe(red.value))
const disposicion = computed(() => disponerRed(red.value))
const caja = computed(() => disposicion.value.caja)

function posicion(id: string): { x: number; y: number } {
  return disposicion.value.posiciones.get(id) ?? { x: 0, y: 0 }
}

// --- Aspecto ---
// Los mismos colores que `RELLENO_PRIORIDAD` (barra de prioridades), como
// relleno SVG; las clases son literales para que Tailwind las genere.
const RELLENO_SVG_PRIORIDAD: Record<ClavePrioridad, string> = {
  1: 'fill-red-600 dark:fill-red-500',
  2: 'fill-orange-500 dark:fill-orange-400',
  3: 'fill-blue-600 dark:fill-blue-400',
  4: 'fill-teal-600 dark:fill-teal-400',
  5: 'fill-gray-500 dark:fill-gray-400',
  sin: 'fill-muted-foreground/30 stroke-muted-foreground',
}

const ETIQUETA_PRIORIDAD: Record<ClavePrioridad, string> = {
  1: 'Prioridad 1',
  2: 'Prioridad 2',
  3: 'Prioridad 3',
  4: 'Prioridad 4',
  5: 'Prioridad 5',
  sin: 'Sin prioridad',
}

const ETIQUETA_TIPO: Record<TipoNodoPropio, string> = {
  etiqueta: 'Etiqueta',
  persona: 'Persona',
  subestado: 'Subestado',
  oportunidad: 'Oportunidad',
}

// Cada tipo de nodo propio con su forma (centrada en 0,0) y su color, de los
// tonos de las paletas de la app.
const FORMA_TIPO: Record<TipoNodoPropio, { puntos: string; clase: string }> = {
  etiqueta: { puntos: '0,-13 13,0 0,13 -13,0', clase: 'fill-violet-600 dark:fill-violet-400' },
  persona: { puntos: '-11,-11 11,-11 11,11 -11,11', clase: 'fill-sky-600 dark:fill-sky-400' },
  subestado: {
    puntos: '0,-13 11.3,-6.5 11.3,6.5 0,13 -11.3,6.5 -11.3,-6.5',
    clase: 'fill-amber-600 dark:fill-amber-400',
  },
  oportunidad: {
    puntos: '0,-14 13,10 -13,10',
    clase: 'fill-emerald-600 dark:fill-emerald-400',
  },
}

const MAXIMO_CARACTERES = 18

function recortar(texto: string): string {
  const caracteres = [...texto]
  return caracteres.length > MAXIMO_CARACTERES
    ? `${caracteres.slice(0, MAXIMO_CARACTERES - 1).join('')}…`
    : texto
}

function nombreDe(nodo: NodoRed): string {
  return nodo.clase === 'tarea' ? nodo.tarea.nombre : nodo.nombre
}

function nombreAccesible(nodo: NodoRed): string {
  if (nodo.clase === 'tarea') {
    const conexiones = vecinos.value.get(nodo.id)?.size ?? 0
    const texto = `Tarea ${nodo.tarea.nombre}: ${conexiones} ${conexiones === 1 ? 'conexión' : 'conexiones'}`
    return nodo.tarea.completada ? `${texto}, completada` : texto
  }
  return `${ETIQUETA_TIPO[nodo.clase]} ${nodo.nombre}: ${nodo.tareas.length} tareas`
}

// --- Resaltado ---
// Pasar el ratón o enfocar un nodo lo resalta con sus vecinos; un clic en un
// nodo propio lo fija hasta otro clic (y mientras, manda sobre el ratón).
const activo = ref<string | null>(null)
const fijado = ref<string | null>(null)
const foco = computed(() => fijado.value ?? activo.value)
const resaltados = computed(() => {
  const id = foco.value
  if (id === null) return null
  return new Set([id, ...(vecinos.value.get(id) ?? [])])
})

watch(red, (nueva) => {
  const ids = new Set(nueva.nodos.map((nodo) => nodo.id))
  if (fijado.value !== null && !ids.has(fijado.value)) fijado.value = null
  if (activo.value !== null && !ids.has(activo.value)) activo.value = null
})

function nodoAtenuado(id: string): boolean {
  return resaltados.value !== null && !resaltados.value.has(id)
}

function aristaAtenuada(origen: string, destino: string): boolean {
  return foco.value !== null && origen !== foco.value && destino !== foco.value
}

function entrar(id: string): void {
  activo.value = id
}

function salir(id: string): void {
  if (activo.value === id) activo.value = null
}

function activar(nodo: NodoRed): void {
  if (nodo.clase === 'tarea') {
    emit('verDetalle', nodo.tarea.id)
    return
  }
  fijado.value = fijado.value === nodo.id ? null : nodo.id
}

// --- Zoom y desplazamiento ---
// La vista se aplica como `translate` (desplazamiento, en unidades del
// lienzo) y `scale` alrededor del centro de la caja; "Ajustar" vuelve a la
// caja completa, que el `viewBox` encaja en el ancho disponible.
const FACTOR_ZOOM = 1.25
const ESCALA_MINIMA = 0.25
const ESCALA_MAXIMA = 4
const escala = ref(1)
const desplazamiento = ref({ x: 0, y: 0 })

function redondear(valor: number): number {
  return Math.round(valor * 10000) / 10000
}

function zoom(factor: number): void {
  escala.value = redondear(Math.min(ESCALA_MAXIMA, Math.max(ESCALA_MINIMA, escala.value * factor)))
}

function ajustar(): void {
  escala.value = 1
  desplazamiento.value = { x: 0, y: 0 }
}

watch(red, ajustar)

const transformacion = computed(() => {
  const { x, y, ancho, alto } = caja.value
  const cx = redondear(x + ancho / 2)
  const cy = redondear(y + alto / 2)
  const { x: tx, y: ty } = desplazamiento.value
  return `translate(${redondear(tx)} ${redondear(ty)}) translate(${cx} ${cy}) scale(${escala.value}) translate(${-cx} ${-cy})`
})

const lienzo = useTemplateRef<SVGSVGElement>('lienzo')
const { width: anchoLienzo, height: altoLienzo } = useElementSize(lienzo)

// Lo que se ve del lienzo: la caja de los nodos sin ampliarla por encima de
// 1:1 (ver `cajaVisible`).
const visible = computed(() => cajaVisible(caja.value, anchoLienzo.value, altoLienzo.value))

const viewBox = computed(() => {
  const { x, y, ancho, alto } = visible.value
  return `${redondear(x)} ${redondear(y)} ${redondear(ancho)} ${redondear(alto)}`
})

function alRodar(evento: WheelEvent): void {
  if (evento.deltaY === 0) return
  zoom(evento.deltaY < 0 ? FACTOR_ZOOM : 1 / FACTOR_ZOOM)
}

let arrastre: { x: number; y: number; inicio: { x: number; y: number } } | null = null

// Unidades del lienzo por píxel de pantalla (el `viewBox` se encaja entero).
function unidadesPorPixel(): number {
  const rect = lienzo.value?.getBoundingClientRect()
  if (!rect || rect.width === 0 || rect.height === 0) return 1
  return Math.max(visible.value.ancho / rect.width, visible.value.alto / rect.height)
}

function alPulsarFondo(evento: PointerEvent): void {
  if (evento.button !== undefined && evento.button !== 0) return
  arrastre = { x: evento.clientX, y: evento.clientY, inicio: { ...desplazamiento.value } }
  const objetivo = evento.currentTarget as Element | null
  try {
    objetivo?.setPointerCapture?.(evento.pointerId)
  } catch {
    // Sin captura del puntero el arrastre sigue funcionando dentro del lienzo.
  }
}

function alMoverFondo(evento: PointerEvent): void {
  if (!arrastre) return
  const factor = unidadesPorPixel()
  desplazamiento.value = {
    x: arrastre.inicio.x + (evento.clientX - arrastre.x) * factor,
    y: arrastre.inicio.y + (evento.clientY - arrastre.y) * factor,
  }
}

function alSoltarFondo(): void {
  arrastre = null
}

// El fondo cubre de sobra lo que se ve, también al alejar o desplazar.
const fondo = computed(() => {
  const { x, y, ancho, alto } = caja.value
  const extra = Math.max(ancho, alto) * 20
  return { x: x - extra, y: y - extra, ancho: ancho + 2 * extra, alto: alto + 2 * extra }
})
</script>

<template>
  <section data-testid="red-tareas" aria-label="Red de tareas" class="mt-4">
    <p v-if="tareas.length === 0" class="text-muted-foreground text-sm">
      Ninguna tarea coincide con los filtros.
    </p>
    <template v-else>
      <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
        <fieldset class="flex flex-wrap items-center gap-x-4 gap-y-2">
          <legend class="sr-only">Uniones que se muestran</legend>
          <label
            v-for="union in TIPOS_UNION"
            :key="union"
            class="flex cursor-pointer items-center gap-2 text-sm"
          >
            <input
              v-model="uniones"
              type="checkbox"
              :value="union"
              :data-union="union"
              class="accent-primary size-4 shrink-0"
            />{{ ETIQUETA_UNION[union] }}</label
          >
        </fieldset>
        <div
          v-if="red.aristas.length > 0"
          role="group"
          aria-label="Zoom"
          class="ml-auto flex gap-1"
        >
          <Button
            type="button"
            size="icon"
            variant="outline"
            aria-label="Acercar"
            title="Acercar"
            @click="zoom(FACTOR_ZOOM)"
          >
            <ZoomIn aria-hidden="true" />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="outline"
            aria-label="Alejar"
            title="Alejar"
            @click="zoom(1 / FACTOR_ZOOM)"
          >
            <ZoomOut aria-hidden="true" />
          </Button>
          <Button type="button" variant="outline" aria-label="Ajustar" @click="ajustar">
            <Maximize aria-hidden="true" />
            Ajustar
          </Button>
        </div>
      </div>

      <p v-if="red.aristas.length === 0" class="text-muted-foreground mt-4 text-sm">
        Estas tareas no tienen nada en común con las uniones elegidas.
      </p>
      <template v-else>
        <div class="bg-card mt-3 overflow-hidden rounded-xl border shadow-xs">
          <svg
            ref="lienzo"
            data-testid="lienzo-red"
            role="group"
            aria-label="Red de tareas"
            :viewBox="viewBox"
            preserveAspectRatio="xMidYMid meet"
            class="block h-[60vh] min-h-72 w-full select-none"
            @wheel.prevent="alRodar"
          >
            <rect
              data-testid="fondo-red"
              :x="fondo.x"
              :y="fondo.y"
              :width="fondo.ancho"
              :height="fondo.alto"
              fill="transparent"
              class="cursor-grab touch-none active:cursor-grabbing"
              @pointerdown="alPulsarFondo"
              @pointermove="alMoverFondo"
              @pointerup="alSoltarFondo"
              @pointercancel="alSoltarFondo"
            />
            <g data-testid="vista-red" :transform="transformacion">
              <line
                v-for="arista in red.aristas"
                :key="`${arista.origen}|${arista.destino}`"
                :data-arista="`${arista.origen}|${arista.destino}`"
                :data-tipo="arista.tipo"
                :data-atenuado="String(aristaAtenuada(arista.origen, arista.destino))"
                :x1="posicion(arista.origen).x"
                :y1="posicion(arista.origen).y"
                :x2="posicion(arista.destino).x"
                :y2="posicion(arista.destino).y"
                class="pointer-events-none transition-opacity"
                :class="[
                  arista.tipo === 'relacionadas'
                    ? 'stroke-foreground/70 stroke-2'
                    : 'stroke-muted-foreground/60 stroke-1',
                  aristaAtenuada(arista.origen, arista.destino) ? 'opacity-15' : '',
                ]"
              />
              <g
                v-for="nodo in red.nodos"
                :key="nodo.id"
                role="button"
                tabindex="0"
                :data-nodo="nodo.id"
                :data-tipo="nodo.clase"
                :data-atenuado="String(nodoAtenuado(nodo.id))"
                :data-completada="
                  nodo.clase === 'tarea' ? String(nodo.tarea.completada) : undefined
                "
                :aria-label="nombreAccesible(nodo)"
                :aria-pressed="nodo.clase === 'tarea' ? undefined : fijado === nodo.id"
                :transform="`translate(${posicion(nodo.id).x} ${posicion(nodo.id).y})`"
                class="group cursor-pointer transition-opacity outline-none"
                :class="nodoAtenuado(nodo.id) ? 'opacity-20' : ''"
                @mouseenter="entrar(nodo.id)"
                @mouseleave="salir(nodo.id)"
                @focus="entrar(nodo.id)"
                @blur="salir(nodo.id)"
                @click="activar(nodo)"
                @keydown.enter.prevent="activar(nodo)"
                @keydown.space.prevent="activar(nodo)"
              >
                <title>{{ nombreDe(nodo) }}</title>
                <!-- Anillo de foco del teclado. -->
                <circle
                  r="19"
                  class="fill-none stroke-ring stroke-2 opacity-0 group-focus-visible:opacity-100"
                />
                <template v-if="nodo.clase === 'tarea'">
                  <circle
                    data-circulo
                    r="10"
                    :class="[
                      RELLENO_SVG_PRIORIDAD[clavePrioridad(nodo.tarea.prioridad)],
                      nodo.tarea.completada ? 'opacity-40' : '',
                    ]"
                  />
                  <text
                    y="25"
                    text-anchor="middle"
                    aria-hidden="true"
                    class="text-[11px]"
                    :class="
                      nodo.tarea.completada
                        ? 'fill-muted-foreground line-through'
                        : 'fill-foreground'
                    "
                  >
                    {{ recortar(nodo.tarea.nombre) }}
                  </text>
                </template>
                <template v-else>
                  <polygon
                    :points="FORMA_TIPO[nodo.clase].puntos"
                    :class="FORMA_TIPO[nodo.clase].clase"
                    class="stroke-card stroke-1"
                  />
                  <text
                    y="27"
                    text-anchor="middle"
                    aria-hidden="true"
                    class="fill-foreground text-[11px] font-semibold"
                  >
                    {{ recortar(nodo.nombre) }}
                  </text>
                </template>
              </g>
            </g>
          </svg>
        </div>
        <p class="text-muted-foreground mt-2 text-xs">
          Pasa el ratón o enfoca un nodo para resaltar sus uniones. Pulsa una tarea para ver su
          detalle o una etiqueta, persona, subestado u oportunidad para fijar el resaltado.
        </p>
      </template>

      <ul
        data-testid="leyenda-red"
        aria-label="Leyenda"
        class="text-muted-foreground mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs"
      >
        <li v-for="clave in CLAVES_PRIORIDAD" :key="clave" class="flex items-center gap-1.5">
          <svg viewBox="-6 -6 12 12" class="size-3" aria-hidden="true">
            <circle r="5" :class="RELLENO_SVG_PRIORIDAD[clave]" />
          </svg>
          {{ ETIQUETA_PRIORIDAD[clave] }}
        </li>
        <li class="flex items-center gap-1.5">
          <svg viewBox="-6 -6 12 12" class="size-3" aria-hidden="true">
            <circle r="5" class="fill-blue-600 opacity-40 dark:fill-blue-400" />
          </svg>
          Completada
        </li>
        <li v-for="tipo in TIPOS_NODO_PROPIO" :key="tipo" class="flex items-center gap-1.5">
          <svg viewBox="-15 -15 30 30" class="size-3.5" aria-hidden="true">
            <polygon :points="FORMA_TIPO[tipo].puntos" :class="FORMA_TIPO[tipo].clase" />
          </svg>
          {{ ETIQUETA_TIPO[tipo] }}
        </li>
        <li class="flex items-center gap-1.5">
          <svg viewBox="0 0 16 4" class="h-1 w-4" aria-hidden="true">
            <line x1="0" y1="2" x2="16" y2="2" class="stroke-foreground/70 stroke-2" />
          </svg>
          Tareas relacionadas
        </li>
      </ul>
    </template>
  </section>
</template>
