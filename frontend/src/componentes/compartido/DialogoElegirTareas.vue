<script lang="ts">
/** Un botón de confirmar del diálogo: "`texto` (n)". */
export interface AccionEleccion {
  /** Valor de `data-accion-eleccion` en su botón. */
  clave: string
  texto: string
  /** Tareas que ya están en su destino: no cuentan en su (n) ni se le pasan. */
  yaIncluida?: (tareaId: number) => boolean
  /** Recibe los ids marcados (sin los `yaIncluida`) en el orden en que se
   * marcaron; `null` cierra el diálogo y un mensaje lo deja abierto con él. */
  confirmar: (ids: number[]) => Promise<string | null>
}
</script>

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

// Diálogo para elegir una o varias tareas de `tareas` (ya filtradas por quien lo
// usa), en orden alfabético y filtradas por un buscador que no distingue
// mayúsculas ni acentos. Cada una de las `acciones` es un botón "`texto` (n)"
// que llama a su `confirmar` con los ids marcados en el orden en que se
// marcaron, sin los que ya están en su destino (`yaIncluida`): si devuelve
// `null` cierra el diálogo (`update:abierto`) y, si devuelve un mensaje, sigue
// abierto mostrándolo. `nota` añade un texto breve junto a una tarea (p. ej.
// dónde está ya). Cancelar, Escape o un clic fuera lo cierran sin cambios; al
// reabrirlo empieza vacío. Lo usan "Relacionar tareas" (una acción) y "Añadir a
// siguientes" (dos).
const props = defineProps<{
  abierto: boolean
  titulo: string
  descripcion: string
  etiquetaLista: string
  textoSinTareas: string
  idBuscador: string
  tareas: readonly Tarea[]
  acciones: readonly AccionEleccion[]
  nota?: (tarea: Tarea) => string | null
}>()
const emit = defineEmits<{ 'update:abierto': [abierto: boolean] }>()

const consulta = ref('')
const elegidas = ref<number[]>([])
const procesando = ref(false)
const error = ref<string | null>(null)

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
  [...props.tareas].sort((a, b) => a.nombre.localeCompare(b.nombre, 'es')),
)

const visibles = computed(() => {
  const clave = normalizarTextoBusqueda(consulta.value.trim())
  return disponibles.value.filter((otra) => normalizarTextoBusqueda(otra.nombre).includes(clave))
})

// Ids marcados que recibe cada acción, en el orden en que se marcaron.
function idsPara(accion: AccionEleccion): number[] {
  return elegidas.value.filter((id) => !accion.yaIncluida?.(id))
}

const botones = computed(() =>
  props.acciones.map((accion) => {
    const n = idsPara(accion).length
    return { accion, n, texto: n === 0 ? accion.texto : `${accion.texto} (${n})` }
  }),
)

function alCambiarApertura(abierto: boolean): void {
  if (!abierto && procesando.value) return
  emit('update:abierto', abierto)
}

async function alConfirmar(accion: AccionEleccion): Promise<void> {
  const ids = idsPara(accion)
  if (ids.length === 0 || procesando.value) return
  procesando.value = true
  error.value = null
  const fallo = await accion.confirmar(ids)
  procesando.value = false
  if (fallo !== null) {
    error.value = fallo
    return
  }
  emit('update:abierto', false)
}
</script>

<template>
  <Dialog :open="props.abierto" @update:open="alCambiarApertura">
    <DialogContent sin-aspa class="flex max-h-[85vh] flex-col sm:max-w-lg">
      <DialogHeader>
        <DialogTitle class="[overflow-wrap:anywhere]">{{ props.titulo }}</DialogTitle>
        <DialogDescription>{{ props.descripcion }}</DialogDescription>
      </DialogHeader>

      <div class="flex flex-col gap-1.5">
        <Label :for="props.idBuscador">Buscar tarea</Label>
        <Input :id="props.idBuscador" v-model="consulta" type="search" autocomplete="off" />
      </div>

      <!-- Un div con scroll (no un fieldset: Chrome no lo recorta y la lista se
           salía del diálogo tapando los botones). -->
      <div
        role="group"
        :aria-label="props.etiquetaLista"
        data-lista-tareas
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
              <span
                data-nombre-eleccion
                :class="otra.completada ? 'text-muted-foreground line-through' : ''"
                >{{ otra.nombre }}</span
              >
              <span
                v-if="props.nota?.(otra)"
                data-nota-eleccion
                class="bg-muted text-muted-foreground ml-auto shrink-0 rounded-full px-2 py-0.5 text-xs"
                >{{ props.nota(otra) }}</span
              >
            </label>
          </li>
        </ul>
        <p v-else class="text-muted-foreground px-3 py-2 text-sm">
          {{
            disponibles.length === 0
              ? props.textoSinTareas
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
          v-for="boton in botones"
          :key="boton.accion.clave"
          type="button"
          data-confirmar-eleccion
          :data-accion-eleccion="boton.accion.clave"
          :disabled="boton.n === 0 || procesando"
          @click="alConfirmar(boton.accion)"
          >{{ boton.texto }}</Button
        >
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
