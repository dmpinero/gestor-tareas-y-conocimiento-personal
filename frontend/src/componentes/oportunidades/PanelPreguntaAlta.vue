<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { PreguntaAlta } from '@/api/altaOportunidades'
import { Button } from '@/componentes/ui/button'

const props = defineProps<{ pregunta: PreguntaAlta; enviando: boolean }>()
const emit = defineEmits<{ responder: [valor: string] }>()

const titulo = ref<HTMLElement | null>(null)

const TITULOS: Record<PreguntaAlta['tipo'], string> = {
  inicio_sesion: 'Esperando el inicio de sesión',
  duplicado: 'La oportunidad ya existe',
  intervencion_manual: 'Hace falta que actúes en el navegador',
  guardar: '¿Guardar la oportunidad?',
}

// Cada pregunta nueva recibe el foco para que se anuncie y se pueda responder
// con el teclado sin buscarla.
watch(
  () => props.pregunta.id,
  async () => {
    await nextTick()
    titulo.value?.focus()
  },
  { immediate: true },
)

function variante(valor: string): 'default' | 'outline' {
  return valor === 'no' || valor === 'no_guardar' ? 'outline' : 'default'
}
</script>

<template>
  <section
    aria-labelledby="titulo-pregunta-alta"
    class="border-primary/40 bg-card grid gap-3 rounded-lg border-2 p-4 shadow-xs"
  >
    <h3 id="titulo-pregunta-alta" ref="titulo" tabindex="-1" class="font-semibold outline-none">
      {{ TITULOS[pregunta.tipo] }}
    </h3>
    <p>{{ pregunta.mensaje }}</p>
    <pre
      v-if="pregunta.detalle"
      class="bg-muted max-h-96 overflow-auto rounded-md p-3 text-sm whitespace-pre-wrap"
      >{{ pregunta.detalle }}</pre>
    <div v-if="pregunta.opciones.length" class="flex flex-wrap gap-2">
      <Button
        v-for="opcion in pregunta.opciones"
        :key="opcion.valor"
        type="button"
        :variant="variante(opcion.valor)"
        :disabled="enviando"
        @click="emit('responder', opcion.valor)"
      >
        {{ opcion.etiqueta }}
      </Button>
    </div>
  </section>
</template>
