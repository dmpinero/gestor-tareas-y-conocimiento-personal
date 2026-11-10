<script setup lang="ts" generic="T extends string | number">
import { ChevronDown } from '@lucide/vue'
import { computed } from 'vue'
import { Button } from '@/componentes/ui/button'
import { Checkbox } from '@/componentes/ui/checkbox'
import { Label } from '@/componentes/ui/label'
import { Popover, PopoverContent, PopoverTrigger } from '@/componentes/ui/popover'
import { Separator } from '@/componentes/ui/separator'

// "Todas las"/"Ninguna" van en femenino, fijo: los usos actuales
// (prioridad/prioridades, etiqueta/etiquetas, persona/personas) lo son.
// Los identificadores pueden ser de texto (p. ej. el propio nombre), así que
// el `id` de cada casilla en el DOM se forma con su posición en la lista.
const props = defineProps<{
  items: { id: T; nombre: string }[]
  modelValue: T[]
  idBase: string
  etiquetaBoton: string
  nombreSingular: string
  nombrePlural: string
}>()

const emit = defineEmits<{ 'update:modelValue': [ids: T[]] }>()

const todosSeleccionados = computed(
  () => props.items.length > 0 && props.modelValue.length === props.items.length,
)

const textoDisparador = computed(() => {
  if (props.items.length === 0 || todosSeleccionados.value) return `Todas las ${props.nombrePlural}`
  if (props.modelValue.length === 0) return `Ninguna ${props.nombreSingular}`
  if (props.modelValue.length === 1) {
    const item = props.items.find((i) => i.id === props.modelValue[0])
    return item ? item.nombre : `1 ${props.nombreSingular}`
  }
  return `${props.modelValue.length} ${props.nombrePlural}`
})

function estaSeleccionado(id: T): boolean {
  return props.modelValue.includes(id)
}

function alternarItem(id: T, marcado: boolean): void {
  emit(
    'update:modelValue',
    marcado ? [...props.modelValue, id] : props.modelValue.filter((v) => v !== id),
  )
}

function alternarTodos(marcado: boolean): void {
  emit('update:modelValue', marcado ? props.items.map((i) => i.id) : [])
}
</script>

<template>
  <Popover>
    <PopoverTrigger as-child>
      <Button
        variant="outline"
        type="button"
        class="justify-between font-normal"
        :aria-label="`${etiquetaBoton}: ${textoDisparador}`"
      >
        {{ textoDisparador }}
        <ChevronDown class="text-muted-foreground size-4" />
      </Button>
    </PopoverTrigger>
    <PopoverContent class="w-64 p-2">
      <div class="flex items-center gap-2 px-2 py-1.5">
        <Checkbox
          :id="`${idBase}-todos`"
          :model-value="todosSeleccionados"
          @update:model-value="(valor) => alternarTodos(valor === true)"
        />
        <Label :for="`${idBase}-todos`" class="font-medium">Seleccionar todas</Label>
      </div>
      <Separator class="my-1" />
      <ul class="max-h-64 space-y-1 overflow-y-auto">
        <li
          v-for="(item, indice) in items"
          :key="item.id"
          class="flex items-center gap-2 px-2 py-1.5"
        >
          <Checkbox
            :id="`${idBase}-${indice}`"
            :model-value="estaSeleccionado(item.id)"
            @update:model-value="(valor) => alternarItem(item.id, valor === true)"
          />
          <Label :for="`${idBase}-${indice}`" class="truncate font-normal">{{ item.nombre }}</Label>
        </li>
      </ul>
    </PopoverContent>
  </Popover>
</template>
