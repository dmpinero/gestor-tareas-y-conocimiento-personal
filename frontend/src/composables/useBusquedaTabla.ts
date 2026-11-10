import { computed, ref, type Ref } from 'vue'

/** Pasa a minúsculas y quita las marcas diacríticas ("Nómina" → "nomina"). */
export function normalizarTextoBusqueda(texto: string): string {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
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
