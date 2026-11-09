import { nextTick, ref } from 'vue'
import { describe, expect, it } from 'vitest'
import {
  compararConNulosAlFinal,
  compararNumero,
  compararTexto,
  useOrdenacionTabla,
  valorAriaSort,
} from '../useOrdenacionTabla'

interface Fila {
  nombre: string
  importe: number
  prioridad: number | null
}

const filas: Fila[] = [
  { nombre: 'Beta', importe: 20, prioridad: 2 },
  { nombre: 'Alfa', importe: 30, prioridad: null },
  { nombre: 'Gamma', importe: 10, prioridad: 1 },
]

const comparadores = {
  nombre: (a: Fila, b: Fila) => compararTexto(a.nombre, b.nombre),
  importe: (a: Fila, b: Fila) => compararNumero(a.importe, b.importe),
  prioridad: compararConNulosAlFinal((fila: Fila) => fila.prioridad, compararNumero),
}

describe('useOrdenacionTabla', () => {
  it('sin campo de orden devuelve las filas en su orden original', () => {
    const { campo, filasOrdenadas } = useOrdenacionTabla(ref(filas), comparadores)

    expect(campo.value).toBeNull()
    expect(filasOrdenadas.value.map((f) => f.nombre)).toEqual(['Beta', 'Alfa', 'Gamma'])
  })

  it('ordena ascendentemente al elegir un campo', () => {
    const { campo, direccion, ordenarPor, filasOrdenadas } = useOrdenacionTabla(
      ref(filas),
      comparadores,
    )

    ordenarPor('nombre')

    expect(campo.value).toBe('nombre')
    expect(direccion.value).toBe('asc')
    expect(filasOrdenadas.value.map((f) => f.nombre)).toEqual(['Alfa', 'Beta', 'Gamma'])
  })

  it('pulsar el mismo campo dos veces invierte la dirección a descendente', () => {
    const { ordenarPor, filasOrdenadas, direccion } = useOrdenacionTabla(ref(filas), comparadores)

    ordenarPor('importe')
    ordenarPor('importe')

    expect(direccion.value).toBe('desc')
    expect(filasOrdenadas.value.map((f) => f.importe)).toEqual([30, 20, 10])
  })

  it('un tercer clic en el mismo campo vuelve a ascendente', () => {
    const { ordenarPor, direccion } = useOrdenacionTabla(ref(filas), comparadores)

    ordenarPor('importe')
    ordenarPor('importe')
    ordenarPor('importe')

    expect(direccion.value).toBe('asc')
  })

  it('cambiar de campo reinicia la dirección a ascendente en el nuevo campo', () => {
    const { campo, ordenarPor, direccion, filasOrdenadas } = useOrdenacionTabla(
      ref(filas),
      comparadores,
    )

    ordenarPor('importe')
    ordenarPor('importe')
    ordenarPor('nombre')

    expect(campo.value).toBe('nombre')
    expect(direccion.value).toBe('asc')
    expect(filasOrdenadas.value.map((f) => f.nombre)).toEqual(['Alfa', 'Beta', 'Gamma'])
  })

  it('no muta el array original', () => {
    const original = ref([...filas])
    const { ordenarPor, filasOrdenadas } = useOrdenacionTabla(original, comparadores)

    ordenarPor('nombre')

    expect(filasOrdenadas.value).not.toBe(original.value)
    expect(original.value.map((f) => f.nombre)).toEqual(['Beta', 'Alfa', 'Gamma'])
  })

  it('reordena cuando cambian las filas', async () => {
    const origen = ref([...filas])
    const { ordenarPor, filasOrdenadas } = useOrdenacionTabla(origen, comparadores)
    ordenarPor('nombre')

    origen.value = [...origen.value, { nombre: 'Aaron', importe: 5, prioridad: 3 }]
    await nextTick()

    expect(filasOrdenadas.value.map((f) => f.nombre)).toEqual(['Aaron', 'Alfa', 'Beta', 'Gamma'])
  })

  it('las prioridades vacías quedan al final en orden ascendente', () => {
    const { ordenarPor, filasOrdenadas } = useOrdenacionTabla(ref(filas), comparadores)

    ordenarPor('prioridad')

    expect(filasOrdenadas.value.map((f) => f.prioridad)).toEqual([1, 2, null])
  })

  it('las prioridades vacías quedan al final también en orden descendente', () => {
    const { ordenarPor, filasOrdenadas } = useOrdenacionTabla(ref(filas), comparadores)

    ordenarPor('prioridad')
    ordenarPor('prioridad')

    expect(filasOrdenadas.value.map((f) => f.prioridad)).toEqual([2, 1, null])
  })
})

describe('compararTexto', () => {
  it('ordena las vocales acentuadas como su letra base', () => {
    expect(['b', 'á', 'a'].sort(compararTexto)).toEqual(['á', 'a', 'b'])
    expect(compararTexto('ábaco', 'barco')).toBeLessThan(0)
  })

  it('no distingue mayúsculas de minúsculas ni acentos', () => {
    expect(compararTexto('Árbol', 'arbol')).toBe(0)
  })
})

describe('compararNumero', () => {
  it('devuelve la diferencia entre los dos números', () => {
    expect(compararNumero(1, 2)).toBeLessThan(0)
    expect(compararNumero(2, 1)).toBeGreaterThan(0)
    expect(compararNumero(3, 3)).toBe(0)
  })
})

describe('valorAriaSort', () => {
  it('devuelve "ascending" en la columna activa ascendente', () => {
    expect(valorAriaSort(true, 'asc')).toBe('ascending')
  })

  it('devuelve "descending" en la columna activa descendente', () => {
    expect(valorAriaSort(true, 'desc')).toBe('descending')
  })

  it('no devuelve valor en una columna inactiva', () => {
    expect(valorAriaSort(false, 'asc')).toBeUndefined()
    expect(valorAriaSort(false, 'desc')).toBeUndefined()
  })
})
