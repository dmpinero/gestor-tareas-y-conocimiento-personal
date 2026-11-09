<script setup lang="ts">
import { X } from '@lucide/vue'
import { computed, ref, useId, watch } from 'vue'
import { Input } from '@/componentes/ui/input'
import { cn } from '@/lib/utils'

interface Opcion {
  valor: string
  texto: string
  nueva: boolean
}

const props = withDefaults(
  defineProps<{
    modelValue: string[]
    sugerencias: string[]
    etiqueta: string
    longitudMaxima: number
    id?: string
    placeholder?: string
    textoNuevo?: string
  }>(),
  { id: undefined, placeholder: undefined, textoNuevo: 'Crear "{valor}"' },
)

const emit = defineEmits<{ 'update:modelValue': [valores: string[]] }>()

const idBase = useId()
const idCampo = computed(() => props.id ?? `${idBase}-campo`)
const idLista = `${idBase}-lista`
const idError = `${idBase}-error`

const texto = ref('')
const abierta = ref(false)
const indiceActivo = ref(-1)
const error = ref('')

// Clave de comparación: sin distinguir mayúsculas ni acentos.
function normalizar(valor: string): string {
  return valor
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLocaleLowerCase('es-ES')
}

function mismoValor(a: string, b: string): boolean {
  return a.toLocaleLowerCase('es-ES') === b.toLocaleLowerCase('es-ES')
}

function estaSeleccionado(valor: string): boolean {
  return props.modelValue.some((seleccionado) => mismoValor(seleccionado, valor))
}

const textoRecortado = computed(() => texto.value.trim())

const opciones = computed<Opcion[]>(() => {
  const consulta = textoRecortado.value
  if (!consulta) return []
  const clave = normalizar(consulta)
  const coincidentes: Opcion[] = props.sugerencias
    .filter((sugerencia) => !estaSeleccionado(sugerencia) && normalizar(sugerencia).includes(clave))
    .sort((a, b) => a.localeCompare(b, 'es-ES', { sensitivity: 'base' }))
    .map((sugerencia) => ({ valor: sugerencia, texto: sugerencia, nueva: false }))
  const existe =
    estaSeleccionado(consulta) ||
    props.sugerencias.some((sugerencia) => mismoValor(sugerencia, consulta))
  if (!existe) {
    coincidentes.push({
      valor: consulta,
      texto: props.textoNuevo.replace('{valor}', consulta),
      nueva: true,
    })
  }
  return coincidentes
})

const listaVisible = computed(() => abierta.value && opciones.value.length > 0)

const idOpcionActiva = computed(() =>
  listaVisible.value && indiceActivo.value >= 0
    ? `${idBase}-opcion-${indiceActivo.value}`
    : undefined,
)

watch(texto, () => {
  error.value = ''
  indiceActivo.value = -1
  abierta.value = true
})

function anadir(valor: string) {
  const recortado = valor.trim()
  if (!recortado) return
  if (recortado.length > props.longitudMaxima) {
    error.value = `Máximo ${props.longitudMaxima} caracteres.`
    return
  }
  const existente = props.sugerencias.find((sugerencia) => mismoValor(sugerencia, recortado))
  const definitivo = existente ?? recortado
  if (!estaSeleccionado(definitivo)) {
    emit('update:modelValue', [...props.modelValue, definitivo])
  }
  texto.value = ''
  abierta.value = false
}

function quitar(indice: number) {
  emit(
    'update:modelValue',
    props.modelValue.filter((_, posicion) => posicion !== indice),
  )
}

function mover(paso: number) {
  if (!abierta.value) {
    abierta.value = true
    return
  }
  const total = opciones.value.length
  if (total === 0) return
  const inicio = indiceActivo.value < 0 ? (paso > 0 ? -1 : total) : indiceActivo.value
  indiceActivo.value = (inicio + paso + total) % total
}

function alPulsarTecla(evento: KeyboardEvent) {
  switch (evento.key) {
    case 'ArrowDown':
      evento.preventDefault()
      mover(1)
      break
    case 'ArrowUp':
      evento.preventDefault()
      mover(-1)
      break
    case 'Enter': {
      evento.preventDefault()
      const activa = listaVisible.value ? opciones.value[indiceActivo.value] : undefined
      anadir(activa ? activa.valor : texto.value)
      break
    }
    case 'Escape':
      if (listaVisible.value) {
        // Evita que el Escape cierre también el panel o diálogo contenedor.
        evento.stopPropagation()
        abierta.value = false
        indiceActivo.value = -1
      }
      break
    case 'Backspace':
      if (texto.value === '' && props.modelValue.length > 0) {
        quitar(props.modelValue.length - 1)
      }
      break
  }
}
</script>

<template>
  <div class="grid gap-2">
    <label :for="idCampo" class="text-sm leading-none font-medium select-none">{{
      etiqueta
    }}</label>
    <ul v-if="modelValue.length > 0" class="flex flex-wrap gap-1.5" :aria-label="etiqueta">
      <li
        v-for="(valor, indice) in modelValue"
        :key="valor"
        data-testid="chip"
        class="bg-secondary text-secondary-foreground inline-flex max-w-full items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium"
      >
        <span class="min-w-0 truncate">{{ valor }}</span>
        <button
          type="button"
          class="hover:bg-muted-foreground/20 focus-visible:ring-ring/50 -mr-1 rounded-sm p-0.5 outline-none focus-visible:ring-[3px]"
          :aria-label="`Quitar ${valor}`"
          @click="quitar(indice)"
        >
          <X class="size-3" aria-hidden="true" />
        </button>
      </li>
    </ul>
    <div class="relative">
      <Input
        :id="idCampo"
        v-model="texto"
        type="text"
        role="combobox"
        autocomplete="off"
        aria-autocomplete="list"
        :aria-expanded="listaVisible ? 'true' : 'false'"
        :aria-controls="idLista"
        :aria-activedescendant="idOpcionActiva"
        :aria-invalid="error ? 'true' : undefined"
        :aria-describedby="error ? idError : undefined"
        :placeholder="placeholder"
        @keydown="alPulsarTecla"
        @blur="abierta = false"
      />
      <ul
        v-if="listaVisible"
        :id="idLista"
        role="listbox"
        :aria-label="etiqueta"
        class="bg-popover text-popover-foreground absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-md border p-1 shadow-md"
      >
        <li
          v-for="(opcion, indice) in opciones"
          :id="`${idBase}-opcion-${indice}`"
          :key="`${opcion.nueva ? 'nueva' : 'sugerencia'}-${opcion.valor}`"
          role="option"
          :aria-selected="indice === indiceActivo ? 'true' : 'false'"
          :class="
            cn(
              'cursor-default rounded-sm px-2 py-1.5 text-sm select-none',
              indice === indiceActivo && 'bg-accent text-accent-foreground',
              opcion.nueva && 'text-muted-foreground italic',
            )
          "
          @mousedown.prevent
          @mousemove="indiceActivo = indice"
          @click="anadir(opcion.valor)"
        >
          {{ opcion.texto }}
        </li>
      </ul>
    </div>
    <p v-if="error" :id="idError" role="alert" class="text-destructive text-sm">{{ error }}</p>
  </div>
</template>
