<script setup lang="ts">
import {
  CalendarDays,
  ChevronRight,
  Circle,
  CircleCheck,
  Columns3,
  Eye,
  Kanban,
  List,
  Pencil,
  Search,
  Trash,
} from '@lucide/vue'
import { computed, nextTick, onMounted, reactive, ref, watch, type Component } from 'vue'

import {
  TIPOS_TAREA,
  etiquetaTipoTarea,
  type DatosTarea,
  type Oportunidad,
  type Tarea,
  type TipoTarea,
} from '@/api/tipos'
import { aFechaHoraIso, formatearFechaHora } from '@/lib/fechas'
import type { ValoresFormularioTarea } from '@/lib/formularioTarea'
import { useTiendaGruposEstados } from '@/stores/gruposEstados'
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
import ContadorVencimiento from '@/componentes/compartido/ContadorVencimiento.vue'
import DetalleTarea from '@/componentes/compartido/DetalleTarea.vue'
import DialogoConfirmacion from '@/componentes/compartido/DialogoConfirmacion.vue'
import FiltroMultiple from '@/componentes/compartido/FiltroMultiple.vue'
import FormularioTarea from '@/componentes/compartido/FormularioTarea.vue'
import CalendarioTareas from '@/componentes/compartido/CalendarioTareas.vue'
import TableroTareas from '@/componentes/compartido/TableroTareas.vue'
import type { CeldaExportada } from '@/lib/exportarTabla'
import { Button } from '@/componentes/ui/button'
import { Checkbox } from '@/componentes/ui/checkbox'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/componentes/ui/collapsible'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/componentes/ui/dialog'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'
import { Popover, PopoverContent, PopoverTrigger } from '@/componentes/ui/popover'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/componentes/ui/sheet'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/componentes/ui/table'

const tienda = useTiendaTareas()
const tiendaGrupos = useTiendaGruposEstados()
// El alta se hace en una ventana modal y la edición en el panel lateral; las
// dos comparten el formulario y su estado.
const modalAltaAbierta = ref(false)
const panelEdicionAbierto = ref(false)
const errorFormulario = ref<string | null>(null)
// `null` en modo crear; el id de la tarea en modo editar.
const idEnEdicion = ref<number | null>(null)
// Id de la tarea abierta en la modal de detalle, o `null` si está cerrada. Se
// lee de la tienda para que la modal refleje los cambios (p. ej. una subtarea resuelta).
const idEnDetalle = ref<number | null>(null)
const tareaEnDetalle = computed<Tarea | null>(
  () => tienda.tareas.find((tarea) => tarea.id === idEnDetalle.value) ?? null,
)

// Texto del tipo en la tabla; en una oportunidad con subtareas (sus pasos del
// workflow se crean como subtareas), con su avance: resueltas / total
// ("Oportunidad · 3/7"). Ordenar, filtrar y exportar usan solo el tipo.
function textoTipoEnTabla(tarea: Tarea): string {
  const etiqueta = etiquetaTipoTarea(tarea.tipo)
  if (etiqueta === null) return '—'
  if (tarea.tipo !== 'oportunidad' || tarea.subtareas.length === 0) return etiqueta
  const resueltas = tarea.subtareas.filter((subtarea) => subtarea.resuelta).length
  return `${etiqueta} · ${resueltas}/${tarea.subtareas.length}`
}

// --- Eliminar tarea, con confirmación --------------------------------------
// Se pide desde la papelera de la fila o desde el detalle. Al confirmar se
// borra (con sus subtareas y comentarios) y se cierra el detalle si estaba
// abierto. Como el botón que abrió la confirmación desaparece, el foco pasa a
// la papelera de la fila siguiente (o la anterior) o, si no quedan filas, al
// título de la lista; nunca al <body>.
const ID_TITULO_LISTA = 'titulo-lista-tareas'
const tareaAEliminar = ref<Tarea | null>(null)
const eliminando = ref(false)
const errorEliminar = ref<string | null>(null)
let destinoFocoTrasEliminar: string | null = null

function idBotonEliminar(id: number): string {
  return `eliminar-tarea-${id}`
}

function pedirEliminar(tarea: Tarea): void {
  errorEliminar.value = null
  tareaAEliminar.value = tarea
}

function alCambiarConfirmacion(abierta: boolean): void {
  if (!abierta && !eliminando.value) tareaAEliminar.value = null
}

function destinoFocoTras(id: number): string {
  // En el tablero y el calendario no hay papeleras por fila.
  if (vista.value !== 'lista') return ID_TITULO_LISTA
  const filas = filasOrdenadas.value
  const indice = filas.findIndex((tarea) => tarea.id === id)
  const vecina = filas[indice + 1] ?? filas[indice - 1]
  return vecina && indice !== -1 ? idBotonEliminar(vecina.id) : ID_TITULO_LISTA
}

async function confirmarEliminar(): Promise<void> {
  const tarea = tareaAEliminar.value
  if (tarea === null || eliminando.value) return
  // Se calcula antes de borrar, con la fila aún en la lista.
  const destino = destinoFocoTras(tarea.id)
  eliminando.value = true
  errorEliminar.value = null
  try {
    if (!(await tienda.eliminarTarea(tarea.id))) {
      errorEliminar.value = tienda.error
      return
    }
  } finally {
    eliminando.value = false
  }
  destinoFocoTrasEliminar = destino
  if (idEnDetalle.value === tarea.id) idEnDetalle.value = null
  tareaAEliminar.value = null
  // Por si la confirmación ya no devuelve el foco (p. ej. sin animación).
  await nextTick()
  enfocarTrasEliminar()
}

function enfocarTrasEliminar(): void {
  if (destinoFocoTrasEliminar === null) return
  document.getElementById(destinoFocoTrasEliminar)?.focus()
}

// Al cerrar la confirmación tras borrar, el foco no vuelve al botón que la
// abrió (ya no existe) sino al destino calculado.
function alDevolverFocoConfirmacion(evento: Event): void {
  if (destinoFocoTrasEliminar === null) return
  evento.preventDefault()
  enfocarTrasEliminar()
  destinoFocoTrasEliminar = null
}

const ERROR_FECHA_HORA = 'La fecha y hora debe tener el formato dd/mm/aaaa hh:mm:ss y ser válida.'
const ERROR_FECHA_VENCIMIENTO =
  'La fecha de vencimiento debe tener el formato dd/mm/aaaa hh:mm:ss y ser válida.'
const ERROR_VENCIMIENTO_ANTERIOR =
  'La fecha de vencimiento no puede ser anterior a la fecha de creación.'

// La prioridad llega como número desde un `<input type="number">`, o como
// cadena vacía cuando el campo se deja en blanco. El tipo vacío es "Sin tipo";
// los campos de la oportunidad solo se envían si el tipo es "Oportunidad".
const formulario = reactive<ValoresFormularioTarea>({
  nombre: '',
  prioridad: '',
  descripcion: '',
  fechaCreacion: '',
  fechaVencimiento: '',
  etiquetas: [],
  asignados: [],
  tipo: '',
  oportunidad: { codigo: '', descripcion: '', observaciones: '' },
  grupoEstadosId: '',
})

onMounted(() => {
  void tienda.cargar()
  void tienda.cargarCatalogos()
  void tiendaGrupos.cargar()
})

// --- Lista / Tablero ---
// Preferencias de este navegador, como las columnas: si no se pueden leer o
// guardar se usa la lista y el primer grupo.
type Vista = 'lista' | 'tablero' | 'calendario'
const CLAVE_VISTA = 'gestor-tareas:vista-tareas'
const CLAVE_GRUPO_TABLERO = 'gestor-tareas:grupo-tablero'

function leerPreferencia(clave: string): string | null {
  try {
    return localStorage.getItem(clave)
  } catch {
    return null
  }
}

function guardarPreferencia(clave: string, valor: string): void {
  try {
    localStorage.setItem(clave, valor)
  } catch {
    // Sin almacenamiento (p. ej. navegación privada) la preferencia dura la sesión.
  }
}

const OPCIONES_VISTA: { valor: Vista; etiqueta: string; icono: Component }[] = [
  { valor: 'lista', etiqueta: 'Ver como lista', icono: List },
  { valor: 'tablero', etiqueta: 'Ver como tablero', icono: Kanban },
  { valor: 'calendario', etiqueta: 'Ver como calendario', icono: CalendarDays },
]

// Un valor guardado desconocido muestra la lista.
function leerVista(): Vista {
  const guardada = leerPreferencia(CLAVE_VISTA)
  return OPCIONES_VISTA.find((opcion) => opcion.valor === guardada)?.valor ?? 'lista'
}

const vista = ref<Vista>(leerVista())
watch(vista, (valor) => guardarPreferencia(CLAVE_VISTA, valor))

function leerGrupoTablero(): number | null {
  const id = Number(leerPreferencia(CLAVE_GRUPO_TABLERO))
  return Number.isInteger(id) && id > 0 ? id : null
}
const idGrupoTablero = ref<number | null>(leerGrupoTablero())
watch(idGrupoTablero, (id) => {
  if (id !== null) guardarPreferencia(CLAVE_GRUPO_TABLERO, String(id))
})

// "Añadir tarea" en una columna del tablero: el alta se abre con su grupo y,
// como la tarea empieza en el primer estado, al crearla se coloca en el de la
// columna si es otro (y si no se cambió el grupo en el formulario).
let destinoAlta: { idGrupo: number; idEstado: number } | null = null

function abrirAltaEnEstado(idGrupo: number, idEstado: number): void {
  abrirParaCrear()
  formulario.grupoEstadosId = idGrupo
  const primero = tiendaGrupos.grupos.find((grupo) => grupo.id === idGrupo)?.estados[0]
  destinoAlta = primero?.id === idEstado ? null : { idGrupo, idEstado }
}

// Clases de las celdas de datos: las tareas completadas se muestran tachadas.
// Se devuelve una cadena porque `TableCell` declara `class` como `string`.
const TEXTO_AJUSTABLE = 'whitespace-normal [overflow-wrap:anywhere]'
function claseCelda(tarea: Tarea, base = ''): string {
  return tarea.completada ? `${base} line-through`.trim() : base
}

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

// Estado de las tareas que se muestran: todas, solo las completadas o solo las
// pendientes.
type EstadoFiltro = 'todas' | 'completadas' | 'pendientes'
const OPCIONES_ESTADO: { valor: EstadoFiltro; etiqueta: string }[] = [
  { valor: 'todas', etiqueta: 'Todas' },
  { valor: 'completadas', etiqueta: 'Completadas' },
  { valor: 'pendientes', etiqueta: 'No completadas' },
]
const estadoFiltro = ref<EstadoFiltro>('todas')
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
    if (estadoFiltro.value === 'completadas' && !tarea.completada) return false
    if (estadoFiltro.value === 'pendientes' && tarea.completada) return false
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
  estadoFiltro.value = 'todas'
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

// --- Columnas visibles ---
// Se guardan las columnas ocultas (no las visibles) para que una columna nueva
// aparezca sin tocar la preferencia. "Nombre" identifica la fila y no se oculta.
// Es una preferencia de este navegador: si no se puede leer o guardar, se
// muestran todas.
const CLAVE_COLUMNAS_OCULTAS = 'gestor-tareas:columnas-ocultas-tareas'
const COLUMNA_FIJA: CampoOrdenable = 'nombre'
const CAMPOS_COLUMNA = new Set<string>(COLUMNAS_ORDENABLES.map((columna) => columna.campo))

function leerColumnasOcultas(): CampoOrdenable[] {
  try {
    const guardado: unknown = JSON.parse(localStorage.getItem(CLAVE_COLUMNAS_OCULTAS) ?? '[]')
    if (!Array.isArray(guardado)) return []
    return guardado.filter(
      (campo): campo is CampoOrdenable =>
        typeof campo === 'string' && CAMPOS_COLUMNA.has(campo) && campo !== COLUMNA_FIJA,
    )
  } catch {
    return []
  }
}

const columnasOcultas = ref<CampoOrdenable[]>(leerColumnasOcultas())
watch(columnasOcultas, (ocultas) => {
  try {
    localStorage.setItem(CLAVE_COLUMNAS_OCULTAS, JSON.stringify(ocultas))
  } catch {
    // Sin almacenamiento (p. ej. navegación privada) la preferencia dura la sesión.
  }
})

function esVisible(campo: CampoOrdenable): boolean {
  return !columnasOcultas.value.includes(campo)
}

function cambiarVisibilidad(campo: CampoOrdenable, visible: boolean): void {
  if (campo === COLUMNA_FIJA) return
  const resto = columnasOcultas.value.filter((oculto) => oculto !== campo)
  // Mismo orden que la tabla, para que lo guardado no dependa del orden de los clics.
  const ocultas = visible ? resto : [...resto, campo]
  columnasOcultas.value = COLUMNAS_ORDENABLES.map((columna) => columna.campo).filter((c) =>
    ocultas.includes(c),
  )
}

function mostrarTodasLasColumnas(): void {
  columnasOcultas.value = []
}

const columnasVisibles = computed(() =>
  COLUMNAS_ORDENABLES.filter((columna) => esVisible(columna.campo)),
)
const camposListaVisibles = computed(() => CAMPOS_LISTA.filter((campo) => esVisible(campo)))

const COLUMNAS_EXPORTACION = computed(() => columnasVisibles.value.map((c) => c.etiqueta))

// Se exportan las filas filtradas en el orden actual, con las columnas visibles y
// los valores tal como se ven (del tipo, solo su texto: los campos propios de cada
// tipo no salen en la tabla).
const filasExportacion = computed<CeldaExportada[][]>(() =>
  filasOrdenadas.value.map((tarea) => {
    const celdas: Record<CampoOrdenable, CeldaExportada> = {
      nombre: tarea.nombre,
      prioridad: tarea.prioridad ?? '—',
      descripcion: tarea.descripcion,
      etiquetas: unirNombres(tarea.etiquetas) ?? '—',
      asignados: unirNombres(tarea.asignados) ?? '—',
      fechaCreacion: formatearFechaHora(tarea.fecha_creacion),
      fechaVencimiento: tarea.fecha_vencimiento ? formatearFechaHora(tarea.fecha_vencimiento) : '—',
      tipo: etiquetaTipoTarea(tarea.tipo) ?? '—',
    }
    return columnasVisibles.value.map((columna) => celdas[columna.campo])
  }),
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
  formulario.grupoEstadosId = ''
  errorFormulario.value = null
  idEnEdicion.value = null
  destinoAlta = null
}

function abrirParaCrear(): void {
  limpiarFormulario()
  formulario.fechaCreacion = formatearFechaHora(new Date())
  modalAltaAbierta.value = true
}

function cerrarFormulario(): void {
  modalAltaAbierta.value = false
  panelEdicionAbierto.value = false
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
  formulario.grupoEstadosId = tarea.grupo_estados?.id ?? ''
  if (tarea.oportunidad) {
    formulario.oportunidad = {
      codigo: tarea.oportunidad.codigo,
      descripcion: tarea.oportunidad.descripcion ?? '',
      observaciones: tarea.oportunidad.observaciones ?? '',
    }
  }
  panelEdicionAbierto.value = true
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
    grupo_estados_id: formulario.grupoEstadosId === '' ? null : formulario.grupoEstadosId,
  }
  const destino = destinoAlta
  try {
    if (idEnEdicion.value === null) {
      const creada = await tienda.crear(datos)
      // Si falla, la tarea ya está creada en el primer estado y el error se
      // muestra en la alerta de la página.
      if (
        destino &&
        datos.grupo_estados_id === destino.idGrupo &&
        creada.estado?.id !== destino.idEstado
      ) {
        await tienda.cambiarEstadoTarea(creada.id, destino.idEstado)
      }
    } else {
      await tienda.actualizar(idEnEdicion.value, datos)
    }
    cerrarFormulario()
    limpiarFormulario()
  } catch (motivo) {
    errorFormulario.value = (motivo as Error).message
  }
}
</script>

<template>
  <section>
    <div class="flex items-center justify-between">
      <h2 :id="ID_TITULO_LISTA" class="text-xl font-semibold" tabindex="-1">Tareas</h2>
      <div class="flex items-center gap-2">
        <div role="group" aria-label="Vista de las tareas" class="flex gap-1">
          <Button
            v-for="opcion in OPCIONES_VISTA"
            :key="opcion.valor"
            type="button"
            size="icon"
            :variant="vista === opcion.valor ? 'default' : 'outline'"
            :aria-label="opcion.etiqueta"
            :title="opcion.etiqueta"
            :aria-pressed="vista === opcion.valor"
            @click="vista = opcion.valor"
          >
            <component :is="opcion.icono" aria-hidden="true" />
          </Button>
        </div>
        <Button variant="success" @click="abrirParaCrear">Crear tarea</Button>
      </div>
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

          <div class="flex flex-col gap-1.5">
            <span id="filtro-estado-titulo" class="text-sm leading-none font-medium select-none"
              >Estado</span
            >
            <div
              role="radiogroup"
              aria-labelledby="filtro-estado-titulo"
              class="flex flex-wrap items-center gap-4"
            >
              <div
                v-for="opcion in OPCIONES_ESTADO"
                :key="opcion.valor"
                class="flex items-center gap-2"
              >
                <input
                  :id="`filtro-estado-${opcion.valor}`"
                  v-model="estadoFiltro"
                  type="radio"
                  name="filtro-estado"
                  :value="opcion.valor"
                  class="accent-primary size-4"
                />
                <Label :for="`filtro-estado-${opcion.valor}`" class="font-normal">{{
                  opcion.etiqueta
                }}</Label>
              </div>
            </div>
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

    <!-- Alta en una ventana modal centrada, como el detalle; la edición sigue
         en el panel lateral. Ambas usan el mismo formulario. -->
    <Dialog v-model:open="modalAltaAbierta">
      <DialogContent
        sin-aspa
        class="flex max-h-[90vh] w-[90vw] max-w-3xl flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl"
      >
        <DialogHeader class="p-4">
          <DialogTitle>Crear tarea</DialogTitle>
          <DialogDescription class="sr-only">Datos de la nueva tarea.</DialogDescription>
        </DialogHeader>
        <FormularioTarea
          v-model:valores="formulario"
          :error="errorFormulario"
          @guardar="guardar"
          @cancelar="cerrarFormulario"
        />
      </DialogContent>
    </Dialog>

    <Sheet v-model:open="panelEdicionAbierto">
      <SheetContent class="gap-0 overflow-hidden">
        <SheetHeader>
          <SheetTitle>Editar tarea</SheetTitle>
        </SheetHeader>
        <FormularioTarea
          v-model:valores="formulario"
          :error="errorFormulario"
          @guardar="guardar"
          @cancelar="cerrarFormulario"
        />
      </SheetContent>
    </Sheet>

    <p v-if="tienda.error" class="mt-2 text-sm text-destructive" role="alert">{{ tienda.error }}</p>

    <TableroTareas
      v-if="vista === 'tablero'"
      v-model:id-grupo="idGrupoTablero"
      :tareas="filasOrdenadas"
      :grupos="tiendaGrupos.grupos"
      :cargando-grupos="tiendaGrupos.cargando"
      @ver-detalle="(id) => (idEnDetalle = id)"
      @anadir-tarea="abrirAltaEnEstado"
    />

    <CalendarioTareas
      v-else-if="vista === 'calendario'"
      :tareas="filasOrdenadas"
      @ver-detalle="(id) => (idEnDetalle = id)"
    />

    <template v-else>
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
      <div v-if="filasFiltradas.length > 0" class="mt-4 flex flex-wrap justify-end gap-2">
        <Popover>
          <PopoverTrigger as-child>
            <Button
              variant="outline"
              type="button"
              aria-label="Elegir columnas visibles"
              title="Columnas"
            >
              <Columns3 aria-hidden="true" />
              Columnas
            </Button>
          </PopoverTrigger>
          <PopoverContent align="end" class="w-60 p-2">
            <ul class="space-y-1">
              <li
                v-for="columna in COLUMNAS_ORDENABLES"
                :key="columna.campo"
                class="flex items-center gap-2 px-2 py-1.5"
              >
                <Checkbox
                  :id="`columna-visible-${columna.campo}`"
                  :model-value="esVisible(columna.campo)"
                  :disabled="columna.campo === COLUMNA_FIJA"
                  @update:model-value="(valor) => cambiarVisibilidad(columna.campo, valor === true)"
                />
                <Label :for="`columna-visible-${columna.campo}`" class="font-normal">{{
                  columna.etiqueta
                }}</Label>
              </li>
            </ul>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              class="mt-1 w-full"
              :disabled="columnasOcultas.length === 0"
              @click="mostrarTodasLasColumnas"
              >Mostrar todas</Button
            >
          </PopoverContent>
        </Popover>
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
              v-for="columna in columnasVisibles"
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
            <TableCell :class="claseCelda(tarea, TEXTO_AJUSTABLE)">{{ tarea.nombre }}</TableCell>
            <TableCell v-if="esVisible('prioridad')" :class="claseCelda(tarea)">{{
              tarea.prioridad ?? '—'
            }}</TableCell>
            <TableCell
              v-if="esVisible('descripcion')"
              :class="claseCelda(tarea, TEXTO_AJUSTABLE)"
              >{{ tarea.descripcion }}</TableCell
            >
            <TableCell
              v-for="campoLista in camposListaVisibles"
              :key="campoLista"
              :class="claseCelda(tarea, TEXTO_AJUSTABLE)"
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
            <TableCell
              v-if="esVisible('fechaCreacion')"
              :class="claseCelda(tarea, TEXTO_AJUSTABLE)"
              >{{ formatearFechaHora(tarea.fecha_creacion) }}</TableCell
            >
            <TableCell
              v-if="esVisible('fechaVencimiento')"
              :class="claseCelda(tarea, TEXTO_AJUSTABLE)"
            >
              <template v-if="tarea.fecha_vencimiento">
                {{ formatearFechaHora(tarea.fecha_vencimiento) }}
                <ContadorVencimiento
                  :vencimiento="tarea.fecha_vencimiento"
                  :class="claseCelda(tarea, 'block text-xs')"
                />
              </template>
              <template v-else>—</template>
            </TableCell>
            <TableCell v-if="esVisible('tipo')" :class="claseCelda(tarea)">{{
              textoTipoEnTabla(tarea)
            }}</TableCell>
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
                  @click="idEnDetalle = tarea.id"
                >
                  <Eye />
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  :aria-label="`Marcar como completada la tarea ${tarea.nombre}`"
                  :aria-pressed="tarea.completada"
                  :title="tarea.completada ? 'Completada' : 'Pendiente'"
                  @click="tienda.alternarCompletada(tarea.id)"
                >
                  <CircleCheck v-if="tarea.completada" />
                  <Circle v-else />
                </Button>
                <Button
                  :id="idBotonEliminar(tarea.id)"
                  variant="outline"
                  size="icon"
                  class="text-destructive"
                  :aria-label="`Eliminar la tarea ${tarea.nombre}`"
                  title="Eliminar"
                  @click="pedirEliminar(tarea)"
                >
                  <Trash />
                </Button>
              </div>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </template>

    <DetalleTarea
      :tarea="tareaEnDetalle"
      :error="tienda.error"
      @cerrar="idEnDetalle = null"
      @eliminar="tareaEnDetalle && pedirEliminar(tareaEnDetalle)"
    />

    <DialogoConfirmacion
      :abierto="tareaAEliminar !== null"
      :titulo="`¿Eliminar la tarea ${tareaAEliminar?.nombre ?? ''}?`"
      descripcion="También se eliminarán sus subtareas y comentarios. No se puede deshacer."
      texto-confirmar="Eliminar"
      :procesando="eliminando"
      :error="errorEliminar"
      @update:abierto="alCambiarConfirmacion"
      @confirmar="confirmarEliminar"
      @cierre-foco="alDevolverFocoConfirmacion"
    />
  </section>
</template>
