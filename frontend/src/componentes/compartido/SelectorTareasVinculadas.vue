<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { Tarea } from '@/api/tipos'
import { normalizarTextoBusqueda } from '@/composables/useBusquedaTabla'
import { Button } from '@/componentes/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/componentes/ui/dialog'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'
import { useTiendaTareas } from '@/stores/tareas'

// Diálogo para vincular `tarea` con una o varias tareas más. Ofrece las demás
// tareas del almacén (sin ella ni las ya vinculadas), en orden alfabético y
// filtradas por un buscador que no distingue mayúsculas ni acentos.
// "Relacionar (n)" las vincula todas de una vez: si acierta cierra el diálogo
// (`update:abierto`) y, si la API falla, sigue abierto con el error. Cancelar,
// Escape o un clic fuera lo cierran sin cambios; al reabrirlo empieza vacío.
const props = defineProps<{ tarea: Tarea; abierto: boolean }>()
const emit = defineEmits<{ 'update:abierto': [abierto: boolean] }>()

const tienda = useTiendaTareas()
const consulta = ref('')
const elegidas = ref<number[]>([])
const procesando = ref(false)
const error = ref<string | null>(null)
const idBuscador = computed(() => `buscar-vinculadas-${props.tarea.id}`)

watch(
  () => props.abierto,
  (abierto) => {
    if (!abierto) return
    consulta.value = ''
    elegidas.value = []
    error.value = null
  },
)

const disponibles = computed(() =>
  tienda.tareas
    .filter((otra) => otra.id !== props.tarea.id && !props.tarea.vinculadas.includes(otra.id))
    .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es')),
)

const visibles = computed(() => {
  const clave = normalizarTextoBusqueda(consulta.value.trim())
  return disponibles.value.filter((otra) => normalizarTextoBusqueda(otra.nombre).includes(clave))
})

const textoConfirmar = computed(() =>
  elegidas.value.length === 0 ? 'Relacionar' : `Relacionar (${elegidas.value.length})`,
)

function alCambiarApertura(abierto: boolean): void {
  if (!abierto && procesando.value) return
  emit('update:abierto', abierto)
}

async function confirmar(): Promise<void> {
  if (elegidas.value.length === 0 || procesando.value) return
  procesando.value = true
  error.value = null
  const ids = [...elegidas.value].sort((a, b) => a - b)
  const hecho = await tienda.vincularTareas(props.tarea.id, ids)
  procesando.value = false
  if (!hecho) {
    error.value = tienda.error
    return
  }
  emit('update:abierto', false)
}
</script>

<template>
  <Dialog :open="props.abierto" @update:open="alCambiarApertura">
    <DialogContent sin-aspa class="flex max-h-[85vh] flex-col sm:max-w-lg">
      <DialogHeader>
        <DialogTitle class="[overflow-wrap:anywhere]"
          >Relacionar tareas con {{ props.tarea.nombre }}</DialogTitle
        >
        <DialogDescription>
          Elige una o varias tareas. Cada una mostrará también esta tarea entre sus tareas
          relacionadas.
        </DialogDescription>
      </DialogHeader>

      <div class="flex flex-col gap-1.5">
        <Label :for="idBuscador">Buscar tarea</Label>
        <Input :id="idBuscador" v-model="consulta" type="search" autocomplete="off" />
      </div>

      <!-- Un div con scroll (no un fieldset: Chrome no lo recorta y la lista se
           salía del diálogo tapando los botones). -->
      <div
        role="group"
        aria-label="Tareas que se pueden relacionar"
        data-lista-vinculables
        class="min-h-0 flex-1 overflow-y-auto rounded-md border"
      >
        <ul v-if="visibles.length > 0" class="divide-y">
          <li v-for="otra in visibles" :key="otra.id">
            <label
              class="hover:bg-muted/60 flex cursor-pointer items-center gap-3 px-3 py-2 text-sm [overflow-wrap:anywhere]"
            >
              <input
                v-model="elegidas"
                type="checkbox"
                :value="otra.id"
                :disabled="procesando"
                class="accent-primary size-4 shrink-0"
              />
              <span :class="otra.completada ? 'text-muted-foreground line-through' : ''">{{
                otra.nombre
              }}</span>
            </label>
          </li>
        </ul>
        <p v-else class="text-muted-foreground px-3 py-2 text-sm">
          {{
            disponibles.length === 0
              ? 'No quedan tareas por relacionar.'
              : 'No hay tareas que coincidan con la búsqueda.'
          }}
        </p>
      </div>

      <p v-if="error" class="text-destructive text-sm" role="alert">{{ error }}</p>

      <DialogFooter>
        <DialogClose as-child>
          <Button type="button" variant="outline" :disabled="procesando">Cancelar</Button>
        </DialogClose>
        <Button
          type="button"
          data-confirmar-vinculadas
          :disabled="elegidas.length === 0 || procesando"
          @click="confirmar"
          >{{ textoConfirmar }}</Button
        >
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
