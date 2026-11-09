<script setup lang="ts">
import { useMediaQuery } from '@vueuse/core'
import { computed, ref, watch } from 'vue'
import { cn } from '@/lib/utils'
import {
  ANCHO_PANEL,
  ANCHO_PANEL_ICONO,
  CLAVE_ALMACENAMIENTO,
  proveerPanelLateral,
} from './useSidebar'

const props = defineProps<{ class?: string }>()

function leerEstadoInicial(): 'expandido' | 'colapsado' {
  const guardado = localStorage.getItem(CLAVE_ALMACENAMIENTO)
  return guardado === 'colapsado' ? 'colapsado' : 'expandido'
}

const estado = ref<'expandido' | 'colapsado'>(leerEstadoInicial())
const abiertoEnMovil = ref(false)
const esMovil = useMediaQuery('(max-width: 767px)')

function alternar(): void {
  if (esMovil.value) {
    abiertoEnMovil.value = !abiertoEnMovil.value
    return
  }
  estado.value = estado.value === 'expandido' ? 'colapsado' : 'expandido'
}

watch(estado, (valor) => {
  localStorage.setItem(CLAVE_ALMACENAMIENTO, valor)
})

proveerPanelLateral({ estado, abiertoEnMovil, esMovil, alternar })

const estiloVariables = computed(() => ({
  '--sidebar-width': ANCHO_PANEL,
  '--sidebar-width-icon': ANCHO_PANEL_ICONO,
}))
</script>

<template>
  <div
    data-slot="sidebar-wrapper"
    :style="estiloVariables"
    :class="cn('group/sidebar-wrapper flex min-h-svh w-full', props.class)"
  >
    <slot />
  </div>
</template>
