<script setup lang="ts">
import { ChevronLeft, ChevronRight } from '@lucide/vue'
import {
  CalendarCell,
  CalendarCellTrigger,
  CalendarGrid,
  CalendarGridBody,
  CalendarGridHead,
  CalendarGridRow,
  CalendarHeadCell,
  CalendarHeader,
  CalendarHeading,
  CalendarNext,
  CalendarPrev,
  CalendarRoot,
  type CalendarRootEmits,
  type CalendarRootProps,
  useForwardPropsEmits,
} from 'reka-ui'
import { computed, type HTMLAttributes } from 'vue'
import { variantesBoton } from '@/componentes/ui/button'
import { cn } from '@/lib/utils'

const props = withDefaults(defineProps<CalendarRootProps & { class?: HTMLAttributes['class'] }>(), {
  locale: 'es-ES',
  weekStartsOn: 1,
  weekdayFormat: 'short',
  calendarLabel: 'Calendario',
  fixedWeeks: true,
  modelValue: undefined,
  placeholder: undefined,
})
const emits = defineEmits<CalendarRootEmits>()

const delegatedProps = computed(() => {
  const { class: clase, ...delegated } = props
  void clase
  return delegated
})

const forwarded = useForwardPropsEmits(delegatedProps, emits)

const clasesBotonNavegacion = cn(
  variantesBoton({ variant: 'outline' }),
  'size-7 bg-transparent p-0 opacity-50 hover:opacity-100',
)
</script>

<template>
  <CalendarRoot
    v-slot="{ grid, weekDays }"
    data-slot="calendar"
    v-bind="forwarded"
    :class="cn('p-1', props.class)"
  >
    <CalendarHeader
      data-slot="calendar-header"
      class="relative flex w-full items-center justify-between pt-1"
    >
      <CalendarPrev
        data-slot="calendar-prev"
        aria-label="Mes anterior"
        :class="clasesBotonNavegacion"
      >
        <ChevronLeft class="size-4" />
      </CalendarPrev>
      <CalendarHeading
        data-slot="calendar-heading"
        class="text-sm font-medium first-letter:uppercase"
      />
      <CalendarNext
        data-slot="calendar-next"
        aria-label="Mes siguiente"
        :class="clasesBotonNavegacion"
      >
        <ChevronRight class="size-4" />
      </CalendarNext>
    </CalendarHeader>

    <div class="mt-4 flex flex-col gap-y-4 sm:flex-row sm:gap-x-4 sm:gap-y-0">
      <CalendarGrid
        v-for="mes in grid"
        :key="mes.value.toString()"
        data-slot="calendar-grid"
        class="w-full border-collapse space-x-1"
      >
        <CalendarGridHead>
          <CalendarGridRow class="flex">
            <CalendarHeadCell
              v-for="diaSemana in weekDays"
              :key="diaSemana"
              data-slot="calendar-head-cell"
              class="text-muted-foreground w-8 rounded-md text-[0.8rem] font-normal"
            >
              {{ diaSemana }}
            </CalendarHeadCell>
          </CalendarGridRow>
        </CalendarGridHead>
        <CalendarGridBody>
          <CalendarGridRow
            v-for="(semana, indice) in mes.rows"
            :key="`semana-${indice}`"
            class="mt-2 flex w-full"
          >
            <CalendarCell
              v-for="fecha in semana"
              :key="fecha.toString()"
              :date="fecha"
              data-slot="calendar-cell"
              class="relative p-0 text-center text-sm focus-within:relative focus-within:z-20"
            >
              <CalendarCellTrigger
                :day="fecha"
                :month="mes.value"
                data-slot="calendar-cell-trigger"
                :class="
                  cn(
                    variantesBoton({ variant: 'ghost' }),
                    'size-8 p-0 font-normal aria-selected:opacity-100',
                    '[&[data-today]:not([data-selected])]:bg-accent [&[data-today]:not([data-selected])]:text-accent-foreground',
                    'data-[selected]:bg-primary data-[selected]:text-primary-foreground data-[selected]:hover:bg-primary data-[selected]:hover:text-primary-foreground data-[selected]:focus:bg-primary data-[selected]:focus:text-primary-foreground',
                    'data-[disabled]:text-muted-foreground data-[disabled]:opacity-50',
                    'data-[unavailable]:text-destructive-foreground data-[unavailable]:line-through',
                    'data-[outside-view]:text-muted-foreground',
                  )
                "
              />
            </CalendarCell>
          </CalendarGridRow>
        </CalendarGridBody>
      </CalendarGrid>
    </div>
  </CalendarRoot>
</template>
