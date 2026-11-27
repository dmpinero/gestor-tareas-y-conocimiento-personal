<script setup lang="ts">
import {
  CalendarDays,
  ChevronDown,
  ChevronRight,
  ChevronsDownUp,
  ChevronsUpDown,
  Columns3,
  Kanban,
  Layers,
  List,
  ListFilter,
  Search,
  Share2,
} from '@lucide/vue'
import { createReusableTemplate, useElementSize } from '@vueuse/core'
import {
  computed,
  nextTick,
  onMounted,
  reactive,
  ref,
  useTemplateRef,
  watch,
  type Component,
} from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  TIPOS_TAREA,
  etiquetaTipoTarea,
  type DatosTarea,
  type Subtarea,
  type Oportunidad,
  type Tarea,
  type TipoTarea,
} from '@/api/tipos'
import {
  CLAVE_SIN_SUBESTADO,
  adelantarGrupoDe,
  agruparPorSubestado,
  type GrupoSubestado,
} from '@/lib/agruparPorSubestado'
import { aFechaHoraIso, formatearFechaCorta, formatearFechaHora } from '@/lib/fechas'
import { estaHibernada, instanteCongelado } from '@/lib/hibernacion'
import type { ValoresFormularioTarea } from '@/lib/formularioTarea'
import { useTiendaFoco } from '@/stores/foco'
import { useTiendaGruposEstados } from '@/stores/gruposEstados'
import { useTiendaWorkflows } from '@/stores/workflows'
import { useTiendaTareas } from '@/stores/tareas'
import { coincideBusqueda, useBusquedaTabla } from '@/composables/useBusquedaTabla'
import {
  compararConNulosAlFinal,
  compararNumero,
  compararTexto,
  useOrdenacionTabla,
  valorAriaSort,
} from '@/composables/useOrdenacionTabla'
import BarraPrioridades from '@/componentes/compartido/BarraPrioridades.vue'
import AvatarPersona from '@/componentes/compartido/AvatarPersona.vue'
import AvisoVencimiento from '@/componentes/compartido/AvisoVencimiento.vue'
import BotonesExportarTabla from '@/componentes/compartido/BotonesExportarTabla.vue'
import VencimientoCorto from '@/componentes/compartido/VencimientoCorto.vue'
import CabeceraOrdenable from '@/componentes/compartido/CabeceraOrdenable.vue'
import ContadorVencimiento from '@/componentes/compartido/ContadorVencimiento.vue'
import DetalleTarea from '@/componentes/compartido/DetalleTarea.vue'
import DialogoConfirmacion from '@/componentes/compartido/DialogoConfirmacion.vue'
import DialogoHibernar from '@/componentes/compartido/DialogoHibernar.vue'
import DialogoDescartarCambios from '@/componentes/compartido/DialogoDescartarCambios.vue'
import FiltroMultiple from '@/componentes/compartido/FiltroMultiple.vue'
import FormularioTarea from '@/componentes/compartido/FormularioTarea.vue'
import InsigniaFoco from '@/componentes/compartido/InsigniaFoco.vue'
import InsigniaHibernada from '@/componentes/compartido/InsigniaHibernada.vue'
import MenuAccionesTarea from '@/componentes/compartido/MenuAccionesTarea.vue'
import NombreRelacionado from '@/componentes/compartido/NombreRelacionado.vue'
import ModalTareasRelacionadas from '@/componentes/compartido/ModalTareasRelacionadas.vue'
import { useProveedorTareasRelacionadas } from '@/composables/useTareasRelacionadas'
import { useConfirmarDescarte } from '@/composables/useConfirmarDescarte'
import CalendarioTareas from '@/componentes/compartido/CalendarioTareas.vue'
import TableroTareas from '@/componentes/compartido/TableroTareas.vue'
import RedTareas from '@/componentes/compartido/RedTareas.vue'
import {
  CLASE_PILDORA,
  PILDORA_PRIORIDAD,
  PILDORA_TIPO,
  clavePrioridad,
  colorEtiqueta,
  pildoraEstado,
} from '@/lib/coloresTarea'
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
const tiendaWorkflows = useTiendaWorkflows()
const tiendaFoco = useTiendaFoco()
const ruta = useRoute()
const enrutador = useRouter()
// El alta y la edición se hacen en ventanas modales; las dos comparten el
// formulario y su estado.
const modalAltaAbierta = ref(false)
const panelEdicionAbierto = ref(false)
const errorFormulario = ref<string | null>(null)
// `null` en modo crear; el id de la tarea en modo editar.
const idEnEdicion = ref<number | null>(null)
// Id de la tarea abierta en la modal de detalle, o `null` si está cerrada. Se
// lee de la tienda para que la modal refleje los cambios (p. ej. una subtarea resuelta).
const idEnDetalle = ref<number | null>(null)
// Tarea que se está hibernando desde el menú "⋯" de su fila (diálogo abierto).
const tareaAHibernar = ref<Tarea | null>(null)
const tareaEnDetalle = computed<Tarea | null>(
  () => tienda.tareas.find((tarea) => tarea.id === idEnDetalle.value) ?? null,
)

// `/tareas?tarea=<id>` (p. ej. desde la píldora de la tarea en foco) abre el
// detalle de esa tarea en cuanto está cargada y quita el parámetro de la URL,
// para que volver a pulsar la píldora lo abra de nuevo. Un valor que no es un
// id se ignora.
watch(
  [() => ruta.query.tarea, () => tienda.tareas],
  ([valor]) => {
    if (typeof valor !== 'string' || !/^\d+$/.test(valor)) return
    const id = Number(valor)
    if (!tienda.tareas.some((tarea) => tarea.id === id)) return
    idEnDetalle.value = id
    const resto = Object.entries(ruta.query).filter(([clave]) => clave !== 'tarea')
    void enrutador.replace({ query: Object.fromEntries(resto) })
  },
  { immediate: true },
)
// La modal de detalle también edita la tarea, con el mismo formulario que la
// modal de edición más dos campos que esta no tiene: si está completada y el
// estado dentro de su grupo. Se guardan con sus propias llamadas tras el resto.
const editandoEnDetalle = ref(false)
const extrasDetalle = reactive<{ completada: boolean; estadoId: number | '' }>({
  completada: false,
  estadoId: '',
})

// Avance que sigue al tipo en la tabla en una oportunidad con subtareas (p. ej.
// los pasos de su workflow): resueltas / total (" · 3/7", tras "Oportunidad").
// Va fuera del botón del tipo, que solo nombra el tipo. Ordenar, filtrar y
// exportar usan solo el tipo.
function avanceTipoEnTabla(tarea: Tarea): string {
  if (tarea.tipo !== 'oportunidad' || tarea.subtareas.length === 0) return ''
  const resueltas = tarea.subtareas.filter((subtarea) => subtarea.resuelta).length
  return ` · ${resueltas}/${tarea.subtareas.length}`
}

// Píldora de la prioridad (sin prioridad no hay píldora, sino "—").
function clasePildoraPrioridad(prioridad: number): string {
  const clave = clavePrioridad(prioridad)
  return clave === 'sin' ? CLASE_PILDORA : `${CLASE_PILDORA} ${PILDORA_PRIORIDAD[clave]}`
}

// Color del estado según su posición en el grupo de estados de la tarea.
function clasePildoraEstado(tarea: Tarea): string {
  const estados =
    tiendaGrupos.grupos.find((grupo) => grupo.id === tarea.grupo_estados?.id)?.estados ?? []
  const indice = estados.findIndex((estado) => estado.id === tarea.estado?.id)
  return `${CLASE_PILDORA} ${pildoraEstado(indice, estados.length)}`
}

// --- Eliminar tarea, con confirmación --------------------------------------
// Se pide desde el menú "⋯" de la fila o desde el detalle. Al confirmar se
// borra (con sus subtareas y comentarios) y se cierra el detalle si estaba
// abierto. Como la fila desaparece, el foco pasa al menú de la fila siguiente
// (o la anterior) o, si no quedan filas, al título de la lista; nunca al
// <body>. Si se cancela desde la fila, vuelve a su menú (la opción "Eliminar"
// ya no existe porque el menú se cerró al elegirla).
const ID_TITULO_LISTA = 'titulo-lista-tareas'
const tareaAEliminar = ref<Tarea | null>(null)
const eliminando = ref(false)
const errorEliminar = ref<string | null>(null)
let destinoFocoTrasEliminar: string | null = null
let destinoFocoAlCancelar: string | null = null

function idBotonAcciones(id: number): string {
  return `acciones-tarea-${id}`
}

function pedirEliminar(tarea: Tarea, desdeFila = false): void {
  errorEliminar.value = null
  destinoFocoAlCancelar = desdeFila ? idBotonAcciones(tarea.id) : null
  tareaAEliminar.value = tarea
}

function alCambiarConfirmacion(abierta: boolean): void {
  if (!abierta && !eliminando.value) tareaAEliminar.value = null
}

function destinoFocoTras(id: number): string {
  // En el tablero, el calendario y la red no hay menús por fila.
  if (vista.value !== 'lista') return ID_TITULO_LISTA
  const filas = filasVisibles.value
  const indice = filas.findIndex((tarea) => tarea.id === id)
  const vecina = filas[indice + 1] ?? filas[indice - 1]
  return vecina && indice !== -1 ? idBotonAcciones(vecina.id) : ID_TITULO_LISTA
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
// abrió (ya no existe) sino al destino calculado; al cancelar desde la fila,
// al menú de esa fila.
function alDevolverFocoConfirmacion(evento: Event): void {
  if (destinoFocoTrasEliminar !== null) {
    evento.preventDefault()
    enfocarTrasEliminar()
    destinoFocoTrasEliminar = null
  } else if (destinoFocoAlCancelar !== null) {
    evento.preventDefault()
    document.getElementById(destinoFocoAlCancelar)?.focus()
  }
  destinoFocoAlCancelar = null
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
  subestado: '',
  tipo: '',
  oportunidad: { codigo: '', descripcion: '', observaciones: '' },
  grupoEstadosId: '',
  workflowId: '',
})

onMounted(() => {
  void tienda.cargar()
  void tienda.cargarCatalogos()
  void tiendaGrupos.cargar()
  void tiendaWorkflows.cargar()
})

// --- Lista / Tablero ---
// Preferencias de este navegador, como las columnas: si no se pueden leer o
// guardar se usa la lista y el primer grupo.
type Vista = 'lista' | 'tablero' | 'calendario' | 'red'
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
  { valor: 'red', etiqueta: 'Ver como red', icono: Share2 },
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

// El grupo de estados es obligatorio al crear y editar. Las altas proponen el
// grupo del tablero o, si no lo hay (o no tiene estados), el primero con
// estados; sin ninguno, no se pueden crear tareas.
const ERROR_SIN_GRUPO = 'Elige un grupo de estados.'
const ERROR_SIN_GRUPOS_CON_ESTADOS =
  'Crea un grupo de estados con estados en Ajustes para poder crear tareas.'

const idGrupoPropuesto = computed<number | null>(() => {
  const conEstados = tiendaGrupos.grupos.filter((grupo) => grupo.estados.length > 0)
  return (
    conEstados.find((grupo) => grupo.id === idGrupoTablero.value)?.id ?? conEstados[0]?.id ?? null
  )
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

// --- Tabla o tarjetas según el ancho disponible ---------------------------
// Por debajo de 640 px la tabla solo deja ver el nombre y la prioridad, así que
// se pasa a tarjetas. Se pinta una sola de las dos vistas (v-if) para no
// duplicar controles ni nombres accesibles. Sin medida (ancho 0, p. ej. en
// jsdom) se usa la tabla.
const ANCHO_MINIMO_TABLA = 640
const raizVista = useTemplateRef<HTMLElement>('raizVista')
const { width: anchoVista } = useElementSize(raizVista, undefined, { box: 'border-box' })
const enTarjetas = computed(() => anchoVista.value > 0 && anchoVista.value < ANCHO_MINIMO_TABLA)
// Píldora de subestado en una línea, truncada a 12rem en vez de a todo el ancho.
const CLASE_PILDORA_SUBESTADO = `${CLASE_PILDORA.replace('max-w-full', 'max-w-48')} whitespace-nowrap`
const CLASE_TARJETA_TAREA =
  'bg-card cursor-pointer rounded-lg border p-3 shadow-xs hover:bg-blue-100/60 dark:hover:bg-blue-950/60'
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
  | 'subestado'
  | 'fechaCreacion'
  | 'fechaVencimiento'
  | 'tipo'
  | 'estado'

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
// El filtro "Asignado a" mira las personas de la tarea y las de sus subtareas:
// "Sin asignar" es que no hay nadie en ninguna de las dos.
function personasDeTarea(tarea: Tarea): string[] {
  const deSubtareas = tarea.subtareas.flatMap((subtarea) =>
    subtarea.asignado ? [subtarea.asignado] : [],
  )
  return [...new Set([...tarea.asignados, ...deSubtareas])]
}
const itemsAsignadosFiltro = computed(() =>
  itemsDeNombres(tienda.personas, tienda.tareas.map(personasDeTarea), 'Sin asignar'),
)

// El subestado es como mucho uno: se filtra como una lista de cero o un nombres.
function nombresSubestado(tarea: Tarea): string[] {
  return tarea.subestado ? [tarea.subestado] : []
}
const itemsSubestadosFiltro = computed(() =>
  itemsDeNombres(tienda.subestados, tienda.tareas.map(nombresSubestado), 'Sin subestado'),
)

const prioridadesFiltro = ref<number[]>(ITEMS_PRIORIDAD.map((item) => item.id))
const etiquetasFiltro = ref<string[]>(itemsEtiquetasFiltro.value.map((item) => item.id))
const asignadosFiltro = ref<string[]>(itemsAsignadosFiltro.value.map((item) => item.id))
const subestadosFiltro = ref<string[]>(itemsSubestadosFiltro.value.map((item) => item.id))
// Con el filtro "Asignado a" activo (no están todas marcadas), el tablero
// resalta las tareas y subtareas de las personas elegidas.
const personasResaltadas = computed(() =>
  asignadosFiltro.value.length === itemsAsignadosFiltro.value.length
    ? []
    : asignadosFiltro.value.filter((nombre) => nombre !== SIN_NOMBRE),
)
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
// Rangos de fechas del panel, agrupados por campo: cada grupo muestra "Desde" y
// "Hasta" bajo su título (el nombre accesible completo lleva el título).
const RANGOS_FECHA = [
  { id: 'creacion', titulo: 'Fecha de creación' },
  { id: 'vencimiento', titulo: 'Fecha de vencimiento' },
] as const
const EXTREMOS_RANGO = ['desde', 'hasta'] as const
const fechasFiltro = reactive({
  creacion: { desde: '', hasta: '' },
  vencimiento: { desde: '', hasta: '' },
})

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
watch(itemsSubestadosFiltro, marcarNuevos(subestadosFiltro))

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
    if (!pasaFiltroNombres(personasDeTarea(tarea), asignadosFiltro.value)) return false
    if (!pasaFiltroNombres(nombresSubestado(tarea), subestadosFiltro.value)) return false
    if (!tiposFiltro.value.includes(tarea.tipo ?? SIN_TIPO)) return false
    if (estadoFiltro.value === 'completadas' && !tarea.completada) return false
    if (estadoFiltro.value === 'pendientes' && tarea.completada) return false
    const { creacion, vencimiento } = fechasFiltro
    if (!dentroDeRango(tarea.fecha_creacion, creacion.desde, creacion.hasta)) {
      return false
    }
    // Con un rango de vencimiento activo, las tareas sin vencimiento no pasan.
    if (vencimiento.desde || vencimiento.hasta) {
      if (tarea.fecha_vencimiento === null) return false
      if (!dentroDeRango(tarea.fecha_vencimiento, vencimiento.desde, vencimiento.hasta)) {
        return false
      }
    }
    return true
  }),
)

// El buscador mira todo lo que se ve de la tarea: textos, personas (también
// las de las subtareas), etiquetas, oportunidad, grupo, estado, workflow,
// tipo y fechas tal como se muestran (dd/mm/aaaa hh:mm:ss).
const { busqueda, filasFiltradas } = useBusquedaTabla(tareasConFiltros, (tarea) => [
  tarea.nombre,
  tarea.descripcion,
  ...tarea.asignados,
  ...tarea.etiquetas,
  tarea.oportunidad?.codigo,
  tarea.oportunidad?.descripcion,
  tarea.oportunidad?.observaciones,
  tarea.grupo_estados?.nombre,
  tarea.estado?.nombre,
  tarea.workflow?.nombre,
  TIPOS_TAREA.find((tipo) => tipo.valor === tarea.tipo)?.etiqueta,
  formatearFechaHora(tarea.fecha_creacion),
  tarea.fecha_vencimiento ? formatearFechaHora(tarea.fecha_vencimiento) : null,
  ...tarea.subtareas.flatMap((subtarea) => [subtarea.nombre, subtarea.asignado]),
])

// Subtareas cuyo nombre coincide con el buscador: la lista las muestra bajo
// el nombre de su tarea («Subtarea: …») y el tablero las marca y despliega.
function subtareasCoincidentes(tarea: Tarea): Subtarea[] {
  return tarea.subtareas.filter((subtarea) => coincideBusqueda(subtarea.nombre, busqueda.value))
}

function limpiarFiltros(): void {
  busqueda.value = ''
  prioridadesFiltro.value = ITEMS_PRIORIDAD.map((item) => item.id)
  etiquetasFiltro.value = itemsEtiquetasFiltro.value.map((item) => item.id)
  asignadosFiltro.value = itemsAsignadosFiltro.value.map((item) => item.id)
  subestadosFiltro.value = itemsSubestadosFiltro.value.map((item) => item.id)
  tiposFiltro.value = ITEMS_TIPO.map((item) => item.id)
  estadoFiltro.value = 'todas'
  fechasFiltro.creacion = { desde: '', hasta: '' }
  fechasFiltro.vencimiento = { desde: '', hasta: '' }
}

// Filtros que restringen algo: el buscador, cada lista sin todas sus opciones
// marcadas, el estado distinto de "Todas" y cada rango de fechas con algún extremo.
const numeroFiltrosActivos = computed(
  () =>
    [
      busqueda.value.trim() !== '',
      prioridadesFiltro.value.length !== ITEMS_PRIORIDAD.length,
      etiquetasFiltro.value.length !== itemsEtiquetasFiltro.value.length,
      asignadosFiltro.value.length !== itemsAsignadosFiltro.value.length,
      subestadosFiltro.value.length !== itemsSubestadosFiltro.value.length,
      tiposFiltro.value.length !== ITEMS_TIPO.length,
      estadoFiltro.value !== 'todas',
      ...RANGOS_FECHA.map(
        ({ id }) => fechasFiltro[id].desde !== '' || fechasFiltro[id].hasta !== '',
      ),
    ].filter(Boolean).length,
)

// El panel con todos los filtros se despliega solo al pedirlo con "Filtrar".
const filtrosAbiertos = ref(false)

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
    subestado: compararConNulosAlFinal((tarea) => tarea.subestado ?? null, compararTexto),
    fechaCreacion: (a, b) => compararIso(a.fecha_creacion, b.fecha_creacion),
    fechaVencimiento: compararConNulosAlFinal((tarea) => tarea.fecha_vencimiento, compararIso),
    tipo: compararConNulosAlFinal((tarea) => etiquetaTipoTarea(tarea.tipo), compararTexto),
    estado: compararConNulosAlFinal((tarea) => tarea.estado?.nombre ?? null, compararTexto),
  },
)

const COLUMNAS_ORDENABLES: { campo: CampoOrdenable; etiqueta: string }[] = [
  { campo: 'nombre', etiqueta: 'Nombre' },
  { campo: 'prioridad', etiqueta: 'Prioridad' },
  { campo: 'descripcion', etiqueta: 'Descripción' },
  { campo: 'etiquetas', etiqueta: 'Etiquetas' },
  { campo: 'asignados', etiqueta: 'Asignado a' },
  { campo: 'subestado', etiqueta: 'Subestado' },
  { campo: 'fechaCreacion', etiqueta: 'Fecha de creación' },
  { campo: 'fechaVencimiento', etiqueta: 'Fecha de vencimiento' },
  { campo: 'tipo', etiqueta: 'Tipo' },
  { campo: 'estado', etiqueta: 'Estado' },
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

// --- Grupos "Pendientes" y "Completadas" ---
// La tabla separa las tareas en dos grupos plegables, cada uno con su color en
// el borde izquierdo y un tinte del mismo color en su fila de cabecera (el
// texto sigue por encima de 4,5:1 en ambos temas). Dentro de cada grupo se mantiene el orden elegido; la
// exportación sigue siendo la lista única. Los grupos plegados se recuerdan en
// este navegador, como las columnas: sin almacenamiento, ambos se despliegan.
type IdGrupoTabla = 'pendientes' | 'completadas'
const CLAVE_GRUPOS_PLEGADOS = 'gestor-tareas:grupos-plegados-tareas'
const GRUPOS_TABLA: {
  id: IdGrupoTabla
  titulo: string
  completada: boolean
  borde: string
  // La franja de color de la celda fija del nombre: con bordes colapsados, un
  // borde no se desplaza con la celda fija y dejaría asomar lo de debajo.
  franja: string
  fondo: string
}[] = [
  {
    id: 'pendientes',
    titulo: 'Pendientes',
    completada: false,
    borde: 'border-l-blue-600 dark:border-l-blue-400',
    franja:
      'shadow-[inset_4px_0_0_var(--color-blue-600),inset_-1px_0_0_var(--border)] dark:shadow-[inset_4px_0_0_var(--color-blue-400),inset_-1px_0_0_var(--border)]',
    fondo: 'bg-blue-50 hover:bg-blue-50 dark:bg-blue-950/50 dark:hover:bg-blue-950/50',
  },
  {
    id: 'completadas',
    titulo: 'Completadas',
    completada: true,
    borde: 'border-l-emerald-600 dark:border-l-emerald-400',
    franja:
      'shadow-[inset_4px_0_0_var(--color-emerald-600),inset_-1px_0_0_var(--border)] dark:shadow-[inset_4px_0_0_var(--color-emerald-400),inset_-1px_0_0_var(--border)]',
    fondo: 'bg-emerald-50 hover:bg-emerald-50 dark:bg-emerald-950/50 dark:hover:bg-emerald-950/50',
  },
]

// Filas de tareas: fondo alterno (cebra) dentro de cada grupo y un resaltado
// claro al pasar el ratón, porque la fila entera abre el detalle.
// Fondos opacos (mezclados con el de la tarjeta): la celda fija del nombre los
// hereda y tapa las columnas que pasan por debajo al desplazar en horizontal.
const FONDO_FILA = 'bg-card'
const FONDO_FILA_ALTERNA = 'bg-[color-mix(in_oklab,var(--muted)_40%,var(--card))]'
const CLASE_FILA_TAREA =
  'cursor-pointer hover:bg-[color-mix(in_oklab,var(--color-blue-100)_60%,var(--card))] dark:hover:bg-[color-mix(in_oklab,var(--color-blue-950)_60%,var(--card))]'
// Columna Nombre fija al desplazar la tabla en horizontal; una línea a su
// derecha la separa de lo que pasa por debajo.
const CLASE_COLUMNA_FIJA = 'sticky left-0 z-10'
const LINEA_COLUMNA_FIJA = 'shadow-[inset_-1px_0_0_var(--border)]'
// Las acciones, fijas a la derecha: siempre al alcance y nunca bajo el nombre.
const CLASE_ACCIONES_FIJAS = 'sticky right-0 z-10 shadow-[inset_1px_0_0_var(--border)]'
// La tarea en foco, con el borde violeta de la tarea en foco del tablero.
const CLASE_FILA_FOCO = 'ring-2 ring-violet-500 ring-inset dark:ring-violet-400'
function claseFilaTarea(indice: number): string {
  return `${CLASE_FILA_TAREA} ${indice % 2 === 1 ? FONDO_FILA_ALTERNA : FONDO_FILA}`
}

function leerGruposPlegados(): IdGrupoTabla[] {
  try {
    const guardado: unknown = JSON.parse(localStorage.getItem(CLAVE_GRUPOS_PLEGADOS) ?? '[]')
    if (!Array.isArray(guardado)) return []
    return GRUPOS_TABLA.map((grupo) => grupo.id).filter((id) => guardado.includes(id))
  } catch {
    return []
  }
}

const gruposPlegados = ref<IdGrupoTabla[]>(leerGruposPlegados())
watch(gruposPlegados, (plegados) => {
  try {
    localStorage.setItem(CLAVE_GRUPOS_PLEGADOS, JSON.stringify(plegados))
  } catch {
    // Sin almacenamiento (p. ej. navegación privada) la preferencia dura la sesión.
  }
})

function estaPlegado(id: IdGrupoTabla): boolean {
  return gruposPlegados.value.includes(id)
}

function alternarGrupo(id: IdGrupoTabla): void {
  gruposPlegados.value = estaPlegado(id)
    ? gruposPlegados.value.filter((plegado) => plegado !== id)
    : GRUPOS_TABLA.map((grupo) => grupo.id).filter((g) => g === id || estaPlegado(g))
}

// La fila en foco (la tarea o la de su subtarea en foco) va la primera de su
// grupo con cualquier orden, como su tarjeta en el tablero; las demás siguen el
// orden elegido. La exportación conserva el orden de la columna.
const filasConFocoPrimero = computed(() => {
  const filas = filasOrdenadas.value
  const indice = filas.findIndex((tarea) => tiendaFoco.tareaContieneFoco(tarea.id))
  if (indice <= 0) return filas
  return [filas[indice]!, ...filas.slice(0, indice), ...filas.slice(indice + 1)]
})

const gruposConFilas = computed(() =>
  GRUPOS_TABLA.map((grupo) => ({
    ...grupo,
    filas: filasConFocoPrimero.value.filter(
      (tarea) => Boolean(tarea.completada) === grupo.completada,
    ),
  })),
)

// --- Agrupar por subestado ---
// Dentro de cada grupo ("Pendientes", "Completadas") las filas se reparten en
// secciones plegables por subestado, ordenadas por nombre como el catálogo y
// con "Sin subestado" al final; solo las que tienen filas. Se recuerda en este
// navegador si se agrupa y qué secciones están plegadas, cada una como
// "<grupo>|<clave del subestado>" (p. ej. "pendientes|sin"); lo que no se
// reconozca se ignora.
const CLAVE_AGRUPAR_SUBESTADO = 'gestor-tareas:agrupar-subestado-tareas'
const CLAVE_SUBESTADOS_PLEGADOS = 'gestor-tareas:subestados-plegados-tareas'

const agruparSubestado = ref(leerPreferencia(CLAVE_AGRUPAR_SUBESTADO) === 'true')
watch(agruparSubestado, (activo) => guardarPreferencia(CLAVE_AGRUPAR_SUBESTADO, String(activo)))

function claveSeccion(idGrupo: IdGrupoTabla, claveSubestado: string): string {
  return `${idGrupo}|${claveSubestado}`
}

function esClaveSeccion(valor: unknown): valor is string {
  if (typeof valor !== 'string') return false
  const separador = valor.indexOf('|')
  const grupo = valor.slice(0, separador)
  const subestado = valor.slice(separador + 1)
  return (
    separador > 0 &&
    GRUPOS_TABLA.some((g) => g.id === grupo) &&
    (subestado === CLAVE_SIN_SUBESTADO || /^subestado:.+/.test(subestado))
  )
}

function leerSeccionesPlegadas(): string[] {
  try {
    const guardado: unknown = JSON.parse(localStorage.getItem(CLAVE_SUBESTADOS_PLEGADOS) ?? '[]')
    return Array.isArray(guardado) ? [...new Set(guardado.filter(esClaveSeccion))] : []
  } catch {
    return []
  }
}

const seccionesPlegadas = ref<string[]>(leerSeccionesPlegadas())
watch(seccionesPlegadas, (plegadas) =>
  guardarPreferencia(CLAVE_SUBESTADOS_PLEGADOS, JSON.stringify(plegadas)),
)

function estaPlegadaSeccion(idGrupo: IdGrupoTabla, claveSubestado: string): boolean {
  return seccionesPlegadas.value.includes(claveSeccion(idGrupo, claveSubestado))
}

function alternarSeccion(idGrupo: IdGrupoTabla, claveSubestado: string): void {
  const clave = claveSeccion(idGrupo, claveSubestado)
  seccionesPlegadas.value = seccionesPlegadas.value.includes(clave)
    ? seccionesPlegadas.value.filter((plegada) => plegada !== clave)
    : [...seccionesPlegadas.value, clave]
}

// El botón de la cabecera del grupo contrae todas sus secciones si alguna está
// desplegada y, si están todas contraídas, las expande todas.
function grupoContraido(idGrupo: IdGrupoTabla): boolean {
  return seccionesPorGrupo.value[idGrupo].every((seccion) =>
    estaPlegadaSeccion(idGrupo, seccion.clave),
  )
}

function alternarSeccionesDeGrupo(idGrupo: IdGrupoTabla): void {
  const claves = seccionesPorGrupo.value[idGrupo].map((seccion) =>
    claveSeccion(idGrupo, seccion.clave),
  )
  seccionesPlegadas.value = grupoContraido(idGrupo)
    ? seccionesPlegadas.value.filter((plegada) => !claves.includes(plegada))
    : [...new Set([...seccionesPlegadas.value, ...claves])]
}

function etiquetaSeccionesDeGrupo(idGrupo: IdGrupoTabla, titulo: string): string {
  return `${grupoContraido(idGrupo) ? 'Expandir' : 'Contraer'} todos los subestados de ${titulo}`
}

// Las secciones de cada grupo, con un id para el `aria-controls` de su cabecera.
const seccionesPorGrupo = computed<
  Record<IdGrupoTabla, (GrupoSubestado<Tarea> & { idCuerpo: string })[]>
>(() => {
  const secciones = {} as Record<IdGrupoTabla, (GrupoSubestado<Tarea> & { idCuerpo: string })[]>
  for (const grupo of gruposConFilas.value) {
    // La sección con la fila en foco va la primera, como la fila en su sección.
    const ordenadas = adelantarGrupoDe(agruparPorSubestado(grupo.filas), (tarea) =>
      tiendaFoco.tareaContieneFoco(tarea.id),
    )
    secciones[grupo.id] = ordenadas.map((seccion, indice) => ({
      ...seccion,
      idCuerpo: `seccion-${grupo.id}-${indice}`,
    }))
  }
  return secciones
})

function filasVisiblesDe(grupo: { id: IdGrupoTabla; filas: Tarea[] }): Tarea[] {
  if (estaPlegado(grupo.id)) return []
  if (!agruparSubestado.value) return grupo.filas
  return seccionesPorGrupo.value[grupo.id].flatMap((seccion) =>
    estaPlegadaSeccion(grupo.id, seccion.clave) ? [] : seccion.tareas,
  )
}

// Filas que se ven, en el orden de la pantalla (los grupos y secciones
// plegados no cuentan).
const filasVisibles = computed(() => gruposConFilas.value.flatMap(filasVisiblesDe))

// La fila de una tarea y el pie de cada grupo (alta rápida y barra de
// prioridades) se escriben una vez y se usan con y sin secciones.
const plantillaFila = createReusableTemplate<{
  tarea: Tarea
  indice: number
  franja: string
}>()
const plantillaPieGrupo = createReusableTemplate<{
  grupo: (typeof gruposConFilas.value)[number]
}>()
// Piezas compartidas por la fila de la tabla y la tarjeta de pantallas estrechas.
const plantillaNombre = createReusableTemplate<{ tarea: Tarea }>()
const plantillaPrioridad = createReusableTemplate<{ tarea: Tarea }>()
const plantillaEstado = createReusableTemplate<{ tarea: Tarea }>()
const plantillaSubestado = createReusableTemplate<{ tarea: Tarea }>()
const plantillaTipo = createReusableTemplate<{ tarea: Tarea }>()
const plantillaAcciones = createReusableTemplate<{ tarea: Tarea }>()
const plantillaAltaRapida = createReusableTemplate<{
  grupo: (typeof gruposConFilas.value)[number]
}>()
const plantillaBotonGrupo = createReusableTemplate<{
  grupo: (typeof gruposConFilas.value)[number]
}>()
const plantillaTarjeta = createReusableTemplate<{ tarea: Tarea }>()

// Celdas de la tabla por fila: las columnas visibles más la de acciones.
const numeroColumnasTabla = computed(() => columnasVisibles.value.length + 1)

// Alta rápida al final de cada grupo: solo con el nombre. La API exige una
// descripción, así que se envía el propio nombre; en "Completadas" la tarea se
// marca como completada nada más crearla.
const altaRapida = reactive<Record<IdGrupoTabla, string>>({ pendientes: '', completadas: '' })
const errorAltaRapida = reactive<Record<IdGrupoTabla, string | null>>({
  pendientes: null,
  completadas: null,
})
const creandoRapida = reactive<Record<IdGrupoTabla, boolean>>({
  pendientes: false,
  completadas: false,
})

async function crearRapida(id: IdGrupoTabla): Promise<void> {
  const nombre = altaRapida[id].trim()
  if (nombre === '' || creandoRapida[id]) return
  const fechaCreacion = aFechaHoraIso(formatearFechaHora(new Date()))
  if (fechaCreacion === null) return
  const idGrupo = idGrupoPropuesto.value
  if (idGrupo === null) {
    errorAltaRapida[id] = ERROR_SIN_GRUPOS_CON_ESTADOS
    return
  }
  creandoRapida[id] = true
  errorAltaRapida[id] = null
  try {
    const creada = await tienda.crear({
      nombre,
      prioridad: null,
      descripcion: nombre,
      fecha_creacion: fechaCreacion,
      fecha_vencimiento: null,
      etiquetas: [],
      asignados: [],
      tipo: null,
      oportunidad: null,
      grupo_estados_id: idGrupo,
      workflow_id: null,
      subestado: null,
    })
    altaRapida[id] = ''
    if (GRUPOS_TABLA.find((grupo) => grupo.id === id)?.completada) {
      await tienda.alternarCompletada(creada.id)
    }
  } catch (motivo) {
    errorAltaRapida[id] = (motivo as Error).message
  } finally {
    creandoRapida[id] = false
  }
}

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
      subestado: tarea.subestado ?? '—',
      fechaCreacion: formatearFechaHora(tarea.fecha_creacion),
      fechaVencimiento: tarea.fecha_vencimiento ? formatearFechaHora(tarea.fecha_vencimiento) : '—',
      tipo: etiquetaTipoTarea(tarea.tipo) ?? '—',
      estado: tarea.estado?.nombre ?? '—',
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
  formulario.subestado = ''
  formulario.tipo = ''
  formulario.oportunidad = { codigo: '', descripcion: '', observaciones: '' }
  formulario.grupoEstadosId = ''
  formulario.workflowId = ''
  errorFormulario.value = null
  idEnEdicion.value = null
  destinoAlta = null
}

// --- Cambios sin guardar en el formulario ---------------------------------
// Al abrir el formulario se guarda una foto de sus valores (con los extras del
// detalle) ya rellenos, p. ej. con la fecha de creación propuesta. Cerrarlo sin
// guardar (clic fuera, Escape, "Cancelar" o "Cerrar") con valores distintos
// pide confirmación antes de descartarlos; guardar cierra sin preguntar.
const fotoInicialFormulario = ref<string | null>(null)

function fotoFormulario(): string {
  return JSON.stringify({
    ...formulario,
    // El campo numérico puede devolver número o texto para el mismo valor.
    prioridad: String(formulario.prioridad ?? ''),
    extras: editandoEnDetalle.value ? { ...extrasDetalle } : null,
  })
}

async function fijarFotoFormulario(): Promise<void> {
  // Tras los ajustes del mismo ciclo (p. ej. el grupo de la columna del
  // tablero o el estado que fija el watcher del detalle).
  await nextTick()
  fotoInicialFormulario.value = fotoFormulario()
}

const formularioCambiado = computed(
  () => fotoInicialFormulario.value !== null && fotoFormulario() !== fotoInicialFormulario.value,
)
const descarteFormulario = useConfirmarDescarte(() => formularioCambiado.value)
const { confirmando: confirmandoDescarteFormulario } = descarteFormulario

function pedirCerrarFormulario(): void {
  descarteFormulario.pedirCierre(cerrarFormulario)
}

function alCambiarAperturaFormulario(abierta: boolean): void {
  if (!abierta) pedirCerrarFormulario()
}

function abrirParaCrear(): void {
  limpiarFormulario()
  formulario.fechaCreacion = formatearFechaHora(new Date())
  formulario.grupoEstadosId = idGrupoPropuesto.value ?? ''
  modalAltaAbierta.value = true
  void fijarFotoFormulario()
}

// Si el alta se abrió antes de que llegaran los grupos, se propone uno al
// llegar (sin contarlo como un cambio sin guardar).
watch(idGrupoPropuesto, (id) => {
  if (id === null || !modalAltaAbierta.value || idEnEdicion.value !== null) return
  if (formulario.grupoEstadosId !== '') return
  formulario.grupoEstadosId = id
  void fijarFotoFormulario()
})

function cerrarFormulario(): void {
  modalAltaAbierta.value = false
  panelEdicionAbierto.value = false
  editandoEnDetalle.value = false
  fotoInicialFormulario.value = null
}

function abrirParaEditar(tarea: Tarea): void {
  cargarFormulario(tarea)
  panelEdicionAbierto.value = true
  void fijarFotoFormulario()
}

function editarEnDetalle(): void {
  const tarea = tareaEnDetalle.value
  if (tarea === null) return
  cargarFormulario(tarea)
  extrasDetalle.completada = tarea.completada
  extrasDetalle.estadoId = tarea.estado?.id ?? ''
  editandoEnDetalle.value = true
  void fijarFotoFormulario()
}

// Modal con las tareas y subtareas de la etiqueta o persona pulsada.
const tareasRelacionadas = useProveedorTareasRelacionadas()

function abrirDesdeRelacionadas(id: number): void {
  tareasRelacionadas.cerrar()
  cerrarDetalle()
  idEnDetalle.value = id
}

// Elementos de la fila con acción propia: pulsarlos no abre el detalle.
const SELECTOR_INTERACTIVO =
  'button, a, input, select, textarea, label, [role="checkbox"], [role="menuitem"]'

// Pulsar cualquier parte de la fila abre el detalle de la tarea, salvo los
// controles de la fila o cuando se está seleccionando texto.
// Desde "Tareas relacionadas" del detalle se pasa a la tarea vinculada.
function abrirVinculada(id: number): void {
  cerrarDetalle()
  idEnDetalle.value = id
}

function alPulsarFila(evento: MouseEvent, id: number): void {
  const objetivo = evento.target
  if (objetivo instanceof Element && objetivo.closest(SELECTOR_INTERACTIVO)) return
  if ((window.getSelection()?.toString() ?? '') !== '') return
  idEnDetalle.value = id
}

function cerrarDetalle(): void {
  idEnDetalle.value = null
  editandoEnDetalle.value = false
  fotoInicialFormulario.value = null
}

// Estados del grupo elegido en el formulario del detalle.
const estadosGrupoElegido = computed(
  () => tiendaGrupos.grupos.find((grupo) => grupo.id === formulario.grupoEstadosId)?.estados ?? [],
)

// Al cambiar de grupo en el detalle, el estado pasa al que tiene la tarea si
// vuelve a su grupo, o al primero del grupo nuevo (como hace la API).
watch(
  () => formulario.grupoEstadosId,
  (idGrupo) => {
    if (!editandoEnDetalle.value) return
    const tarea = tareaEnDetalle.value
    extrasDetalle.estadoId =
      tarea?.grupo_estados?.id === idGrupo && tarea.estado
        ? tarea.estado.id
        : (estadosGrupoElegido.value[0]?.id ?? '')
  },
)

/**
 * Guarda los campos del detalle que la edición no envía: si está completada
 * y el estado del grupo. Los fallos quedan en el error de la tienda.
 */
async function guardarExtrasDetalle(id: number): Promise<void> {
  const tarea = tienda.tareas.find((candidata) => candidata.id === id)
  if (!tarea) return
  if (tarea.completada !== extrasDetalle.completada) await tienda.alternarCompletada(id)
  const estadoId = extrasDetalle.estadoId
  if (estadoId !== '' && tarea.estado?.id !== estadoId) {
    await tienda.cambiarEstadoTarea(id, estadoId)
  }
}

/** Pone en el formulario los datos de la tarea que se va a editar. */
function cargarFormulario(tarea: Tarea): void {
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
  formulario.subestado = tarea.subestado ?? ''
  formulario.tipo = tarea.tipo ?? ''
  formulario.grupoEstadosId = tarea.grupo_estados?.id ?? ''
  formulario.workflowId = tarea.workflow?.id ?? ''
  if (tarea.oportunidad) {
    formulario.oportunidad = {
      codigo: tarea.oportunidad.codigo,
      descripcion: tarea.oportunidad.descripcion ?? '',
      observaciones: tarea.oportunidad.observaciones ?? '',
    }
  }
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
  if (formulario.grupoEstadosId === '') {
    errorFormulario.value = ERROR_SIN_GRUPO
    return
  }
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
    grupo_estados_id: formulario.grupoEstadosId,
    workflow_id: formulario.workflowId === '' ? null : formulario.workflowId,
    subestado: formulario.subestado === '' ? null : formulario.subestado,
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
      const id = idEnEdicion.value
      await tienda.actualizar(id, datos)
      if (editandoEnDetalle.value) await guardarExtrasDetalle(id)
    }
    cerrarFormulario()
    limpiarFormulario()
  } catch (motivo) {
    errorFormulario.value = (motivo as Error).message
  }
}
</script>

<template>
  <section ref="raizVista">
    <plantillaFila.define v-slot="{ tarea, indice, franja }">
      <TableRow
        data-fila-tarea
        :data-en-foco="tiendaFoco.esTareaEnFoco(tarea.id) ? 'true' : undefined"
        :class="
          tiendaFoco.esTareaEnFoco(tarea.id)
            ? `${claseFilaTarea(indice)} ${CLASE_FILA_FOCO}`
            : claseFilaTarea(indice)
        "
        @click="alPulsarFila($event, tarea.id)"
      >
        <!--
          Ancho mínimo para que la casilla y las campanas no estrechen el
          nombre, que se parte entre palabras salvo si una sola no cabe.
        -->
        <TableCell
          :class="
            claseCelda(
              tarea,
              `whitespace-normal min-w-56 pl-3 bg-inherit ${CLASE_COLUMNA_FIJA} ${franja}`,
            )
          "
        >
          <plantillaNombre.reuse :tarea="tarea" />
        </TableCell>
        <TableCell v-if="esVisible('prioridad')" :class="claseCelda(tarea)">
          <plantillaPrioridad.reuse :tarea="tarea" />
        </TableCell>
        <!-- Dos líneas como mucho: la descripción entera, al pasar el ratón. -->
        <TableCell
          v-if="esVisible('descripcion')"
          :class="claseCelda(tarea, `${TEXTO_AJUSTABLE} min-w-48 max-w-80`)"
        >
          <span
            v-if="tarea.descripcion"
            data-descripcion-tarea
            class="line-clamp-2"
            :title="tarea.descripcion"
            >{{ tarea.descripcion }}</span
          >
          <template v-else>—</template>
        </TableCell>
        <TableCell
          v-for="campoLista in camposListaVisibles"
          :key="campoLista"
          :class="claseCelda(tarea, TEXTO_AJUSTABLE)"
        >
          <ul
            v-if="tarea[campoLista].length > 0 && campoLista === 'asignados'"
            class="flex flex-wrap gap-1"
          >
            <li
              v-for="nombre in tarea.asignados"
              :key="nombre"
              data-testid="chip-tabla"
              :data-nombre="nombre"
              class="inline-flex"
            >
              <NombreRelacionado tipo="persona" :nombre="nombre" class="rounded-full">
                <AvatarPersona :nombre="nombre" />
              </NombreRelacionado>
            </li>
          </ul>
          <ul v-else-if="tarea[campoLista].length > 0" class="flex flex-wrap gap-1">
            <li
              v-for="nombre in tarea.etiquetas"
              :key="nombre"
              data-testid="chip-tabla"
              :data-nombre="nombre"
              :class="`${CLASE_PILDORA} ${colorEtiqueta(nombre)}`"
            >
              <NombreRelacionado tipo="etiqueta" :nombre="nombre" />
            </li>
          </ul>
          <template v-else>—</template>
        </TableCell>
        <TableCell
          v-if="esVisible('subestado')"
          data-columna="subestado"
          :class="claseCelda(tarea)"
        >
          <plantillaSubestado.reuse :tarea="tarea" />
        </TableCell>
        <TableCell v-if="esVisible('fechaCreacion')" :class="claseCelda(tarea)">
          <!-- Como el vencimiento: corta a la vista, completa al pasar el ratón
               y para el lector de pantalla. -->
          <time
            data-fecha-creacion
            class="whitespace-nowrap"
            :datetime="tarea.fecha_creacion"
            :title="formatearFechaHora(tarea.fecha_creacion)"
            ><span aria-hidden="true">{{ formatearFechaCorta(tarea.fecha_creacion) }}</span
            ><span class="sr-only">{{ formatearFechaHora(tarea.fecha_creacion) }}</span></time
          >
        </TableCell>
        <TableCell v-if="esVisible('fechaVencimiento')" :class="claseCelda(tarea, TEXTO_AJUSTABLE)">
          <template v-if="tarea.fecha_vencimiento">
            <VencimientoCorto
              :vencimiento="tarea.fecha_vencimiento"
              :completada="tarea.completada"
              :congelada-en="instanteCongelado(tarea)"
            />
            <ContadorVencimiento
              :vencimiento="tarea.fecha_vencimiento"
              :congelada-en="instanteCongelado(tarea)"
              :hibernada="estaHibernada(tarea)"
              :class="claseCelda(tarea, 'block text-xs')"
            />
          </template>
          <template v-else>—</template>
        </TableCell>
        <TableCell v-if="esVisible('tipo')" :class="claseCelda(tarea)">
          <plantillaTipo.reuse :tarea="tarea" />
        </TableCell>
        <TableCell v-if="esVisible('estado')" :class="claseCelda(tarea)">
          <plantillaEstado.reuse :tarea="tarea" />
        </TableCell>
        <TableCell :class="`w-0 bg-inherit ${CLASE_ACCIONES_FIJAS}`">
          <plantillaAcciones.reuse :tarea="tarea" />
        </TableCell>
      </TableRow>
    </plantillaFila.define>

    <!-- Nombre con su casilla. Las insignias van debajo para no estrechar el
         nombre, que si no se partía letra a letra. -->
    <plantillaNombre.define v-slot="{ tarea }">
      <div class="flex items-start gap-2">
        <Checkbox
          class="mt-0.5"
          :model-value="tarea.completada"
          :aria-label="`Marcar como completada la tarea ${tarea.nombre}`"
          :title="tarea.completada ? 'Completada' : 'Pendiente'"
          @update:model-value="tienda.alternarCompletada(tarea.id)"
        />
        <div class="min-w-0 flex-1">
          <span data-nombre-tarea class="block break-words">{{ tarea.nombre }}</span>
          <span
            v-for="subtarea in subtareasCoincidentes(tarea)"
            :key="subtarea.id"
            data-subtarea-coincidente
            class="text-muted-foreground block text-xs break-words"
            >Subtarea: {{ subtarea.nombre }}</span
          >
          <span
            v-if="tiendaFoco.esTareaEnFoco(tarea.id) || estaHibernada(tarea)"
            data-insignias-tarea
            class="mt-1 flex flex-wrap gap-1"
          >
            <InsigniaFoco v-if="tiendaFoco.esTareaEnFoco(tarea.id)" />
            <InsigniaHibernada v-if="estaHibernada(tarea)" />
          </span>
        </div>
        <AvisoVencimiento
          class="mt-0.5"
          :vencimiento="tarea.fecha_vencimiento"
          :completada="tarea.completada"
          :congelada-en="instanteCongelado(tarea)"
        />
      </div>
    </plantillaNombre.define>
    <plantillaPrioridad.define v-slot="{ tarea }">
      <span
        v-if="tarea.prioridad !== null"
        data-testid="pildora-prioridad"
        :class="clasePildoraPrioridad(tarea.prioridad)"
        ><NombreRelacionado tipo="prioridad" :nombre="String(tarea.prioridad)"
      /></span>
      <template v-else>—</template>
    </plantillaPrioridad.define>
    <plantillaEstado.define v-slot="{ tarea }">
      <span v-if="tarea.estado" data-testid="pildora-estado" :class="clasePildoraEstado(tarea)"
        ><NombreRelacionado tipo="estado" :nombre="tarea.estado.nombre"
      /></span>
      <template v-else>—</template>
    </plantillaEstado.define>
    <!-- En una línea: si no cabe se trunca y se lee entero al pasar el ratón. -->
    <plantillaSubestado.define v-slot="{ tarea }">
      <span
        v-if="tarea.subestado"
        data-testid="pildora-subestado"
        :class="`${CLASE_PILDORA_SUBESTADO} ${colorEtiqueta(tarea.subestado)}`"
        ><NombreRelacionado
          tipo="subestado"
          :nombre="tarea.subestado"
          class="block min-w-0 truncate"
          :title="tarea.subestado"
      /></span>
      <template v-else>—</template>
    </plantillaSubestado.define>
    <plantillaTipo.define v-slot="{ tarea }">
      <span
        v-if="tarea.tipo !== null"
        data-testid="pildora-tipo"
        :class="`${CLASE_PILDORA} ${PILDORA_TIPO}`"
        ><NombreRelacionado tipo="tipo" :nombre="etiquetaTipoTarea(tarea.tipo) ?? ''" />{{
          avanceTipoEnTabla(tarea)
        }}</span
      >
      <template v-else>—</template>
    </plantillaTipo.define>
    <plantillaAcciones.define v-slot="{ tarea }">
      <MenuAccionesTarea
        :nombre="tarea.nombre"
        :id-disparador="idBotonAcciones(tarea.id)"
        :tarea-id="tarea.id"
        :completada="tarea.completada"
        @editar="abrirParaEditar(tarea)"
        @detalle="idEnDetalle = tarea.id"
        :hibernada="estaHibernada(tarea)"
        @eliminar="pedirEliminar(tarea, true)"
        @hibernar="tareaAHibernar = tarea"
        @reanudar="tienda.reanudar(tarea.id)"
      />
    </plantillaAcciones.define>

    <!-- Tarjeta de una tarea en pantallas estrechas: lo que la tabla reparte
         en columnas, apilado. Pulsarla abre el detalle, como la fila. -->
    <plantillaTarjeta.define v-slot="{ tarea }">
      <article
        data-tarjeta-tarea
        :data-en-foco="tiendaFoco.esTareaEnFoco(tarea.id) ? 'true' : undefined"
        :class="[
          CLASE_TARJETA_TAREA,
          tiendaFoco.esTareaEnFoco(tarea.id) && CLASE_FILA_FOCO,
          tarea.completada && 'text-muted-foreground',
        ]"
        @click="alPulsarFila($event, tarea.id)"
      >
        <div class="flex items-start gap-1">
          <div :class="['min-w-0 flex-1 font-medium', tarea.completada && 'line-through']">
            <plantillaNombre.reuse :tarea="tarea" />
          </div>
          <plantillaAcciones.reuse :tarea="tarea" />
        </div>
        <div class="mt-2 flex flex-wrap items-center gap-1.5 pl-6">
          <plantillaPrioridad.reuse v-if="tarea.prioridad !== null" :tarea="tarea" />
          <plantillaEstado.reuse v-if="tarea.estado" :tarea="tarea" />
          <plantillaSubestado.reuse v-if="tarea.subestado" :tarea="tarea" />
          <plantillaTipo.reuse v-if="tarea.tipo !== null" :tarea="tarea" />
          <span
            v-for="nombre in tarea.etiquetas"
            :key="nombre"
            :class="`${CLASE_PILDORA} ${colorEtiqueta(nombre)}`"
            ><NombreRelacionado tipo="etiqueta" :nombre="nombre"
          /></span>
        </div>
        <div
          v-if="tarea.fecha_vencimiento || tarea.asignados.length > 0"
          class="mt-2 flex items-end justify-between gap-2 pl-6 text-sm"
        >
          <div v-if="tarea.fecha_vencimiento">
            <VencimientoCorto
              :vencimiento="tarea.fecha_vencimiento"
              :completada="tarea.completada"
              :congelada-en="instanteCongelado(tarea)"
            />
            <ContadorVencimiento
              :vencimiento="tarea.fecha_vencimiento"
              :congelada-en="instanteCongelado(tarea)"
              :hibernada="estaHibernada(tarea)"
              class="block text-xs"
            />
          </div>
          <ul v-if="tarea.asignados.length > 0" class="ml-auto flex flex-wrap gap-1">
            <li v-for="nombre in tarea.asignados" :key="nombre" class="inline-flex">
              <NombreRelacionado tipo="persona" :nombre="nombre" class="rounded-full">
                <AvatarPersona :nombre="nombre" />
              </NombreRelacionado>
            </li>
          </ul>
        </div>
      </article>
    </plantillaTarjeta.define>
    <plantillaPieGrupo.define v-slot="{ grupo }">
      <TableRow class="hover:bg-transparent">
        <TableCell :colspan="numeroColumnasTabla" :class="`border-l-4 ${grupo.borde}`">
          <plantillaAltaRapida.reuse :grupo="grupo" />
        </TableCell>
      </TableRow>
      <TableRow
        v-if="grupo.filas.length > 0 && esVisible('prioridad')"
        class="hover:bg-transparent"
      >
        <TableCell :class="`border-l-4 ${grupo.borde}`" />
        <TableCell v-for="columna in columnasVisibles.slice(1)" :key="columna.campo">
          <BarraPrioridades
            v-if="columna.campo === 'prioridad'"
            :prioridades="grupo.filas.map((tarea) => tarea.prioridad)"
            :titulo="grupo.titulo"
          />
        </TableCell>
        <TableCell />
      </TableRow>
    </plantillaPieGrupo.define>
    <plantillaAltaRapida.define v-slot="{ grupo }">
      <form class="sticky left-4 flex flex-col gap-1" @submit.prevent="crearRapida(grupo.id)">
        <Input
          v-model="altaRapida[grupo.id]"
          data-alta-rapida
          placeholder="+ Agregar tarea"
          :aria-label="`Agregar tarea a ${grupo.titulo}`"
          :disabled="creandoRapida[grupo.id]"
          class="h-8 max-w-sm border-dashed shadow-none"
          @keydown.enter.prevent="crearRapida(grupo.id)"
        />
        <p v-if="errorAltaRapida[grupo.id]" role="alert" class="text-destructive text-sm">
          {{ errorAltaRapida[grupo.id] }}
        </p>
      </form>
    </plantillaAltaRapida.define>
    <plantillaBotonGrupo.define v-slot="{ grupo }">
      <div class="sticky left-4 flex w-fit items-center gap-2">
        <button
          type="button"
          class="hover:text-foreground focus-visible:ring-ring/50 flex items-center gap-1.5 rounded-sm text-sm font-semibold outline-none focus-visible:ring-[3px]"
          :aria-expanded="!estaPlegado(grupo.id)"
          @click="alternarGrupo(grupo.id)"
        >
          <ChevronRight
            class="size-4 transition-transform"
            :class="estaPlegado(grupo.id) ? '' : 'rotate-90'"
            aria-hidden="true"
          />
          {{ grupo.titulo }}
          <span
            class="bg-muted text-muted-foreground rounded-full px-2 py-0.5 text-xs font-medium"
            >{{ grupo.filas.length }}</span
          >
        </button>
        <!-- Con secciones por subestado: contraerlas o expandirlas todas. -->
        <button
          v-if="
            agruparSubestado && !estaPlegado(grupo.id) && seccionesPorGrupo[grupo.id].length > 0
          "
          type="button"
          data-plegar-secciones
          class="text-muted-foreground hover:text-foreground hover:bg-background/60 focus-visible:ring-ring/50 rounded-sm p-1 outline-none focus-visible:ring-[3px] [&_svg]:size-4"
          :aria-label="etiquetaSeccionesDeGrupo(grupo.id, grupo.titulo)"
          :title="etiquetaSeccionesDeGrupo(grupo.id, grupo.titulo)"
          @click="alternarSeccionesDeGrupo(grupo.id)"
        >
          <ChevronsUpDown v-if="grupoContraido(grupo.id)" aria-hidden="true" />
          <ChevronsDownUp v-else aria-hidden="true" />
        </button>
      </div>
    </plantillaBotonGrupo.define>
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

    <Collapsible v-model:open="filtrosAbiertos" class="mt-4">
      <!-- Barra de una línea: buscar, persona, filtrar, columnas y exportar. -->
      <div
        data-testid="barra-tareas"
        class="bg-card text-card-foreground flex flex-wrap items-center gap-2 rounded-xl border p-3 shadow-xs"
      >
        <div class="relative w-full sm:w-64">
          <Label for="filtro-buscar" class="sr-only">Buscar</Label>
          <Search
            class="text-muted-foreground pointer-events-none absolute top-2.5 left-2.5 size-4"
            aria-hidden="true"
          />
          <Input id="filtro-buscar" v-model="busqueda" placeholder="Buscar tareas…" class="pl-8" />
        </div>
        <!-- Atajo del filtro "Asignado a" del panel: comparten la selección. -->
        <div class="w-44">
          <FiltroMultiple
            v-model="asignadosFiltro"
            :items="itemsAsignadosFiltro"
            id-base="filtro-persona"
            etiqueta-boton="Filtrar por persona"
            nombre-singular="persona"
            nombre-plural="personas"
          />
        </div>
        <CollapsibleTrigger as-child>
          <Button type="button" variant="outline">
            <ListFilter aria-hidden="true" />
            Filtrar
            <ChevronDown
              class="size-4 transition-transform"
              :class="filtrosAbiertos ? 'rotate-180' : ''"
              aria-hidden="true"
            />
          </Button>
        </CollapsibleTrigger>
        <!-- Fuera del botón: dentro, su texto no formaría parte del nombre
             "Filtrar" (WCAG 2.5.3). -->
        <span
          v-if="numeroFiltrosActivos > 0"
          data-testid="filtros-activos"
          class="bg-primary text-primary-foreground rounded-full px-2 py-0.5 text-xs"
          >{{ numeroFiltrosActivos === 1 ? '1 activo' : `${numeroFiltrosActivos} activos` }}</span
        >
        <Button
          v-if="numeroFiltrosActivos > 0"
          type="button"
          variant="ghost"
          @click="limpiarFiltros"
          >Limpiar filtros</Button
        >
        <div
          v-if="vista === 'lista' && filasFiltradas.length > 0"
          class="ml-auto flex flex-wrap items-center gap-2"
        >
          <!-- Su texto visible es su nombre accesible (WCAG 2.5.3). -->
          <Button
            type="button"
            data-testid="agrupar-subestado"
            :variant="agruparSubestado ? 'default' : 'outline'"
            :aria-pressed="agruparSubestado"
            @click="agruparSubestado = !agruparSubestado"
          >
            <Layers aria-hidden="true" />
            Agrupar por subestado
          </Button>
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
                    @update:model-value="
                      (valor) => cambiarVisibilidad(columna.campo, valor === true)
                    "
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
      </div>

      <CollapsibleContent
        class="bg-card text-card-foreground mt-3 flex flex-col gap-4 rounded-xl border p-4 shadow-xs"
      >
        <!-- Listas desplegables, todas del mismo ancho. -->
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div class="flex min-w-0 flex-col gap-1.5">
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
          <div class="flex min-w-0 flex-col gap-1.5">
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
          <div class="flex min-w-0 flex-col gap-1.5">
            <Label>Subestado</Label>
            <FiltroMultiple
              v-model="subestadosFiltro"
              :items="itemsSubestadosFiltro"
              id-base="filtro-subestados"
              etiqueta-boton="Filtrar por subestado"
              nombre-singular="subestado"
              nombre-plural="subestados"
              genero="masculino"
            />
          </div>
          <div class="flex min-w-0 flex-col gap-1.5">
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
          <div class="flex min-w-0 flex-col gap-1.5">
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
        </div>

        <!-- Estado y rangos de fechas. -->
        <div class="grid gap-4 lg:grid-cols-3">
          <div class="flex min-w-0 flex-col gap-1.5">
            <span id="filtro-estado-titulo" class="text-sm leading-none font-medium select-none"
              >Estado</span
            >
            <!-- Control segmentado con radios nativos: el radio, transparente, cubre
                   cada opción para que el clic y el teclado sigan siendo los del radio. -->
            <div
              role="radiogroup"
              aria-labelledby="filtro-estado-titulo"
              class="bg-muted inline-flex w-full rounded-md border p-0.5"
            >
              <div v-for="opcion in OPCIONES_ESTADO" :key="opcion.valor" class="relative flex-1">
                <input
                  :id="`filtro-estado-${opcion.valor}`"
                  v-model="estadoFiltro"
                  type="radio"
                  name="filtro-estado"
                  :value="opcion.valor"
                  class="peer absolute inset-0 z-10 cursor-pointer opacity-0"
                />
                <Label
                  :for="`filtro-estado-${opcion.valor}`"
                  class="text-muted-foreground peer-checked:bg-background peer-checked:text-foreground peer-focus-visible:ring-ring/50 flex h-8 items-center justify-center rounded-sm px-2 text-center font-normal whitespace-nowrap peer-checked:shadow-sm peer-focus-visible:ring-[3px]"
                  >{{ opcion.etiqueta }}</Label
                >
              </div>
            </div>
          </div>
          <fieldset
            v-for="rango in RANGOS_FECHA"
            :key="rango.id"
            class="flex min-w-0 flex-col gap-1.5"
          >
            <legend class="mb-1.5 text-sm leading-none font-medium">{{ rango.titulo }}</legend>
            <div class="grid gap-2 sm:grid-cols-2">
              <div
                v-for="extremo in EXTREMOS_RANGO"
                :key="extremo"
                class="flex min-w-0 flex-col gap-1"
              >
                <Label
                  :for="`filtro-${rango.id}-${extremo}`"
                  class="text-muted-foreground text-xs font-normal"
                  ><span class="sr-only">{{ `${rango.titulo} ` }}</span
                  ><span class="capitalize">{{ extremo }}</span></Label
                >
                <Input
                  :id="`filtro-${rango.id}-${extremo}`"
                  v-model="fechasFiltro[rango.id][extremo]"
                  type="date"
                  class="min-w-0"
                />
              </div>
            </div>
          </fieldset>
        </div>
      </CollapsibleContent>
    </Collapsible>

    <!-- Alta y edición en ventanas modales centradas, como el detalle. Ambas
         usan el mismo formulario. -->
    <Dialog :open="modalAltaAbierta" @update:open="alCambiarAperturaFormulario">
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
          alta
          @guardar="guardar"
          @cancelar="pedirCerrarFormulario"
        />
      </DialogContent>
    </Dialog>

    <Dialog :open="panelEdicionAbierto" @update:open="alCambiarAperturaFormulario">
      <DialogContent
        sin-aspa
        class="flex max-h-[90vh] w-[90vw] max-w-3xl flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl"
      >
        <DialogHeader class="p-4">
          <DialogTitle>Editar tarea</DialogTitle>
          <DialogDescription class="sr-only">Datos de la tarea que se edita.</DialogDescription>
        </DialogHeader>
        <FormularioTarea
          v-model:valores="formulario"
          :error="errorFormulario"
          @guardar="guardar"
          @cancelar="pedirCerrarFormulario"
        />
      </DialogContent>
    </Dialog>

    <p v-if="tienda.error" class="mt-2 text-sm text-destructive" role="alert">{{ tienda.error }}</p>
    <p v-if="tiendaFoco.error" class="mt-2 text-sm text-destructive" role="alert">
      {{ tiendaFoco.error }}
    </p>

    <TableroTareas
      v-if="vista === 'tablero'"
      v-model:id-grupo="idGrupoTablero"
      :tareas="filasOrdenadas"
      :grupos="tiendaGrupos.grupos"
      :cargando-grupos="tiendaGrupos.cargando"
      :personas-resaltadas="personasResaltadas"
      :busqueda="busqueda"
      @ver-detalle="(id) => (idEnDetalle = id)"
      @anadir-tarea="abrirAltaEnEstado"
    />

    <CalendarioTareas
      v-else-if="vista === 'calendario'"
      :tareas="filasOrdenadas"
      @ver-detalle="(id) => (idEnDetalle = id)"
    />

    <RedTareas
      v-else-if="vista === 'red'"
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
      <!-- La tabla va en su propia superficie, que destaca sobre el lienzo. -->
      <div
        v-if="filasFiltradas.length > 0"
        data-testid="superficie-tabla"
        class="bg-card text-card-foreground mt-4 overflow-hidden rounded-xl border shadow-xs"
      >
        <div v-if="enTarjetas" data-lista-tarjetas>
          <section
            v-for="grupo in gruposConFilas"
            :key="grupo.id"
            :data-grupo="grupo.id"
            :class="`border-b-0 border-l-4 ${grupo.borde}`"
          >
            <div :class="`${grupo.fondo} px-3 py-2`">
              <plantillaBotonGrupo.reuse :grupo="grupo" />
            </div>
            <div v-if="!estaPlegado(grupo.id)" class="flex flex-col gap-2 p-2">
              <template v-if="agruparSubestado">
                <template v-for="seccion in seccionesPorGrupo[grupo.id]" :key="seccion.clave">
                  <h3 class="flex items-center gap-1.5 px-1 pt-1 text-sm font-medium">
                    <span
                      v-if="seccion.subestado !== null"
                      :class="`${CLASE_PILDORA} ${colorEtiqueta(seccion.subestado)}`"
                      >{{ seccion.subestado }}</span
                    >
                    <template v-else>Sin subestado</template>
                    <span class="text-muted-foreground">{{ ` · ${seccion.tareas.length}` }}</span>
                  </h3>
                  <plantillaTarjeta.reuse
                    v-for="tarea in seccion.tareas"
                    :key="tarea.id"
                    :tarea="tarea"
                  />
                </template>
              </template>
              <template v-else>
                <plantillaTarjeta.reuse
                  v-for="tarea in grupo.filas"
                  :key="tarea.id"
                  :tarea="tarea"
                />
              </template>
              <plantillaAltaRapida.reuse :grupo="grupo" />
            </div>
          </section>
        </div>
        <Table v-else>
          <TableHeader class="bg-muted">
            <TableRow class="bg-muted hover:bg-muted">
              <TableHead
                v-for="columna in columnasVisibles"
                :key="columna.campo"
                :aria-sort="valorAriaSort(campo === columna.campo, direccion)"
                :class="
                  columna.campo === COLUMNA_FIJA
                    ? `bg-muted ${CLASE_COLUMNA_FIJA} ${LINEA_COLUMNA_FIJA}`
                    : ''
                "
              >
                <CabeceraOrdenable
                  :activo="campo === columna.campo"
                  :direccion="direccion"
                  @ordenar="ordenarPor(columna.campo)"
                  >{{ columna.etiqueta }}</CabeceraOrdenable
                >
              </TableHead>
              <TableHead :class="`bg-muted ${CLASE_ACCIONES_FIJAS}`"
                ><span class="sr-only">Acciones</span></TableHead
              >
            </TableRow>
          </TableHeader>
          <template v-for="grupo in gruposConFilas" :key="grupo.id">
            <TableBody :data-grupo="grupo.id">
              <TableRow :class="grupo.fondo">
                <TableCell :colspan="numeroColumnasTabla" :class="`border-l-4 ${grupo.borde}`">
                  <plantillaBotonGrupo.reuse :grupo="grupo" />
                </TableCell>
              </TableRow>
              <template v-if="!estaPlegado(grupo.id) && !agruparSubestado">
                <plantillaFila.reuse
                  v-for="(tarea, indice) in grupo.filas"
                  :key="tarea.id"
                  :tarea="tarea"
                  :indice="indice"
                  :franja="grupo.franja"
                />
                <plantillaPieGrupo.reuse :grupo="grupo" />
              </template>
            </TableBody>
            <template v-if="!estaPlegado(grupo.id) && agruparSubestado">
              <!-- Una sección por subestado: su cabecera nombra el grupo de filas. -->
              <TableBody
                v-for="(seccion, indiceSeccion) in seccionesPorGrupo[grupo.id]"
                :id="seccion.idCuerpo"
                :key="seccion.clave"
                :data-grupo="grupo.id"
                :data-subgrupo="seccion.clave"
              >
                <!-- Una línea separa cada sección de subestado de la anterior. -->
                <TableRow
                  :data-separador-subestado="indiceSeccion > 0 ? '' : undefined"
                  :class="
                    indiceSeccion > 0
                      ? 'border-foreground/20 border-t-2 hover:bg-transparent'
                      : 'hover:bg-transparent'
                  "
                >
                  <TableHead
                    scope="rowgroup"
                    :colspan="numeroColumnasTabla"
                    :class="`border-l-4 pl-6 ${grupo.borde}`"
                  >
                    <button
                      type="button"
                      class="hover:text-foreground focus-visible:ring-ring/50 flex items-center gap-1.5 rounded-sm text-sm font-medium outline-none focus-visible:ring-[3px]"
                      :aria-expanded="!estaPlegadaSeccion(grupo.id, seccion.clave)"
                      :aria-controls="seccion.idCuerpo"
                      @click="alternarSeccion(grupo.id, seccion.clave)"
                    >
                      <ChevronRight
                        class="size-4 transition-transform"
                        :class="estaPlegadaSeccion(grupo.id, seccion.clave) ? '' : 'rotate-90'"
                        aria-hidden="true"
                      />
                      <span
                        v-if="seccion.subestado !== null"
                        data-testid="pildora-subestado"
                        :class="`${CLASE_PILDORA} ${colorEtiqueta(seccion.subestado)}`"
                        >{{ seccion.subestado }}</span
                      >
                      <template v-else>Sin subestado</template>
                      <span class="text-muted-foreground">{{ ` · ${seccion.tareas.length}` }}</span>
                    </button>
                  </TableHead>
                </TableRow>
                <template v-if="!estaPlegadaSeccion(grupo.id, seccion.clave)">
                  <plantillaFila.reuse
                    v-for="(tarea, indice) in seccion.tareas"
                    :key="tarea.id"
                    :tarea="tarea"
                    :indice="indice"
                    :franja="grupo.franja"
                  />
                </template>
              </TableBody>
              <TableBody :data-grupo="grupo.id">
                <plantillaPieGrupo.reuse :grupo="grupo" />
              </TableBody>
            </template>
          </template>
        </Table>
      </div>
    </template>

    <DetalleTarea
      :tarea="tareaEnDetalle"
      :error="tienda.error"
      :editando="editandoEnDetalle"
      :hay-cambios="editandoEnDetalle && formularioCambiado"
      @cerrar="cerrarDetalle"
      @editar="editarEnDetalle"
      @alternar-completada="tareaEnDetalle && tienda.alternarCompletada(tareaEnDetalle.id)"
      @eliminar="tareaEnDetalle && pedirEliminar(tareaEnDetalle)"
      @ver-tarea="abrirVinculada"
    >
      <template #edicion>
        <FormularioTarea
          v-model:valores="formulario"
          :error="errorFormulario"
          @guardar="guardar"
          @cancelar="pedirCerrarFormulario"
        >
          <template #extra>
            <div class="campo-opcional flex items-center gap-2">
              <input
                id="tarea-completada"
                v-model="extrasDetalle.completada"
                type="checkbox"
                class="accent-primary size-4"
              />
              <Label for="tarea-completada">Completada</Label>
            </div>
            <div
              v-if="formulario.grupoEstadosId !== ''"
              class="campo-opcional flex flex-col gap-1.5"
            >
              <Label for="tarea-estado">Estado del grupo</Label>
              <select
                id="tarea-estado"
                v-model="extrasDetalle.estadoId"
                class="border-input dark:bg-input/30 bg-background focus-visible:border-ring focus-visible:ring-ring/50 h-9 w-full rounded-md border px-3 py-1 text-base shadow-xs outline-none focus-visible:ring-[3px] md:text-sm"
              >
                <option v-for="estado in estadosGrupoElegido" :key="estado.id" :value="estado.id">
                  {{ estado.nombre }}
                </option>
              </select>
            </div>
          </template>
        </FormularioTarea>
      </template>
    </DetalleTarea>

    <DialogoDescartarCambios
      :abierto="confirmandoDescarteFormulario"
      @update:abierto="descarteFormulario.alCambiarConfirmacion"
      @descartar="descarteFormulario.descartar"
      @cierre-foco="descarteFormulario.alDevolverFoco"
    />

    <ModalTareasRelacionadas
      :seleccion="tareasRelacionadas.seleccion.value"
      :tareas="tienda.tareas"
      :grupos="tiendaGrupos.grupos"
      @cerrar="tareasRelacionadas.cerrar"
      @ver-tarea="abrirDesdeRelacionadas"
    />

    <DialogoHibernar :tarea="tareaAHibernar" @cerrar="tareaAHibernar = null" />

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
