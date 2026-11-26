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

const TAREAS = [
  tarea(1, 'Preparar demo', { vinculadas: [2] }),
  tarea(2, 'Enviar factura', { vinculadas: [1] }),
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

function tituloDetalle(): string | undefined {
  return document.body.querySelector('[role="dialog"] h2')?.textContent?.trim()
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

describe('VistaTareas: tareas relacionadas en el detalle', () => {
  it('pulsar una tarea relacionada abre su detalle', async () => {
    await montar()
    const fila = [...document.body.querySelectorAll<HTMLElement>('[data-fila-tarea]')].find(
      (f) => f.querySelector('[data-nombre-tarea]')?.textContent?.trim() === 'Preparar demo',
    )!
    fila.click()
    await flushPromises()
    expect(tituloDetalle()).toBe('Preparar demo')

    const vinculada = document.body.querySelector<HTMLButtonElement>(
      '[data-testid="tareas-vinculadas"] [data-vinculada]',
    )!
    expect(vinculada.textContent?.trim()).toBe('Enviar factura')
    vinculada.click()
    await flushPromises()

    expect(tituloDetalle()).toBe('Enviar factura')
    const vuelta = document.body.querySelector('[data-testid="tareas-vinculadas"] [data-vinculada]')
    expect(vuelta?.textContent?.trim()).toBe('Preparar demo')
  })
})
