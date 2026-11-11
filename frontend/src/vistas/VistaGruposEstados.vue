<script setup lang="ts">
import { ArrowDown, ArrowLeft, ArrowUp, GripVertical, Pencil, Trash2 } from '@lucide/vue'
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'

import type { EstadoGrupo, GrupoEstados } from '@/api/tipos'
import DialogoConfirmacion from '@/componentes/compartido/DialogoConfirmacion.vue'
import { Button } from '@/componentes/ui/button'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'
import { useTiendaGruposEstados } from '@/stores/gruposEstados'

// Grupos de estados de Ajustes. A diferencia del workflow, los estados no son
// una secuencia: el orden solo decide el de las columnas del tablero.
const LONGITUD_MAXIMA = 50
const ID_GRUPO_NUEVO = 'nombre-grupo-nuevo'

const tienda = useTiendaGruposEstados()
const grupos = computed(() => tienda.grupos)

onMounted(() => {
  void tienda.cargar()
})

function textoTareas(total: number): string {
  return total === 1 ? '1 tarea' : `${total} tareas`
}

function idEstadoNuevo(grupo: GrupoEstados): string {
  return `estado-nuevo-${grupo.id}`
}

// Devuelve el mensaje de error del nombre recortado, o `null` si es válido.
function validarNombre(nombre: string, que: 'grupo' | 'estado'): string | null {
  if (nombre.length === 0) return `El nombre del ${que} es obligatorio.`
  if (nombre.length > LONGITUD_MAXIMA) {
    return `El nombre del ${que} no puede superar los ${LONGITUD_MAXIMA} caracteres.`
  }
  return null
}

async function enfocarPorId(id: string): Promise<void> {
  await nextTick()
  document.getElementById(id)?.focus()
}

// --- Alta de grupos y estados ---------------------------------------------
const nombreGrupoNuevo = ref('')
const errorGrupoNuevo = ref<string | null>(null)
const guardandoGrupo = ref(false)

async function anadirGrupo(): Promise<void> {
  const nombre = nombreGrupoNuevo.value.trim()
  errorGrupoNuevo.value = validarNombre(nombre, 'grupo')
  if (errorGrupoNuevo.value) return
  guardandoGrupo.value = true
  const correcto = await tienda.crear(nombre)
  guardandoGrupo.value = false
  if (correcto) nombreGrupoNuevo.value = ''
}

const nombresEstadoNuevo = reactive<Record<number, string>>({})
const erroresEstadoNuevo = reactive<Record<number, string | null>>({})

async function anadirEstado(grupo: GrupoEstados): Promise<void> {
  const nombre = (nombresEstadoNuevo[grupo.id] ?? '').trim()
  erroresEstadoNuevo[grupo.id] = validarNombre(nombre, 'estado')
  if (erroresEstadoNuevo[grupo.id]) return
  if (await tienda.anadirEstado(grupo.id, nombre)) nombresEstadoNuevo[grupo.id] = ''
}

// --- Renombrar en línea ----------------------------------------------------
type Edicion = { tipo: 'grupo'; id: number } | { tipo: 'estado'; id: number }
const edicion = ref<Edicion | null>(null)
const nombreEditando = ref('')
const errorEdicion = ref<string | null>(null)

function editando(tipo: Edicion['tipo'], id: number): boolean {
  return edicion.value?.tipo === tipo && edicion.value.id === id
}

async function empezarEdicion(tipo: Edicion['tipo'], id: number, nombre: string): Promise<void> {
  edicion.value = { tipo, id }
  nombreEditando.value = nombre
  errorEdicion.value = null
  await enfocarPorId(`nombre-${tipo}-${id}`)
}

function cancelarEdicion(): void {
  edicion.value = null
  errorEdicion.value = null
}

async function guardarGrupo(grupo: GrupoEstados): Promise<void> {
  const nombre = nombreEditando.value.trim()
  errorEdicion.value = validarNombre(nombre, 'grupo')
  if (errorEdicion.value) return
  if (await tienda.renombrar(grupo.id, nombre)) edicion.value = null
}

async function guardarEstado(grupo: GrupoEstados, estado: EstadoGrupo): Promise<void> {
  const nombre = nombreEditando.value.trim()
  errorEdicion.value = validarNombre(nombre, 'estado')
  if (errorEdicion.value) return
  if (await tienda.renombrarEstado(grupo.id, estado.id, nombre)) edicion.value = null
}

// --- Eliminar, con confirmación --------------------------------------------
// El elemento que abrió la confirmación desaparece al borrar: el foco va al
// campo de alta correspondiente en vez de perderse en el <body>.
const grupoAEliminar = ref<GrupoEstados | null>(null)
const estadoAEliminar = ref<{ grupo: GrupoEstados; estado: EstadoGrupo } | null>(null)
const moverA = ref<number | null>(null)
const procesando = ref(false)
const errorDialogo = ref<string | null>(null)
let destinoFoco: string | null = null

const descripcionEliminarGrupo = computed(() => {
  const total = grupoAEliminar.value?.tareas ?? 0
  const tareas =
    total === 0
      ? 'El grupo no tiene tareas.'
      : `${textoTareas(total)} ${total === 1 ? 'quedará' : 'quedarán'} sin grupo.`
  return `${tareas} Sus estados también se eliminarán.`
})

const otrosEstados = computed<EstadoGrupo[]>(() => {
  const seleccion = estadoAEliminar.value
  if (!seleccion) return []
  return seleccion.grupo.estados.filter((estado) => estado.id !== seleccion.estado.id)
})
const conTareas = computed(() => (estadoAEliminar.value?.estado.tareas ?? 0) > 0)
const sinDestino = computed(() => conTareas.value && otrosEstados.value.length === 0)

const descripcionEliminarEstado = computed(() => {
  const total = estadoAEliminar.value?.estado.tareas ?? 0
  if (total === 0) return 'El estado no tiene tareas.'
  if (sinDestino.value) {
    return `Tiene ${textoTareas(total)} y no hay otro estado del grupo al que moverlas. Añade otro estado antes de eliminarlo.`
  }
  return `Tiene ${textoTareas(total)}. Elige a qué estado del grupo moverlas.`
})

function pedirEliminarGrupo(grupo: GrupoEstados): void {
  errorDialogo.value = null
  grupoAEliminar.value = grupo
}

function pedirEliminarEstado(grupo: GrupoEstados, estado: EstadoGrupo): void {
  errorDialogo.value = null
  estadoAEliminar.value = { grupo, estado }
  moverA.value = grupo.estados.find((otro) => otro.id !== estado.id)?.id ?? null
}

function alCambiarConfirmacion(abierta: boolean): void {
  if (abierta || procesando.value) return
  grupoAEliminar.value = null
  estadoAEliminar.value = null
}

async function terminarEliminacion(correcto: boolean, destino: string): Promise<void> {
  if (!correcto) {
    errorDialogo.value = tienda.error
    return
  }
  destinoFoco = destino
  grupoAEliminar.value = null
  estadoAEliminar.value = null
  // Por si la confirmación no devuelve el foco (p. ej. sin animación).
  await enfocarPorId(destino)
}

async function confirmarEliminarGrupo(): Promise<void> {
  const grupo = grupoAEliminar.value
  if (!grupo || procesando.value) return
  procesando.value = true
  const correcto = await tienda.eliminar(grupo.id)
  procesando.value = false
  await terminarEliminacion(correcto, ID_GRUPO_NUEVO)
}

async function confirmarEliminarEstado(): Promise<void> {
  const seleccion = estadoAEliminar.value
  if (!seleccion || procesando.value || sinDestino.value) return
  const destino = conTareas.value ? (moverA.value ?? undefined) : undefined
  procesando.value = true
  const correcto = await tienda.eliminarEstado(seleccion.grupo.id, seleccion.estado.id, destino)
  procesando.value = false
  await terminarEliminacion(correcto, idEstadoNuevo(seleccion.grupo))
}

function alDevolverFoco(evento: Event): void {
  if (destinoFoco === null) return
  evento.preventDefault()
  document.getElementById(destinoFoco)?.focus()
  destinoFoco = null
}

// --- Ordenar estados (botones y arrastrar) ---------------------------------
const reordenando = ref(false)
const anuncio = ref('')
const arrastre = ref<{ idGrupo: number; indice: number } | null>(null)
const destinoArrastre = ref<{ idGrupo: number; indice: number } | null>(null)

// Tras mover con los botones, el foco vuelve al mismo botón del estado movido
// (o al otro si ya está en un extremo); el botón se desactiva mientras se
// guarda y el navegador mandaba el foco al <body>.
async function enfocarBotonDeMover(
  grupo: string,
  estado: string,
  accion: 'Subir' | 'Bajar',
): Promise<void> {
  await nextTick()
  const otra = accion === 'Subir' ? 'Bajar' : 'Subir'
  for (const etiqueta of [
    `${accion} estado ${estado} de ${grupo}`,
    `${otra} estado ${estado} de ${grupo}`,
  ]) {
    const boton = [...document.querySelectorAll<HTMLButtonElement>('button[aria-label]')].find(
      (b) => b.getAttribute('aria-label') === etiqueta && !b.disabled,
    )
    if (boton) {
      boton.focus()
      return
    }
  }
}

async function mover(
  grupo: GrupoEstados,
  origen: number,
  destino: number,
  accion?: 'Subir' | 'Bajar',
): Promise<void> {
  const estado = grupo.estados[origen]
  if (!estado || origen === destino || destino < 0 || destino >= grupo.estados.length) return
  const ids = grupo.estados.map((e) => e.id)
  ids.splice(origen, 1)
  ids.splice(destino, 0, estado.id)
  anuncio.value = ''
  reordenando.value = true
  const correcto = await tienda.reordenarEstados(grupo.id, ids)
  reordenando.value = false
  if (!correcto) return
  const actualizado = tienda.grupos.find((g) => g.id === grupo.id)
  const movido = actualizado?.estados.find((e) => e.id === estado.id)
  if (!actualizado || !movido) return
  anuncio.value = `${movido.nombre} movido a la posición ${movido.posicion}`
  if (accion) await enfocarBotonDeMover(actualizado.nombre, movido.nombre, accion)
}

function alEmpezarArrastre(evento: DragEvent, grupo: GrupoEstados, indice: number): void {
  arrastre.value = { idGrupo: grupo.id, indice }
  if (evento.dataTransfer) {
    evento.dataTransfer.effectAllowed = 'move'
    evento.dataTransfer.setData('text/plain', String(grupo.estados[indice]?.id ?? ''))
  }
}

// Solo se puede soltar sobre estados del mismo grupo.
function alArrastrarSobre(evento: DragEvent, grupo: GrupoEstados, indice: number): void {
  if (arrastre.value?.idGrupo !== grupo.id) return
  evento.preventDefault()
  if (evento.dataTransfer) evento.dataTransfer.dropEffect = 'move'
  destinoArrastre.value = { idGrupo: grupo.id, indice }
}

function alSalirDeFila(grupo: GrupoEstados, indice: number): void {
  const actual = destinoArrastre.value
  if (actual?.idGrupo === grupo.id && actual.indice === indice) destinoArrastre.value = null
}

function alSoltar(evento: DragEvent, grupo: GrupoEstados, indice: number): void {
  evento.preventDefault()
  const origen = arrastre.value
  terminarArrastre()
  if (origen?.idGrupo === grupo.id) void mover(grupo, origen.indice, indice)
}

function terminarArrastre(): void {
  arrastre.value = null
  destinoArrastre.value = null
}

// Dónde se pinta la línea de destino: antes de la fila si el estado sube y
// después si baja, que es donde quedará al soltarlo.
function posicionDestino(grupo: GrupoEstados, indice: number): 'antes' | 'despues' | undefined {
  const origen = arrastre.value
  const destino = destinoArrastre.value
  if (!origen || !destino || origen.idGrupo !== grupo.id || destino.idGrupo !== grupo.id) {
    return undefined
  }
  if (destino.indice !== indice || origen.indice === indice) return undefined
  return indice < origen.indice ? 'antes' : 'despues'
}

function esArrastrado(grupo: GrupoEstados, indice: number): boolean {
  return arrastre.value?.idGrupo === grupo.id && arrastre.value.indice === indice
}
</script>

<template>
  <section class="max-w-3xl">
    <RouterLink
      to="/ajustes"
      class="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 text-sm"
    >
      <ArrowLeft class="size-4" aria-hidden="true" />
      Volver a Ajustes
    </RouterLink>
    <h2 class="mt-2 text-xl font-semibold">Grupos de estados</h2>
    <p class="text-muted-foreground mt-1 text-sm">
      Cada tarea puede tener un grupo y pasar de cualquiera de sus estados a cualquier otro. El
      orden de los estados es el de las columnas del tablero: arrastra un estado o usa los botones
      Subir y Bajar para cambiarlo.
    </p>

    <form
      aria-label="Añadir grupo"
      class="mt-6 flex flex-wrap items-end gap-2"
      novalidate
      @submit.prevent="anadirGrupo"
    >
      <div class="grid min-w-0 flex-1 gap-1.5">
        <Label :for="ID_GRUPO_NUEVO">Nombre del grupo</Label>
        <Input
          :id="ID_GRUPO_NUEVO"
          v-model="nombreGrupoNuevo"
          required
          :maxlength="LONGITUD_MAXIMA"
          autocomplete="off"
          :aria-invalid="errorGrupoNuevo ? true : undefined"
        />
      </div>
      <Button type="submit" :disabled="guardandoGrupo">Añadir grupo</Button>
    </form>
    <p v-if="errorGrupoNuevo" class="text-destructive mt-2 text-sm" role="alert">
      {{ errorGrupoNuevo }}
    </p>

    <p v-if="tienda.error" class="text-destructive mt-4 text-sm" role="alert">{{ tienda.error }}</p>

    <p v-if="!tienda.cargando && grupos.length === 0" class="text-muted-foreground mt-6 text-sm">
      Todavía no hay grupos de estados.
    </p>

    <ul v-else class="mt-6 grid gap-4" aria-label="Grupos de estados">
      <li
        v-for="grupo in grupos"
        :key="grupo.id"
        data-grupo
        class="bg-background grid gap-3 rounded-lg border p-4"
      >
        <form
          v-if="editando('grupo', grupo.id)"
          :aria-label="`Renombrar grupo ${grupo.nombre}`"
          class="flex flex-wrap items-center gap-2"
          novalidate
          @submit.prevent="guardarGrupo(grupo)"
        >
          <Input
            :id="`nombre-grupo-${grupo.id}`"
            v-model="nombreEditando"
            class="min-w-0 flex-1"
            required
            :maxlength="LONGITUD_MAXIMA"
            autocomplete="off"
            :aria-label="`Nuevo nombre del grupo ${grupo.nombre}`"
            :aria-invalid="errorEdicion ? true : undefined"
            @keydown.esc="cancelarEdicion"
          />
          <Button type="submit" size="sm">Guardar</Button>
          <Button type="button" size="sm" variant="outline" @click="cancelarEdicion">
            Cancelar
          </Button>
          <p v-if="errorEdicion" class="text-destructive w-full text-sm" role="alert">
            {{ errorEdicion }}
          </p>
        </form>
        <div v-else class="flex flex-wrap items-center gap-2">
          <h3 class="min-w-0 text-base font-semibold break-words">{{ grupo.nombre }}</h3>
          <span data-tareas-grupo class="text-muted-foreground flex-1 text-sm">{{
            textoTareas(grupo.tareas)
          }}</span>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            :aria-label="`Renombrar grupo ${grupo.nombre}`"
            @click="empezarEdicion('grupo', grupo.id, grupo.nombre)"
          >
            <Pencil aria-hidden="true" />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            :aria-label="`Eliminar grupo ${grupo.nombre}`"
            @click="pedirEliminarGrupo(grupo)"
          >
            <Trash2 aria-hidden="true" />
          </Button>
        </div>

        <p v-if="grupo.estados.length === 0" class="text-muted-foreground text-sm">
          Este grupo todavía no tiene estados.
        </p>
        <ol v-else class="grid gap-2" :aria-label="`Estados de ${grupo.nombre}`">
          <li
            v-for="(estado, indice) in grupo.estados"
            :key="estado.id"
            data-estado
            :data-destino="posicionDestino(grupo, indice)"
            :draggable="editando('estado', estado.id) ? 'false' : 'true'"
            :class="[
              'bg-background flex items-center gap-2 rounded-md border p-2',
              esArrastrado(grupo, indice) && 'opacity-50',
              posicionDestino(grupo, indice) === 'antes' && 'border-t-primary border-t-4',
              posicionDestino(grupo, indice) === 'despues' && 'border-b-primary border-b-4',
            ]"
            @dragstart="alEmpezarArrastre($event, grupo, indice)"
            @dragover="alArrastrarSobre($event, grupo, indice)"
            @dragleave="alSalirDeFila(grupo, indice)"
            @drop="alSoltar($event, grupo, indice)"
            @dragend="terminarArrastre"
          >
            <span class="text-muted-foreground cursor-grab px-1" aria-hidden="true">
              <GripVertical class="size-4" />
            </span>

            <form
              v-if="editando('estado', estado.id)"
              :aria-label="`Renombrar estado ${estado.nombre} de ${grupo.nombre}`"
              class="flex flex-1 flex-wrap items-center gap-2"
              novalidate
              @submit.prevent="guardarEstado(grupo, estado)"
            >
              <Input
                :id="`nombre-estado-${estado.id}`"
                v-model="nombreEditando"
                class="min-w-0 flex-1"
                required
                :maxlength="LONGITUD_MAXIMA"
                autocomplete="off"
                :aria-label="`Nuevo nombre del estado ${estado.nombre} de ${grupo.nombre}`"
                :aria-invalid="errorEdicion ? true : undefined"
                @keydown.esc="cancelarEdicion"
              />
              <Button type="submit" size="sm">Guardar</Button>
              <Button type="button" size="sm" variant="outline" @click="cancelarEdicion">
                Cancelar
              </Button>
              <p v-if="errorEdicion" class="text-destructive w-full text-sm" role="alert">
                {{ errorEdicion }}
              </p>
            </form>

            <template v-else>
              <span data-texto-estado class="min-w-0 break-words">{{ estado.nombre }}</span>
              <span data-tareas-estado class="text-muted-foreground flex-1 text-sm">{{
                textoTareas(estado.tareas)
              }}</span>
              <Button
                type="button"
                size="icon"
                variant="ghost"
                :aria-label="`Subir estado ${estado.nombre} de ${grupo.nombre}`"
                :disabled="indice === 0 || reordenando"
                @click="mover(grupo, indice, indice - 1, 'Subir')"
              >
                <ArrowUp aria-hidden="true" />
              </Button>
              <Button
                type="button"
                size="icon"
                variant="ghost"
                :aria-label="`Bajar estado ${estado.nombre} de ${grupo.nombre}`"
                :disabled="indice === grupo.estados.length - 1 || reordenando"
                @click="mover(grupo, indice, indice + 1, 'Bajar')"
              >
                <ArrowDown aria-hidden="true" />
              </Button>
              <Button
                type="button"
                size="icon"
                variant="ghost"
                :aria-label="`Renombrar estado ${estado.nombre} de ${grupo.nombre}`"
                @click="empezarEdicion('estado', estado.id, estado.nombre)"
              >
                <Pencil aria-hidden="true" />
              </Button>
              <Button
                type="button"
                size="icon"
                variant="ghost"
                :aria-label="`Eliminar estado ${estado.nombre} de ${grupo.nombre}`"
                @click="pedirEliminarEstado(grupo, estado)"
              >
                <Trash2 aria-hidden="true" />
              </Button>
            </template>
          </li>
        </ol>

        <form
          :aria-label="`Añadir estado a ${grupo.nombre}`"
          class="flex flex-wrap items-end gap-2"
          novalidate
          @submit.prevent="anadirEstado(grupo)"
        >
          <div class="grid min-w-0 flex-1 gap-1.5">
            <Label :for="idEstadoNuevo(grupo)">Nuevo estado</Label>
            <Input
              :id="idEstadoNuevo(grupo)"
              v-model="nombresEstadoNuevo[grupo.id]"
              required
              :maxlength="LONGITUD_MAXIMA"
              autocomplete="off"
              :aria-label="`Nuevo estado de ${grupo.nombre}`"
              :aria-invalid="erroresEstadoNuevo[grupo.id] ? true : undefined"
            />
          </div>
          <Button type="submit" variant="outline" :aria-label="`Añadir estado a ${grupo.nombre}`"
            >Añadir estado</Button
          >
          <p
            v-if="erroresEstadoNuevo[grupo.id]"
            class="text-destructive w-full text-sm"
            role="alert"
          >
            {{ erroresEstadoNuevo[grupo.id] }}
          </p>
        </form>
      </li>
    </ul>

    <p class="sr-only" aria-live="polite">{{ anuncio }}</p>

    <DialogoConfirmacion
      :abierto="grupoAEliminar !== null"
      :titulo="`¿Eliminar el grupo ${grupoAEliminar?.nombre ?? ''}?`"
      :descripcion="descripcionEliminarGrupo"
      texto-confirmar="Eliminar"
      :procesando="procesando"
      :error="errorDialogo"
      @update:abierto="alCambiarConfirmacion"
      @confirmar="confirmarEliminarGrupo"
      @cierre-foco="alDevolverFoco"
    />

    <DialogoConfirmacion
      :abierto="estadoAEliminar !== null"
      :titulo="`¿Eliminar el estado ${estadoAEliminar?.estado.nombre ?? ''}?`"
      :descripcion="descripcionEliminarEstado"
      texto-confirmar="Eliminar"
      :procesando="procesando || sinDestino"
      :error="errorDialogo"
      @update:abierto="alCambiarConfirmacion"
      @confirmar="confirmarEliminarEstado"
      @cierre-foco="alDevolverFoco"
    >
      <div v-if="conTareas && !sinDestino" class="grid gap-1.5">
        <Label for="mover-tareas-a">Mover las tareas a</Label>
        <select
          id="mover-tareas-a"
          v-model="moverA"
          class="border-input dark:bg-input/30 bg-background focus-visible:border-ring focus-visible:ring-ring/50 h-9 w-full rounded-md border px-3 py-1 text-base shadow-xs outline-none focus-visible:ring-[3px] md:text-sm"
        >
          <option v-for="estado in otrosEstados" :key="estado.id" :value="estado.id">
            {{ estado.nombre }}
          </option>
        </select>
      </div>
    </DialogoConfirmacion>
  </section>
</template>
