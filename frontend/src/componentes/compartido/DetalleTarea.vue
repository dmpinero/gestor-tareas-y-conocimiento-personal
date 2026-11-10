<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { etiquetaTipoTarea, type Tarea } from '@/api/tipos'
import { formatearFechaHora } from '@/lib/fechas'
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
// sea `null`; al cerrarla (botón, Escape o clic fuera) emite `cerrar`.
const props = defineProps<{ tarea: Tarea | null }>()
const emit = defineEmits<{ cerrar: [] }>()

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
    },
    { termino: 'Tipo', valor: textoOVacio(etiquetaTipoTarea(tarea.tipo)) },
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

      <div
        data-testid="detalle-contenido"
        class="min-h-0 flex-1 overflow-y-auto pr-2"
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
            <dd
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
      </div>

      <DialogFooter>
        <DialogClose as-child>
          <Button type="button" variant="secondary">Cerrar</Button>
        </DialogClose>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
