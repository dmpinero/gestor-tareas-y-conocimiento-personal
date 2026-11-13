<script setup lang="ts">
/**
 * Campo de fecha y hora `dd/mm/aaaa hh:mm:ss` con un calendario desplegable.
 *
 * El v-model es el texto tal y como se ve en el campo; la vista lo convierte
 * a ISO con `aFechaHoraIso`. Escribir una fecha válida mueve el calendario a
 * ella y elegir en el calendario (día, hora, minutos o segundos) reescribe el
 * campo. Un texto no válido se deja tal cual y no mueve el calendario.
 */
import { CalendarDays, X } from '@lucide/vue'
import {
  CalendarDateTime,
  getLocalTimeZone,
  parseDateTime,
  toCalendarDate,
  today,
  type CalendarDate,
  type DateValue,
} from '@internationalized/date'
import { computed, ref, shallowRef, useId, watch } from 'vue'

import { Button } from '@/componentes/ui/button'
import { Calendar } from '@/componentes/ui/calendar'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'
import { Popover, PopoverAnchor, PopoverContent, PopoverTrigger } from '@/componentes/ui/popover'
import { aFechaHoraIso, formatearFechaHora, PATRON_FECHA_HORA } from '@/lib/fechas'

defineOptions({ inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    /** `id` del campo de texto, para asociarlo a su `<label>`. */
    id?: string
    /** Nombre del campo; completa el nombre accesible de los botones. */
    etiqueta?: string
    required?: boolean
    /** Muestra el botón "Borrar fecha", que deja el campo vacío. */
    anulable?: boolean
  }>(),
  { id: undefined, etiqueta: undefined, required: false, anulable: false },
)

const modelo = defineModel<string>({ default: '' })

type UnidadTiempo = 'hour' | 'minute' | 'second'

const camposTiempo: { unidad: UnidadTiempo; etiqueta: string; maximo: number }[] = [
  { unidad: 'hour', etiqueta: 'Hora', maximo: 23 },
  { unidad: 'minute', etiqueta: 'Minutos', maximo: 59 },
  { unidad: 'second', etiqueta: 'Segundos', maximo: 59 },
]

const idBase = useId()
const abierto = ref(false)

const etiquetaAbrir = computed(() =>
  props.etiqueta ? `Abrir calendario de ${props.etiqueta}` : 'Abrir calendario',
)

/** Fecha y hora del campo, o `null` si el texto está vacío o no es válido. */
const fechaHora = computed<CalendarDateTime | null>(() => {
  const iso = aFechaHoraIso(modelo.value)
  return iso ? parseDateTime(iso) : null
})

const diaSeleccionado = computed<CalendarDate | undefined>(() =>
  fechaHora.value ? toCalendarDate(fechaHora.value) : undefined,
)

/** Mes que muestra el calendario: el de la fecha del campo o el actual. */
const mesVisible = shallowRef<DateValue>(diaSeleccionado.value ?? today(getLocalTimeZone()))

watch(diaSeleccionado, (dia) => {
  if (dia) mesVisible.value = dia
})

function emitir(valor: CalendarDateTime) {
  modelo.value = formatearFechaHora(valor.toString())
}

function alElegirDia(dia: DateValue | undefined) {
  if (!dia) return
  const actual = fechaHora.value
  emitir(
    new CalendarDateTime(
      dia.year,
      dia.month,
      dia.day,
      actual?.hour ?? 0,
      actual?.minute ?? 0,
      actual?.second ?? 0,
    ),
  )
}

function alCambiarTiempo(unidad: UnidadTiempo, maximo: number, valor: string | number | null) {
  const numero = Math.trunc(Number(valor))
  if (valor === null || valor === '' || Number.isNaN(numero)) return
  const acotado = Math.min(Math.max(numero, 0), maximo)
  const base =
    fechaHora.value ??
    new CalendarDateTime(mesVisible.value.year, mesVisible.value.month, mesVisible.value.day)
  emitir(base.set({ [unidad]: acotado }))
}
</script>

<template>
  <Popover v-model:open="abierto">
    <PopoverAnchor as-child>
      <div class="flex items-center gap-2">
        <Input
          v-bind="$attrs"
          :id="id"
          v-model="modelo"
          placeholder="dd/mm/aaaa hh:mm:ss"
          :pattern="PATRON_FECHA_HORA"
          :required="required"
        />
        <PopoverTrigger as-child>
          <Button
            type="button"
            variant="outline"
            size="icon"
            :aria-label="etiquetaAbrir"
            :title="etiquetaAbrir"
          >
            <CalendarDays aria-hidden="true" />
          </Button>
        </PopoverTrigger>
        <Button
          v-if="anulable"
          type="button"
          variant="outline"
          size="icon"
          aria-label="Borrar fecha"
          title="Borrar fecha"
          :disabled="modelo === ''"
          @click="modelo = ''"
        >
          <X aria-hidden="true" />
        </Button>
      </div>
    </PopoverAnchor>

    <!-- Con poco espacio arriba y abajo (formulario largo en un modal), el calendario
         se limita a la altura disponible en la ventana y hace scroll en vez de quedar
         cortado fuera de ella. -->
    <PopoverContent
      align="end"
      :collision-padding="8"
      class="max-h-(--reka-popover-content-available-height) w-auto overflow-y-auto"
    >
      <Calendar
        v-model:placeholder="mesVisible"
        :model-value="diaSeleccionado"
        prevent-deselect
        initial-focus
        @update:model-value="alElegirDia"
      />

      <div class="mt-3 grid grid-cols-3 gap-2">
        <div v-for="campo in camposTiempo" :key="campo.unidad" class="grid gap-1">
          <Label :for="`${idBase}-${campo.unidad}`">{{ campo.etiqueta }}</Label>
          <Input
            :id="`${idBase}-${campo.unidad}`"
            type="number"
            inputmode="numeric"
            min="0"
            :max="campo.maximo"
            :model-value="fechaHora ? fechaHora[campo.unidad] : 0"
            @update:model-value="alCambiarTiempo(campo.unidad, campo.maximo, $event)"
          />
        </div>
      </div>

      <div class="mt-3 flex justify-end">
        <Button type="button" size="sm" @click="abierto = false">Aceptar</Button>
      </div>
    </PopoverContent>
  </Popover>
</template>
