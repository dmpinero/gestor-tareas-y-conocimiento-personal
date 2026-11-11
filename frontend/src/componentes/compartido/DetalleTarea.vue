<script setup lang="ts">
import { Trash } from '@lucide/vue'
import { computed, ref, watch } from 'vue'

import { etiquetaTipoTarea, type Tarea } from '@/api/tipos'
import { formatearFechaHora } from '@/lib/fechas'
import ComentariosTarea from '@/componentes/compartido/ComentariosTarea.vue'
import ContadorVencimiento from '@/componentes/compartido/ContadorVencimiento.vue'
import SubtareasTarea from '@/componentes/compartido/SubtareasTarea.vue'
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

// Modal con todos los campos de una tarea. Está abierta mientras `tarea` no
// sea `null`; al cerrarla (botón, Escape o clic fuera) emite `cerrar`. El botón
// de la papelera emite `eliminar`: la confirmación, el borrado y el cierre son
// cosa de quien la usa. `error` se muestra dentro de la modal porque, mientras
// está abierta, el resto de la página queda oculto.
const props = defineProps<{ tarea: Tarea | null; error?: string | null }>()
const emit = defineEmits<{ cerrar: []; eliminar: [] }>()

// Se conserva la última tarea mostrada para que el contenido no desaparezca
// mientras dura la animación de cierre.
const tareaMostrada = ref<Tarea | null>(props.tarea)
watch(
  () => props.tarea,
  (tarea) => {
    if (tarea !== null) tareaMostrada.value = tarea
  },
)

const VACIO = '—'

function textoOVacio(valor: string | number | null | undefined): string {
  if (valor === null || valor === undefined || valor === '') return VACIO
  return String(valor)
}

function unirNombres(nombres: string[]): string {
  return nombres.length > 0 ? nombres.join(', ') : VACIO
}

interface Campo {
  termino: string
  valor: string
  // Textos largos que pueden traer saltos de línea.
  multilinea?: boolean
  // Fecha ISO de la que mostrar la cuenta atrás junto al valor.
  cuentaAtras?: string
}

const camposTarea = computed<Campo[]>(() => {
  const tarea = tareaMostrada.value
  if (tarea === null) return []
  return [
    { termino: 'Nombre', valor: tarea.nombre },
    { termino: 'Prioridad', valor: textoOVacio(tarea.prioridad) },
    { termino: 'Descripción', valor: textoOVacio(tarea.descripcion), multilinea: true },
    { termino: 'Etiquetas', valor: unirNombres(tarea.etiquetas) },
    { termino: 'Asignado a', valor: unirNombres(tarea.asignados) },
    { termino: 'Fecha de creación', valor: formatearFechaHora(tarea.fecha_creacion) },
    {
      termino: 'Fecha de vencimiento',
      valor: tarea.fecha_vencimiento ? formatearFechaHora(tarea.fecha_vencimiento) : VACIO,
      cuentaAtras: tarea.fecha_vencimiento ?? undefined,
    },
    { termino: 'Tipo', valor: textoOVacio(etiquetaTipoTarea(tarea.tipo)) },
    { termino: 'Estado', valor: tarea.completada ? 'Completada' : 'Pendiente' },
    // "Estado del grupo" para no confundirlo con el de completado.
    { termino: 'Grupo de estados', valor: textoOVacio(tarea.grupo_estados?.nombre) },
    { termino: 'Estado del grupo', valor: textoOVacio(tarea.estado?.nombre) },
  ]
})

// Bloque propio de cada tipo; hoy solo existe "Oportunidad".
const camposOportunidad = computed<Campo[] | null>(() => {
  const tarea = tareaMostrada.value
  if (tarea?.tipo !== 'oportunidad' || !tarea.oportunidad) return null
  const { codigo, descripcion, observaciones } = tarea.oportunidad
  return [
    { termino: 'Código', valor: textoOVacio(codigo) },
    {
      termino: 'Descripción de la oportunidad',
      valor: textoOVacio(descripcion),
      multilinea: true,
    },
    { termino: 'Observaciones', valor: textoOVacio(observaciones), multilinea: true },
  ]
})

function alCambiarApertura(abierta: boolean): void {
  if (!abierta) emit('cerrar')
}
</script>

<template>
  <Dialog :open="props.tarea !== null" @update:open="alCambiarApertura">
    <DialogContent sin-aspa class="flex h-[90vh] w-[90vw] max-w-none flex-col sm:max-w-none">
      <DialogHeader>
        <DialogTitle class="[overflow-wrap:anywhere]">{{ tareaMostrada?.nombre }}</DialogTitle>
        <DialogDescription class="sr-only">Todos los datos de la tarea.</DialogDescription>
      </DialogHeader>

      <!-- Dos columnas: datos y subtareas a la izquierda, comentarios a la derecha.
           En pantallas estrechas se apilan y desplaza el conjunto. -->
      <div
        class="grid min-h-0 flex-1 gap-6 overflow-y-auto md:grid-cols-[minmax(0,3fr)_minmax(18rem,2fr)] md:overflow-hidden"
      >
        <div
          data-testid="detalle-contenido"
          class="min-h-0 overflow-y-auto pr-2"
          role="region"
          aria-label="Contenido del detalle"
          tabindex="0"
        >
          <dl data-testid="campos-tarea" class="grid gap-3">
            <div
              v-for="campo in camposTarea"
              :key="campo.termino"
              class="grid gap-1 sm:grid-cols-[14rem_1fr]"
            >
              <dt class="text-muted-foreground text-sm font-medium">{{ campo.termino }}</dt>
              <dd v-if="campo.cuentaAtras" class="text-sm [overflow-wrap:anywhere]">
                {{ campo.valor }}
                <ContadorVencimiento :vencimiento="campo.cuentaAtras" class="ml-2" />
              </dd>
              <dd
                v-else
                class="text-sm [overflow-wrap:anywhere]"
                :class="campo.multilinea ? 'whitespace-pre-wrap' : ''"
                v-text="campo.valor"
              />
            </div>
          </dl>

          <section v-if="camposOportunidad" class="mt-6 border-t pt-4">
            <h3 class="mb-3 text-base font-semibold">Oportunidad</h3>
            <dl data-testid="campos-oportunidad" class="grid gap-3">
              <div
                v-for="campo in camposOportunidad"
                :key="campo.termino"
                class="grid gap-1 sm:grid-cols-[14rem_1fr]"
              >
                <dt class="text-muted-foreground text-sm font-medium">{{ campo.termino }}</dt>
                <dd
                  class="text-sm [overflow-wrap:anywhere]"
                  :class="campo.multilinea ? 'whitespace-pre-wrap' : ''"
                  v-text="campo.valor"
                />
              </div>
            </dl>
          </section>

          <div v-if="tareaMostrada" class="mt-6 border-t pt-4">
            <SubtareasTarea :tarea="tareaMostrada" />
          </div>
        </div>

        <aside
          v-if="tareaMostrada"
          data-testid="columna-comentarios"
          aria-label="Comentarios de la tarea"
          class="flex min-h-0 flex-col border-t pt-4 md:border-t-0 md:border-l md:pt-0 md:pl-6"
        >
          <ComentariosTarea :ruta="`/tareas/${tareaMostrada.id}/comentarios`" />
        </aside>
      </div>

      <p v-if="props.error" class="text-sm text-destructive" role="alert">{{ props.error }}</p>

      <DialogFooter>
        <Button
          type="button"
          variant="outline"
          class="text-destructive sm:mr-auto"
          :aria-label="`Eliminar la tarea ${tareaMostrada?.nombre ?? ''}`"
          @click="emit('eliminar')"
        >
          <Trash aria-hidden="true" />
          Eliminar
        </Button>
        <DialogClose as-child>
          <Button type="button" variant="secondary">Cerrar</Button>
        </DialogClose>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
