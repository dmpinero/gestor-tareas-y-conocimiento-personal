import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { clienteApi } from '@/api/cliente'
import type { Tarea } from '@/api/tipos'
import VistaTareas from '../VistaTareas.vue'

vi.mock('@/lib/exportarTabla', () => ({
  exportarTablaExcel: vi.fn<(...args: unknown[]) => Promise<void>>(),
  exportarTablaPDF: vi.fn<(...args: unknown[]) => Promise<void>>(),
}))

vi.mock('@/api/cliente', async (original) => ({
  ...(await original()),
  clienteApi: {
    obtener: vi.fn<(...args: unknown[]) => unknown>(),
    crear: vi.fn<(...args: unknown[]) => unknown>(),
    actualizar: vi.fn<(...args: unknown[]) => unknown>(),
    parchear: vi.fn<(...args: unknown[]) => unknown>(),
    eliminar: vi.fn<(...args: unknown[]) => unknown>(),
  },
}))

function tarea(id: number, nombre: string, cambios: Partial<Tarea> = {}): Tarea {
  return {
    id,
    nombre,
    prioridad: null,
    descripcion: '',
    fecha_creacion: '2026-11-10T09:30:00',
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

function subtarea(id: number, nombre: string) {
  return { id, nombre, asignado: null, prioridad: null, resuelta: false, comentarios: 0 }
}

const TAREAS = [
  tarea(1, 'Altas de personal', {
    subtareas: [
      subtarea(10, 'Buscar persona fuera de KMM'),
      subtarea(11, 'Buscar sala'),
      subtarea(12, 'Firmar contrato'),
    ],
  }),
  tarea(2, 'Preparar demo', { subtareas: [subtarea(20, 'Ensayar')] }),
]

let contenedor: VueWrapper | null = null

async function montar(): Promise<void> {
  vi.mocked(clienteApi.obtener).mockImplementation((ruta) => {
    if (ruta === '/tareas') return Promise.resolve(structuredClone(TAREAS))
    return Promise.resolve([])
  })
  const pinia = createPinia()
  setActivePinia(pinia)
  const enrutador = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/tareas', component: { template: '<div />' } }],
  })
  await enrutador.push('/tareas')
  contenedor = mount(VistaTareas, {
    global: { plugins: [pinia, enrutador] },
    attachTo: document.body,
  })
  await flushPromises()
}

async function buscar(texto: string): Promise<void> {
  const campo = document.body.querySelector<HTMLInputElement>('#filtro-buscar')!
  campo.value = texto
  campo.dispatchEvent(new Event('input'))
  await flushPromises()
}

function filas(): { nombre: string; subtareas: string[] }[] {
  return [...document.body.querySelectorAll<HTMLElement>('[data-fila-tarea]')].map((fila) => ({
    nombre: fila.querySelector('[data-nombre-tarea]')!.textContent!.trim(),
    subtareas: [...fila.querySelectorAll('[data-subtarea-coincidente]')].map((s) =>
      s.textContent!.trim(),
    ),
  }))
}

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
})

afterEach(() => {
  contenedor?.unmount()
  contenedor = null
  document.body.innerHTML = ''
  localStorage.clear()
})

describe('VistaTareas: el buscador encuentra subtareas', () => {
  it('muestra la tarea dueña con una línea «Subtarea: …» por cada subtarea que coincide', async () => {
    await montar()

    await buscar('BUSCAR persona fuera de kmm')
    expect(filas()).toEqual([
      { nombre: 'Altas de personal', subtareas: ['Subtarea: Buscar persona fuera de KMM'] },
    ])

    await buscar('búscar')
    expect(filas()).toEqual([
      {
        nombre: 'Altas de personal',
        subtareas: ['Subtarea: Buscar persona fuera de KMM', 'Subtarea: Buscar sala'],
      },
    ])
  })

  it('cada subtarea que coincide tiene su «Añadir a siguientes», que añade la subtarea y no la tarea', async () => {
    vi.mocked(clienteApi.crear).mockResolvedValue([])
    await montar()
    await buscar('persona fuera de kmm')

    const boton = document.body.querySelector<HTMLButtonElement>(
      'button[aria-label="Añadir a siguientes (Buscar persona fuera de KMM)"]',
    )!
    boton.click()
    await flushPromises()

    expect(clienteApi.crear).toHaveBeenCalledWith('/siguientes', {
      tarea_id: expect.any(Number),
      subtarea_id: expect.any(Number),
    })
  })

  it('sin búsqueda, o si solo coincide la tarea, no muestra líneas de subtareas', async () => {
    await montar()
    expect(filas().every((fila) => fila.subtareas.length === 0)).toBe(true)

    await buscar('demo')
    expect(filas()).toEqual([{ nombre: 'Preparar demo', subtareas: [] }])
  })
})
