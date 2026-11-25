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

// Instante en UTC, como lo da la API ("YYYY-MM-DDTHH:MM:SSZ"), de una hora local.
function instanteUtc(fechaLocal: Date): string {
  return fechaLocal.toISOString().replace(/\.\d{3}Z$/, 'Z')
}

function tarea(id: number, nombre: string, cambios: Partial<Tarea> = {}): Tarea {
  return {
    id,
    nombre,
    prioridad: null,
    descripcion: '',
    fecha_creacion: '2026-11-10T09:30:00',
    // Vence en 1 h: sin congelar muestra la campana urgente.
    fecha_vencimiento: '2026-11-20T18:00:00',
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
    ...cambios,
  }
}

const HIBERNADA_DESDE = instanteUtc(new Date(2026, 10, 20, 16, 0, 0))
const TAREAS = [
  tarea(1, 'Normal'),
  tarea(2, 'Hibernada', { hibernada_desde: HIBERNADA_DESDE }),
  tarea(3, 'Completada', {
    completada: true,
    congelada_en: instanteUtc(new Date(2026, 10, 20, 15, 0, 0)),
  }),
]

let contenedor: VueWrapper | null = null

async function montar(ruta = '/tareas'): Promise<VueWrapper> {
  vi.mocked(clienteApi.obtener).mockImplementation((r) => {
    if (r === '/tareas') return Promise.resolve(structuredClone(TAREAS))
    return Promise.resolve([])
  })
  const pinia = createPinia()
  setActivePinia(pinia)
  const enrutador = createRouter({
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

function filaDe(nombre: string): Element {
  const fila = [...document.body.querySelectorAll('[data-fila-tarea]')].find(
    (f) => f.querySelector('[data-nombre-tarea]')?.textContent?.trim() === nombre,
  )
  if (!fila) throw new Error(`No hay fila «${nombre}»`)
  return fila
}

function textoContador(fila: Element): string | null | undefined {
  return fila.querySelector('[data-testid="contador-texto"]')?.textContent
}

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
  vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
  vi.setSystemTime(new Date(2026, 10, 20, 17, 0, 0))
})

afterEach(() => {
  vi.useRealTimers()
  contenedor?.unmount()
  contenedor = null
  document.body.innerHTML = ''
  localStorage.clear()
})

describe('VistaTareas: tareas hibernadas', () => {
  it('la fila de una tarea hibernada muestra "Hibernada", sin campanas y con el contador detenido', async () => {
    await montar()

    const fila = filaDe('Hibernada')
    expect(fila.querySelector('[data-insignia-hibernada]')?.textContent?.trim()).toBe('Hibernada')
    expect(fila.querySelector('[data-aviso-vencimiento]')).toBeNull()
    expect(
      fila.querySelector('[data-testid="contador-vencimiento"]')?.getAttribute('data-congelado'),
    ).toBe('true')
    expect(textoContador(fila)).toBe('Vence en 02 h 00 min 00 s')
    vi.advanceTimersByTime(2000)
    await flushPromises()
    expect(textoContador(filaDe('Hibernada'))).toBe('Vence en 02 h 00 min 00 s')
  })

  it('una tarea completada sin hibernar sigue mostrando su contador congelado como antes', async () => {
    await montar()

    const fila = filaDe('Completada')
    expect(fila.querySelector('[data-insignia-hibernada]')).toBeNull()
    const contador = fila.querySelector('[data-testid="contador-vencimiento"]')!
    expect(contador.getAttribute('data-congelado')).toBe('true')
    expect(contador.getAttribute('title')).toBe(
      'Contador detenido: la tarea está completada o en DONE',
    )
    expect(textoContador(fila)).toBe('Vence en 03 h 00 min 00 s')
  })

  it('una tarea normal sigue con su campana y el contador en marcha', async () => {
    await montar()

    const fila = filaDe('Normal')
    expect(fila.querySelector('[data-insignia-hibernada]')).toBeNull()
    expect(fila.querySelector('[data-aviso-vencimiento]')).not.toBeNull()
    expect(textoContador(fila)).toBe('Vence en 01 h 00 min 00 s')
    vi.advanceTimersByTime(1000)
    await flushPromises()
    expect(textoContador(filaDe('Normal'))).toBe('Vence en 00 h 59 min 59 s')
  })

  it('al hibernar desde el detalle la fila pasa a "Hibernada" con el contador detenido', async () => {
    vi.mocked(clienteApi.crear).mockResolvedValueOnce(
      tarea(1, 'Normal', { hibernada_desde: instanteUtc(new Date(2026, 10, 20, 17, 0, 0)) }),
    )
    await montar('/tareas?tarea=1')

    const dialogo = document.body.querySelector('[role="dialog"]')!
    ;[...dialogo.querySelectorAll<HTMLButtonElement>('button')]
      .find((b) => b.textContent?.trim() === 'Hibernar')!
      .click()
    await flushPromises()
    ;[...document.body.querySelectorAll<HTMLButtonElement>('[role="alertdialog"] button')]
      .find((b) => b.textContent?.trim() === 'Hibernar')!
      .click()
    await flushPromises()

    expect(clienteApi.crear).toHaveBeenCalledWith('/tareas/1/hibernar', { comentario: null })
    const fila = filaDe('Normal')
    expect(fila.querySelector('[data-insignia-hibernada]')?.textContent?.trim()).toBe('Hibernada')
    expect(
      fila.querySelector('[data-testid="contador-vencimiento"]')?.getAttribute('data-congelado'),
    ).toBe('true')
  })

  it('el menú "⋯" de la fila ofrece "Hibernar", que abre el diálogo e hiberna la tarea', async () => {
    vi.mocked(clienteApi.crear).mockResolvedValueOnce(
      tarea(1, 'Normal', { hibernada_desde: instanteUtc(new Date(2026, 10, 20, 17, 0, 0)) }),
    )
    await montar()

    filaDe('Normal')
      .querySelector<HTMLButtonElement>('button[aria-label="Acciones de la tarea Normal"]')!
      .click()
    await flushPromises()
    document.body
      .querySelector<HTMLButtonElement>('button[aria-label="Hibernar la tarea Normal"]')!
      .click()
    await flushPromises()
    const dialogo = document.body.querySelector<HTMLElement>('[role="alertdialog"]')!
    expect(dialogo.textContent).toContain('Hibernar la tarea Normal')
    ;[...dialogo.querySelectorAll<HTMLButtonElement>('button')]
      .find((b) => b.textContent?.trim() === 'Hibernar')!
      .click()
    await flushPromises()

    expect(clienteApi.crear).toHaveBeenCalledWith('/tareas/1/hibernar', { comentario: null })
    expect(filaDe('Normal').querySelector('[data-insignia-hibernada]')).not.toBeNull()
  })

  it('en una tarea hibernada el menú "⋯" ofrece "Reanudar", que la reanuda sin diálogo', async () => {
    vi.mocked(clienteApi.crear).mockResolvedValueOnce(tarea(2, 'Hibernada'))
    await montar()

    filaDe('Hibernada')
      .querySelector<HTMLButtonElement>('button[aria-label="Acciones de la tarea Hibernada"]')!
      .click()
    await flushPromises()
    expect(
      document.body.querySelector('button[aria-label="Hibernar la tarea Hibernada"]'),
    ).toBeNull()
    document.body
      .querySelector<HTMLButtonElement>('button[aria-label="Reanudar la tarea Hibernada"]')!
      .click()
    await flushPromises()

    expect(document.body.querySelector('[role="alertdialog"]')).toBeNull()
    expect(clienteApi.crear).toHaveBeenCalledWith('/tareas/2/reanudar', null)
    expect(filaDe('Hibernada').querySelector('[data-insignia-hibernada]')).toBeNull()
  })
})
