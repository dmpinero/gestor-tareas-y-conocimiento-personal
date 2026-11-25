<script setup lang="ts">
import { Play, Snowflake } from '@lucide/vue'
import { computed, ref } from 'vue'

import type { Tarea } from '@/api/tipos'
import { Button } from '@/componentes/ui/button'
import DialogoHibernar from '@/componentes/compartido/DialogoHibernar.vue'
import { estaHibernada } from '@/lib/hibernacion'
import { cn } from '@/lib/utils'
import { useTiendaTareas } from '@/stores/tareas'

// "Hibernar" abre el diálogo con el comentario opcional; sobre una tarea ya
// hibernada pasa a "Reanudar", que la despierta al momento. `compacto` lo deja
// en solo icono (tablero). El nombre accesible incluye el de la tarea, para
// que no se repita entre tarjetas. Reenvía `hibernada` del diálogo.
const props = defineProps<{ tarea: Tarea; compacto?: boolean }>()
const emit = defineEmits<{ hibernada: [conComentario: boolean] }>()

const tiendaTareas = useTiendaTareas()
const hibernada = computed(() => estaHibernada(props.tarea))
const etiqueta = computed(() => (hibernada.value ? 'Reanudar' : 'Hibernar'))
const enDialogo = ref<Tarea | null>(null)

function pulsar(): void {
  if (hibernada.value) void tiendaTareas.reanudar(props.tarea.id)
  else enDialogo.value = props.tarea
}
</script>

<template>
  <Button
    type="button"
    :variant="props.compacto ? 'ghost' : 'outline'"
    :size="props.compacto ? 'icon' : 'default'"
    :data-reanudar="hibernada ? '' : undefined"
    :data-hibernar="hibernada ? undefined : ''"
    :class="
      cn(
        props.compacto && 'size-8',
        hibernada ? 'text-sky-700 dark:text-sky-300' : props.compacto && 'text-muted-foreground',
      )
    "
    :aria-label="`${etiqueta} la tarea ${props.tarea.nombre}`"
    :title="etiqueta"
    @click="pulsar"
  >
    <Play v-if="hibernada" aria-hidden="true" />
    <Snowflake v-else aria-hidden="true" />
    <template v-if="!props.compacto">{{ etiqueta }}</template>
  </Button>
  <DialogoHibernar
    :tarea="enDialogo"
    @cerrar="enDialogo = null"
    @hibernada="(conComentario: boolean) => emit('hibernada', conComentario)"
  />
</template>
