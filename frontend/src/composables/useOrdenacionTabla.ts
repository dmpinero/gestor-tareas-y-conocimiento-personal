import { computed, ref, shallowRef, type Ref } from 'vue'

export type Direccion = 'asc' | 'desc'

/**
 * Un comparador es una función normal (la dirección invierte su resultado) o
 * un comparador con nulos, cuyas filas sin valor quedan siempre al final,
 * sea cual sea la dirección. Este último se construye con `compararConNulosAlFinal`.
 */
export type Comparador<T> =
  ((a: T, b: T) => number) | { esNulo: (fila: T) => boolean; comparar: (a: T, b: T) => number }

export function compararTexto(a: string, b: string): number {
  return a.localeCompare(b, 'es', { sensitivity: 'base' })
}

export function compararNumero(a: number, b: number): number {
  return a - b
}

export function compararConNulosAlFinal<T, V>(
  obtener: (fila: T) => V | null | undefined,
  comparar: (a: V, b: V) => number,
): Comparador<T> {
  return {
    esNulo: (fila) => obtener(fila) == null,
    comparar: (a, b) => comparar(obtener(a) as V, obtener(b) as V),
  }
}

export function valorAriaSort(
  activo: boolean,
  direccion: Direccion,
): 'ascending' | 'descending' | undefined {
  if (!activo) return undefined
  return direccion === 'asc' ? 'ascending' : 'descending'
}

function ordenar<T>(filas: T[], comparador: Comparador<T>, direccion: Direccion): T[] {
  const signo = direccion === 'asc' ? 1 : -1
  if (typeof comparador === 'function') {
    return [...filas].sort((a, b) => signo * comparador(a, b))
  }
  return [...filas].sort((a, b) => {
    const aNulo = comparador.esNulo(a)
    const bNulo = comparador.esNulo(b)
    if (aNulo || bNulo) return Number(aNulo) - Number(bNulo)
    return signo * comparador.comparar(a, b)
  })
}

export function useOrdenacionTabla<T, C extends string>(
  filas: Ref<T[]>,
  comparadores: Record<C, Comparador<T>>,
) {
  const campo = shallowRef<C | null>(null)
  const direccion = ref<Direccion>('asc')

  function ordenarPor(nuevoCampo: C): void {
    if (campo.value === nuevoCampo) {
      direccion.value = direccion.value === 'asc' ? 'desc' : 'asc'
    } else {
      campo.value = nuevoCampo
      direccion.value = 'asc'
    }
  }

  const filasOrdenadas = computed(() => {
    const campoActivo = campo.value
    if (campoActivo === null) return filas.value
    return ordenar(filas.value, comparadores[campoActivo as C], direccion.value)
  })

  return { campo, direccion, ordenarPor, filasOrdenadas }
}
