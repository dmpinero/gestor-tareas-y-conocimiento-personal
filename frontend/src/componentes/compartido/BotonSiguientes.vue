<script setup lang="ts">
import { ListMinus, ListPlus } from '@lucide/vue'
import { computed } from 'vue'

import { Button } from '@/componentes/ui/button'
import { cn } from '@/lib/utils'
import { useTiendaSiguientes } from '@/stores/siguientes'

// "Añadir a siguientes" pone la tarea al final de la cola de "A continuación";
// si ya está, pasa a "Quitar de siguientes". Como `BotonFoco`: `compacto` lo
// deja en solo icono y, con `nombre`, el nombre accesible lo añade entre
// paréntesis. En una tarea completada no se muestra (la cola no las enseña).
// Los fallos quedan en el `error` de la tienda de siguientes.
const props = defineProps<{
  tareaId: number
  nombre?: string
  compacto?: boolean
  completada?: boolean
}>()

const tiendaSiguientes = useTiendaSiguientes()

const enCola = computed(() => tiendaSiguientes.estaEnCola(props.tareaId))
const etiqueta = computed(() => (enCola.value ? 'Quitar de siguientes' : 'Añadir a siguientes'))
const clases = computed(() =>
  cn(
    props.compacto && 'size-8',
    enCola.value ? 'text-sky-700 dark:text-sky-300' : props.compacto && 'text-muted-foreground',
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
  if (enCola.value) void tiendaSiguientes.quitar(props.tareaId)
  else void tiendaSiguientes.anadir(props.tareaId)
}
</script>

<template>
  <Button
    v-if="!completada"
    type="button"
    :variant="compacto ? 'ghost' : 'outline'"
    :size="compacto ? 'icon' : 'default'"
    data-boton-siguientes
    :data-en-siguientes="enCola ? 'true' : undefined"
    :class="clases"
    :aria-label="nombreAccesible"
    :title="etiqueta"
    @click="alternar"
  >
    <ListMinus v-if="enCola" aria-hidden="true" />
    <ListPlus v-else aria-hidden="true" />
    <template v-if="!compacto">{{ etiqueta }}</template>
  </Button>
</template>
