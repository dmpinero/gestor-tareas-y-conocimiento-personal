<script lang="ts">
/** Un botón de confirmar del diálogo: "`texto` (n)". `V` es el valor de cada
 * elemento: el id de la tarea si se le pasan `tareas`. */
export interface AccionEleccion<V = number> {
  /** Valor de `data-accion-eleccion` en su botón. */
  clave: string
  texto: string
  /** Elementos que ya están en su destino: no cuentan en su (n) ni se le pasan. */
  yaIncluida?: (valor: V) => boolean
  /** Recibe los valores marcados (sin los `yaIncluida`) en el orden en que se
   * marcaron; `null` cierra el diálogo y un mensaje lo deja abierto con él. */
  confirmar: (valores: V[]) => Promise<string | null>
}

/** Un elemento que se puede elegir, cuando no son solo tareas. */
export interface ElementoEleccion<V> {
  /** Única entre los elementos (clave de la lista y valor de su casilla). */
  clave: string
  valor: V
  /** Lo que se muestra; también se busca en él. */
  nombre: string
  /** Se muestra tachado y atenuado (p. ej. una tarea completada). */
  tachado?: boolean
  /** Texto breve junto al elemento (p. ej. dónde está ya). */
  nota?: string | null
}
</script>

<script setup lang="ts" generic="V = number">
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
// usa) o, en su lugar, unos `elementos` cualesquiera (p. ej. tareas y
// subtareas), en orden alfabético y filtradas por un buscador que no distingue
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
  tareas?: readonly Tarea[]
  elementos?: readonly ElementoEleccion<V>[]
  acciones: readonly AccionEleccion<V>[]
  nota?: (tarea: Tarea) => string | null
}>()
const emit = defineEmits<{ 'update:abierto': [abierto: boolean] }>()

const consulta = ref('')
// Claves de los elementos marcados, en el orden en que se marcaron.
const elegidas = ref<string[]>([])
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

// Con `tareas`, cada una es un elemento cuyo valor es su id.
function elementoDeTarea(tarea: Tarea): ElementoEleccion<V> {
  return {
    clave: String(tarea.id),
    valor: tarea.id as V,
    nombre: tarea.nombre,
    tachado: tarea.completada,
    nota: props.nota?.(tarea) ?? null,
  }
}

const disponibles = computed(() =>
  [...(props.elementos ?? (props.tareas ?? []).map(elementoDeTarea))].sort((a, b) =>
    a.nombre.localeCompare(b.nombre, 'es'),
  ),
)

const visibles = computed(() => {
  const clave = normalizarTextoBusqueda(consulta.value.trim())
  return disponibles.value.filter((otro) => normalizarTextoBusqueda(otro.nombre).includes(clave))
})

// Valores marcados que recibe cada acción, en el orden en que se marcaron.
function valoresPara(accion: AccionEleccion<V>): V[] {
  const porClave = new Map(disponibles.value.map((elemento) => [elemento.clave, elemento.valor]))
  return elegidas.value
    .filter((clave) => porClave.has(clave))
    .map((clave) => porClave.get(clave)!)
    .filter((valor) => !accion.yaIncluida?.(valor))
}

const botones = computed(() =>
  props.acciones.map((accion) => {
    const n = valoresPara(accion).length
    return { accion, n, texto: n === 0 ? accion.texto : `${accion.texto} (${n})` }
  }),
)

function alCambiarApertura(abierto: boolean): void {
  if (!abierto && procesando.value) return
  emit('update:abierto', abierto)
}

async function alConfirmar(accion: AccionEleccion<V>): Promise<void> {
  const valores = valoresPara(accion)
  if (valores.length === 0 || procesando.value) return
  procesando.value = true
  error.value = null
  const fallo = await accion.confirmar(valores)
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
          <li v-for="otro in visibles" :key="otro.clave">
            <label
              class="hover:bg-muted/60 flex cursor-pointer items-center gap-3 px-3 py-2 text-sm [overflow-wrap:anywhere]"
            >
              <input
                v-model="elegidas"
                type="checkbox"
                :value="otro.clave"
                :disabled="procesando"
                class="accent-primary size-4 shrink-0"
              />
              <span
                data-nombre-eleccion
                :class="otro.tachado ? 'text-muted-foreground line-through' : ''"
                >{{ otro.nombre }}</span
              >
              <span
                v-if="otro.nota"
                data-nota-eleccion
                class="bg-muted text-muted-foreground ml-auto shrink-0 rounded-full px-2 py-0.5 text-xs"
                >{{ otro.nota }}</span
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
