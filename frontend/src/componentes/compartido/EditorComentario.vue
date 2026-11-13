<script setup lang="ts">
/**
 * Editor de texto enriquecido para los comentarios (Tiptap): negrita, cursiva,
 * subrayado, tachado, color de texto, resaltado, listas y enlaces.
 *
 * `v-model` es el HTML del contenido (cadena vacía si no hay nada escrito).
 * El área editable es un `textbox` multilínea con el nombre `etiqueta` y el
 * `id` recibido, para poder enfocarlo desde fuera. Ctrl/Cmd+Enter emite
 * `enviar`. `limite` es el máximo de caracteres visibles. El área editable
 * se crea tras el montaje: para enfocarla al aparecer, usar `autoenfoque`.
 */
import {
  Baseline,
  Bold,
  Highlighter,
  Italic,
  Link as IconoEnlace,
  List,
  ListOrdered,
  Strikethrough,
  Underline,
} from '@lucide/vue'
import { Highlight } from '@tiptap/extension-highlight'
import { Color, TextStyle } from '@tiptap/extension-text-style'
import { CharacterCount, Placeholder } from '@tiptap/extensions'
import { StarterKit } from '@tiptap/starter-kit'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import { onBeforeUnmount, ref, useTemplateRef, watch, type Component } from 'vue'

import { Button } from '@/componentes/ui/button'
import { Input } from '@/componentes/ui/input'
import { Popover, PopoverContent, PopoverTrigger } from '@/componentes/ui/popover'
import { CLASES_CONTENIDO_COMENTARIO } from '@/lib/htmlComentario'
import { cn } from '@/lib/utils'

const props = withDefaults(
  defineProps<{
    modelValue: string
    etiqueta: string
    id?: string
    placeholder?: string
    limite?: number
    describedBy?: string
    invalido?: boolean
    soloLectura?: boolean
    /** Enfoca el editor (al final del texto) en cuanto se crea. */
    autoenfoque?: boolean
  }>(),
  { limite: 500 },
)
const emit = defineEmits<{ 'update:modelValue': [html: string]; enviar: [] }>()

// Colores legibles tanto en modo claro como en oscuro.
const COLORES_TEXTO = [
  { nombre: 'Rojo', valor: '#dc2626' },
  { nombre: 'Naranja', valor: '#ea580c' },
  { nombre: 'Verde', valor: '#16a34a' },
  { nombre: 'Azul', valor: '#2563eb' },
  { nombre: 'Morado', valor: '#9333ea' },
  { nombre: 'Gris', valor: '#6b7280' },
]
// Fondos claros: el texto resaltado se pinta oscuro (ver CLASES_CONTENIDO_COMENTARIO).
const COLORES_RESALTADO = [
  { nombre: 'Amarillo', valor: '#fef08a' },
  { nombre: 'Verde', valor: '#bbf7d0' },
  { nombre: 'Azul', valor: '#bfdbfe' },
  { nombre: 'Rosa', valor: '#fbcfe8' },
  { nombre: 'Naranja', valor: '#fed7aa' },
  { nombre: 'Morado', valor: '#e9d5ff' },
]
const URL_PERMITIDA = /^(?:https?:\/\/|mailto:)\S+$/i

function atributosEditable(): Record<string, string> {
  const atributos: Record<string, string> = {
    role: 'textbox',
    'aria-multiline': 'true',
    'aria-label': props.etiqueta,
    class: cn(
      'min-h-12 w-full px-3 py-2 text-base outline-none md:text-sm',
      CLASES_CONTENIDO_COMENTARIO,
      '[&_p.is-editor-empty:first-child]:before:text-muted-foreground [&_p.is-editor-empty:first-child]:before:pointer-events-none [&_p.is-editor-empty:first-child]:before:float-left [&_p.is-editor-empty:first-child]:before:h-0 [&_p.is-editor-empty:first-child]:before:content-[attr(data-placeholder)]',
    ),
  }
  if (props.id) atributos.id = props.id
  if (props.describedBy) atributos['aria-describedby'] = props.describedBy
  if (props.invalido) atributos['aria-invalid'] = 'true'
  if (props.soloLectura) atributos['aria-readonly'] = 'true'
  return atributos
}

const editor = useEditor({
  content: props.modelValue,
  editable: !props.soloLectura,
  extensions: [
    StarterKit.configure({
      blockquote: false,
      code: false,
      codeBlock: false,
      heading: false,
      horizontalRule: false,
      trailingNode: false,
      link: {
        openOnClick: false,
        autolink: true,
        protocols: ['http', 'https', 'mailto'],
        isAllowedUri: (url) => URL_PERMITIDA.test(url),
        HTMLAttributes: { rel: 'noopener noreferrer nofollow', target: '_blank' },
      },
    }),
    TextStyle,
    Color,
    Highlight.configure({ multicolor: true }),
    CharacterCount.configure({ limit: props.limite }),
    Placeholder.configure({ placeholder: props.placeholder ?? '' }),
  ],
  editorProps: {
    attributes: atributosEditable(),
    handleKeyDown: (_vista, evento) => {
      if (evento.key === 'Escape') {
        reenviarEscape(evento)
        return true
      }
      if (evento.key !== 'Enter' || !(evento.ctrlKey || evento.metaKey)) return false
      evento.preventDefault()
      emit('enviar')
      return true
    },
  },
  // Sin desplazar: el campo aparece donde se ha pulsado "Editar".
  onCreate: ({ editor: actual }) => {
    if (props.autoenfoque) actual.commands.focus('end', { scrollIntoView: false })
  },
  onUpdate: ({ editor: actual }) => {
    emit('update:modelValue', actual.isEmpty ? '' : actual.getHTML())
  },
})

function valorActual(): string {
  const actual = editor.value
  if (!actual) return ''
  return actual.isEmpty ? '' : actual.getHTML()
}

watch(
  () => props.modelValue,
  (valor) => {
    if (!editor.value || valor === valorActual()) return
    editor.value.commands.setContent(valor, { emitUpdate: false })
  },
)

watch(
  () => [props.etiqueta, props.id, props.describedBy, props.invalido, props.soloLectura],
  () => {
    if (!editor.value) return
    editor.value.setEditable(!props.soloLectura, false)
    editor.value.setOptions({
      editorProps: { ...editor.value.options.editorProps, attributes: atributosEditable() },
    })
  },
)

onBeforeUnmount(() => editor.value?.destroy())

interface BotonFormato {
  nombre: string
  icono: Component
  activo: () => boolean
  alternar: () => void
}

function cadena() {
  return editor.value!.chain().focus()
}

const botonesFormato: BotonFormato[] = [
  {
    nombre: 'Negrita',
    icono: Bold,
    activo: () => !!editor.value?.isActive('bold'),
    alternar: () => cadena().toggleBold().run(),
  },
  {
    nombre: 'Cursiva',
    icono: Italic,
    activo: () => !!editor.value?.isActive('italic'),
    alternar: () => cadena().toggleItalic().run(),
  },
  {
    nombre: 'Subrayado',
    icono: Underline,
    activo: () => !!editor.value?.isActive('underline'),
    alternar: () => cadena().toggleUnderline().run(),
  },
  {
    nombre: 'Tachado',
    icono: Strikethrough,
    activo: () => !!editor.value?.isActive('strike'),
    alternar: () => cadena().toggleStrike().run(),
  },
]
const botonesLista: BotonFormato[] = [
  {
    nombre: 'Lista con viñetas',
    icono: List,
    activo: () => !!editor.value?.isActive('bulletList'),
    alternar: () => cadena().toggleBulletList().run(),
  },
  {
    nombre: 'Lista numerada',
    icono: ListOrdered,
    activo: () => !!editor.value?.isActive('orderedList'),
    alternar: () => cadena().toggleOrderedList().run(),
  },
]

// Funciones y no `computed`: el estado del editor no es reactivo para Vue,
// pero el componente se vuelve a pintar en cada transacción.
const colorActivo = () => !!editor.value?.getAttributes('textStyle').color
const resaltadoActivo = () => !!editor.value?.isActive('highlight')
const enlaceActivo = () => !!editor.value?.isActive('link')

// ProseMirror cancela el Escape (preventDefault) y las modales de reka-ui no se
// cierran con un Escape cancelado. Se corta el original y se envía uno nuevo,
// sin cancelar, desde la raíz del componente: así sigue llegando a quien lo
// escucha (p. ej. cancelar la edición de un comentario) y a la modal.
const raiz = useTemplateRef<HTMLElement>('raiz')

function reenviarEscape(evento: KeyboardEvent): void {
  evento.stopPropagation()
  raiz.value?.dispatchEvent(
    new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }),
  )
}

const abiertoColor = ref(false)
const abiertoResaltado = ref(false)
const abiertoEnlace = ref(false)

function aplicarColor(valor: string | null): void {
  if (valor) cadena().setColor(valor).run()
  else cadena().unsetColor().run()
  abiertoColor.value = false
}

function aplicarResaltado(valor: string | null): void {
  if (valor) cadena().setHighlight({ color: valor }).run()
  else cadena().unsetHighlight().run()
  abiertoResaltado.value = false
}

const url = ref('')
const errorUrl = ref<string | null>(null)

watch(abiertoEnlace, (abierto) => {
  if (!abierto) return
  url.value = (editor.value?.getAttributes('link').href as string | undefined) ?? ''
  errorUrl.value = null
})

function aplicarEnlace(): void {
  const valor = url.value.trim()
  if (!URL_PERMITIDA.test(valor)) {
    errorUrl.value = 'Introduce una URL que empiece por http://, https:// o mailto:'
    return
  }
  const actual = editor.value!
  if (actual.state.selection.empty && !enlaceActivo()) {
    // Sin texto seleccionado se inserta la propia URL como enlace.
    cadena()
      .insertContent({
        type: 'text',
        text: valor,
        marks: [{ type: 'link', attrs: { href: valor } }],
      })
      .run()
  } else {
    cadena().extendMarkRange('link').setLink({ href: valor }).run()
  }
  abiertoEnlace.value = false
}

function quitarEnlace(): void {
  cadena().extendMarkRange('link').unsetLink().run()
  abiertoEnlace.value = false
}

defineExpose({ editor })
</script>

<template>
  <div
    ref="raiz"
    data-slot="editor-comentario"
    class="border-input dark:bg-input/30 focus-within:border-ring focus-within:ring-ring/50 has-[[aria-invalid=true]]:border-destructive flex w-full min-w-0 flex-col rounded-md border bg-transparent shadow-xs transition-[color,box-shadow] focus-within:ring-[3px]"
  >
    <div
      role="toolbar"
      :aria-label="`Formato: ${etiqueta}`"
      class="flex flex-wrap items-center gap-0.5 border-b p-1"
    >
      <Button
        v-for="boton in botonesFormato"
        :key="boton.nombre"
        type="button"
        variant="ghost"
        size="icon"
        class="size-7 aria-pressed:bg-accent"
        :aria-label="boton.nombre"
        :aria-pressed="boton.activo() ? 'true' : 'false'"
        :disabled="soloLectura"
        @click="boton.alternar()"
      >
        <component :is="boton.icono" aria-hidden="true" />
      </Button>

      <Popover v-model:open="abiertoColor">
        <PopoverTrigger as-child>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            class="size-7 aria-pressed:bg-accent"
            aria-label="Color del texto"
            :aria-pressed="colorActivo() ? 'true' : 'false'"
            :disabled="soloLectura"
          >
            <Baseline aria-hidden="true" />
          </Button>
        </PopoverTrigger>
        <PopoverContent class="w-auto p-2" aria-label="Color del texto">
          <div class="flex items-center gap-1">
            <button
              v-for="color in COLORES_TEXTO"
              :key="color.valor"
              type="button"
              class="focus-visible:ring-ring/50 size-6 rounded-full border outline-none focus-visible:ring-[3px]"
              :style="{ backgroundColor: color.valor }"
              :aria-label="color.nombre"
              :title="color.nombre"
              @click="aplicarColor(color.valor)"
            />
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            class="mt-1 w-full"
            @click="aplicarColor(null)"
            >Quitar color</Button
          >
        </PopoverContent>
      </Popover>

      <Popover v-model:open="abiertoResaltado">
        <PopoverTrigger as-child>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            class="size-7 aria-pressed:bg-accent"
            aria-label="Resaltado"
            :aria-pressed="resaltadoActivo() ? 'true' : 'false'"
            :disabled="soloLectura"
          >
            <Highlighter aria-hidden="true" />
          </Button>
        </PopoverTrigger>
        <PopoverContent class="w-auto p-2" aria-label="Resaltado">
          <div class="flex items-center gap-1">
            <button
              v-for="color in COLORES_RESALTADO"
              :key="color.valor"
              type="button"
              class="focus-visible:ring-ring/50 size-6 rounded-full border outline-none focus-visible:ring-[3px]"
              :style="{ backgroundColor: color.valor }"
              :aria-label="color.nombre"
              :title="color.nombre"
              @click="aplicarResaltado(color.valor)"
            />
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            class="mt-1 w-full"
            @click="aplicarResaltado(null)"
            >Quitar resaltado</Button
          >
        </PopoverContent>
      </Popover>

      <Button
        v-for="boton in botonesLista"
        :key="boton.nombre"
        type="button"
        variant="ghost"
        size="icon"
        class="size-7 aria-pressed:bg-accent"
        :aria-label="boton.nombre"
        :aria-pressed="boton.activo() ? 'true' : 'false'"
        :disabled="soloLectura"
        @click="boton.alternar()"
      >
        <component :is="boton.icono" aria-hidden="true" />
      </Button>

      <Popover v-model:open="abiertoEnlace">
        <PopoverTrigger as-child>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            class="size-7 aria-pressed:bg-accent"
            aria-label="Enlace"
            :aria-pressed="enlaceActivo() ? 'true' : 'false'"
            :disabled="soloLectura"
          >
            <IconoEnlace aria-hidden="true" />
          </Button>
        </PopoverTrigger>
        <PopoverContent class="w-72 p-2" aria-label="Enlace">
          <!-- Sin <form>: el editor puede estar dentro de otro formulario. -->
          <div class="flex flex-col gap-2" @keydown.enter.prevent="aplicarEnlace">
            <Input
              v-model="url"
              type="url"
              placeholder="https://"
              aria-label="URL del enlace"
              :aria-invalid="errorUrl ? 'true' : undefined"
            />
            <p v-if="errorUrl" role="alert" class="text-destructive text-xs">{{ errorUrl }}</p>
            <div class="flex justify-end gap-2">
              <Button
                v-if="enlaceActivo()"
                type="button"
                variant="outline"
                size="sm"
                aria-label="Quitar enlace"
                @click="quitarEnlace"
                >Quitar</Button
              >
              <Button type="button" size="sm" aria-label="Aplicar enlace" @click="aplicarEnlace"
                >Aplicar</Button
              >
            </div>
          </div>
        </PopoverContent>
      </Popover>
    </div>
    <EditorContent :editor="editor" />
  </div>
</template>
