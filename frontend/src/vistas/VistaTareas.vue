<script setup lang="ts">
import { ChevronRight, Eye, Pencil, Search } from '@lucide/vue'
import { computed, onMounted, reactive, ref, watch } from 'vue'

import {
  TIPOS_TAREA,
  etiquetaTipoTarea,
  type DatosTarea,
  type Oportunidad,
  type Tarea,
  type TipoTarea,
} from '@/api/tipos'
import { aFechaHoraIso, formatearFechaHora } from '@/lib/fechas'
import { useTiendaTareas } from '@/stores/tareas'
import { useBusquedaTabla } from '@/composables/useBusquedaTabla'
import {
  compararConNulosAlFinal,
  compararNumero,
  compararTexto,
  useOrdenacionTabla,
  valorAriaSort,
} from '@/composables/useOrdenacionTabla'
import BotonesExportarTabla from '@/componentes/compartido/BotonesExportarTabla.vue'
import CabeceraOrdenable from '@/componentes/compartido/CabeceraOrdenable.vue'
import DetalleTarea from '@/componentes/compartido/DetalleTarea.vue'
import FiltroMultiple from '@/componentes/compartido/FiltroMultiple.vue'
import SelectorEtiquetas from '@/componentes/compartido/SelectorEtiquetas.vue'
import SelectorFechaHora from '@/componentes/compartido/SelectorFechaHora.vue'
import type { CeldaExportada } from '@/lib/exportarTabla'
import { Button } from '@/componentes/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/componentes/ui/collapsible'
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
// Tarea abierta en la modal de detalle, o `null` si está cerrada.
const tareaEnDetalle = ref<Tarea | null>(null)

const ERROR_FECHA_HORA = 'La fecha y hora debe tener el formato dd/mm/aaaa hh:mm:ss y ser válida.'
const ERROR_FECHA_VENCIMIENTO =
  'La fecha de vencimiento debe tener el formato dd/mm/aaaa hh:mm:ss y ser válida.'
const ERROR_VENCIMIENTO_ANTERIOR =
  'La fecha de vencimiento no puede ser anterior a la fecha de creación.'

// La prioridad llega como número desde un `<input type="number">`, o como
// cadena vacía cuando el campo se deja en blanco. El tipo vacío es "Sin tipo";
// los campos de la oportunidad solo se envían si el tipo es "Oportunidad".
const formulario = reactive<{
  nombre: string
  prioridad: string | number | null
  descripcion: string
  fechaCreacion: string
  fechaVencimiento: string
  etiquetas: string[]
  asignados: string[]
  tipo: TipoTarea | ''
  oportunidad: { codigo: string; descripcion: string; observaciones: string }
}>({
  nombre: '',
  prioridad: '',
  descripcion: '',
  fechaCreacion: '',
  fechaVencimiento: '',
  etiquetas: [],
  asignados: [],
  tipo: '',
  oportunidad: { codigo: '', descripcion: '', observaciones: '' },
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
  | 'tipo'

// --- Filtros (en el navegador; el orden y la exportación usan las filas filtradas) ---

// Opciones "Sin …" de los filtros múltiples: valores que nunca coinciden con
// una prioridad real (1–5) ni con un nombre de catálogo (nunca vacío).
const SIN_PRIORIDAD = 0
const SIN_NOMBRE = ''
const SIN_TIPO = ''

const ITEMS_PRIORIDAD = [
  ...[1, 2, 3, 4, 5].map((valor) => ({ id: valor, nombre: String(valor) })),
  { id: SIN_PRIORIDAD, nombre: 'Sin prioridad' },
]

const ITEMS_TIPO: { id: TipoTarea | typeof SIN_TIPO; nombre: string }[] = [
  ...TIPOS_TAREA.map((tipo) => ({ id: tipo.valor, nombre: tipo.etiqueta })),
  { id: SIN_TIPO, nombre: 'Sin tipo' },
]

/**
 * Opciones de un filtro por nombres: el catálogo más los nombres que ya usan
 * las tareas (por si el catálogo no se pudo cargar), en orden alfabético, y
 * al final la opción para las tareas sin ninguno.
 */
function itemsDeNombres(
  catalogo: string[],
  usados: string[][],
  textoSinNombre: string,
): { id: string; nombre: string }[] {
  const nombres = [...new Set([...catalogo, ...usados.flat()])].sort(compararTexto)
  return [
    ...nombres.map((nombre) => ({ id: nombre, nombre })),
    { id: SIN_NOMBRE, nombre: textoSinNombre },
  ]
}

const itemsEtiquetasFiltro = computed(() =>
  itemsDeNombres(
    tienda.etiquetas,
    tienda.tareas.map((tarea) => tarea.etiquetas),
    'Sin etiquetas',
  ),
)
const itemsAsignadosFiltro = computed(() =>
  itemsDeNombres(
    tienda.personas,
    tienda.tareas.map((tarea) => tarea.asignados),
    'Sin asignar',
  ),
)

const prioridadesFiltro = ref<number[]>(ITEMS_PRIORIDAD.map((item) => item.id))
const etiquetasFiltro = ref<string[]>(itemsEtiquetasFiltro.value.map((item) => item.id))
const asignadosFiltro = ref<string[]>(itemsAsignadosFiltro.value.map((item) => item.id))
const tiposFiltro = ref<string[]>(ITEMS_TIPO.map((item) => item.id))
// Fechas de los `<input type="date">` (`YYYY-MM-DD`), o '' sin límite.
const creacionDesde = ref('')
const creacionHasta = ref('')
const vencimientoDesde = ref('')
const vencimientoHasta = ref('')

// Un nombre que aparece en el catálogo (p. ej. creado al guardar una tarea)
// queda marcado; los que ya existían conservan lo que el usuario marcó.
function marcarNuevos(seleccion: { value: string[] }) {
  return (items: { id: string }[], itemsAnteriores: { id: string }[]) => {
    const conocidos = new Set(itemsAnteriores.map((item) => item.id))
    const nuevos = items.filter((item) => !conocidos.has(item.id)).map((item) => item.id)
    if (nuevos.length > 0) seleccion.value = [...seleccion.value, ...nuevos]
  }
}
watch(itemsEtiquetasFiltro, marcarNuevos(etiquetasFiltro))
watch(itemsAsignadosFiltro, marcarNuevos(asignadosFiltro))

/** Pasa si alguno de sus nombres está marcado o, sin ninguno, si lo está la opción "Sin …". */
function pasaFiltroNombres(nombres: string[], seleccion: string[]): boolean {
  if (nombres.length === 0) return seleccion.includes(SIN_NOMBRE)
  return nombres.some((nombre) => seleccion.includes(nombre))
}

/** Compara por día (`YYYY-MM-DD`), con ambos extremos incluidos. */
function dentroDeRango(fechaIso: string, desde: string, hasta: string): boolean {
  const dia = fechaIso.slice(0, 10)
  if (desde && dia < desde) return false
  if (hasta && dia > hasta) return false
  return true
}

const tareasConFiltros = computed(() =>
  tienda.tareas.filter((tarea) => {
    if (!prioridadesFiltro.value.includes(tarea.prioridad ?? SIN_PRIORIDAD)) return false
    if (!pasaFiltroNombres(tarea.etiquetas, etiquetasFiltro.value)) return false
    if (!pasaFiltroNombres(tarea.asignados, asignadosFiltro.value)) return false
    if (!tiposFiltro.value.includes(tarea.tipo ?? SIN_TIPO)) return false
    if (!dentroDeRango(tarea.fecha_creacion, creacionDesde.value, creacionHasta.value)) {
      return false
    }
    // Con un rango de vencimiento activo, las tareas sin vencimiento no pasan.
    if (vencimientoDesde.value || vencimientoHasta.value) {
      if (tarea.fecha_vencimiento === null) return false
      if (!dentroDeRango(tarea.fecha_vencimiento, vencimientoDesde.value, vencimientoHasta.value)) {
        return false
      }
    }
    return true
  }),
)

const { busqueda, filasFiltradas } = useBusquedaTabla(tareasConFiltros, (tarea) => [
  tarea.nombre,
  tarea.descripcion,
])

function limpiarFiltros(): void {
  busqueda.value = ''
  prioridadesFiltro.value = ITEMS_PRIORIDAD.map((item) => item.id)
  etiquetasFiltro.value = itemsEtiquetasFiltro.value.map((item) => item.id)
  asignadosFiltro.value = itemsAsignadosFiltro.value.map((item) => item.id)
  tiposFiltro.value = ITEMS_TIPO.map((item) => item.id)
  creacionDesde.value = ''
  creacionHasta.value = ''
  vencimientoDesde.value = ''
  vencimientoHasta.value = ''
}

const filtrosAbiertos = ref(true)

// Las fechas llegan en ISO (`YYYY-MM-DDTHH:MM:SS`), que ya ordena bien como texto.
// Las listas vacías y el vencimiento sin fecha quedan al final en ambos sentidos.
const { campo, direccion, ordenarPor, filasOrdenadas } = useOrdenacionTabla<Tarea, CampoOrdenable>(
  filasFiltradas,
  {
    nombre: (a, b) => compararTexto(a.nombre, b.nombre),
    prioridad: compararConNulosAlFinal((tarea) => tarea.prioridad, compararNumero),
    descripcion: (a, b) => compararTexto(a.descripcion, b.descripcion),
    etiquetas: compararConNulosAlFinal((tarea) => unirNombres(tarea.etiquetas), compararTexto),
    asignados: compararConNulosAlFinal((tarea) => unirNombres(tarea.asignados), compararTexto),
    fechaCreacion: (a, b) => compararIso(a.fecha_creacion, b.fecha_creacion),
    fechaVencimiento: compararConNulosAlFinal((tarea) => tarea.fecha_vencimiento, compararIso),
    tipo: compararConNulosAlFinal((tarea) => etiquetaTipoTarea(tarea.tipo), compararTexto),
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
  { campo: 'tipo', etiqueta: 'Tipo' },
]
// Columnas de la tabla que se muestran como chips.
const CAMPOS_LISTA = ['etiquetas', 'asignados'] as const

const COLUMNAS_EXPORTACION = COLUMNAS_ORDENABLES.map((columna) => columna.etiqueta)

// Se exportan las filas filtradas en el orden actual y con los valores tal como se ven
// (del tipo, solo su texto: los campos propios de cada tipo no salen en la tabla).
const filasExportacion = computed<CeldaExportada[][]>(() =>
  filasOrdenadas.value.map((tarea) => [
    tarea.nombre,
    tarea.prioridad ?? '—',
    tarea.descripcion,
    unirNombres(tarea.etiquetas) ?? '—',
    unirNombres(tarea.asignados) ?? '—',
    formatearFechaHora(tarea.fecha_creacion),
    tarea.fecha_vencimiento ? formatearFechaHora(tarea.fecha_vencimiento) : '—',
    etiquetaTipoTarea(tarea.tipo) ?? '—',
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
  formulario.tipo = ''
  formulario.oportunidad = { codigo: '', descripcion: '', observaciones: '' }
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
  formulario.tipo = tarea.tipo ?? ''
  if (tarea.oportunidad) {
    formulario.oportunidad = {
      codigo: tarea.oportunidad.codigo,
      descripcion: tarea.oportunidad.descripcion ?? '',
      observaciones: tarea.oportunidad.observaciones ?? '',
    }
  }
  panelAbierto.value = true
}

function aPrioridad(valor: string | number | null): number | null {
  if (valor === null || valor === '') return null
  return Number(valor)
}

/** Texto opcional del formulario: vacío (o solo espacios) se envía como `null`. */
function aTextoOpcional(valor: string): string | null {
  return valor.trim() === '' ? null : valor
}

/** Datos de la oportunidad a enviar, o `null` si el tipo elegido no es "Oportunidad". */
function datosOportunidad(): Oportunidad | null {
  if (formulario.tipo !== 'oportunidad') return null
  return {
    codigo: formulario.oportunidad.codigo,
    descripcion: aTextoOpcional(formulario.oportunidad.descripcion),
    observaciones: aTextoOpcional(formulario.oportunidad.observaciones),
  }
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
    tipo: formulario.tipo === '' ? null : formulario.tipo,
    oportunidad: datosOportunidad(),
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

    <div class="bg-muted/40 mt-4 flex flex-col gap-4 rounded-lg border p-4">
      <Collapsible v-model:open="filtrosAbiertos">
        <CollapsibleTrigger
          class="text-muted-foreground flex items-center gap-1 text-sm font-medium"
          :aria-label="filtrosAbiertos ? 'Contraer filtros' : 'Expandir filtros'"
        >
          <ChevronRight
            class="size-4 transition-transform"
            :class="filtrosAbiertos ? 'rotate-90' : ''"
          />
          Filtros
        </CollapsibleTrigger>
        <CollapsibleContent class="mt-4 flex flex-wrap items-end gap-4">
          <div class="flex max-w-xs flex-col gap-1.5">
            <Label for="filtro-buscar">Buscar</Label>
            <div class="relative">
              <Search
                class="text-muted-foreground pointer-events-none absolute top-2.5 left-2.5 size-4"
              />
              <Input
                id="filtro-buscar"
                v-model="busqueda"
                placeholder="Buscar tareas…"
                class="pl-8"
              />
            </div>
          </div>

          <div class="flex flex-col gap-1.5">
            <Label>Prioridad</Label>
            <FiltroMultiple
              v-model="prioridadesFiltro"
              :items="ITEMS_PRIORIDAD"
              id-base="filtro-prioridad"
              etiqueta-boton="Filtrar por prioridad"
              nombre-singular="prioridad"
              nombre-plural="prioridades"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <Label>Etiquetas</Label>
            <FiltroMultiple
              v-model="etiquetasFiltro"
              :items="itemsEtiquetasFiltro"
              id-base="filtro-etiquetas"
              etiqueta-boton="Filtrar por etiquetas"
              nombre-singular="etiqueta"
              nombre-plural="etiquetas"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <Label>Asignado a</Label>
            <FiltroMultiple
              v-model="asignadosFiltro"
              :items="itemsAsignadosFiltro"
              id-base="filtro-asignados"
              etiqueta-boton="Filtrar por asignado a"
              nombre-singular="persona"
              nombre-plural="personas"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <Label>Tipo</Label>
            <FiltroMultiple
              v-model="tiposFiltro"
              :items="ITEMS_TIPO"
              id-base="filtro-tipo"
              etiqueta-boton="Filtrar por tipo"
              nombre-singular="tipo"
              nombre-plural="tipos"
              genero="masculino"
            />
          </div>

          <div class="flex flex-wrap items-end gap-4">
            <div class="flex flex-col gap-1.5">
              <Label for="filtro-creacion-desde">Fecha de creación desde</Label>
              <Input id="filtro-creacion-desde" v-model="creacionDesde" type="date" />
            </div>
            <div class="flex flex-col gap-1.5">
              <Label for="filtro-creacion-hasta">Fecha de creación hasta</Label>
              <Input id="filtro-creacion-hasta" v-model="creacionHasta" type="date" />
            </div>
          </div>

          <div class="flex flex-wrap items-end gap-4">
            <div class="flex flex-col gap-1.5">
              <Label for="filtro-vencimiento-desde">Fecha de vencimiento desde</Label>
              <Input id="filtro-vencimiento-desde" v-model="vencimientoDesde" type="date" />
            </div>
            <div class="flex flex-col gap-1.5">
              <Label for="filtro-vencimiento-hasta">Fecha de vencimiento hasta</Label>
              <Input id="filtro-vencimiento-hasta" v-model="vencimientoHasta" type="date" />
            </div>
          </div>

          <Button type="button" variant="secondary" @click="limpiarFiltros">Limpiar filtros</Button>
        </CollapsibleContent>
      </Collapsible>
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
          <div class="flex flex-col gap-1.5">
            <Label for="tarea-tipo">Tipo de tarea</Label>
            <select
              id="tarea-tipo"
              v-model="formulario.tipo"
              class="border-input dark:bg-input/30 bg-background focus-visible:border-ring focus-visible:ring-ring/50 h-9 w-full rounded-md border px-3 py-1 text-base shadow-xs outline-none focus-visible:ring-[3px] md:text-sm"
            >
              <option value="">Sin tipo</option>
              <option v-for="tipo in TIPOS_TAREA" :key="tipo.valor" :value="tipo.valor">
                {{ tipo.etiqueta }}
              </option>
            </select>
          </div>
          <fieldset
            v-if="formulario.tipo === 'oportunidad'"
            class="flex flex-col gap-3 rounded-md border p-3"
          >
            <legend class="px-1 text-sm font-medium">Oportunidad</legend>
            <div class="flex flex-col gap-1.5">
              <Label for="oportunidad-codigo">Código de la oportunidad</Label>
              <Input
                id="oportunidad-codigo"
                v-model="formulario.oportunidad.codigo"
                required
                maxlength="10"
              />
            </div>
            <div class="flex flex-col gap-1.5">
              <Label for="oportunidad-descripcion">Descripción de la oportunidad</Label>
              <Input
                id="oportunidad-descripcion"
                v-model="formulario.oportunidad.descripcion"
                maxlength="200"
              />
            </div>
            <div class="flex flex-col gap-1.5">
              <Label for="oportunidad-observaciones">Observaciones</Label>
              <Textarea
                id="oportunidad-observaciones"
                v-model="formulario.oportunidad.observaciones"
                maxlength="5000"
              />
            </div>
          </fieldset>

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
    <p
      v-else-if="tienda.tareas.length > 0 && filasFiltradas.length === 0"
      class="text-muted-foreground mt-4 text-sm"
    >
      Ninguna tarea coincide con los filtros.
    </p>
    <div v-if="filasFiltradas.length > 0" class="mt-4 flex justify-end">
      <BotonesExportarTabla
        nombre-fichero="Tareas"
        titulo="Tareas"
        :columnas="COLUMNAS_EXPORTACION"
        :filas="filasExportacion"
      />
    </div>
    <Table v-if="filasFiltradas.length > 0" class="mt-2">
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
          <TableCell>{{ etiquetaTipoTarea(tarea.tipo) ?? '—' }}</TableCell>
          <TableCell>
            <div class="flex gap-1">
              <Button
                variant="outline"
                size="icon"
                :aria-label="`Editar tarea ${tarea.nombre}`"
                title="Editar"
                @click="abrirParaEditar(tarea)"
              >
                <Pencil />
              </Button>
              <Button
                variant="outline"
                size="icon"
                :aria-label="`Ver detalle de la tarea ${tarea.nombre}`"
                title="Detalle"
                @click="tareaEnDetalle = tarea"
              >
                <Eye />
              </Button>
            </div>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>

    <DetalleTarea :tarea="tareaEnDetalle" @cerrar="tareaEnDetalle = null" />
  </section>
</template>
