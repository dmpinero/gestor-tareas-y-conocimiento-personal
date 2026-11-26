<script setup lang="ts">
import { X } from '@lucide/vue'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { formatearTiempoFoco, textoFoco } from '@/lib/foco'
import { useTiendaFoco } from '@/stores/foco'

// Píldora de la barra superior con la tarea (o `Tarea › Subtarea`) en la que se
// está trabajando y desde hace cuánto. Pulsarla abre la tarea; el ✕ deja de
// trabajar en ella. Sin foco no se muestra. El foco se carga al montarla, que
// es al arrancar la aplicación.
const INTERVALO_MS = 60_000

const tiendaFoco = useTiendaFoco()
const router = useRouter()
const ahora = ref(new Date())
let intervalo: ReturnType<typeof setInterval> | null = null

const texto = computed(() => (tiendaFoco.foco ? textoFoco(tiendaFoco.foco) : ''))
const tiempo = computed(() =>
  tiendaFoco.foco ? formatearTiempoFoco(tiendaFoco.foco.desde, ahora.value) : '',
)

function abrir(): void {
  if (tiendaFoco.foco) {
    void router.push({ path: '/tareas', query: { tarea: String(tiendaFoco.foco.tarea_id) } })
  }
}

onMounted(() => {
  void tiendaFoco.cargar()
  intervalo = setInterval(() => {
    ahora.value = new Date()
  }, INTERVALO_MS)
})

onUnmounted(() => {
  if (intervalo !== null) clearInterval(intervalo)
})
</script>

<template>
  <div
    v-if="tiendaFoco.foco"
    data-indicador-foco
    class="flex min-w-0 items-center rounded-full border border-violet-500 bg-violet-50 text-xs text-violet-900 dark:border-violet-400 dark:bg-violet-950 dark:text-violet-100"
  >
    <button
      type="button"
      data-abrir-foco
      class="flex min-w-0 items-center gap-2 rounded-full py-1 pr-1 pl-3 outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-violet-500/50"
      :title="`Abrir ${texto}`"
      @click="abrir"
    >
      <span
        aria-hidden="true"
        class="size-2 shrink-0 rounded-full bg-violet-500 motion-safe:animate-pulse"
      />
      <!-- En pantallas estrechas el prefijo solo lo oye el lector de pantalla:
           así cabe el nombre de la tarea. -->
      <span class="truncate"
        ><span data-prefijo-foco class="max-sm:sr-only">Trabajando en: </span>{{ texto }}</span
      >
      <span class="-ml-2 shrink-0 whitespace-pre">{{ ` · ${tiempo}` }}</span>
    </button>
    <button
      type="button"
      aria-label="Dejar de trabajar"
      title="Dejar de trabajar"
      class="mr-1 rounded-full p-1 outline-none hover:bg-violet-100 focus-visible:ring-[3px] focus-visible:ring-violet-500/50 dark:hover:bg-violet-900"
      @click="tiendaFoco.quitar()"
    >
      <X class="size-3.5" aria-hidden="true" />
    </button>
  </div>
</template>
