import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { clienteApi } from '@/api/cliente'
import type { Tarea } from '@/api/tipos'
import { useTiendaTareas } from '@/stores/tareas'
import SeccionTareasVinculadas from '../SeccionTareasVinculadas.vue'

vi.mock('@/api/cliente', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('@/api/cliente')>()
  return {
    ...original,
    clienteApi: {
      obtener: vi.fn<(...args: unknown[]) => unknown>(),
      crear: vi.fn<(...args: unknown[]) => unknown>(),
      actualizar: vi.fn<(...args: unknown[]) => unknown>(),
      parchear: vi.fn<(...args: unknown[]) => unknown>(),
      eliminar: vi.fn<(...args: unknown[]) => unknown>(),
    },
  }
})

function tarea(id: number, nombre: string, cambios: Partial<Tarea> = {}): Tarea {
  return {
    id,
    nombre,
    prioridad: null,
    descripcion: '',
    fecha_creacion: '2026-11-20T10:00:00',
    fecha_vencimiento: null,
    etiquetas: [],
    asignados: [],
    tipo: null,
    oportunidad: null,
    completada: false,
    subtareas: [],
    grupo_estados: null,
    estado: null,
    workflow: null,
    subestado: null,
    congelada_en: null,
    hibernada_desde: null,
    vinculadas: [],
    ...cambios,
  }
}

let envoltorio: VueWrapper | null = null
let tienda: ReturnType<typeof useTiendaTareas>

// Monta la sección de la tarea `id` con las tareas dadas ya en el almacén.
function montar(tareas: Tarea[], id = 1): VueWrapper {
  const pinia = createPinia()
  setActivePinia(pinia)
  tienda = useTiendaTareas()
  tienda.tareas = tareas
  envoltorio = mount(
    {
      components: { SeccionTareasVinculadas },
      setup: () => ({ tienda, id }),
      template: `<SeccionTareasVinculadas :tarea="tienda.tareas.find((t) => t.id === id)" />`,
    },
    { global: { plugins: [pinia] }, attachTo: document.body },
  )
  return envoltorio
}

function botonPorTexto(texto: string): HTMLButtonElement {
  const boton = [...document.body.querySelectorAll('button')].find(
    (b) => b.textContent?.trim() === texto || b.getAttribute('aria-label') === texto,
  )
  if (!boton) throw new Error(`No hay botón «${texto}»`)
  return boton
}

function dialogo(): HTMLElement | null {
  return document.body.querySelector('[role="dialog"]')
}

function casillas(): HTMLInputElement[] {
  return [...(dialogo()?.querySelectorAll<HTMLInputElement>('input[type="checkbox"]') ?? [])]
}

function nombresCasillas(): string[] {
  return casillas().map((c) => c.closest('label')?.textContent?.trim() ?? '')
}

async function abrirSelector(): Promise<void> {
  botonPorTexto('Relacionar tareas').click()
  await flushPromises()
}

async function buscar(texto: string): Promise<void> {
  const campo = dialogo()!.querySelector<HTMLInputElement>('input[type="search"]')!
  campo.value = texto
  campo.dispatchEvent(new Event('input'))
  await flushPromises()
}

async function marcar(nombre: string): Promise<void> {
  const casilla = casillas().find((c) => c.closest('label')?.textContent?.trim() === nombre)!
  casilla.click()
  await flushPromises()
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  envoltorio?.unmount()
  envoltorio = null
  document.body.innerHTML = ''
})

describe('SeccionTareasVinculadas', () => {
  it('lista con su nombre las tareas vinculadas, tachando las completadas', () => {
    montar([
      tarea(1, 'Principal', { vinculadas: [2, 3] }),
      tarea(2, 'Preparar demo', { vinculadas: [1] }),
      tarea(3, 'Enviar factura', { vinculadas: [1], completada: true }),
    ])

    const seccion = document.body.querySelector('[data-testid="tareas-vinculadas"]')!
    expect(seccion.querySelector('h3')?.textContent?.trim()).toBe('Tareas relacionadas')
    const nombres = [...seccion.querySelectorAll('[data-vinculada]')].map((boton) =>
      boton.textContent?.replace(/\s+/g, ' ').trim(),
    )
    expect(nombres).toEqual(['Preparar demo', 'Enviar factura (completada)'])
    const completada = seccion.querySelectorAll('[data-vinculada]')[1]!
    expect(completada.querySelector('.line-through')?.textContent).toBe('Enviar factura')
  })

  it('sin vínculos muestra un aviso', () => {
    montar([tarea(1, 'Principal'), tarea(2, 'Otra')])

    const seccion = document.body.querySelector('[data-testid="tareas-vinculadas"]')!
    expect(seccion.querySelectorAll('[data-vinculada]')).toHaveLength(0)
    expect(seccion.textContent).toContain('Esta tarea no tiene tareas relacionadas.')
  })

  it('pulsar una tarea vinculada emite verTarea con su id', async () => {
    const envoltorio = montar([
      tarea(1, 'Principal', { vinculadas: [2] }),
      tarea(2, 'Preparar demo', { vinculadas: [1] }),
    ])

    botonPorTexto('Preparar demo').click()
    await flushPromises()

    expect(envoltorio.findComponent(SeccionTareasVinculadas).emitted('verTarea')).toEqual([[2]])
  })

  it('"Quitar relación con …" pide al almacén que quite el vínculo', async () => {
    montar([
      tarea(1, 'Principal', { vinculadas: [2] }),
      tarea(2, 'Preparar demo', { vinculadas: [1] }),
    ])
    vi.mocked(clienteApi.eliminar).mockResolvedValue(tarea(1, 'Principal'))

    botonPorTexto('Quitar relación con Preparar demo').click()
    await flushPromises()

    expect(clienteApi.eliminar).toHaveBeenCalledWith('/tareas/1/vinculadas/2')
    expect(document.body.textContent).toContain('Esta tarea no tiene tareas relacionadas.')
  })

  describe('selector de tareas', () => {
    const TAREAS = [
      tarea(1, 'Principal', { vinculadas: [2] }),
      tarea(2, 'Ya vinculada', { vinculadas: [1] }),
      tarea(3, 'Revisión técnica'),
      tarea(4, 'Diseño de pantallas'),
      tarea(5, 'Revisar presupuesto'),
    ]

    it('ofrece las demás tareas, sin la propia ni las ya vinculadas', async () => {
      montar(structuredClone(TAREAS))
      await abrirSelector()

      expect(dialogo()).not.toBeNull()
      expect(nombresCasillas()).toEqual([
        'Diseño de pantallas',
        'Revisar presupuesto',
        'Revisión técnica',
      ])
    })

    it('filtra por el texto buscado sin distinguir mayúsculas ni acentos', async () => {
      montar(structuredClone(TAREAS))
      await abrirSelector()

      await buscar('REVISION')
      expect(nombresCasillas()).toEqual(['Revisión técnica'])

      await buscar('zzz')
      expect(nombresCasillas()).toEqual([])
      expect(dialogo()!.textContent).toContain('No hay tareas que coincidan con la búsqueda.')
    })

    it('relaciona varias tareas a la vez y cierra el selector', async () => {
      montar(structuredClone(TAREAS))
      vi.mocked(clienteApi.crear).mockResolvedValue(
        tarea(1, 'Principal', { vinculadas: [2, 3, 4] }),
      )
      await abrirSelector()
      expect(botonPorTexto('Relacionar').disabled).toBe(true)

      await marcar('Revisión técnica')
      await marcar('Diseño de pantallas')
      const confirmar = botonPorTexto('Relacionar (2)')
      expect(confirmar.disabled).toBe(false)
      confirmar.click()
      await flushPromises()

      expect(clienteApi.crear).toHaveBeenCalledWith('/tareas/1/vinculadas', { ids: [3, 4] })
      expect(dialogo()).toBeNull()
      const nombres = [...document.body.querySelectorAll('[data-vinculada]')].map((b) =>
        b.textContent?.trim(),
      )
      expect(nombres).toEqual(['Ya vinculada', 'Revisión técnica', 'Diseño de pantallas'])
      // La vuelta queda en las otras tareas del almacén.
      expect(tienda.tareas.find((t) => t.id === 3)!.vinculadas).toEqual([1])
    })

    it('si la API falla, el selector sigue abierto con el error', async () => {
      montar(structuredClone(TAREAS))
      vi.mocked(clienteApi.crear).mockRejectedValue(new Error('No existe la tarea con id 3'))
      await abrirSelector()
      await marcar('Revisión técnica')

      botonPorTexto('Relacionar (1)').click()
      await flushPromises()

      expect(dialogo()).not.toBeNull()
      expect(dialogo()!.querySelector('[role="alert"]')?.textContent).toBe(
        'No existe la tarea con id 3',
      )
    })

    it('"Cancelar" cierra sin relacionar nada', async () => {
      montar(structuredClone(TAREAS))
      await abrirSelector()
      await marcar('Revisión técnica')

      botonPorTexto('Cancelar').click()
      await flushPromises()

      expect(dialogo()).toBeNull()
      expect(clienteApi.crear).not.toHaveBeenCalled()
    })

    it('Escape cierra sin relacionar nada y al reabrir no queda nada marcado', async () => {
      montar(structuredClone(TAREAS))
      await abrirSelector()
      await marcar('Revisión técnica')
      await buscar('rev')

      document.activeElement!.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }),
      )
      await flushPromises()
      expect(dialogo()).toBeNull()
      expect(clienteApi.crear).not.toHaveBeenCalled()

      await abrirSelector()
      expect(casillas().filter((c) => c.checked)).toHaveLength(0)
      expect(dialogo()!.querySelector<HTMLInputElement>('input[type="search"]')!.value).toBe('')
    })
  })
})
