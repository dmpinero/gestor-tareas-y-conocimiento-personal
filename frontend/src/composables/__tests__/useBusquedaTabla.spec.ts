import { ref } from 'vue'
import { describe, expect, it } from 'vitest'
import { useBusquedaTabla } from '../useBusquedaTabla'

interface Fila {
  nombre: string
  alias: string | null
}

const filas: Fila[] = [
  { nombre: 'Cuenta nómina', alias: 'Principal' },
  { nombre: 'Cuenta ahorro', alias: null },
]

describe('useBusquedaTabla', () => {
  it('sin término de búsqueda devuelve todas las filas', () => {
    const { filasFiltradas } = useBusquedaTabla(ref(filas), (f) => [f.nombre, f.alias])

    expect(filasFiltradas.value).toEqual(filas)
  })

  it('filtra por coincidencia parcial e insensible a mayúsculas', () => {
    const { busqueda, filasFiltradas } = useBusquedaTabla(ref(filas), (f) => [f.nombre, f.alias])

    busqueda.value = 'NÓMINA'

    expect(filasFiltradas.value).toEqual([filas[0]])
  })

  it('no distingue acentos ni en el término ni en el texto', () => {
    const { busqueda, filasFiltradas } = useBusquedaTabla(ref(filas), (f) => [f.nombre, f.alias])

    busqueda.value = 'NOMINA'
    expect(filasFiltradas.value).toEqual([filas[0]])

    busqueda.value = 'príncipal'
    expect(filasFiltradas.value).toEqual([filas[0]])
  })

  it('ignora los espacios al principio y al final del término', () => {
    const { busqueda, filasFiltradas } = useBusquedaTabla(ref(filas), (f) => [f.nombre, f.alias])

    busqueda.value = '  ahorro  '

    expect(filasFiltradas.value).toEqual([filas[1]])
  })

  it('encuentra coincidencias en cualquiera de los campos extraídos', () => {
    const { busqueda, filasFiltradas } = useBusquedaTabla(ref(filas), (f) => [f.nombre, f.alias])

    busqueda.value = 'principal'

    expect(filasFiltradas.value).toEqual([filas[0]])
  })

  it('no falla con campos nulos', () => {
    const { busqueda, filasFiltradas } = useBusquedaTabla(ref(filas), (f) => [f.nombre, f.alias])

    busqueda.value = 'ahorro'

    expect(filasFiltradas.value).toEqual([filas[1]])
  })

  it('sin coincidencias devuelve una lista vacía', () => {
    const { busqueda, filasFiltradas } = useBusquedaTabla(ref(filas), (f) => [f.nombre, f.alias])

    busqueda.value = 'inexistente'

    expect(filasFiltradas.value).toEqual([])
  })
})
