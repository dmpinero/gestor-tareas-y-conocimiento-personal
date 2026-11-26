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
  tarea(1, 'Preparar demo', { etiquetas: ['cliente-x'], vinculadas: [2] }),
  tarea(2, 'Enviar factura', { etiquetas: ['cliente-x'], vinculadas: [1] }),
  tarea(3, 'Revisar contrato', { etiquetas: ['cliente-x'] }),
]

const CLAVE_VISTA = 'gestor-tareas:vista-tareas'

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

function botonVista(etiqueta: string): HTMLButtonElement {
  const boton = document.body.querySelector<HTMLButtonElement>(`button[aria-label="${etiqueta}"]`)
  if (!boton) throw new Error(`No se encontró el botón "${etiqueta}"`)
  return boton
}

function nodosTarea(): string[] {
  return [...document.body.querySelectorAll('[data-testid="red-tareas"] [data-tipo="tarea"]')].map(
    (nodo) => nodo.getAttribute('aria-label')!,
  )
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

describe('VistaTareas: ver como red', () => {
  it('"Ver como red" muestra la red, oculta la tabla y recuerda la elección', async () => {
    await montar()
    expect(botonVista('Ver como red').getAttribute('aria-pressed')).toBe('false')
    expect(botonVista('Ver como red').getAttribute('title')).toBe('Ver como red')

    botonVista('Ver como red').click()
    await flushPromises()

    expect(botonVista('Ver como red').getAttribute('aria-pressed')).toBe('true')
    expect(botonVista('Ver como lista').getAttribute('aria-pressed')).toBe('false')
    expect(document.body.querySelector('table')).toBeNull()
    expect(document.body.querySelector('[data-testid="red-tareas"]')).not.toBeNull()
    expect(document.body.querySelector('[data-testid="agrupar-subestado"]')).toBeNull()
    expect(localStorage.getItem(CLAVE_VISTA)).toBe('red')
    expect(nodosTarea()).toEqual([
      'Tarea Preparar demo: 2 conexiones',
      'Tarea Enviar factura: 2 conexiones',
      'Tarea Revisar contrato: 1 conexión',
    ])

    contenedor!.unmount()
    document.body.innerHTML = ''
    await montar()
    expect(botonVista('Ver como red').getAttribute('aria-pressed')).toBe('true')
    expect(document.body.querySelector('[data-testid="red-tareas"]')).not.toBeNull()
  })

  it('usa las tareas filtradas por la búsqueda', async () => {
    localStorage.setItem(CLAVE_VISTA, 'red')
    await montar()
    expect(document.body.querySelector('[data-testid="lienzo-red"]')).not.toBeNull()
    const buscar = document.body.querySelector<HTMLInputElement>('#filtro-buscar')!
    buscar.value = 'contrato'
    buscar.dispatchEvent(new Event('input'))
    await flushPromises()

    // Sin filtrar habría uniones; solo con «Revisar contrato» no hay ninguna.
    expect(document.body.querySelector('[data-testid="lienzo-red"]')).toBeNull()
    expect(document.body.textContent).toContain(
      'Estas tareas no tienen nada en común con las uniones elegidas.',
    )
  })

  it('pulsar una tarea de la red abre su detalle', async () => {
    localStorage.setItem(CLAVE_VISTA, 'red')
    await montar()
    document.body
      .querySelector<SVGElement>('[data-testid="red-tareas"] [data-nodo="tarea:2"]')!
      .dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await flushPromises()
    expect(tituloDetalle()).toBe('Enviar factura')
  })
})

function tituloDetalle(): string | undefined {
  return document.body.querySelector('[role="dialog"] h2')?.textContent?.trim()
}
