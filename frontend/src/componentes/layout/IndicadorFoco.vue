<script setup lang="ts">
import { ListOrdered, SkipForward, X } from '@lucide/vue'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { Popover, PopoverContent, PopoverTrigger } from '@/componentes/ui/popover'
import { formatearTiempoFoco, textoFoco } from '@/lib/foco'
import { useTiendaFoco } from '@/stores/foco'
import { useTiendaSiguientes } from '@/stores/siguientes'

// Píldora de la barra superior con la tarea (o `Tarea › Subtarea`) en la que se
// está trabajando y desde hace cuánto. Pulsarla abre la tarea; el ✕ deja de
// trabajar en ella. Con la cola de siguientes no vacía, al lado, el desplegable
// "Siguientes" con las 3 primeras y "Pasar a la siguiente: X" (también sin
// foco). Sin foco ni cola no se muestra. El foco y la cola se cargan al
// montarla, que es al arrancar la aplicación.
const INTERVALO_MS = 60_000
const MAXIMO_SIGUIENTES = 3

const tiendaFoco = useTiendaFoco()
const tiendaSiguientes = useTiendaSiguientes()
const desplegableAbierto = ref(false)
const primeras = computed(() => tiendaSiguientes.cola.slice(0, MAXIMO_SIGUIENTES))
const siguiente = computed(() => tiendaSiguientes.cola[0] ?? null)

async function pasarALaSiguiente(): Promise<void> {
  desplegableAbierto.value = false
  await tiendaSiguientes.pasarALaSiguiente()
}
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
  void tiendaSiguientes.cargar()
  intervalo = setInterval(() => {
    ahora.value = new Date()
  }, INTERVALO_MS)
})

onUnmounted(() => {
  if (intervalo !== null) clearInterval(intervalo)
})
</script>

<template>
  <div v-if="tiendaFoco.foco || siguiente" class="flex min-w-0 items-center gap-1">
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
    <Popover v-if="siguiente" v-model:open="desplegableAbierto">
      <PopoverTrigger as-child>
        <button
          type="button"
          data-siguientes
          class="flex shrink-0 items-center gap-1 rounded-full border px-2 py-1 text-xs outline-none hover:bg-accent hover:text-accent-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50"
          title="Siguientes"
        >
          <ListOrdered class="size-3.5" aria-hidden="true" />
          <span class="max-sm:sr-only">Siguientes</span>
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" class="w-72 max-w-[calc(100vw-2rem)] p-2">
        <p class="text-muted-foreground px-2 pb-1 text-xs font-semibold">Siguientes</p>
        <ol class="text-sm">
          <li v-for="(entrada, indice) in primeras" :key="entrada.tarea_id" data-siguiente>
            <RouterLink
              :to="{ path: '/tareas', query: { tarea: String(entrada.tarea_id) } }"
              class="hover:bg-accent hover:text-accent-foreground focus-visible:ring-ring/50 flex gap-2 rounded-sm px-2 py-1.5 outline-none focus-visible:ring-[3px]"
              @click="desplegableAbierto = false"
            >
              <span class="text-muted-foreground tabular-nums" aria-hidden="true"
                >{{ indice + 1 }}.</span
              >
              <span data-nombre-siguiente class="truncate">{{ entrada.tarea_nombre }}</span>
            </RouterLink>
          </li>
        </ol>
        <button
          type="button"
          data-pasar-siguiente
          class="hover:bg-accent hover:text-accent-foreground focus-visible:ring-ring/50 mt-1 flex w-full items-center gap-2 rounded-sm border-t px-2 py-1.5 text-left text-sm font-medium outline-none focus-visible:ring-[3px] [&_svg]:size-4"
          @click="pasarALaSiguiente"
        >
          <SkipForward aria-hidden="true" />
          <span class="truncate">Pasar a la siguiente: {{ siguiente.tarea_nombre }}</span>
        </button>
        <p v-if="tiendaSiguientes.error" class="text-destructive px-2 pt-1 text-xs" role="alert">
          {{ tiendaSiguientes.error }}
        </p>
      </PopoverContent>
    </Popover>
  </div>
</template>
