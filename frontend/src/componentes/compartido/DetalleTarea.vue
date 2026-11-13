<script setup lang="ts">
import { Pencil, Trash } from '@lucide/vue'
import { computed, ref, watch } from 'vue'

import { etiquetaTipoTarea, type Tarea } from '@/api/tipos'
import type { TipoRelacion } from '@/composables/useTareasRelacionadas'
import {
  CLASE_PILDORA,
  PILDORA_COMPLETADA,
  PILDORA_PENDIENTE,
  PILDORA_PRIORIDAD,
  PILDORA_TIPO,
  clavePrioridad,
  colorEtiqueta,
  pildoraEstado,
} from '@/lib/coloresTarea'
import { formatearFechaHora } from '@/lib/fechas'
import { useTiendaGruposEstados } from '@/stores/gruposEstados'
import AvatarPersona from '@/componentes/compartido/AvatarPersona.vue'
import ComentariosTarea from '@/componentes/compartido/ComentariosTarea.vue'
import AvisoVencimiento from '@/componentes/compartido/AvisoVencimiento.vue'
import ContadorVencimiento from '@/componentes/compartido/ContadorVencimiento.vue'
import NombreRelacionado from '@/componentes/compartido/NombreRelacionado.vue'
import SubtareasTarea from '@/componentes/compartido/SubtareasTarea.vue'
import VencimientoCorto from '@/componentes/compartido/VencimientoCorto.vue'
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
// está abierta, el resto de la página queda oculto. "Editar" emite `editar`;
// mientras `editando` sea cierto, la columna de los datos muestra el slot
// `edicion` (el formulario, que pone quien la usa) y los comentarios siguen a
// la vista. Las zonas (cabecera, tarjetas de campos, subtareas y comentarios)
// son superficies que destacan sobre el lienzo de la modal.
const props = defineProps<{ tarea: Tarea | null; error?: string | null; editando?: boolean }>()
const emit = defineEmits<{ cerrar: []; eliminar: []; editar: [] }>()

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

interface Campo {
  termino: string
  valor: string
  // Textos largos que pueden traer saltos de línea.
  multilinea?: boolean
  // Etiquetas o personas que se pueden pulsar para ver sus tareas relacionadas:
  // las personas se muestran con su avatar y las etiquetas como píldoras.
  relacionados?: { tipo: TipoRelacion; nombres: string[] }
}

interface Tarjeta {
  titulo: string
  campos: Campo[]
  // Clases de colocación en la rejilla de tarjetas.
  clase?: string
}

// Campos de la tarea agrupados en tarjetas con título. La descripción tiene su
// propia tarjeta (texto libre) y la cabecera resume prioridad, estado, tipo y
// vencimiento con píldoras.
const tarjetasCampos = computed<Tarjeta[]>(() => {
  const tarea = tareaMostrada.value
  if (tarea === null) return []
  return [
    {
      titulo: 'Planificación',
      clase: 'xl:row-span-2',
      campos: [
        { termino: 'Fecha de creación', valor: formatearFechaHora(tarea.fecha_creacion) },
        {
          termino: 'Fecha de vencimiento',
          valor: tarea.fecha_vencimiento ? formatearFechaHora(tarea.fecha_vencimiento) : VACIO,
        },
        { termino: 'Prioridad', valor: textoOVacio(tarea.prioridad) },
        { termino: 'Estado', valor: tarea.completada ? 'Completada' : 'Pendiente' },
        // "Estado del grupo" para no confundirlo con el de completado.
        { termino: 'Grupo de estados', valor: textoOVacio(tarea.grupo_estados?.nombre) },
        { termino: 'Estado del grupo', valor: textoOVacio(tarea.estado?.nombre) },
      ],
    },
    {
      titulo: 'Personas y etiquetas',
      campos: [
        {
          termino: 'Asignado a',
          valor: VACIO,
          relacionados: { tipo: 'persona', nombres: tarea.asignados },
        },
        {
          termino: 'Etiquetas',
          valor: VACIO,
          relacionados: { tipo: 'etiqueta', nombres: tarea.etiquetas },
        },
      ],
    },
    {
      titulo: 'Datos generales',
      campos: [
        { termino: 'Nombre', valor: tarea.nombre },
        { termino: 'Tipo', valor: textoOVacio(etiquetaTipoTarea(tarea.tipo)) },
        { termino: 'Workflow', valor: textoOVacio(tarea.workflow?.nombre) },
      ],
    },
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

// --- Píldoras de la cabecera ---
const tiendaGrupos = useTiendaGruposEstados()

const clasePildoraPrioridad = computed(() => {
  const prioridad = tareaMostrada.value?.prioridad ?? null
  const clave = clavePrioridad(prioridad)
  return clave === 'sin' ? '' : `${CLASE_PILDORA} ${PILDORA_PRIORIDAD[clave]}`
})

// Mismo color que en la tabla: según la posición del estado en su grupo.
const clasePildoraEstado = computed(() => {
  const tarea = tareaMostrada.value
  const estados =
    tiendaGrupos.grupos.find((grupo) => grupo.id === tarea?.grupo_estados?.id)?.estados ?? []
  const indice = estados.findIndex((estado) => estado.id === tarea?.estado?.id)
  return `${CLASE_PILDORA} ${pildoraEstado(indice, estados.length)}`
})

// Cada tarjeta de campos lleva un título enlazado por id para su región.
function idTarjeta(titulo: string): string {
  const base = titulo
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
  return `detalle-tarjeta-${base}`
}

const CLASE_TARJETA = 'bg-card text-card-foreground rounded-xl border p-4 shadow-xs'
const CLASE_TITULO_TARJETA =
  'text-muted-foreground mb-3 text-xs font-semibold tracking-wide uppercase'

function alCambiarApertura(abierta: boolean): void {
  if (!abierta) emit('cerrar')
}
</script>

<template>
  <Dialog :open="props.tarea !== null" @update:open="alCambiarApertura">
    <DialogContent
      sin-aspa
      class="bg-lienzo flex h-[90vh] w-[90vw] max-w-none flex-col sm:max-w-none"
    >
      <!-- Banda de cabecera: nombre, campanas y píldoras con el resumen. -->
      <DialogHeader data-testid="cabecera-detalle" :class="`${CLASE_TARJETA} gap-3`">
        <div class="flex items-start gap-2">
          <DialogTitle class="text-xl [overflow-wrap:anywhere]">{{
            tareaMostrada?.nombre
          }}</DialogTitle>
          <AvisoVencimiento
            v-if="tareaMostrada"
            class="mt-1.5"
            :vencimiento="tareaMostrada.fecha_vencimiento"
            :completada="tareaMostrada.completada"
          />
        </div>
        <ul
          v-if="tareaMostrada"
          aria-label="Resumen de la tarea"
          class="flex flex-wrap items-center gap-2"
        >
          <li v-if="tareaMostrada.prioridad !== null" class="flex">
            <span data-testid="pildora-prioridad" :class="clasePildoraPrioridad"
              >Prioridad {{ tareaMostrada.prioridad }}</span
            >
          </li>
          <li class="flex">
            <span
              data-testid="pildora-completado"
              :class="`${CLASE_PILDORA} ${tareaMostrada.completada ? PILDORA_COMPLETADA : PILDORA_PENDIENTE}`"
              >{{ tareaMostrada.completada ? 'Completada' : 'Pendiente' }}</span
            >
          </li>
          <li v-if="tareaMostrada.estado" class="flex">
            <span
              data-testid="pildora-estado"
              :class="clasePildoraEstado"
              :title="`Estado del grupo ${tareaMostrada.grupo_estados?.nombre ?? ''}`.trim()"
              >{{ tareaMostrada.estado.nombre }}</span
            >
          </li>
          <li v-if="tareaMostrada.tipo !== null" class="flex">
            <span data-testid="pildora-tipo" :class="`${CLASE_PILDORA} ${PILDORA_TIPO}`">{{
              etiquetaTipoTarea(tareaMostrada.tipo)
            }}</span>
          </li>
          <!-- Fondo de superficie: los colores de la cuenta atrás mantienen 4,5:1. -->
          <li v-if="tareaMostrada.fecha_vencimiento" class="flex">
            <span
              data-testid="pildora-vencimiento"
              :class="`${CLASE_PILDORA} bg-background gap-1.5 border`"
            >
              <VencimientoCorto
                :vencimiento="tareaMostrada.fecha_vencimiento"
                :completada="tareaMostrada.completada"
              />
              <span aria-hidden="true">·</span>
              <ContadorVencimiento :vencimiento="tareaMostrada.fecha_vencimiento" />
            </span>
          </li>
        </ul>
        <DialogDescription class="sr-only">Todos los datos de la tarea.</DialogDescription>
      </DialogHeader>

      <!-- Dos columnas: datos y subtareas a la izquierda, comentarios a la derecha.
           En pantallas estrechas se apilan y desplaza el conjunto. -->
      <div
        class="grid min-h-0 flex-1 gap-4 overflow-y-auto md:grid-cols-[minmax(0,3fr)_minmax(18rem,2fr)] md:overflow-hidden"
      >
        <div
          v-if="props.editando"
          data-testid="detalle-edicion"
          :class="`${CLASE_TARJETA} flex min-h-0 flex-col`"
          role="region"
          aria-label="Edición de la tarea"
        >
          <slot name="edicion" />
        </div>
        <div
          v-else
          data-testid="detalle-contenido"
          class="flex min-h-0 flex-col gap-4 overflow-y-auto pr-1"
          role="region"
          aria-label="Contenido del detalle"
          tabindex="0"
        >
          <div v-if="tareaMostrada" data-testid="campos-tarea" class="grid gap-4 xl:grid-cols-2">
            <section
              :class="`${CLASE_TARJETA} xl:col-span-2`"
              :aria-labelledby="idTarjeta('Descripción')"
            >
              <h3 :id="idTarjeta('Descripción')" :class="CLASE_TITULO_TARJETA">Descripción</h3>
              <p
                data-testid="descripcion-tarea"
                class="text-sm whitespace-pre-wrap [overflow-wrap:anywhere]"
                v-text="textoOVacio(tareaMostrada.descripcion)"
              />
            </section>
            <section
              v-for="tarjeta in tarjetasCampos"
              :key="tarjeta.titulo"
              :class="`${CLASE_TARJETA} ${tarjeta.clase ?? ''}`"
              :aria-labelledby="idTarjeta(tarjeta.titulo)"
            >
              <h3 :id="idTarjeta(tarjeta.titulo)" :class="CLASE_TITULO_TARJETA">
                {{ tarjeta.titulo }}
              </h3>
              <dl class="grid gap-3">
                <div
                  v-for="campo in tarjeta.campos"
                  :key="campo.termino"
                  class="grid gap-1 sm:grid-cols-[10rem_1fr]"
                >
                  <dt class="text-muted-foreground text-sm font-medium">{{ campo.termino }}</dt>
                  <dd
                    v-if="campo.relacionados && campo.relacionados.nombres.length > 0"
                    class="min-w-0 text-sm"
                  >
                    <ul class="flex flex-wrap items-center gap-2">
                      <li v-for="nombre in campo.relacionados.nombres" :key="nombre" class="flex">
                        <NombreRelacionado
                          v-if="campo.relacionados.tipo === 'persona'"
                          tipo="persona"
                          :nombre="nombre"
                          class="inline-flex items-center gap-1.5"
                          ><span aria-hidden="true" class="inline-flex"
                            ><AvatarPersona :nombre="nombre" class="size-6" /></span
                          >{{ nombre }}</NombreRelacionado
                        >
                        <NombreRelacionado
                          v-else
                          tipo="etiqueta"
                          :nombre="nombre"
                          class="rounded-full"
                          ><span
                            data-testid="etiqueta-detalle"
                            :class="`${CLASE_PILDORA} ${colorEtiqueta(nombre)}`"
                            >{{ nombre }}</span
                          ></NombreRelacionado
                        >
                      </li>
                    </ul>
                  </dd>
                  <dd
                    v-else
                    class="text-sm [overflow-wrap:anywhere]"
                    :class="campo.multilinea ? 'whitespace-pre-wrap' : ''"
                    v-text="campo.valor"
                  />
                </div>
              </dl>
            </section>
          </div>

          <section
            v-if="camposOportunidad"
            :class="CLASE_TARJETA"
            :aria-labelledby="idTarjeta('Oportunidad')"
          >
            <h3 :id="idTarjeta('Oportunidad')" :class="CLASE_TITULO_TARJETA">Oportunidad</h3>
            <dl data-testid="campos-oportunidad" class="grid gap-3">
              <div
                v-for="campo in camposOportunidad"
                :key="campo.termino"
                class="grid gap-1 sm:grid-cols-[10rem_1fr]"
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

          <div v-if="tareaMostrada" data-testid="seccion-subtareas" :class="CLASE_TARJETA">
            <SubtareasTarea :tarea="tareaMostrada" />
          </div>
        </div>

        <aside
          v-if="tareaMostrada"
          data-testid="columna-comentarios"
          aria-label="Comentarios de la tarea"
          :class="`${CLASE_TARJETA} flex min-h-0 flex-col`"
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
        <Button
          v-if="!props.editando"
          type="button"
          variant="outline"
          :aria-label="`Editar la tarea ${tareaMostrada?.nombre ?? ''}`"
          @click="emit('editar')"
        >
          <Pencil aria-hidden="true" />
          Editar
        </Button>
        <DialogClose as-child>
          <Button type="button" variant="secondary">Cerrar</Button>
        </DialogClose>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
