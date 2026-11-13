<script setup lang="ts">
import { Ellipsis, Eye, Pencil, Trash } from '@lucide/vue'
import { ref } from 'vue'

import { Button } from '@/componentes/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/componentes/ui/popover'

// Menú "⋯" con las acciones de una fila de la tabla de tareas. Cada acción
// conserva el nombre accesible que tenía como botón suelto. El disparador
// siempre recibe el foco; en pantallas anchas con ratón solo se ve al pasar
// por la fila o al enfocarla (estilos `data-acciones-fila` en main.css).
const props = defineProps<{
  nombre: string
  idDisparador: string
}>()

const emit = defineEmits<{ editar: []; detalle: []; eliminar: [] }>()

const abierto = ref(false)

function elegir(accion: 'editar' | 'detalle' | 'eliminar'): void {
  abierto.value = false
  if (accion === 'editar') emit('editar')
  else if (accion === 'detalle') emit('detalle')
  else emit('eliminar')
}

const CLASE_OPCION =
  'hover:bg-accent hover:text-accent-foreground focus-visible:ring-ring/50 flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm outline-none focus-visible:ring-[3px] [&_svg]:size-4'
</script>

<template>
  <Popover v-model:open="abierto">
    <PopoverTrigger as-child>
      <Button
        :id="props.idDisparador"
        type="button"
        variant="ghost"
        size="icon"
        data-acciones-fila
        :aria-label="`Acciones de la tarea ${props.nombre}`"
        title="Acciones"
      >
        <Ellipsis aria-hidden="true" />
      </Button>
    </PopoverTrigger>
    <PopoverContent align="end" class="w-44 p-1">
      <button
        type="button"
        :class="CLASE_OPCION"
        :aria-label="`Editar tarea ${props.nombre}`"
        @click="elegir('editar')"
      >
        <Pencil aria-hidden="true" />Editar
      </button>
      <button
        type="button"
        :class="CLASE_OPCION"
        :aria-label="`Ver detalle de la tarea ${props.nombre}`"
        @click="elegir('detalle')"
      >
        <Eye aria-hidden="true" />Ver detalle
      </button>
      <button
        type="button"
        :class="[CLASE_OPCION, 'text-destructive']"
        :aria-label="`Eliminar la tarea ${props.nombre}`"
        @click="elegir('eliminar')"
      >
        <Trash aria-hidden="true" />Eliminar
      </button>
    </PopoverContent>
  </Popover>
</template>
