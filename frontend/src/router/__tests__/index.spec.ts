import { describe, expect, it } from 'vitest'
import router from '../index'

describe('router', () => {
  it.each([
    ['/', 'inicio'],
    ['/tareas', 'tareas'],
    ['/conocimiento', 'conocimiento'],
    ['/ajustes', 'ajustes'],
  ])('resuelve %s a la ruta con nombre "%s"', (ruta, nombre) => {
    expect(router.resolve(ruta).name).toBe(nombre)
  })

  it('una ruta desconocida no coincide con ninguna vista', () => {
    expect(router.resolve('/no-existe').matched).toHaveLength(0)
  })
})
