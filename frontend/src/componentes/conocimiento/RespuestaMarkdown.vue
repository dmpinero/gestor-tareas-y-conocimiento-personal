<script setup lang="ts">
import { ref, watch } from 'vue'

import { htmlRespuesta } from './markdownRespuesta'

const props = defineProps<{ texto: string }>()

const html = ref<string | null>(null)
// Durante el streaming el texto cambia con cada trozo: solo se aplica el HTML
// de la última versión pedida, aunque las anteriores terminen después.
let version = 0

watch(
  () => props.texto,
  async (texto) => {
    const propia = ++version
    const resultado = await htmlRespuesta(texto)
    if (propia === version) html.value = resultado
  },
  { immediate: true },
)
</script>

<template>
  <!-- HTML saneado con DOMPurify (ver markdownRespuesta.ts). -->
  <div
    v-if="html !== null"
    class="space-y-2 break-words [&_a]:text-primary [&_a]:underline [&_a]:underline-offset-2 [&_code]:bg-muted [&_code]:rounded [&_code]:px-1 [&_h1]:font-semibold [&_h2]:font-semibold [&_h3]:font-semibold [&_ol]:list-decimal [&_ol]:pl-5 [&_pre]:bg-muted [&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:p-2 [&_ul]:list-disc [&_ul]:pl-5 [&_blockquote]:border-l-2 [&_blockquote]:pl-3"
    v-html="html"
  />
  <p v-else class="whitespace-pre-wrap break-words">{{ props.texto }}</p>
</template>
