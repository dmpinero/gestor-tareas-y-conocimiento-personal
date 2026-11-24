<script setup lang="ts">
import { ArrowLeft, Pencil, Trash2 } from '@lucide/vue'
import { nextTick, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import type { CodigoServicio } from '@/api/tipos'
import DialogoConfirmacion from '@/componentes/compartido/DialogoConfirmacion.vue'
import { Button } from '@/componentes/ui/button'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'
import { validarCodigoServicio } from '@/lib/codigosServicio'
import { useTiendaCodigosServicio } from '@/stores/codigosServicio'

// Catálogo de códigos de servicio de Ajustes (como el de subestados). Se eligen
// al dar de alta una oportunidad AXAS MS3, donde también se pueden crear.
const ID_NUEVO = 'nombre-codigo-servicio-nuevo'

const tienda = useTiendaCodigosServicio()

onMounted(() => {
  void tienda.cargar()
})

async function enfocarPorId(id: string): Promise<void> {
  await nextTick()
  document.getElementById(id)?.focus()
}

// --- Alta ---------------------------------------------------------------------
// Sin `maxlength` en los campos: así se ve el mensaje del límite en vez de cortar
// lo que se pega.
const nombreNuevo = ref('')
const errorNuevo = ref<string | null>(null)
const guardando = ref(false)

async function anadir(): Promise<void> {
  const validacion = validarCodigoServicio(nombreNuevo.value)
  errorNuevo.value = 'error' in validacion ? validacion.error : null
  if ('error' in validacion) return
  guardando.value = true
  const creado = await tienda.crear(validacion.nombre)
  guardando.value = false
  if (creado) nombreNuevo.value = ''
}

// --- Renombrar en línea ---------------------------------------------------------
const idEditando = ref<number | null>(null)
const nombreEditando = ref('')
const errorEdicion = ref<string | null>(null)

async function empezarEdicion(codigo: CodigoServicio): Promise<void> {
  idEditando.value = codigo.id
  nombreEditando.value = codigo.nombre
  errorEdicion.value = null
  await enfocarPorId(`nombre-codigo-servicio-${codigo.id}`)
}

function cancelarEdicion(): void {
  idEditando.value = null
  errorEdicion.value = null
}

async function guardar(codigo: CodigoServicio): Promise<void> {
  const validacion = validarCodigoServicio(nombreEditando.value)
  errorEdicion.value = 'error' in validacion ? validacion.error : null
  if ('error' in validacion) return
  if (await tienda.renombrar(codigo.id, validacion.nombre)) idEditando.value = null
}

// --- Eliminar, con confirmación ----------------------------------------------
// El botón que abrió la confirmación desaparece al borrar: el foco va al campo
// de alta en vez de perderse en el <body>.
const aEliminar = ref<CodigoServicio | null>(null)
const procesando = ref(false)
const errorDialogo = ref<string | null>(null)
let devolverFoco = false

function pedirEliminar(codigo: CodigoServicio): void {
  errorDialogo.value = null
  aEliminar.value = codigo
}

function alCambiarConfirmacion(abierta: boolean): void {
  if (abierta || procesando.value) return
  aEliminar.value = null
}

async function confirmarEliminar(): Promise<void> {
  const codigo = aEliminar.value
  if (!codigo || procesando.value) return
  procesando.value = true
  const correcto = await tienda.eliminar(codigo.id)
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
    <h2 class="mt-2 text-xl font-semibold">Códigos de servicio</h2>
    <p class="text-muted-foreground mt-1 text-sm">
      Se eligen al dar de alta una oportunidad AXAS MS3, que usa sus 2 últimos caracteres. También
      se crean al escribir uno nuevo en ese formulario.
    </p>

    <form
      aria-label="Añadir código de servicio"
      class="mt-6 flex flex-wrap items-end gap-2"
      novalidate
      @submit.prevent="anadir"
    >
      <div class="grid min-w-0 flex-1 gap-1.5">
        <Label :for="ID_NUEVO">Código de servicio</Label>
        <Input
          :id="ID_NUEVO"
          v-model="nombreNuevo"
          required
          autocomplete="off"
          placeholder="AXAS0024"
          :aria-invalid="errorNuevo ? true : undefined"
        />
      </div>
      <Button type="submit" :disabled="guardando">Añadir código</Button>
    </form>
    <p v-if="errorNuevo" class="text-destructive mt-2 text-sm" role="alert">{{ errorNuevo }}</p>

    <p v-if="tienda.error" class="text-destructive mt-4 text-sm" role="alert">{{ tienda.error }}</p>

    <p
      v-if="!tienda.cargando && tienda.codigos.length === 0"
      class="text-muted-foreground mt-6 text-sm"
    >
      Todavía no hay códigos de servicio.
    </p>

    <ul v-else class="mt-6 grid gap-2" aria-label="Códigos de servicio">
      <li
        v-for="codigo in tienda.codigos"
        :key="codigo.id"
        data-codigo-servicio
        class="bg-background flex items-center gap-2 rounded-md border p-2"
      >
        <form
          v-if="idEditando === codigo.id"
          :aria-label="`Renombrar código de servicio ${codigo.nombre}`"
          class="flex flex-1 flex-wrap items-center gap-2"
          novalidate
          @submit.prevent="guardar(codigo)"
        >
          <Input
            :id="`nombre-codigo-servicio-${codigo.id}`"
            v-model="nombreEditando"
            class="min-w-0 flex-1"
            required
            autocomplete="off"
            :aria-label="`Nuevo nombre del código de servicio ${codigo.nombre}`"
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
          <span
            data-testid="nombre-codigo-servicio"
            class="min-w-0 flex-1 px-1 font-mono text-sm [overflow-wrap:anywhere]"
            >{{ codigo.nombre }}</span
          >
          <Button
            type="button"
            size="icon"
            variant="ghost"
            :aria-label="`Renombrar código de servicio ${codigo.nombre}`"
            @click="empezarEdicion(codigo)"
          >
            <Pencil aria-hidden="true" />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            :aria-label="`Eliminar código de servicio ${codigo.nombre}`"
            @click="pedirEliminar(codigo)"
          >
            <Trash2 aria-hidden="true" />
          </Button>
        </template>
      </li>
    </ul>

    <DialogoConfirmacion
      :abierto="aEliminar !== null"
      :titulo="`¿Eliminar el código de servicio ${aEliminar?.nombre ?? ''}?`"
      descripcion="Dejará de aparecer al dar de alta oportunidades AXAS MS3."
      texto-confirmar="Eliminar"
      :procesando="procesando"
      :error="errorDialogo"
      @update:abierto="alCambiarConfirmacion"
      @confirmar="confirmarEliminar"
      @cierre-foco="alDevolverFoco"
    />
  </section>
</template>
