import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { clienteApi } from '@/api/cliente'
import VistaTareas from '../VistaTareas.vue'

vi.mock('@/lib/exportarTabla', () => ({
  exportarTablaExcel: vi.fn<(...args: unknown[]) => Promise<void>>(),
  exportarTablaPDF: vi.fn<(...args: unknown[]) => Promise<void>>(),
}))

vi.mock('@/api/cliente', () => ({
  clienteApi: {
    obtener: vi.fn<(...args: unknown[]) => unknown>(),
    crear: vi.fn<(...args: unknown[]) => unknown>(),
    actualizar: vi.fn<(...args: unknown[]) => unknown>(),
    parchear: vi.fn<(...args: unknown[]) => unknown>(),
    eliminar: vi.fn<(...args: unknown[]) => unknown>(),
  },
}))

const GRUPO = {
  id: 1,
  nombre: 'Desarrollo',
  tareas: 1,
  estados: [{ id: 10, nombre: 'Pendiente', posicion: 1, tareas: 1 }],
}

function tarea(id: number, nombre: string, enGrupo: boolean) {
  return {
    id,
    nombre,
    prioridad: null,
    descripcion: 'd',
    fecha_creacion: '2026-11-10T09:00:00',
    fecha_vencimiento: null,
    etiquetas: [],
    asignados: [],
    tipo: null,
    oportunidad: null,
    completada: false,
    subtareas: [],
    grupo_estados: enGrupo ? { id: 1, nombre: 'Desarrollo' } : null,
    estado: enGrupo ? { id: 10, nombre: 'Pendiente' } : null,
    workflow: null,
    subestado: null,
    congelada_en: null,
  }
}

const EN_GRUPO = tarea(1, 'Con grupo', true)
const SUELTA_A = tarea(2, 'Suelta axas uno', false)
const SUELTA_B = tarea(3, 'Suelta axas dos', false)

const VISTA = 'gestor-tareas:vista-tareas'
let contenedor: VueWrapper | null = null

async function montarEnTablero(tareas: unknown[]): Promise<VueWrapper> {
  vi.mocked(clienteApi.obtener).mockImplementation((ruta) => {
    if (ruta === '/grupos-estados') return Promise.resolve([structuredClone(GRUPO)])
    if (ruta === '/tareas') return Promise.resolve(structuredClone(tareas))
    return Promise.resolve([])
  })
  localStorage.setItem(VISTA, 'tablero')
  const pinia = createPinia()
  setActivePinia(pinia)
  const enrutador = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/tareas', component: { template: '<div />' } },
      { path: '/ajustes/grupos-estados', component: { template: '<div />' } },
    ],
  })
  await enrutador.push('/tareas')
  contenedor = mount(VistaTareas, {
    global: { plugins: [pinia, enrutador] },
    attachTo: document.body,
  })
  await flushPromises()
  return contenedor
}

function aviso(): HTMLElement | null {
  return document.body.querySelector<HTMLElement>('[data-aviso-sin-grupo]')
}

function texto(elemento: HTMLElement): string {
  return elemento.textContent!.replace(/\s+/g, ' ').trim()
}

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.removeItem(VISTA)
})

afterEach(() => {
  contenedor?.unmount()
  contenedor = null
  document.body.innerHTML = ''
  localStorage.removeItem(VISTA)
})

describe('VistaTareas: aviso del tablero por las tareas sin grupo de estados', () => {
  it('avisa de cuántas tareas no se ven en el tablero por no tener grupo', async () => {
    await montarEnTablero([EN_GRUPO, SUELTA_A, SUELTA_B])

    expect(texto(aviso()!)).toBe(
      '2 tareas no se ven en el tablero porque no tienen grupo de estados. Verlas en la lista',
    )
  })

  it('en singular si es una sola', async () => {
    await montarEnTablero([EN_GRUPO, SUELTA_A])

    expect(texto(aviso()!)).toBe(
      '1 tarea no se ve en el tablero porque no tiene grupo de estados. Verla en la lista',
    )
  })

  it('"Verlas en la lista" cambia a la vista de lista, donde se ven', async () => {
    const envoltorio = await montarEnTablero([EN_GRUPO, SUELTA_A, SUELTA_B])

    aviso()!.querySelector('button')!.click()
    await flushPromises()

    expect(
      document.body
        .querySelector('button[aria-label="Ver como lista"]')!
        .getAttribute('aria-pressed'),
    ).toBe('true')
    expect(envoltorio.text()).toContain('Suelta axas uno')
    expect(envoltorio.text()).toContain('Suelta axas dos')
  })

  it('solo cuenta las que pasan los filtros', async () => {
    const envoltorio = await montarEnTablero([EN_GRUPO, SUELTA_A, SUELTA_B])

    await envoltorio.get('#filtro-buscar').setValue('uno')
    await flushPromises()
    expect(texto(aviso()!)).toContain('1 tarea no se ve en el tablero')

    await envoltorio.get('#filtro-buscar').setValue('Con grupo')
    await flushPromises()
    expect(aviso()).toBeNull()
  })

  it('sin tareas sueltas no hay aviso', async () => {
    await montarEnTablero([EN_GRUPO])

    expect(aviso()).toBeNull()
  })
})
