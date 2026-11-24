<script setup lang="ts">
import { CalendarDays, ChevronLeft, ChevronRight } from '@lucide/vue'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import type { EntradaHistorialFoco } from '@/api/tipos'
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
import {
  desplazarDia,
  fechaLocal,
  formatearDuracionFoco,
  horaLocal,
  normalizarFechaLocal,
  textoEntradaHistorial,
} from '@/lib/foco'
import { useTiendaFoco } from '@/stores/foco'
import { useTiendaHistorialFoco } from '@/stores/historialFoco'

// Historial de los periodos de foco. "Por día" muestra un día local (con su
// total) y "Todo" la lista completa, ambas de la más reciente a la más antigua.
// La vista y el día viven en la URL (`?vista=dia|todo&dia=YYYY-MM-DD`) para que
// atrás/adelante del navegador funcionen. La entrada en curso (sin `hasta`)
// avanza cada minuto, y al cambiar el foco se vuelve a pedir el historial.
const INTERVALO_MS = 60_000
const NOMBRE_RUTA = 'historial-foco'

type Vista = 'dia' | 'todo'

const route = useRoute()
const router = useRouter()
const tienda = useTiendaHistorialFoco()
const tiendaFoco = useTiendaFoco()

const ahora = ref(new Date())
let intervalo: ReturnType<typeof setInterval> | null = null

const hoy = computed(() => fechaLocal(ahora.value))
const vista = computed<Vista>(() => (route.query.vista === 'todo' ? 'todo' : 'dia'))
const dia = computed(() => normalizarFechaLocal(route.query.dia) ?? hoy.value)
const esHoyOPosterior = computed(() => dia.value >= hoy.value)

const tituloDia = computed(() =>
  new Date(`${dia.value}T00:00:00`).toLocaleDateString('es-ES', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }),
)

const entradas = computed(() =>
  [...tienda.entradas].sort((a, b) => new Date(b.desde).getTime() - new Date(a.desde).getTime()),
)

function duracionMs(entrada: EntradaHistorialFoco): number {
  const fin = entrada.hasta === null ? ahora.value : new Date(entrada.hasta)
  return Math.max(0, fin.getTime() - new Date(entrada.desde).getTime())
}

const totalDia = computed(() =>
  formatearDuracionFoco(entradas.value.reduce((suma, e) => suma + duracionMs(e), 0)),
)

function fechaCorta(instante: string): string {
  return new Date(instante).toLocaleDateString('es-ES', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

function enlaceTarea(tareaId: number) {
  return { path: '/tareas', query: { tarea: String(tareaId) } }
}

function ir(cambios: { vista?: Vista; dia?: string }): void {
  void router.push({
    query: { vista: cambios.vista ?? vista.value, dia: cambios.dia ?? dia.value },
  })
}

function elegirDia(valor: string | number | null): void {
  const elegido = normalizarFechaLocal(valor)
  if (elegido !== null) ir({ dia: elegido })
}

function recargar(): void {
  // Al salir de la página la URL cambia antes de desmontarla: no se recarga.
  if (route.name !== NOMBRE_RUTA) return
  void (vista.value === 'todo' ? tienda.cargarTodo() : tienda.cargarDia(dia.value))
}

watch([vista, dia], recargar, { immediate: true })
watch(() => tiendaFoco.foco, recargar)

onMounted(() => {
  intervalo = setInterval(() => {
    ahora.value = new Date()
  }, INTERVALO_MS)
})

onUnmounted(() => {
  if (intervalo !== null) clearInterval(intervalo)
})
</script>

<template>
  <section class="max-w-4xl">
    <h2 class="text-xl font-semibold">Historial de foco</h2>
    <p class="text-muted-foreground mt-1 text-sm">
      Cada periodo en que una tarea o subtarea estuvo en foco. Pulsa una para abrirla.
    </p>

    <div role="group" aria-label="Vista del historial" class="mt-4 inline-flex gap-1">
      <Button
        :variant="vista === 'dia' ? 'default' : 'outline'"
        size="sm"
        :aria-pressed="vista === 'dia'"
        @click="ir({ vista: 'dia' })"
        >Por día</Button
      >
      <Button
        :variant="vista === 'todo' ? 'default' : 'outline'"
        size="sm"
        :aria-pressed="vista === 'todo'"
        @click="ir({ vista: 'todo' })"
        >Todo</Button
      >
    </div>

    <p v-if="tienda.error" class="text-destructive mt-4 text-sm" role="alert">
      {{ tienda.error }}
    </p>

    <!-- Por día -->
    <div v-if="vista === 'dia'" class="mt-4">
      <div class="flex flex-wrap items-end gap-2">
        <Button variant="outline" size="sm" @click="ir({ dia: desplazarDia(dia, -1) })">
          <ChevronLeft aria-hidden="true" />Día anterior
        </Button>
        <div class="grid gap-1">
          <Label for="dia-historial-foco" class="sr-only">Día</Label>
          <Input
            id="dia-historial-foco"
            type="date"
            class="h-8 w-auto"
            :model-value="dia"
            :max="hoy"
            @update:model-value="elegirDia"
          />
        </div>
        <Button variant="outline" size="sm" :disabled="dia === hoy" @click="ir({ dia: hoy })">
          <CalendarDays aria-hidden="true" />Hoy
        </Button>
        <Button
          variant="outline"
          size="sm"
          :disabled="esHoyOPosterior"
          @click="ir({ dia: desplazarDia(dia, 1) })"
        >
          Día siguiente<ChevronRight aria-hidden="true" />
        </Button>
      </div>

      <h3
        id="titulo-dia-historial-foco"
        class="mt-4 text-base font-semibold first-letter:uppercase"
      >
        {{ tituloDia }}
      </h3>
      <p v-if="entradas.length > 0" data-total-dia class="text-muted-foreground text-sm">
        Total: <span class="text-foreground font-medium">{{ totalDia }}</span>
      </p>

      <p
        v-if="!tienda.cargando && entradas.length === 0"
        class="text-muted-foreground mt-3 text-sm"
      >
        No hubo foco este día.
      </p>
      <ol
        v-else-if="entradas.length > 0"
        aria-labelledby="titulo-dia-historial-foco"
        class="border-border bg-card mt-3 divide-y rounded-md border"
      >
        <li
          v-for="entrada in entradas"
          :key="entrada.id"
          data-entrada-historial
          class="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-3 py-2 text-sm"
        >
          <span class="text-muted-foreground shrink-0 tabular-nums">
            <time :datetime="entrada.desde">{{ horaLocal(entrada.desde) }}</time>
            –
            <time v-if="entrada.hasta !== null" :datetime="entrada.hasta">{{
              horaLocal(entrada.hasta)
            }}</time>
            <span v-else class="font-medium text-violet-700 dark:text-violet-300">en curso</span>
          </span>
          <span class="shrink-0 tabular-nums">{{
            formatearDuracionFoco(duracionMs(entrada))
          }}</span>
          <RouterLink
            v-if="entrada.tarea_id !== null"
            :to="enlaceTarea(entrada.tarea_id)"
            class="min-w-0 break-words underline-offset-4 hover:underline focus-visible:underline"
          >
            {{ textoEntradaHistorial(entrada) }}
          </RouterLink>
          <span
            v-else
            data-tarea-eliminada
            class="text-muted-foreground min-w-0 break-words italic"
            title="Tarea eliminada"
          >
            {{ textoEntradaHistorial(entrada) }}<span class="sr-only"> (tarea eliminada)</span>
          </span>
        </li>
      </ol>
    </div>

    <!-- Todo -->
    <div v-else class="mt-4">
      <h3 class="sr-only">Todo el historial</h3>
      <p v-if="!tienda.cargando && entradas.length === 0" class="text-muted-foreground text-sm">
        Todavía no hay historial de foco.
      </p>
      <div v-else-if="entradas.length > 0" class="border-border bg-card rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Fecha</TableHead>
              <TableHead>Inicio</TableHead>
              <TableHead>Fin</TableHead>
              <TableHead>Duración</TableHead>
              <TableHead>Tarea</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="entrada in entradas" :key="entrada.id" data-entrada-historial>
              <TableCell class="tabular-nums">{{ fechaCorta(entrada.desde) }}</TableCell>
              <TableCell class="tabular-nums">
                <time :datetime="entrada.desde">{{ horaLocal(entrada.desde) }}</time>
              </TableCell>
              <TableCell class="tabular-nums">
                <time v-if="entrada.hasta !== null" :datetime="entrada.hasta">{{
                  horaLocal(entrada.hasta)
                }}</time>
                <span v-else class="font-medium text-violet-700 dark:text-violet-300"
                  >en curso</span
                >
              </TableCell>
              <TableCell class="tabular-nums">{{
                formatearDuracionFoco(duracionMs(entrada))
              }}</TableCell>
              <TableCell class="whitespace-normal">
                <RouterLink
                  v-if="entrada.tarea_id !== null"
                  :to="enlaceTarea(entrada.tarea_id)"
                  class="underline-offset-4 hover:underline focus-visible:underline"
                >
                  {{ textoEntradaHistorial(entrada) }}
                </RouterLink>
                <span
                  v-else
                  data-tarea-eliminada
                  class="text-muted-foreground italic"
                  title="Tarea eliminada"
                >
                  {{ textoEntradaHistorial(entrada)
                  }}<span class="sr-only"> (tarea eliminada)</span>
                </span>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
    </div>
  </section>
</template>
