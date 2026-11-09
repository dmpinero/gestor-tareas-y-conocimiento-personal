// La versión y el historial de cambios de la aplicación se leen en vivo desde
// la API pública de GitHub (el repositorio es público, no requiere token) en
// vez de "congelarse" en el build. Así siempre coincide con la última release
// publicada, sin depender de que el pipeline de release pueda escribir de
// vuelta en la rama protegida `main`.
const REPOSITORIO = 'dmpinero/gestor-tareas-y-conocimiento-personal'
const URL_BASE = `https://api.github.com/repos/${REPOSITORIO}`

export interface ReleaseGitHub {
  tag_name: string
  name: string | null
  body: string | null
  published_at: string | null
  html_url: string
}

export async function obtenerUltimaVersion(): Promise<string> {
  const respuesta = await fetch(`${URL_BASE}/releases/latest`)
  if (!respuesta.ok) {
    throw new Error('No se pudo obtener la versión desde GitHub.')
  }
  const release = (await respuesta.json()) as ReleaseGitHub
  return release.tag_name.replace(/^v/, '')
}

const RELEASES_POR_PAGINA = 100

export async function obtenerHistorialDeReleases(): Promise<ReleaseGitHub[]> {
  const releases: ReleaseGitHub[] = []
  let pagina = 1

  // La API de GitHub pagina (30 resultados por defecto, 100 como máximo);
  // sin recorrer todas las páginas, el historial se corta silenciosamente
  // en las releases más recientes en cuanto el repositorio supera ese límite.
  for (;;) {
    const respuesta = await fetch(
      `${URL_BASE}/releases?per_page=${RELEASES_POR_PAGINA}&page=${pagina}`,
    )
    if (!respuesta.ok) {
      throw new Error('No se pudo obtener el historial de cambios desde GitHub.')
    }
    const paginaReleases = (await respuesta.json()) as ReleaseGitHub[]
    releases.push(...paginaReleases)
    if (paginaReleases.length < RELEASES_POR_PAGINA) break
    pagina += 1
  }

  return releases
}
