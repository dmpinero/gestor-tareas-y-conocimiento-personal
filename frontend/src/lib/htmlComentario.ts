/**
 * HTML de los comentarios con formato.
 *
 * La API ya guarda y devuelve HTML saneado; aquí se vuelve a sanear antes de
 * pintarlo con `v-html` (defensa en profundidad) con la misma lista de
 * etiquetas y atributos que el backend. Usa su propia instancia de DOMPurify
 * para que sus hooks no afecten a otros usos (p. ej. el historial de cambios).
 */
import DOMPurify, { type DOMPurify as InstanciaDOMPurify } from 'dompurify'

const ETIQUETAS_PERMITIDAS = [
  'p',
  'br',
  'strong',
  'em',
  'u',
  's',
  'ul',
  'ol',
  'li',
  'a',
  'span',
  'mark',
]
const ATRIBUTOS_PERMITIDOS = ['href', 'target', 'rel', 'style', 'data-color']
// Atributos que solo tienen sentido en ciertas etiquetas.
const ATRIBUTOS_POR_ETIQUETA: Record<string, string[]> = {
  href: ['a'],
  target: ['a'],
  rel: ['a'],
  style: ['span', 'mark'],
  'data-color': ['mark'],
}
// Propiedades CSS que se conservan en `style`, según la etiqueta.
const PROPIEDADES_POR_ETIQUETA: Record<string, string> = {
  span: 'color',
  mark: 'background-color',
}
// Valores de color sencillos: `#rgb`, nombres, `rgb(…)`/`hsl(…)`.
const VALOR_COLOR = /^[#a-z0-9(),.%\s-]+$/i
const URL_PERMITIDA = /^(?:https?:|mailto:)/i
const REL_ENLACES = 'noopener noreferrer nofollow'

/**
 * Clases de Tailwind para el contenido de un comentario (en el editor y en el
 * historial): el preflight quita viñetas y márgenes de las listas.
 */
export const CLASES_CONTENIDO_COMENTARIO =
  'break-words [&_ul]:list-disc [&_ol]:list-decimal [&_ul]:pl-5 [&_ol]:pl-5 [&_p:empty]:min-h-[1lh] [&_a]:text-primary [&_a]:underline [&_a]:underline-offset-2 [&_mark]:rounded-sm [&_mark]:px-0.5 [&_mark]:text-neutral-900'

function filtrarEstilo(etiqueta: string, estilo: string): string {
  const propiedad = PROPIEDADES_POR_ETIQUETA[etiqueta]
  if (!propiedad) return ''
  const declaraciones: string[] = []
  for (const declaracion of estilo.split(';')) {
    const separador = declaracion.indexOf(':')
    if (separador < 0) continue
    const nombre = declaracion.slice(0, separador).trim().toLowerCase()
    const valor = declaracion.slice(separador + 1).trim()
    if (nombre !== propiedad || !VALOR_COLOR.test(valor) || /expression|url/i.test(valor)) continue
    declaraciones.push(`${nombre}: ${valor}`)
  }
  return declaraciones.join('; ')
}

let purificador: InstanciaDOMPurify | null = null

function obtenerPurificador(): InstanciaDOMPurify {
  if (purificador) return purificador
  const instancia = DOMPurify(window)
  instancia.addHook('uponSanitizeAttribute', (nodo, datos) => {
    const etiqueta = nodo.nodeName.toLowerCase()
    const permitidas = ATRIBUTOS_POR_ETIQUETA[datos.attrName]
    // Los `data-*` los deja pasar DOMPurify por su cuenta: solo vale `data-color`.
    if (!permitidas || !permitidas.includes(etiqueta)) {
      datos.keepAttr = false
      return
    }
    if (datos.attrName === 'style') {
      const filtrado = filtrarEstilo(etiqueta, datos.attrValue)
      if (filtrado === '') datos.keepAttr = false
      else datos.attrValue = filtrado
    }
  })
  instancia.addHook('afterSanitizeAttributes', (nodo) => {
    if (nodo.nodeName.toLowerCase() !== 'a') return
    nodo.setAttribute('target', '_blank')
    nodo.setAttribute('rel', REL_ENLACES)
  })
  purificador = instancia
  return instancia
}

/** Sanea el HTML de un comentario con la lista permitida del backend. */
export function sanitizarHtmlComentario(html: string): string {
  return obtenerPurificador().sanitize(html, {
    ALLOWED_TAGS: ETIQUETAS_PERMITIDAS,
    ALLOWED_ATTR: ATRIBUTOS_PERMITIDOS,
    // Con `false` DOMPurify quita también `data-color`; el hook filtra el resto.
    ALLOW_DATA_ATTR: true,
    ALLOWED_URI_REGEXP: URL_PERMITIDA,
  })
}

/**
 * Texto visible de un comentario: sin etiquetas, con las entidades
 * decodificadas y sin espacios en los extremos. Es lo que cuenta para el
 * límite de caracteres y para saber si está vacío.
 */
export function textoVisible(html: string): string {
  if (html === '') return ''
  // DOMParser no ejecuta scripts ni carga recursos del documento analizado.
  const documento = new DOMParser().parseFromString(html, 'text/html')
  return (documento.body.textContent ?? '').trim()
}

function escaparHtml(texto: string): string {
  return texto
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/** Texto plano a HTML como lo hace el backend: un `<p>` escapado por línea. */
export function textoPlanoAHtml(texto: string): string {
  return texto
    .split(/\r\n|\r|\n/)
    .map((linea) => `<p>${escaparHtml(linea)}</p>`)
    .join('')
}

/** Si el texto no tiene ninguna etiqueta HTML, es texto plano (datos antiguos). */
function esTextoPlano(texto: string): boolean {
  return !/<\/?[a-z][^>]*>/i.test(texto)
}

/** HTML listo para el editor: el texto plano se convierte en párrafos. */
export function htmlComentarioEditable(texto: string): string {
  return esTextoPlano(texto) ? textoPlanoAHtml(texto) : texto
}

/** HTML saneado de un comentario, listo para `v-html`. */
export function htmlComentarioMostrado(texto: string): string {
  return sanitizarHtmlComentario(htmlComentarioEditable(texto))
}
