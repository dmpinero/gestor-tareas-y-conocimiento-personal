import { readonly, ref } from 'vue'
import { obtenerHistorialDeReleases } from '@/api/github'

// El estado vive a nivel de módulo y no dentro del componente: la modal está
// dentro del popover de ayuda, que reka desmonta al cerrarse. Con el estado en
// el componente se volvía a descargar todo el historial en cada apertura, y la
// API de GitHub sin token solo admite 60 peticiones por hora (las comparte con
// la versión de la barra de estado).
const cargando = ref(false)
const error = ref<string | null>(null)
const contenidoHtml = ref<string | null>(null)

async function cargar(): Promise<void> {
  if (contenidoHtml.value || cargando.value) return

  cargando.value = true
  error.value = null
  try {
    // `marked` y `dompurify` solo hacen falta al abrir el historial: se cargan
    // bajo demanda para no engordar el bundle inicial.
    const [releases, { marked }, { default: purificador }] = await Promise.all([
      obtenerHistorialDeReleases(),
      import('marked'),
      import('dompurify'),
    ])
    const markdown = releases
      .map((release) => `## ${release.name ?? release.tag_name}\n\n${release.body ?? ''}`)
      .join('\n\n')
    // Las notas llegan de la red y cualquiera con permisos de escritura en el
    // repositorio público puede editarlas: se sanea el HTML antes de inyectarlo
    // con v-html. Además de lo que DOMPurify quita por defecto (scripts,
    // manejadores, URLs `javascript:`), se prohíben los estilos para que una
    // release no pueda tapar o falsear la interfaz.
    contenidoHtml.value = purificador.sanitize(await marked.parse(markdown), {
      FORBID_TAGS: ['style'],
      FORBID_ATTR: ['style'],
    })
  } catch {
    // No se cachea el error: la siguiente apertura vuelve a intentarlo.
    error.value = 'No se pudo cargar el historial de cambios.'
  } finally {
    cargando.value = false
  }
}

export function useHistorialCambios() {
  return {
    cargando: readonly(cargando),
    error: readonly(error),
    contenidoHtml: readonly(contenidoHtml),
    cargar,
  }
}

/** Vacía la caché del historial (solo para aislar los tests). */
export function reiniciarHistorialCambios(): void {
  cargando.value = false
  error.value = null
  contenidoHtml.value = null
}
