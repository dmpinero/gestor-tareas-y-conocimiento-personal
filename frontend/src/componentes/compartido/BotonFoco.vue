<script setup lang="ts">
import { CircleStop, Target } from '@lucide/vue'
import { computed } from 'vue'

import { Button } from '@/componentes/ui/button'
import { cn } from '@/lib/utils'
import { useTiendaFoco } from '@/stores/foco'

// "Trabajar en esta" pone la tarea (o la subtarea, si se indica) en foco y
// sustituye la que hubiera, sin preguntar. Sobre la que ya está en foco pasa a
// "Dejar de trabajar". `compacto` lo deja en solo icono. Con `nombre`, el
// nombre accesible lo añade entre paréntesis (como "Mover a…"), para que no se
// repita entre tarjetas o filas. Los fallos quedan en el `error` de la tienda
// del foco.
const props = defineProps<{
  tareaId: number
  subtareaId?: number | null
  nombre?: string
  compacto?: boolean
}>()

const tiendaFoco = useTiendaFoco()

const enFoco = computed(() =>
  props.subtareaId == null
    ? tiendaFoco.esTareaEnFoco(props.tareaId)
    : tiendaFoco.esSubtareaEnFoco(props.subtareaId),
)

const etiqueta = computed(() => (enFoco.value ? 'Dejar de trabajar' : 'Trabajar en esta'))
const clases = computed(() =>
  cn(
    props.compacto && 'size-8',
    enFoco.value
      ? 'text-violet-700 dark:text-violet-300'
      : props.compacto && 'text-muted-foreground',
  ),
)
const nombreAccesible = computed(() =>
  props.nombre
    ? `${etiqueta.value} (${props.nombre})`
    : props.compacto
      ? etiqueta.value
      : undefined,
)

function alternar(): void {
  if (enFoco.value) void tiendaFoco.quitar()
  else void tiendaFoco.fijar(props.tareaId, props.subtareaId ?? null)
}
</script>

<template>
  <Button
    type="button"
    :variant="compacto ? 'ghost' : 'outline'"
    :size="compacto ? 'icon' : 'default'"
    data-boton-foco
    :data-en-foco="enFoco ? 'true' : undefined"
    :class="clases"
    :aria-label="nombreAccesible"
    :title="etiqueta"
    @click="alternar"
  >
    <CircleStop v-if="enFoco" aria-hidden="true" />
    <Target v-else aria-hidden="true" />
    <template v-if="!compacto">{{ etiqueta }}</template>
  </Button>
</template>
