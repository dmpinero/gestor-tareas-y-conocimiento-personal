/**
 * HTML de los comentarios con formato.
 *
 * La API ya guarda y devuelve HTML saneado; aquí se vuelve a sanear antes de
 * pintarlo con `v-html` (defensa en profundidad) con la misma lista de
 * etiquetas y atributos que el backend. Usa su propia instancia de DOMPurify
 * para que sus hooks no afecten a otros usos (p. ej. el historial de cambios).
 *
 * Las imágenes (`img`) solo se conservan si su `src` es la URL de una imagen
 * subida a la aplicación (`/api/v1/imagenes/<id>`), como en el backend.
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
  'img',
]
const ATRIBUTOS_PERMITIDOS = ['href', 'target', 'rel', 'style', 'data-color', 'src', 'alt']
// Atributos que solo tienen sentido en ciertas etiquetas.
const ATRIBUTOS_POR_ETIQUETA: Record<string, string[]> = {
  href: ['a'],
  target: ['a'],
  rel: ['a'],
  style: ['span', 'mark'],
  'data-color': ['mark'],
  src: ['img'],
  alt: ['img'],
}
// Propiedades CSS que se conservan en `style`, según la etiqueta.
const PROPIEDADES_POR_ETIQUETA: Record<string, string> = {
  span: 'color',
  mark: 'background-color',
}
// Valores de color sencillos: `#rgb`, nombres, `rgb(…)`/`hsl(…)`.
const VALOR_COLOR = /^[#a-z0-9(),.%\s-]+$/i
/** La única URL de imagen que admiten los comentarios (relativa, de esta aplicación). */
export const URL_IMAGEN_PERMITIDA = /^\/api\/v1\/imagenes\/[0-9a-f]{32}$/
// Para `href` y `src`: esquemas http/https/mailto sin distinguir mayúsculas
// (como el backend) o la ruta exacta de una imagen. El hook deja en `src` solo
// URL_IMAGEN_PERMITIDA.
const URL_PERMITIDA =
  /^(?:[hH][tT][tT][pP][sS]?:|[mM][aA][iI][lL][tT][oO]:|\/api\/v1\/imagenes\/[0-9a-f]{32}$)/
const REL_ENLACES = 'noopener noreferrer nofollow'

/**
 * Clases de Tailwind para el contenido de un comentario (en el editor y en el
 * historial): el preflight quita viñetas y márgenes de las listas.
 */
export const CLASES_CONTENIDO_COMENTARIO =
  'break-words [&_ul]:list-disc [&_ol]:list-decimal [&_ul]:pl-5 [&_ol]:pl-5 [&_p:empty]:min-h-[1lh] [&_a]:text-primary [&_a]:underline [&_a]:underline-offset-2 [&_mark]:rounded-sm [&_mark]:px-0.5 [&_mark]:text-neutral-900 [&_img]:my-1 [&_img]:max-h-80 [&_img]:max-w-full [&_img]:rounded-md [&_img]:border'

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
    if (datos.attrName === 'src' && !URL_IMAGEN_PERMITIDA.test(datos.attrValue)) {
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
    // Una imagen sin `src` válido no muestra nada: se quita entera.
    if (nodo.nodeName.toLowerCase() === 'img') {
      if (!nodo.hasAttribute('src')) nodo.parentNode?.removeChild(nodo)
      return
    }
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

/**
 * Si el comentario tiene algo que guardar: texto visible o alguna imagen subida
 * a la aplicación (un comentario puede ser solo una captura de pantalla).
 */
export function tieneContenidoComentario(html: string): boolean {
  if (textoVisible(html) !== '') return true
  if (html === '') return false
  const documento = new DOMParser().parseFromString(html, 'text/html')
  return [...documento.querySelectorAll('img')].some((imagen) =>
    URL_IMAGEN_PERMITIDA.test(imagen.getAttribute('src') ?? ''),
  )
}

/** Envuelve cada imagen (no enlazada ya) en un enlace que la abre entera en una pestaña nueva. */
function enlazarImagenes(html: string): string {
  if (!html.includes('<img')) return html
  const plantilla = document.createElement('template')
  plantilla.innerHTML = html
  for (const imagen of plantilla.content.querySelectorAll('img')) {
    if (imagen.closest('a')) continue
    const enlace = document.createElement('a')
    enlace.setAttribute('href', imagen.getAttribute('src') ?? '')
    enlace.setAttribute('target', '_blank')
    enlace.setAttribute('rel', REL_ENLACES)
    imagen.replaceWith(enlace)
    enlace.append(imagen)
  }
  return plantilla.innerHTML
}

/** HTML saneado de un comentario, listo para `v-html`. */
export function htmlComentarioMostrado(texto: string): string {
  return enlazarImagenes(sanitizarHtmlComentario(htmlComentarioEditable(texto)))
}
