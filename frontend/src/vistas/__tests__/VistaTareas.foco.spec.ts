import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { clienteApi } from '@/api/cliente'
import type { Foco } from '@/api/tipos'
import { useTiendaFoco } from '@/stores/foco'
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

function tarea(id: number, nombre: string) {
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
  }
}

const TAREAS = [tarea(1, 'Escribir informe'), tarea(2, 'Leer artículo')]

function foco(tareaId: number, subtareaId: number | null = null): Foco {
  return {
    tarea_id: tareaId,
    tarea_nombre: 'x',
    subtarea_id: subtareaId,
    subtarea_nombre: subtareaId === null ? null : 'y',
    desde: '2026-11-24T10:00:00',
  }
}

let contenedor: VueWrapper | null = null
let enrutador: Router

async function montar(
  ruta = '/tareas',
  focoInicial: Foco | null = null,
  tareas: unknown[] = TAREAS,
): Promise<VueWrapper> {
  vi.mocked(clienteApi.obtener).mockImplementation((r) => {
    if (r === '/tareas') return Promise.resolve(structuredClone(tareas))
    return Promise.resolve([])
  })
  const pinia = createPinia()
  setActivePinia(pinia)
  useTiendaFoco().foco = focoInicial
  enrutador = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/tareas', component: { template: '<div />' } },
      { path: '/ajustes/grupos-estados', component: { template: '<div />' } },
    ],
  })
  await enrutador.push(ruta)
  contenedor = mount(VistaTareas, {
    global: { plugins: [pinia, enrutador] },
    attachTo: document.body,
  })
  await flushPromises()
  return contenedor
}

function tituloDetalle(): string | null {
  return document.body.querySelector('[role="dialog"] h2')?.textContent?.trim() ?? null
}

function filaDe(nombre: string): Element {
  return [...document.body.querySelectorAll('[data-fila-tarea]')].find(
    (fila) => fila.querySelector('[data-nombre-tarea]')?.textContent?.trim() === nombre,
  )!
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

describe('VistaTareas: tarea en foco', () => {
  it('/tareas?tarea=<id> abre el detalle de esa tarea y quita el parámetro', async () => {
    await montar('/tareas?tarea=2')

    expect(tituloDetalle()).toBe('Leer artículo')
    expect(enrutador.currentRoute.value.query).toEqual({})
  })

  it('estando ya en /tareas, navegar a ?tarea=<id> abre su detalle', async () => {
    await montar('/tareas')
    expect(tituloDetalle()).toBeNull()

    await enrutador.push('/tareas?tarea=1')
    await flushPromises()

    expect(tituloDetalle()).toBe('Escribir informe')
  })

  it('un ?tarea= que no es un id no abre nada', async () => {
    await montar('/tareas?tarea=abc')

    expect(tituloDetalle()).toBeNull()
  })

  it('marca la fila de la tarea en foco con "En foco"', async () => {
    await montar('/tareas', foco(2))

    const fila = filaDe('Leer artículo')
    expect(fila.getAttribute('data-en-foco')).toBe('true')
    expect(fila.querySelector('[data-insignia-foco]')?.textContent?.trim()).toBe('En foco')
    expect(filaDe('Escribir informe').getAttribute('data-en-foco')).toBeNull()
  })

  it('con una subtarea en foco la fila de su tarea no se marca', async () => {
    await montar('/tareas', foco(2, 20))

    expect(filaDe('Leer artículo').getAttribute('data-en-foco')).toBeNull()
  })

  it('el menú de la fila ofrece "Trabajar en esta" y la pone en foco', async () => {
    vi.mocked(clienteApi.actualizar).mockResolvedValue(foco(1))
    const envoltorio = await montar('/tareas')

    await envoltorio
      .get('button[aria-label="Acciones de la tarea Escribir informe"]')
      .trigger('click')
    await flushPromises()
    document.body
      .querySelector<HTMLButtonElement>(
        '[data-slot="popover-content"] button[aria-label="Trabajar en esta (Escribir informe)"]',
      )!
      .click()
    await flushPromises()

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/foco', { tarea_id: 1, subtarea_id: null })
    expect(filaDe('Escribir informe').getAttribute('data-en-foco')).toBe('true')
  })

  it('en la tarea en foco el menú ofrece "Dejar de trabajar"', async () => {
    vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)
    const envoltorio = await montar('/tareas', foco(1))

    await envoltorio
      .get('button[aria-label="Acciones de la tarea Escribir informe"]')
      .trigger('click')
    await flushPromises()
    document.body
      .querySelector<HTMLButtonElement>(
        '[data-slot="popover-content"] button[aria-label="Dejar de trabajar (Escribir informe)"]',
      )!
      .click()
    await flushPromises()

    expect(clienteApi.eliminar).toHaveBeenCalledWith('/foco')
    expect(useTiendaFoco().foco).toBeNull()
  })

  it('muestra el error si no se pudo poner en foco', async () => {
    vi.mocked(clienteApi.actualizar).mockRejectedValue(new Error('Tarea no encontrada'))
    const envoltorio = await montar('/tareas')

    await useTiendaFoco().fijar(9)
    await flushPromises()

    expect(envoltorio.text()).toContain('Tarea no encontrada')
  })

  describe('la fila en foco va la primera de su grupo', () => {
    const CON_VENCIMIENTO = [
      { ...tarea(1, 'Vence antes'), fecha_vencimiento: '2026-11-21T10:00:00' },
      { ...tarea(2, 'Vence en medio'), fecha_vencimiento: '2026-11-25T10:00:00' },
      { ...tarea(3, 'Vence después'), fecha_vencimiento: '2026-11-30T10:00:00' },
      { ...tarea(4, 'Hecha'), completada: true },
    ]

    function nombres(): string[] {
      return [...document.body.querySelectorAll('[data-fila-tarea] [data-nombre-tarea]')].map(
        (n) => n.textContent?.trim() ?? '',
      )
    }

    async function ordenarPor(columna: string): Promise<void> {
      contenedor!
        .findAll('th button')
        .find((b) => b.text() === columna)!
        .element.dispatchEvent(new MouseEvent('click', { bubbles: true }))
      await flushPromises()
    }

    it('aunque venza después, la tarea en foco sale arriba en cualquier orden', async () => {
      await montar('/tareas', foco(3), CON_VENCIMIENTO)

      expect(nombres()).toEqual(['Vence después', 'Vence antes', 'Vence en medio', 'Hecha'])
      await ordenarPor('Fecha de vencimiento')
      expect(nombres()).toEqual(['Vence después', 'Vence antes', 'Vence en medio', 'Hecha'])
      await ordenarPor('Fecha de vencimiento')
      expect(nombres()).toEqual(['Vence después', 'Vence en medio', 'Vence antes', 'Hecha'])
      await ordenarPor('Nombre')
      expect(nombres()).toEqual(['Vence después', 'Vence antes', 'Vence en medio', 'Hecha'])
    })

    it('con el foco en una subtarea, su tarea sale arriba', async () => {
      await montar('/tareas', foco(2, 20), CON_VENCIMIENTO)

      expect(nombres()).toEqual(['Vence en medio', 'Vence antes', 'Vence después', 'Hecha'])
    })

    it('sin foco el orden es el de siempre', async () => {
      await montar('/tareas', null, CON_VENCIMIENTO)

      expect(nombres()).toEqual(['Vence antes', 'Vence en medio', 'Vence después', 'Hecha'])
      await ordenarPor('Fecha de vencimiento')
      await ordenarPor('Fecha de vencimiento')
      expect(nombres()).toEqual(['Vence después', 'Vence en medio', 'Vence antes', 'Hecha'])
    })
  })
})
