<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import {
  lanzarAlta,
  obtenerConfiguracionAlta,
  obtenerEjecucionAlta,
  responderPreguntaAlta,
  urlCapturaAlta,
  type EjecucionAlta,
  type ResumenConfiguracionAlta,
} from '@/api/altaOportunidades'
import { ErrorApi } from '@/api/cliente'
import PanelPreguntaAlta from '@/componentes/oportunidades/PanelPreguntaAlta.vue'
import { Button } from '@/componentes/ui/button'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'
import {
  aSolicitudAlta,
  INTERVALO_SEGUIMIENTO_MS,
  nombrePrevisto,
  validarCamposAlta,
  type CamposAlta,
} from '@/lib/altaOportunidad'

type Campo = keyof CamposAlta

const CAMPOS: {
  campo: Campo
  etiqueta: string
  ayuda?: string
  modo: 'text' | 'numeric' | 'decimal'
}[] = [
  { campo: 'prj', etiqueta: 'Código del proyecto', ayuda: 'Formato PRJ-XXXXX.', modo: 'text' },
  {
    campo: 'descripcion',
    etiqueta: 'Descripción (opcional)',
    ayuda: 'Si la dejas vacía, se busca en Notion.',
    modo: 'text',
  },
  { campo: 'duracion', etiqueta: 'Duración (meses)', modo: 'numeric' },
  { campo: 'importe', etiqueta: 'Importe total previsto (EUR)', modo: 'decimal' },
  { campo: 'coste', etiqueta: 'Coste total previsto (EUR)', modo: 'decimal' },
]

const ETIQUETAS_ESTADO: Record<EjecucionAlta['estado'], string> = {
  en_curso: 'En curso',
  guardada: 'Guardada',
  no_guardada: 'No guardada',
  error: 'Error',
}

const campos = reactive<CamposAlta>({
  prj: '',
  descripcion: '',
  duracion: '',
  importe: '',
  coste: '',
})
const tocados = reactive<Partial<Record<Campo, boolean>>>({})
const intentado = ref(false)
const configuracion = ref<ResumenConfiguracionAlta | null>(null)
const errorCarga = ref<string | null>(null)
const errorAccion = ref<string | null>(null)
const ejecucion = ref<EjecucionAlta | null>(null)
const enviando = ref(false)
let temporizador: ReturnType<typeof setTimeout> | undefined
let montada = true

const errores = computed(() => validarCamposAlta(campos))
const enCurso = computed(() => ejecucion.value !== null && !ejecucion.value.terminada)
const sePuedeLanzar = computed(
  () => configuracion.value?.valores != null && !enCurso.value && !enviando.value,
)

function errorVisible(campo: Campo): string | undefined {
  return intentado.value || tocados[campo] ? errores.value[campo] : undefined
}

function mensajeDe(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

function porcentajes(lista: { nombre: string; porcentaje: string }[]): string {
  return lista.map((a) => `${a.nombre} (${a.porcentaje} %)`).join(', ')
}

function programarSeguimiento(): void {
  clearTimeout(temporizador)
  if (montada && enCurso.value) temporizador = setTimeout(refrescar, INTERVALO_SEGUIMIENTO_MS)
}

async function refrescar(): Promise<void> {
  try {
    ejecucion.value = await obtenerEjecucionAlta()
  } catch (error) {
    if (!(error instanceof ErrorApi && error.estado === 404)) errorAccion.value = mensajeDe(error)
  }
  programarSeguimiento()
}

async function lanzar(): Promise<void> {
  intentado.value = true
  errorAccion.value = null
  if (Object.keys(errores.value).length > 0) {
    document.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus()
    return
  }
  if (!sePuedeLanzar.value) return
  enviando.value = true
  try {
    ejecucion.value = await lanzarAlta(aSolicitudAlta(campos))
    programarSeguimiento()
  } catch (error) {
    errorAccion.value = mensajeDe(error)
  } finally {
    enviando.value = false
  }
}

async function responder(valor: string): Promise<void> {
  const pregunta = ejecucion.value?.pregunta
  if (!pregunta) return
  enviando.value = true
  errorAccion.value = null
  try {
    ejecucion.value = await responderPreguntaAlta(pregunta.id, valor)
  } catch (error) {
    errorAccion.value = mensajeDe(error)
  } finally {
    enviando.value = false
  }
  programarSeguimiento()
}

onMounted(async () => {
  try {
    configuracion.value = await obtenerConfiguracionAlta()
  } catch (error) {
    errorCarga.value = mensajeDe(error)
  }
  // Recupera el alta en curso si se recarga la página a mitad.
  await refrescar()
})

onBeforeUnmount(() => {
  montada = false
  clearTimeout(temporizador)
})
</script>

<template>
  <section class="grid max-w-3xl gap-6">
    <div>
      <h2 class="text-xl font-semibold">Oportunidades</h2>
      <p class="text-muted-foreground mt-1 text-sm">
        Alta automática de una oportunidad en Digital Desktop. Rellena los campos variables, revisa
        el resumen y lanza el alta: se abrirá una ventana del navegador y aquí verás cada paso. Nada
        se guarda sin que pulses «Guardar».
      </p>
    </div>

    <div
      v-if="errorCarga || configuracion?.error"
      role="alert"
      class="border-destructive text-destructive rounded-md border p-3 text-sm"
    >
      <template v-if="errorCarga">
        No se pudo contactar con el servicio de altas: {{ errorCarga }}
      </template>
      <template v-else>No se puede lanzar el alta: {{ configuracion?.error }}</template>
    </div>

    <form id="formulario-alta" novalidate class="grid gap-4" @submit.prevent="lanzar">
      <fieldset :disabled="enCurso" class="grid gap-4 sm:grid-cols-2">
        <legend class="sr-only">Campos variables de la oportunidad</legend>
        <div
          v-for="definicion in CAMPOS"
          :key="definicion.campo"
          class="grid content-start gap-1.5"
          :class="{ 'sm:col-span-2': definicion.campo === 'descripcion' }"
        >
          <Label :for="`alta-${definicion.campo}`">{{ definicion.etiqueta }}</Label>
          <Input
            :id="`alta-${definicion.campo}`"
            v-model="campos[definicion.campo]"
            :inputmode="definicion.modo"
            autocomplete="off"
            :aria-invalid="errorVisible(definicion.campo) ? 'true' : undefined"
            :aria-describedby="
              [
                errorVisible(definicion.campo) ? `error-alta-${definicion.campo}` : '',
                definicion.ayuda ? `ayuda-alta-${definicion.campo}` : '',
              ]
                .filter(Boolean)
                .join(' ') || undefined
            "
            @blur="tocados[definicion.campo] = true"
          />
          <p
            v-if="definicion.ayuda"
            :id="`ayuda-alta-${definicion.campo}`"
            class="text-muted-foreground text-xs"
          >
            {{ definicion.ayuda }}
          </p>
          <p
            v-if="errorVisible(definicion.campo)"
            :id="`error-alta-${definicion.campo}`"
            class="text-destructive text-sm"
          >
            {{ errorVisible(definicion.campo) }}
          </p>
        </div>
      </fieldset>
    </form>

    <section aria-labelledby="titulo-resumen-alta" class="bg-card rounded-lg border p-4">
      <h3 id="titulo-resumen-alta" class="font-semibold">Qué se va a crear</h3>
      <dl class="mt-3 grid gap-x-4 gap-y-1 text-sm sm:grid-cols-[auto_1fr]">
        <dt class="text-muted-foreground">Nombre</dt>
        <dd>{{ nombrePrevisto(campos.prj || 'PRJ-XXXXX', campos.descripcion) }}</dd>
        <dt class="text-muted-foreground">Fecha límite</dt>
        <dd>{{ configuracion?.fecha_limite ?? '—' }}</dd>
        <dt class="text-muted-foreground">Fecha de inicio</dt>
        <dd>{{ configuracion?.fecha_inicio ?? '—' }}</dd>
        <template v-if="configuracion?.valores">
          <dt class="text-muted-foreground">Responsable</dt>
          <dd>{{ configuracion.valores.perfil }}</dd>
          <dt class="text-muted-foreground">Cliente</dt>
          <dd>{{ configuracion.valores.cliente }}</dd>
          <dt class="text-muted-foreground">Grupo y tipo</dt>
          <dd>{{ configuracion.valores.grupo }} · {{ configuracion.valores.tipo }}</dd>
          <dt class="text-muted-foreground">Segmentación</dt>
          <dd>{{ configuracion.valores.segmentacion }}</dd>
          <dt class="text-muted-foreground">Fase y probabilidad</dt>
          <dd>{{ configuracion.valores.fase }} · {{ configuracion.valores.probabilidad }} %</dd>
          <dt class="text-muted-foreground">Tipo de servicio</dt>
          <dd>{{ configuracion.valores.tipo_servicio }}</dd>
          <dt class="text-muted-foreground">Líneas de negocio</dt>
          <dd>{{ porcentajes(configuracion.valores.lineas_negocio) }}</dd>
          <dt class="text-muted-foreground">Comunidades</dt>
          <dd>{{ porcentajes(configuracion.valores.comunidades) }}</dd>
        </template>
      </dl>
    </section>

    <div class="flex flex-wrap items-center gap-3">
      <Button type="submit" form="formulario-alta" :disabled="!sePuedeLanzar">
        Crear oportunidad
      </Button>
      <p class="text-muted-foreground text-sm">
        Necesita la VPN corporativa. La primera vez inicia sesión en la ventana del navegador.
      </p>
    </div>

    <div
      v-if="errorAccion"
      role="alert"
      class="border-destructive text-destructive rounded-md border p-3 text-sm"
    >
      {{ errorAccion }}
    </div>

    <section v-if="ejecucion" aria-labelledby="titulo-avance-alta" class="grid gap-4">
      <h3 id="titulo-avance-alta" class="font-semibold">
        Avance del alta de {{ ejecucion.prj }}: {{ ETIQUETAS_ESTADO[ejecucion.estado] }}
      </h3>
      <ol aria-live="polite" class="grid list-decimal gap-1 pl-6 text-sm">
        <li v-for="(paso, indice) in ejecucion.pasos" :key="indice">{{ paso }}</li>
      </ol>

      <PanelPreguntaAlta
        v-if="ejecucion.pregunta"
        :pregunta="ejecucion.pregunta"
        :enviando="enviando"
        @responder="responder"
      />

      <p
        v-if="ejecucion.terminada && ejecucion.mensaje_final"
        role="status"
        class="rounded-md border p-3 text-sm"
        :class="ejecucion.estado === 'error' ? 'border-destructive text-destructive' : ''"
      >
        {{ ejecucion.mensaje_final }}
      </p>

      <img
        v-if="ejecucion.hay_captura"
        :src="urlCapturaAlta(ejecucion.id)"
        :alt="`Captura del resultado del alta de ${ejecucion.prj}`"
        class="max-w-full rounded-md border"
      />
    </section>
  </section>
</template>
