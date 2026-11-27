/**
 * Ayudas del buscador de Conocimiento (sin IA): agrupar los trozos encontrados
 * por página y partir su texto en segmentos para resaltar las palabras buscadas.
 *
 * El texto de los trozos viene de Notion (contenido que no controla la
 * aplicación): nunca se pinta como HTML. Los segmentos son texto plano y la
 * vista pone cada palabra resaltada en un `<mark>` desde la plantilla.
 */
import type { ResultadoBusquedaConocimiento } from '@/api/tipos'

/** Las fuentes y páginas solo se enlazan si su URL es http(s) (las de Notion lo son). */
export function esUrlWeb(url: string): boolean {
  return /^https?:\/\//i.test(url)
}

export interface PaginaEncontrada {
  pagina_id: string
  titulo: string
  url: string
  /** Sus trozos encontrados, en el orden en que están en la página. */
  fragmentos: { orden: number; texto: string }[]
}

/** Agrupa los trozos por página: las páginas, en el orden de relevancia de su
 * primer trozo (la API los devuelve del más al menos relevante). */
export function agruparPorPagina(resultados: ResultadoBusquedaConocimiento[]): PaginaEncontrada[] {
  const paginas = new Map<string, PaginaEncontrada>()
  for (const r of resultados) {
    let pagina = paginas.get(r.pagina_id)
    if (!pagina) {
      pagina = { pagina_id: r.pagina_id, titulo: r.titulo, url: r.url, fragmentos: [] }
      paginas.set(r.pagina_id, pagina)
    }
    pagina.fragmentos.push({ orden: r.orden, texto: r.fragmento })
  }
  const grupos = [...paginas.values()]
  for (const grupo of grupos) grupo.fragmentos.sort((a, b) => a.orden - b.orden)
  return grupos
}

/** Sin tildes ni otras marcas y en minúsculas, como compara la búsqueda de MySQL. */
function normalizar(texto: string): string {
  return texto.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()
}

const NO_PALABRA = /[^\p{L}\p{N}_]+/u
const ES_PALABRA = /[\p{L}\p{N}_]/u
// MySQL no indexa las palabras de menos de 3 caracteres
// (`innodb_ft_min_token_size`): no se encuentran por ellas, así que no se resaltan.
const LONGITUD_MINIMA_PALABRA = 3

/** Las palabras de la búsqueda (normalizadas y sin repetir) que se resaltan. */
export function palabrasBuscadas(consulta: string): string[] {
  const palabras = normalizar(consulta)
    .split(NO_PALABRA)
    .filter((p) => [...p].length >= LONGITUD_MINIMA_PALABRA)
  return [...new Set(palabras)]
}

export interface Segmento {
  texto: string
  resaltado: boolean
}

/**
 * Parte `texto` en segmentos que, unidos, lo reproducen tal cual; los que son
 * una palabra entera de `consulta` (sin distinguir mayúsculas ni tildes) van
 * con `resaltado`.
 */
export function segmentosResaltados(texto: string, consulta: string): Segmento[] {
  if (texto === '') return []
  const palabras = palabrasBuscadas(consulta)
  if (palabras.length === 0) return [{ texto, resaltado: false }]

  // El texto normalizado, con el tramo del original del que sale cada unidad.
  let normalizado = ''
  const origen: { inicio: number; fin: number }[] = []
  for (let i = 0; i < texto.length;) {
    const caracter = String.fromCodePoint(texto.codePointAt(i)!)
    const pieza = normalizar(caracter)
    const fin = i + caracter.length
    if (pieza === '') {
      // Una marca suelta (p. ej. una tilde combinada): va con el carácter anterior.
      if (origen.length > 0) {
        const anterior = origen[origen.length - 1]!
        for (let k = origen.length - 1; k >= 0 && origen[k]!.fin === anterior.fin; k--) {
          origen[k]!.fin = fin
        }
      }
    } else {
      for (let k = 0; k < pieza.length; k++) origen.push({ inicio: i, fin })
      normalizado += pieza
    }
    i = fin
  }

  const tramos: [number, number][] = []
  for (const palabra of palabras) {
    let desde = 0
    for (;;) {
      const posicion = normalizado.indexOf(palabra, desde)
      if (posicion < 0) break
      const final = posicion + palabra.length
      const antes = normalizado[posicion - 1]
      const despues = normalizado[final]
      const entera =
        (antes === undefined || !ES_PALABRA.test(antes)) &&
        (despues === undefined || !ES_PALABRA.test(despues))
      if (entera) tramos.push([origen[posicion]!.inicio, origen[final - 1]!.fin])
      desde = posicion + 1
    }
  }
  if (tramos.length === 0) return [{ texto, resaltado: false }]

  tramos.sort((a, b) => a[0] - b[0])
  const segmentos: Segmento[] = []
  let cursor = 0
  for (const [inicio, fin] of tramos) {
    if (fin <= cursor) continue
    const desde = Math.max(inicio, cursor)
    if (desde > cursor) segmentos.push({ texto: texto.slice(cursor, desde), resaltado: false })
    const ultimo = segmentos[segmentos.length - 1]
    if (ultimo?.resaltado && desde === cursor) ultimo.texto += texto.slice(desde, fin)
    else segmentos.push({ texto: texto.slice(desde, fin), resaltado: true })
    cursor = fin
  }
  if (cursor < texto.length) segmentos.push({ texto: texto.slice(cursor), resaltado: false })
  return segmentos
}
