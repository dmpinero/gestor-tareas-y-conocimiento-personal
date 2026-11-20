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

// La API pública de GitHub admite 60 peticiones por hora por IP sin token: si
// cada carga de la página la consultara, el límite se agota y la versión
// desaparece. Se guarda la última versión conocida en este navegador, se vuelve
// a consultar como mucho una vez por hora y, si GitHub falla, se muestra la
// guardada aunque sea antigua.
export const CLAVE_VERSION_GUARDADA = 'gestor-tareas:version'
const VIGENCIA_VERSION_MS = 60 * 60 * 1000

interface VersionGuardada {
  version: string
  consultada: number
}

function leerVersionGuardada(): VersionGuardada | null {
  try {
    const guardada: unknown = JSON.parse(localStorage.getItem(CLAVE_VERSION_GUARDADA) ?? 'null')
    if (
      typeof guardada === 'object' &&
      guardada !== null &&
      typeof (guardada as VersionGuardada).version === 'string' &&
      typeof (guardada as VersionGuardada).consultada === 'number'
    ) {
      return guardada as VersionGuardada
    }
  } catch {
    // Valor no válido o almacenamiento no disponible: como si no hubiera nada.
  }
  return null
}

function guardarVersion(guardada: VersionGuardada): void {
  try {
    localStorage.setItem(CLAVE_VERSION_GUARDADA, JSON.stringify(guardada))
  } catch {
    // Sin almacenamiento (p. ej. navegación privada) se consulta cada vez.
  }
}

/**
 * Versión que se muestra en la barra de estado: la guardada si se consultó hace
 * menos de una hora; si no, la última release de GitHub (que se guarda) o, si
 * GitHub falla, la última guardada. Solo falla si GitHub falla y no hay ninguna.
 */
export async function obtenerVersionMostrada(ahora: number = Date.now()): Promise<string> {
  const guardada = leerVersionGuardada()
  if (guardada && ahora - guardada.consultada < VIGENCIA_VERSION_MS) return guardada.version
  try {
    const version = await obtenerUltimaVersion()
    guardarVersion({ version, consultada: ahora })
    return version
  } catch (error) {
    if (guardada) return guardada.version
    throw error
  }
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
