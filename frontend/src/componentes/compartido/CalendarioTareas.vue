<script setup lang="ts">
import { ChevronLeft, ChevronRight } from '@lucide/vue'
import { createReusableTemplate, useElementSize } from '@vueuse/core'
import { computed, nextTick, ref, useTemplateRef } from 'vue'

import type { Tarea } from '@/api/tipos'
import AvisoVencimiento from '@/componentes/compartido/AvisoVencimiento.vue'
import { Button } from '@/componentes/ui/button'
import { dosCifras } from '@/lib/fechas'

// Calendario mensual de las tareas: cada una va en el día de su vencimiento
// (fecha local tal cual llega de la API, sin convertir de zona; la hora solo se
// muestra). `tareas` llega ya filtrada y ordenada por quien lo usa. Las semanas
// empiezan en lunes. En un contenedor estrecho se muestra una agenda con los
// días del mes que tienen tareas. Abrir el detalle es cosa del padre.
const props = defineProps<{ tareas: Tarea[] }>()
const emit = defineEmits<{ verDetalle: [id: number] }>()

const LOCALE = 'es-ES'
const MAXIMO_VISIBLES = 3
// Por debajo de este ancho del contenedor (px) la cuadrícula no cabe.
const ANCHO_MINIMO_CUADRICULA = 640

const formatoMes = new Intl.DateTimeFormat(LOCALE, { month: 'long', year: 'numeric' })
const formatoDia = new Intl.DateTimeFormat(LOCALE, {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
})
const formatoDiaSemana = new Intl.DateTimeFormat(LOCALE, { weekday: 'long' })
// El 1 de enero de 2024 fue lunes.
const DIAS_SEMANA = Array.from({ length: 7 }, (_, indice) =>
  formatoDiaSemana.format(new Date(2024, 0, 1 + indice)),
)

function claveDe(fecha: Date): string {
  return `${fecha.getFullYear()}-${dosCifras(fecha.getMonth() + 1)}-${dosCifras(fecha.getDate())}`
}

const hoy = new Date()
const claveHoy = claveDe(hoy)
const primeroDelMes = ref(new Date(hoy.getFullYear(), hoy.getMonth(), 1))

const tituloMes = computed(() => formatoMes.format(primeroDelMes.value))

function cambiarMes(desplazamiento: number): void {
  const actual = primeroDelMes.value
  primeroDelMes.value = new Date(actual.getFullYear(), actual.getMonth() + desplazamiento, 1)
}

function irAHoy(): void {
  primeroDelMes.value = new Date(hoy.getFullYear(), hoy.getMonth(), 1)
}

// Tareas por día (`YYYY-MM-DD`), cada día por hora de vencimiento.
const tareasPorDia = computed(() => {
  const mapa = new Map<string, Tarea[]>()
  for (const tarea of props.tareas) {
    if (!tarea.fecha_vencimiento) continue
    const clave = tarea.fecha_vencimiento.slice(0, 10)
    mapa.set(clave, [...(mapa.get(clave) ?? []), tarea])
  }
  for (const lista of mapa.values()) {
    lista.sort((a, b) => a.fecha_vencimiento!.localeCompare(b.fecha_vencimiento!))
  }
  return mapa
})

const sinFecha = computed(() => props.tareas.filter((t) => !t.fecha_vencimiento).length)
const textoSinFecha = computed(() =>
  sinFecha.value === 1
    ? '1 tarea sin fecha de vencimiento'
    : `${sinFecha.value} tareas sin fecha de vencimiento`,
)

interface Dia {
  clave: string
  numero: number
  nombre: string
  esHoy: boolean
  tareas: Tarea[]
}

const diasDelMes = computed<Dia[]>(() => {
  const primero = primeroDelMes.value
  const total = new Date(primero.getFullYear(), primero.getMonth() + 1, 0).getDate()
  return Array.from({ length: total }, (_, indice) => {
    const fecha = new Date(primero.getFullYear(), primero.getMonth(), indice + 1)
    const clave = claveDe(fecha)
    return {
      clave,
      numero: indice + 1,
      nombre: formatoDia.format(fecha),
      esHoy: clave === claveHoy,
      tareas: tareasPorDia.value.get(clave) ?? [],
    }
  })
})

// Semanas de lunes a domingo; los huecos de otros meses quedan a `null`.
const semanas = computed<(Dia | null)[][]>(() => {
  const huecosIniciales = (primeroDelMes.value.getDay() + 6) % 7
  const celdas: (Dia | null)[] = [...Array<null>(huecosIniciales).fill(null), ...diasDelMes.value]
  while (celdas.length % 7 !== 0) celdas.push(null)
  return Array.from({ length: celdas.length / 7 }, (_, indice) =>
    celdas.slice(indice * 7, indice * 7 + 7),
  )
})

const diasConTareas = computed(() => diasDelMes.value.filter((dia) => dia.tareas.length > 0))

const raiz = useTemplateRef<HTMLElement>('raiz')
// Sin medida (ancho 0, p. ej. en jsdom) se usa la cuadrícula.
const { width: ancho } = useElementSize(raiz, undefined, { box: 'border-box' })
const enAgenda = computed(() => ancho.value > 0 && ancho.value < ANCHO_MINIMO_CUADRICULA)

// --- Días desplegados ("+N más") ---
const desplegados = ref<string[]>([])

function visibles(dia: Dia): Tarea[] {
  return desplegados.value.includes(dia.clave) ? dia.tareas : dia.tareas.slice(0, MAXIMO_VISIBLES)
}

function ocultas(dia: Dia): number {
  return dia.tareas.length - visibles(dia).length
}

// El botón "+N más" desaparece al desplegar: el foco va a la primera tarea
// que estaba oculta.
async function desplegar(dia: Dia): Promise<void> {
  desplegados.value = [...desplegados.value, dia.clave]
  await nextTick()
  document
    .getElementById(`dia-${dia.clave}`)
    ?.querySelectorAll<HTMLButtonElement>('[data-tarea-calendario]')
    [MAXIMO_VISIBLES]?.focus()
}

function hora(tarea: Tarea): string {
  return tarea.fecha_vencimiento?.slice(11, 16) ?? ''
}

const plantillaTareasDia = createReusableTemplate<{ dia: Dia }>()
</script>

<template>
  <plantillaTareasDia.define v-slot="{ dia }">
    <ul
      v-if="dia.tareas.length > 0"
      :aria-label="`Tareas del ${dia.nombre}`"
      class="flex min-w-0 flex-col gap-1"
    >
      <li v-for="tarea in visibles(dia)" :key="tarea.id" class="flex min-w-0 items-start gap-1">
        <button
          type="button"
          data-tarea-calendario
          :class="[
            'hover:bg-accent focus-visible:ring-ring/50 min-w-0 flex-1 rounded-sm border px-1.5 py-0.5 text-left text-xs outline-none focus-visible:ring-[3px]',
            tarea.completada ? 'text-muted-foreground line-through' : 'bg-background',
          ]"
          @click="emit('verDetalle', tarea.id)"
        >
          <span class="line-clamp-2 [overflow-wrap:anywhere]"
            ><span class="font-medium tabular-nums">{{ hora(tarea) }}</span
            >{{ ` ${tarea.nombre}` }}</span
          >
        </button>
        <AvisoVencimiento
          class="mt-0.5"
          :vencimiento="tarea.fecha_vencimiento"
          :completada="tarea.completada"
        />
      </li>
    </ul>
    <Button
      v-if="ocultas(dia) > 0"
      type="button"
      variant="link"
      size="sm"
      class="h-6 self-start px-1 text-xs"
      :aria-label="`+${ocultas(dia)} más (${dia.nombre})`"
      @click="desplegar(dia)"
      >+{{ ocultas(dia) }} más</Button
    >
  </plantillaTareasDia.define>

  <div ref="raiz" data-testid="calendario-tareas" class="mt-4 flex min-w-0 flex-col gap-3">
    <div class="flex flex-wrap items-center gap-2">
      <h3
        id="titulo-calendario"
        data-titulo-mes
        class="mr-auto text-base font-semibold first-letter:uppercase"
        aria-live="polite"
      >
        {{ tituloMes }}
      </h3>
      <Button type="button" variant="outline" size="sm" @click="cambiarMes(-1)">
        <ChevronLeft aria-hidden="true" />
        Mes anterior
      </Button>
      <Button type="button" variant="outline" size="sm" @click="irAHoy">Hoy</Button>
      <Button type="button" variant="outline" size="sm" @click="cambiarMes(1)">
        Mes siguiente
        <ChevronRight aria-hidden="true" />
      </Button>
    </div>

    <p v-if="sinFecha > 0" class="text-muted-foreground text-sm">{{ textoSinFecha }}</p>

    <template v-if="enAgenda">
      <p v-if="diasConTareas.length === 0" class="text-muted-foreground text-sm">
        No hay tareas que venzan este mes.
      </p>
      <ol v-else data-agenda :aria-label="`Agenda de ${tituloMes}`" class="flex flex-col gap-3">
        <li v-for="dia in diasConTareas" :key="dia.clave">
          <section
            :id="`dia-${dia.clave}`"
            :aria-label="dia.nombre"
            :aria-current="dia.esHoy ? 'date' : undefined"
            :class="[
              'flex flex-col gap-2 rounded-md border p-2',
              dia.esHoy && 'border-primary bg-primary/5',
            ]"
          >
            <h3 class="text-sm font-semibold">{{ dia.nombre }}</h3>
            <plantillaTareasDia.reuse :dia="dia" />
          </section>
        </li>
      </ol>
    </template>

    <table v-else class="w-full table-fixed border-collapse" aria-labelledby="titulo-calendario">
      <thead>
        <tr>
          <th
            v-for="nombre in DIAS_SEMANA"
            :key="nombre"
            scope="col"
            class="text-muted-foreground truncate px-1 py-1 text-left text-xs font-medium"
          >
            {{ nombre }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(semana, indiceSemana) in semanas" :key="indiceSemana">
          <td
            v-for="(dia, indiceDia) in semana"
            :key="dia?.clave ?? `hueco-${indiceSemana}-${indiceDia}`"
            :class="[
              'h-28 border p-1 align-top',
              dia === null && 'bg-muted/30',
              dia?.esHoy && 'bg-primary/5',
            ]"
          >
            <div
              v-if="dia"
              :id="`dia-${dia.clave}`"
              role="group"
              :aria-label="dia.nombre"
              :aria-current="dia.esHoy ? 'date' : undefined"
              class="flex min-w-0 flex-col gap-1"
            >
              <span
                aria-hidden="true"
                :class="[
                  'inline-flex size-6 items-center justify-center self-start rounded-full text-xs tabular-nums',
                  dia.esHoy ? 'bg-primary text-primary-foreground font-semibold' : '',
                ]"
                >{{ dia.numero }}</span
              >
              <plantillaTareasDia.reuse :dia="dia" />
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
