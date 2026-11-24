<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { Input } from '@/componentes/ui/input'
import { validarCodigoServicio } from '@/lib/codigosServicio'
import { cn } from '@/lib/utils'
import { useTiendaCodigosServicio } from '@/stores/codigosServicio'

// Combobox del código de servicio del alta AXAS MS3: al abrirlo lista todos
// los códigos del catálogo, filtra al escribir y ofrece crear el escrito si
// no existe y es válido (con las mismas reglas que la API). Crear lo da de
// alta en el catálogo y lo deja elegido.
const props = defineProps<{
  id: string
  invalido?: boolean
  descritoPor?: string
  deshabilitado?: boolean
}>()
const codigo = defineModel<string>({ required: true })
const emit = defineEmits<{ blur: [] }>()

interface Opcion {
  valor: string
  texto: string
  nueva: boolean
}

const tienda = useTiendaCodigosServicio()
onMounted(() => void tienda.cargar())
const texto = ref(codigo.value)
const abierta = ref(false)
const indiceActivo = ref(-1)
const creando = ref(false)

const idLista = computed(() => `${props.id}-lista`)
const idError = computed(() => `${props.id}-error-creacion`)

function mismo(a: string, b: string): boolean {
  return a.toLocaleLowerCase('es-ES') === b.toLocaleLowerCase('es-ES')
}

const consulta = computed(() => texto.value.trim())
// Si el texto es el código elegido, se listan todos (como al abrirlo).
const filtrando = computed(() => consulta.value !== '' && !mismo(consulta.value, codigo.value))

const validacion = computed(() => (filtrando.value ? validarCodigoServicio(consulta.value) : null))
const errorCreacion = computed(() =>
  validacion.value && 'error' in validacion.value && abierta.value ? validacion.value.error : null,
)

const opciones = computed<Opcion[]>(() => {
  const clave = consulta.value.toLocaleLowerCase('es-ES')
  const lista: Opcion[] = tienda.codigos
    .filter((c) => !filtrando.value || c.nombre.toLocaleLowerCase('es-ES').includes(clave))
    .map((c) => ({ valor: c.nombre, texto: c.nombre, nueva: false }))
  const existe = tienda.codigos.some((c) => mismo(c.nombre, consulta.value))
  if (filtrando.value && !existe && validacion.value && 'nombre' in validacion.value) {
    lista.push({ valor: validacion.value.nombre, texto: `Crear "${consulta.value}"`, nueva: true })
  }
  return lista
})

const listaVisible = computed(() => abierta.value && opciones.value.length > 0)
const idOpcionActiva = computed(() =>
  listaVisible.value && indiceActivo.value >= 0
    ? `${props.id}-opcion-${indiceActivo.value}`
    : undefined,
)

watch(codigo, (valor) => {
  texto.value = valor
})

function alEscribir(evento: Event): void {
  // Se lee del evento: no depende del orden en que se actualiza el v-model.
  texto.value = (evento.target as HTMLInputElement).value
  abierta.value = true
  indiceActivo.value = -1
  // Lo escrito deja de ser un código elegido hasta que se elija o se cree.
  if (!mismo(consulta.value, codigo.value)) codigo.value = ''
}

async function elegir(opcion: Opcion): Promise<void> {
  if (opcion.nueva) {
    creando.value = true
    const creado = await tienda.crear(opcion.valor)
    creando.value = false
    if (!creado) return
    codigo.value = creado.nombre
  } else {
    codigo.value = opcion.valor
  }
  texto.value = codigo.value
  abierta.value = false
  indiceActivo.value = -1
}

function mover(paso: number): void {
  abierta.value = true
  const total = opciones.value.length
  if (total === 0) return
  const inicio = indiceActivo.value < 0 ? (paso > 0 ? -1 : total) : indiceActivo.value
  indiceActivo.value = (inicio + paso + total) % total
}

function alPulsarTecla(evento: KeyboardEvent): void {
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
      const activa = listaVisible.value ? opciones.value[indiceActivo.value] : undefined
      if (activa) {
        evento.preventDefault()
        void elegir(activa)
      }
      break
    }
    case 'Escape':
      if (listaVisible.value) {
        evento.stopPropagation()
        abierta.value = false
        indiceActivo.value = -1
      }
      break
  }
}

function alSalir(): void {
  abierta.value = false
  // Un texto que no se llegó a elegir ni crear se descarta.
  if (!codigo.value) texto.value = ''
  else texto.value = codigo.value
  emit('blur')
}
</script>

<template>
  <div class="relative">
    <Input
      :id="id"
      v-model="texto"
      type="text"
      role="combobox"
      autocomplete="off"
      aria-autocomplete="list"
      :aria-expanded="listaVisible ? 'true' : 'false'"
      :aria-controls="idLista"
      :aria-activedescendant="idOpcionActiva"
      :aria-invalid="invalido || errorCreacion ? 'true' : undefined"
      :aria-describedby="
        [errorCreacion ? idError : '', descritoPor ?? ''].filter(Boolean).join(' ') || undefined
      "
      :aria-busy="creando ? 'true' : undefined"
      :disabled="deshabilitado"
      placeholder="Elige o escribe un código"
      @input="alEscribir"
      @focus="abierta = true"
      @click="abierta = true"
      @keydown="alPulsarTecla"
      @blur="alSalir"
    />
    <ul
      v-if="listaVisible"
      :id="idLista"
      role="listbox"
      aria-label="Códigos de servicio"
      class="bg-popover text-popover-foreground absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-md border p-1 shadow-md"
    >
      <li
        v-for="(opcion, indice) in opciones"
        :id="`${id}-opcion-${indice}`"
        :key="`${opcion.nueva ? 'nueva' : 'codigo'}-${opcion.valor}`"
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
        @click="elegir(opcion)"
      >
        {{ opcion.texto }}
      </li>
    </ul>
    <p v-if="errorCreacion" :id="idError" class="text-destructive mt-1.5 text-sm">
      {{ errorCreacion }}
    </p>
    <p v-if="tienda.error" role="alert" class="text-destructive mt-1.5 text-sm">
      {{ tienda.error }}
    </p>
  </div>
</template>
