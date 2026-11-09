<script setup lang="ts">
import { computed, onMounted, reactive, ref, toRef } from 'vue'

import type { DatosTarea, Tarea } from '@/api/tipos'
import { aFechaHoraIso, formatearFechaHora } from '@/lib/fechas'
import { useTiendaTareas } from '@/stores/tareas'
import {
  compararConNulosAlFinal,
  compararNumero,
  compararTexto,
  useOrdenacionTabla,
  valorAriaSort,
} from '@/composables/useOrdenacionTabla'
import BotonesExportarTabla from '@/componentes/compartido/BotonesExportarTabla.vue'
import CabeceraOrdenable from '@/componentes/compartido/CabeceraOrdenable.vue'
import SelectorEtiquetas from '@/componentes/compartido/SelectorEtiquetas.vue'
import SelectorFechaHora from '@/componentes/compartido/SelectorFechaHora.vue'
import type { CeldaExportada } from '@/lib/exportarTabla'
import { Button } from '@/componentes/ui/button'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/componentes/ui/sheet'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/componentes/ui/table'
import { Textarea } from '@/componentes/ui/textarea'

const tienda = useTiendaTareas()
const panelAbierto = ref(false)
const errorFormulario = ref<string | null>(null)
// `null` en modo crear; el id de la tarea en modo editar.
const idEnEdicion = ref<number | null>(null)

const ERROR_FECHA_HORA = 'La fecha y hora debe tener el formato dd/mm/aaaa hh:mm:ss y ser válida.'
const ERROR_FECHA_VENCIMIENTO =
  'La fecha de vencimiento debe tener el formato dd/mm/aaaa hh:mm:ss y ser válida.'
const ERROR_VENCIMIENTO_ANTERIOR =
  'La fecha de vencimiento no puede ser anterior a la fecha de creación.'

// La prioridad llega como número desde un `<input type="number">`, o como
// cadena vacía cuando el campo se deja en blanco.
const formulario = reactive<{
  nombre: string
  prioridad: string | number | null
  descripcion: string
  fechaCreacion: string
  fechaVencimiento: string
  etiquetas: string[]
  asignados: string[]
}>({
  nombre: '',
  prioridad: '',
  descripcion: '',
  fechaCreacion: '',
  fechaVencimiento: '',
  etiquetas: [],
  asignados: [],
})

onMounted(() => {
  void tienda.cargar()
  void tienda.cargarCatalogos()
})

/** Nombres en orden alfabético unidos por ", ", o `null` si no hay ninguno. */
function unirNombres(nombres: string[]): string | null {
  if (nombres.length === 0) return null
  return [...nombres].sort(compararTexto).join(', ')
}

function compararIso(a: string, b: string): number {
  return a.localeCompare(b)
}

type CampoOrdenable =
  | 'nombre'
  | 'prioridad'
  | 'descripcion'
  | 'etiquetas'
  | 'asignados'
  | 'fechaCreacion'
  | 'fechaVencimiento'

// Las fechas llegan en ISO (`YYYY-MM-DDTHH:MM:SS`), que ya ordena bien como texto.
// Las listas vacías y el vencimiento sin fecha quedan al final en ambos sentidos.
const { campo, direccion, ordenarPor, filasOrdenadas } = useOrdenacionTabla<Tarea, CampoOrdenable>(
  toRef(tienda, 'tareas'),
  {
    nombre: (a, b) => compararTexto(a.nombre, b.nombre),
    prioridad: compararConNulosAlFinal((tarea) => tarea.prioridad, compararNumero),
    descripcion: (a, b) => compararTexto(a.descripcion, b.descripcion),
    etiquetas: compararConNulosAlFinal((tarea) => unirNombres(tarea.etiquetas), compararTexto),
    asignados: compararConNulosAlFinal((tarea) => unirNombres(tarea.asignados), compararTexto),
    fechaCreacion: (a, b) => compararIso(a.fecha_creacion, b.fecha_creacion),
    fechaVencimiento: compararConNulosAlFinal((tarea) => tarea.fecha_vencimiento, compararIso),
  },
)

const COLUMNAS_ORDENABLES: { campo: CampoOrdenable; etiqueta: string }[] = [
  { campo: 'nombre', etiqueta: 'Nombre' },
  { campo: 'prioridad', etiqueta: 'Prioridad' },
  { campo: 'descripcion', etiqueta: 'Descripción' },
  { campo: 'etiquetas', etiqueta: 'Etiquetas' },
  { campo: 'asignados', etiqueta: 'Asignado a' },
  { campo: 'fechaCreacion', etiqueta: 'Fecha de creación' },
  { campo: 'fechaVencimiento', etiqueta: 'Fecha de vencimiento' },
]
// Columnas de la tabla que se muestran como chips.
const CAMPOS_LISTA = ['etiquetas', 'asignados'] as const

const COLUMNAS_EXPORTACION = COLUMNAS_ORDENABLES.map((columna) => columna.etiqueta)

// Se exportan todas las filas en el orden actual y con los valores tal como se ven.
const filasExportacion = computed<CeldaExportada[][]>(() =>
  filasOrdenadas.value.map((tarea) => [
    tarea.nombre,
    tarea.prioridad ?? '—',
    tarea.descripcion,
    unirNombres(tarea.etiquetas) ?? '—',
    unirNombres(tarea.asignados) ?? '—',
    formatearFechaHora(tarea.fecha_creacion),
    tarea.fecha_vencimiento ? formatearFechaHora(tarea.fecha_vencimiento) : '—',
  ]),
)

function limpiarFormulario(): void {
  formulario.nombre = ''
  formulario.prioridad = ''
  formulario.descripcion = ''
  formulario.fechaCreacion = ''
  formulario.fechaVencimiento = ''
  formulario.etiquetas = []
  formulario.asignados = []
  errorFormulario.value = null
  idEnEdicion.value = null
}

function abrirParaCrear(): void {
  limpiarFormulario()
  formulario.fechaCreacion = formatearFechaHora(new Date())
  panelAbierto.value = true
}

function abrirParaEditar(tarea: Tarea): void {
  limpiarFormulario()
  idEnEdicion.value = tarea.id
  formulario.nombre = tarea.nombre
  formulario.prioridad = tarea.prioridad ?? ''
  formulario.descripcion = tarea.descripcion
  formulario.fechaCreacion = formatearFechaHora(tarea.fecha_creacion)
  formulario.fechaVencimiento = tarea.fecha_vencimiento
    ? formatearFechaHora(tarea.fecha_vencimiento)
    : ''
  // Copias, para que editar los chips no altere la tarea mostrada en la tabla.
  formulario.etiquetas = [...tarea.etiquetas]
  formulario.asignados = [...tarea.asignados]
  panelAbierto.value = true
}

function aPrioridad(valor: string | number | null): number | null {
  if (valor === null || valor === '') return null
  return Number(valor)
}

/**
 * Comprueba las fechas del formulario y las devuelve en ISO, o devuelve el
 * mensaje de error que hay que mostrar.
 */
function validarFechas(): { creacion: string; vencimiento: string | null } | { error: string } {
  const creacion = aFechaHoraIso(formulario.fechaCreacion)
  if (creacion === null) return { error: ERROR_FECHA_HORA }
  if (formulario.fechaVencimiento.trim() === '') return { creacion, vencimiento: null }
  const vencimiento = aFechaHoraIso(formulario.fechaVencimiento)
  if (vencimiento === null) return { error: ERROR_FECHA_VENCIMIENTO }
  // Ambas en ISO con la misma forma: comparar el texto es comparar las fechas.
  if (vencimiento < creacion) return { error: ERROR_VENCIMIENTO_ANTERIOR }
  return { creacion, vencimiento }
}

async function guardar(): Promise<void> {
  errorFormulario.value = null
  const fechas = validarFechas()
  if ('error' in fechas) {
    errorFormulario.value = fechas.error
    return
  }
  const datos: DatosTarea = {
    nombre: formulario.nombre,
    prioridad: aPrioridad(formulario.prioridad),
    descripcion: formulario.descripcion,
    fecha_creacion: fechas.creacion,
    fecha_vencimiento: fechas.vencimiento,
    etiquetas: [...formulario.etiquetas],
    asignados: [...formulario.asignados],
  }
  try {
    if (idEnEdicion.value === null) {
      await tienda.crear(datos)
    } else {
      await tienda.actualizar(idEnEdicion.value, datos)
    }
    panelAbierto.value = false
    limpiarFormulario()
  } catch (motivo) {
    errorFormulario.value = (motivo as Error).message
  }
}
</script>

<template>
  <section>
    <div class="flex items-center justify-between">
      <h2 class="text-xl font-semibold">Tareas</h2>
      <Button variant="success" @click="abrirParaCrear">Crear tarea</Button>
    </div>

    <Sheet v-model:open="panelAbierto">
      <SheetContent>
        <SheetHeader>
          <SheetTitle>{{ idEnEdicion === null ? 'Crear tarea' : 'Editar tarea' }}</SheetTitle>
        </SheetHeader>

        <form class="flex flex-col gap-3 px-4" @submit.prevent="guardar">
          <div class="flex flex-col gap-1.5">
            <Label for="tarea-nombre">Nombre</Label>
            <Input
              id="tarea-nombre"
              v-model="formulario.nombre"
              placeholder="Nombre"
              required
              maxlength="200"
            />
          </div>
          <div class="flex flex-col gap-1.5">
            <Label for="tarea-prioridad">Prioridad</Label>
            <Input
              id="tarea-prioridad"
              v-model="formulario.prioridad"
              type="number"
              min="1"
              max="5"
              placeholder="Prioridad"
            />
          </div>
          <div class="flex flex-col gap-1.5">
            <Label for="tarea-descripcion">Descripción</Label>
            <Textarea
              id="tarea-descripcion"
              v-model="formulario.descripcion"
              placeholder="Descripción"
              required
              maxlength="500"
            />
          </div>
          <SelectorEtiquetas
            id="etiquetas"
            v-model="formulario.etiquetas"
            etiqueta="Etiquetas"
            :longitud-maxima="50"
            texto-nuevo='Crear etiqueta "{valor}"'
            :sugerencias="tienda.etiquetas"
          />
          <SelectorEtiquetas
            id="asignados"
            v-model="formulario.asignados"
            etiqueta="Asignado a"
            :longitud-maxima="100"
            texto-nuevo='Añadir persona "{valor}"'
            :sugerencias="tienda.personas"
          />
          <div class="flex flex-col gap-1.5">
            <Label for="fecha-creacion">Fecha de creación</Label>
            <SelectorFechaHora
              id="fecha-creacion"
              v-model="formulario.fechaCreacion"
              etiqueta="Fecha de creación"
              required
            />
          </div>
          <div class="flex flex-col gap-1.5">
            <Label for="fecha-vencimiento">Fecha de vencimiento</Label>
            <SelectorFechaHora
              id="fecha-vencimiento"
              v-model="formulario.fechaVencimiento"
              etiqueta="Fecha de vencimiento"
              anulable
            />
          </div>

          <p v-if="errorFormulario" class="text-sm text-destructive" role="alert">
            {{ errorFormulario }}
          </p>

          <div class="flex gap-2">
            <Button type="submit" variant="success">Guardar</Button>
            <Button type="button" variant="destructive" @click="panelAbierto = false"
              >Cancelar</Button
            >
          </div>
        </form>
      </SheetContent>
    </Sheet>

    <p v-if="tienda.error" class="mt-2 text-sm text-destructive" role="alert">{{ tienda.error }}</p>

    <p
      v-if="!tienda.cargando && tienda.tareas.length === 0"
      class="text-muted-foreground mt-4 text-sm"
    >
      Todavía no hay tareas.
    </p>
    <div v-if="tienda.tareas.length > 0" class="mt-4 flex justify-end">
      <BotonesExportarTabla
        nombre-fichero="Tareas"
        titulo="Tareas"
        :columnas="COLUMNAS_EXPORTACION"
        :filas="filasExportacion"
      />
    </div>
    <Table v-if="tienda.tareas.length > 0" class="mt-2">
      <TableHeader>
        <TableRow>
          <TableHead
            v-for="columna in COLUMNAS_ORDENABLES"
            :key="columna.campo"
            :aria-sort="valorAriaSort(campo === columna.campo, direccion)"
          >
            <CabeceraOrdenable
              :activo="campo === columna.campo"
              :direccion="direccion"
              @ordenar="ordenarPor(columna.campo)"
              >{{ columna.etiqueta }}</CabeceraOrdenable
            >
          </TableHead>
          <TableHead><span class="sr-only">Acciones</span></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow v-for="tarea in filasOrdenadas" :key="tarea.id">
          <TableCell class="whitespace-normal [overflow-wrap:anywhere]">{{
            tarea.nombre
          }}</TableCell>
          <TableCell>{{ tarea.prioridad ?? '—' }}</TableCell>
          <TableCell class="whitespace-normal [overflow-wrap:anywhere]">{{
            tarea.descripcion
          }}</TableCell>
          <TableCell
            v-for="campoLista in CAMPOS_LISTA"
            :key="campoLista"
            class="whitespace-normal [overflow-wrap:anywhere]"
          >
            <ul v-if="tarea[campoLista].length > 0" class="flex flex-wrap gap-1">
              <li
                v-for="nombre in tarea[campoLista]"
                :key="nombre"
                data-testid="chip-tabla"
                class="bg-secondary text-secondary-foreground inline-flex max-w-full rounded-md border px-2 py-0.5 text-xs font-medium"
              >
                {{ nombre }}
              </li>
            </ul>
            <template v-else>—</template>
          </TableCell>
          <TableCell class="whitespace-normal [overflow-wrap:anywhere]">{{
            formatearFechaHora(tarea.fecha_creacion)
          }}</TableCell>
          <TableCell class="whitespace-normal [overflow-wrap:anywhere]">{{
            tarea.fecha_vencimiento ? formatearFechaHora(tarea.fecha_vencimiento) : '—'
          }}</TableCell>
          <TableCell>
            <Button
              variant="outline"
              size="sm"
              :aria-label="`Editar tarea ${tarea.nombre}`"
              @click="abrirParaEditar(tarea)"
              >Editar</Button
            >
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  </section>
</template>
