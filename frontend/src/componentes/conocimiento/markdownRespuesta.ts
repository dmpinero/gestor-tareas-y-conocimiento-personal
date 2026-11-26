/**
 * HTML de las respuestas del chat de Conocimiento, que llegan en Markdown.
 *
 * El texto lo escribe Claude a partir de notas de Notion (contenido que no
 * controla la aplicación), así que se sanea con DOMPurify antes de pintarlo con
 * `v-html`, como el historial de cambios: además de lo que quita por defecto
 * (scripts, manejadores, URLs `javascript:`), se prohíben los estilos, los
 * formularios y las imágenes (podrían cargar recursos externos). Los enlaces se
 * abren en una pestaña nueva sin dar acceso a esta.
 *
 * `marked` y `dompurify` se cargan bajo demanda (la vista se importa sin
 * división de código) y con una instancia propia de DOMPurify para que su hook
 * no afecte a otros usos.
 */
import type { DOMPurify as InstanciaDOMPurify } from 'dompurify'
import type { Marked } from 'marked'

interface Renderizador {
  marked: Marked
  purificador: InstanciaDOMPurify
}

let cargando: Promise<Renderizador> | null = null

function cargarRenderizador(): Promise<Renderizador> {
  cargando ??= Promise.all([import('marked'), import('dompurify')]).then(
    ([modMarked, modPurificador]) => {
      const purificador = modPurificador.default(window)
      purificador.addHook('afterSanitizeAttributes', (nodo) => {
        if (nodo.nodeName.toLowerCase() !== 'a') return
        nodo.setAttribute('target', '_blank')
        nodo.setAttribute('rel', 'noopener noreferrer')
      })
      return {
        marked: new modMarked.Marked({ gfm: true, breaks: true, async: false }),
        purificador,
      }
    },
  )
  return cargando
}

/** Markdown de una respuesta → HTML saneado, listo para `v-html`. */
export async function htmlRespuesta(markdown: string): Promise<string> {
  const { marked, purificador } = await cargarRenderizador()
  return purificador.sanitize(marked.parse(markdown) as string, {
    FORBID_TAGS: ['style', 'img', 'form', 'input', 'button', 'iframe'],
    FORBID_ATTR: ['style'],
  })
}
