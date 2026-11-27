import { computed, ref, type Ref } from 'vue'

/** Pasa a minúsculas y quita las marcas diacríticas ("Nómina" → "nomina"). */
export function normalizarTextoBusqueda(texto: string): string {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}

/** `true` si `texto` contiene la `busqueda` (sin espacios alrededor) sin
 * distinguir mayúsculas ni acentos. Con la búsqueda vacía, `false`. */
export function coincideBusqueda(texto: string, busqueda: string): boolean {
  const termino = normalizarTextoBusqueda(busqueda.trim())
  return termino !== '' && normalizarTextoBusqueda(texto).includes(termino)
}

// La búsqueda no distingue mayúsculas ni acentos, ni en el término ni en el texto.
export function useBusquedaTabla<T>(
  filas: Ref<T[]>,
  extraerTexto: (fila: T) => Array<string | null | undefined>,
) {
  const busqueda = ref('')

  const filasFiltradas = computed(() => {
    const termino = normalizarTextoBusqueda(busqueda.value.trim())
    if (!termino) return filas.value
    return filas.value.filter((fila) =>
      extraerTexto(fila).some((valor) => normalizarTextoBusqueda(valor ?? '').includes(termino)),
    )
  })

  return { busqueda, filasFiltradas }
}
