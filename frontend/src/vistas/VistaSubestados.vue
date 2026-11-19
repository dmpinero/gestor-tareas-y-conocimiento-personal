<script setup lang="ts">
import { ArrowLeft, Pencil, Trash2 } from '@lucide/vue'
import { nextTick, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import type { ElementoCatalogo } from '@/api/tipos'
import DialogoConfirmacion from '@/componentes/compartido/DialogoConfirmacion.vue'
import { Button } from '@/componentes/ui/button'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'
import { CLASE_PILDORA, colorEtiqueta } from '@/lib/coloresTarea'
import { useTiendaSubestados } from '@/stores/subestados'

// Catálogo de subestados de Ajustes: como mucho uno por tarea. También se dan de
// alta desde el formulario de la tarea, como las etiquetas.
const LONGITUD_MAXIMA = 50
const ID_NUEVO = 'nombre-subestado-nuevo'

const tienda = useTiendaSubestados()

onMounted(() => {
  void tienda.cargar()
})

// Devuelve el mensaje de error del nombre recortado, o `null` si es válido.
function validarNombre(nombre: string): string | null {
  if (nombre.length === 0) return 'El nombre del subestado es obligatorio.'
  if (nombre.length > LONGITUD_MAXIMA) {
    return `El nombre del subestado no puede superar los ${LONGITUD_MAXIMA} caracteres.`
  }
  return null
}

async function enfocarPorId(id: string): Promise<void> {
  await nextTick()
  document.getElementById(id)?.focus()
}

// --- Alta ---------------------------------------------------------------------
const nombreNuevo = ref('')
const errorNuevo = ref<string | null>(null)
const guardando = ref(false)

async function anadir(): Promise<void> {
  const nombre = nombreNuevo.value.trim()
  errorNuevo.value = validarNombre(nombre)
  if (errorNuevo.value) return
  guardando.value = true
  const correcto = await tienda.crear(nombre)
  guardando.value = false
  if (correcto) nombreNuevo.value = ''
}

// --- Renombrar en línea ---------------------------------------------------------
const idEditando = ref<number | null>(null)
const nombreEditando = ref('')
const errorEdicion = ref<string | null>(null)

async function empezarEdicion(subestado: ElementoCatalogo): Promise<void> {
  idEditando.value = subestado.id
  nombreEditando.value = subestado.nombre
  errorEdicion.value = null
  await enfocarPorId(`nombre-subestado-${subestado.id}`)
}

function cancelarEdicion(): void {
  idEditando.value = null
  errorEdicion.value = null
}

async function guardar(subestado: ElementoCatalogo): Promise<void> {
  const nombre = nombreEditando.value.trim()
  errorEdicion.value = validarNombre(nombre)
  if (errorEdicion.value) return
  if (await tienda.renombrar(subestado.id, nombre)) idEditando.value = null
}

// --- Eliminar, con confirmación ----------------------------------------------
// El botón que abrió la confirmación desaparece al borrar: el foco va al campo
// de alta en vez de perderse en el <body>.
const aEliminar = ref<ElementoCatalogo | null>(null)
const procesando = ref(false)
const errorDialogo = ref<string | null>(null)
let devolverFoco = false

function pedirEliminar(subestado: ElementoCatalogo): void {
  errorDialogo.value = null
  aEliminar.value = subestado
}

function alCambiarConfirmacion(abierta: boolean): void {
  if (abierta || procesando.value) return
  aEliminar.value = null
}

async function confirmarEliminar(): Promise<void> {
  const subestado = aEliminar.value
  if (!subestado || procesando.value) return
  procesando.value = true
  const correcto = await tienda.eliminar(subestado.id)
  procesando.value = false
  if (!correcto) {
    errorDialogo.value = tienda.error
    return
  }
  devolverFoco = true
  aEliminar.value = null
  await enfocarPorId(ID_NUEVO)
}

function alDevolverFoco(evento: Event): void {
  if (!devolverFoco) return
  evento.preventDefault()
  document.getElementById(ID_NUEVO)?.focus()
  devolverFoco = false
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
    <h2 class="mt-2 text-xl font-semibold">Subestados</h2>
    <p class="text-muted-foreground mt-1 text-sm">
      Cada tarea puede tener como mucho un subestado. También se crean al escribir uno nuevo en el
      formulario de la tarea.
    </p>

    <form
      aria-label="Añadir subestado"
      class="mt-6 flex flex-wrap items-end gap-2"
      novalidate
      @submit.prevent="anadir"
    >
      <div class="grid min-w-0 flex-1 gap-1.5">
        <Label :for="ID_NUEVO">Nombre del subestado</Label>
        <Input
          :id="ID_NUEVO"
          v-model="nombreNuevo"
          required
          :maxlength="LONGITUD_MAXIMA"
          autocomplete="off"
          :aria-invalid="errorNuevo ? true : undefined"
        />
      </div>
      <Button type="submit" :disabled="guardando">Añadir subestado</Button>
    </form>
    <p v-if="errorNuevo" class="text-destructive mt-2 text-sm" role="alert">{{ errorNuevo }}</p>

    <p v-if="tienda.error" class="text-destructive mt-4 text-sm" role="alert">{{ tienda.error }}</p>

    <p
      v-if="!tienda.cargando && tienda.subestados.length === 0"
      class="text-muted-foreground mt-6 text-sm"
    >
      Todavía no hay subestados.
    </p>

    <ul v-else class="mt-6 grid gap-2" aria-label="Subestados">
      <li
        v-for="subestado in tienda.subestados"
        :key="subestado.id"
        data-subestado
        class="bg-background flex items-center gap-2 rounded-md border p-2"
      >
        <form
          v-if="idEditando === subestado.id"
          :aria-label="`Renombrar subestado ${subestado.nombre}`"
          class="flex flex-1 flex-wrap items-center gap-2"
          novalidate
          @submit.prevent="guardar(subestado)"
        >
          <Input
            :id="`nombre-subestado-${subestado.id}`"
            v-model="nombreEditando"
            class="min-w-0 flex-1"
            required
            :maxlength="LONGITUD_MAXIMA"
            autocomplete="off"
            :aria-label="`Nuevo nombre del subestado ${subestado.nombre}`"
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
          <span class="min-w-0 flex-1">
            <span
              data-testid="pildora-subestado"
              :class="`${CLASE_PILDORA} ${colorEtiqueta(subestado.nombre)} [overflow-wrap:anywhere]`"
              >{{ subestado.nombre }}</span
            >
          </span>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            :aria-label="`Renombrar subestado ${subestado.nombre}`"
            @click="empezarEdicion(subestado)"
          >
            <Pencil aria-hidden="true" />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            :aria-label="`Eliminar subestado ${subestado.nombre}`"
            @click="pedirEliminar(subestado)"
          >
            <Trash2 aria-hidden="true" />
          </Button>
        </template>
      </li>
    </ul>

    <DialogoConfirmacion
      :abierto="aEliminar !== null"
      :titulo="`¿Eliminar el subestado ${aEliminar?.nombre ?? ''}?`"
      descripcion="Las tareas que lo tengan quedarán sin subestado."
      texto-confirmar="Eliminar"
      :procesando="procesando"
      :error="errorDialogo"
      @update:abierto="alCambiarConfirmacion"
      @confirmar="confirmarEliminar"
      @cierre-foco="alDevolverFoco"
    />
  </section>
</template>
