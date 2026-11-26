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
    vinculadas: [],
    subestado: null,
    congelada_en: null,
    hibernada_desde: null,
    ...cambios,
  }
}

const GRUPO = { id: 1, nombre: 'Flujo' }
const GRUPO_CATALOGO = {
  ...GRUPO,
  tareas: 3,
  estados: [
    { id: 11, nombre: 'En curso', posicion: 1, tareas: 2 },
    { id: 12, nombre: 'Hecho', posicion: 2, tareas: 1 },
  ],
}
const TAREAS = [
  tarea(1, 'Preparar demo', {
    prioridad: 2,
    tipo: 'oportunidad',
    grupo_estados: GRUPO,
    estado: { id: 11, nombre: 'En curso' },
    hibernada_desde: '2026-11-20T10:00:00Z',
  }),
  tarea(2, 'Revisar contrato', {
    prioridad: 2,
    completada: true,
    grupo_estados: GRUPO,
    estado: { id: 12, nombre: 'Hecho' },
    subtareas: [
      {
        id: 20,
        nombre: 'Leer anexo',
        asignado: null,
        prioridad: 2,
        resuelta: false,
        comentarios: 0,
      },
    ],
  }),
  tarea(3, 'Llamar a cliente', {
    grupo_estados: GRUPO,
    estado: { id: 11, nombre: 'En curso' },
    hibernada_desde: '2026-11-21T10:00:00Z',
  }),
]

// Texto que lee el lector de pantalla: sin lo marcado aria-hidden.
function textoAccesible(elemento: Element | null | undefined): string {
  const copia = elemento?.cloneNode(true) as Element | undefined
  copia?.querySelectorAll('[aria-hidden="true"]').forEach((nodo) => nodo.remove())
  return copia?.textContent?.replace(/\s+/g, ' ').trim() ?? ''
}

let contenedor: VueWrapper | null = null

async function montar(ruta = '/tareas'): Promise<VueWrapper> {
  vi.mocked(clienteApi.obtener).mockImplementation((r) => {
    if (r === '/tareas') return Promise.resolve(structuredClone(TAREAS))
    if (r === '/grupos-estados') return Promise.resolve(structuredClone([GRUPO_CATALOGO]))
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

function dialogoTitulado(titulo: string): HTMLElement {
  const dialogo = [...document.body.querySelectorAll<HTMLElement>('[role="dialog"]')].find(
    (d) => d.querySelector('h2')?.textContent?.trim() === titulo,
  )
  if (!dialogo) throw new Error(`No se encontró el diálogo "${titulo}"`)
  return dialogo
}

function tareasDe(dialogo: HTMLElement): string[] {
  return [...dialogo.querySelectorAll('[data-tabla="Tareas"] tbody button')].map(
    (b) => b.textContent?.trim() ?? '',
  )
}

async function pulsar(dentro: Element, nombreAccesible: string): Promise<void> {
  const boton = dentro.querySelector<HTMLButtonElement>(`button[aria-label="${nombreAccesible}"]`)
  if (!boton) throw new Error(`No hay botón «${nombreAccesible}»`)
  boton.click()
  await flushPromises()
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

const CASOS = [
  {
    boton: 'Ver tareas: Hibernada',
    titulo: 'Tareas hibernadas',
    tareas: ['Preparar demo', 'Llamar a cliente'],
  },
  {
    boton: 'Ver tareas y subtareas con la prioridad 2',
    titulo: 'Prioridad: 2',
    tareas: ['Preparar demo', 'Revisar contrato'],
  },
  {
    boton: 'Ver tareas de tipo Oportunidad',
    titulo: 'Tipo: Oportunidad',
    tareas: ['Preparar demo'],
  },
  {
    boton: 'Ver tareas en el estado En curso',
    titulo: 'Estado: En curso',
    tareas: ['Preparar demo', 'Llamar a cliente'],
  },
] as const

describe('VistaTareas: píldoras pulsables', () => {
  it.each(CASOS)(
    'en la fila, «$boton» abre la modal con sus tareas y cuántas son, sin abrir el detalle',
    async ({ boton, titulo, tareas }) => {
      await montar()

      await pulsar(filaDe('Preparar demo'), boton)

      const modal = dialogoTitulado(titulo)
      expect(textoAccesible(modal.querySelector('h3'))).toBe(`Tareas (${tareas.length})`)
      expect(tareasDe(modal)).toEqual(tareas)
      expect(document.body.querySelectorAll('[role="dialog"]')).toHaveLength(1)
    },
  )

  it.each([
    ...CASOS,
    {
      boton: 'Ver tareas: Pendiente',
      titulo: 'Tareas pendientes',
      tareas: ['Preparar demo', 'Llamar a cliente'],
    },
  ])('en la cabecera del detalle, «$boton» abre la modal con sus tareas', async (caso) => {
    await montar('/tareas?tarea=1')

    await pulsar(dialogoTitulado('Preparar demo'), caso.boton)

    expect(tareasDe(dialogoTitulado(caso.titulo))).toEqual(caso.tareas)
  })

  it('en la cabecera del detalle de una completada, «Completada» lista las completadas', async () => {
    await montar('/tareas?tarea=2')

    await pulsar(dialogoTitulado('Revisar contrato'), 'Ver tareas: Completada')

    expect(tareasDe(dialogoTitulado('Tareas completadas'))).toEqual(['Revisar contrato'])
  })

  it('en el detalle, la prioridad de una subtarea abre la modal con esa prioridad', async () => {
    await montar('/tareas?tarea=2')

    // Fila (tabla) o tarjeta de la subtarea, según el ancho: la más interna.
    const subtarea = [
      ...dialogoTitulado('Revisar contrato').querySelectorAll(
        'tr, [data-testid="tarjeta-subtarea"]',
      ),
    ]
      .reverse()
      .find((el) => el.textContent?.includes('Leer anexo'))!
    await pulsar(subtarea, 'Ver tareas y subtareas con la prioridad 2')

    const modal = dialogoTitulado('Prioridad: 2')
    expect(tareasDe(modal)).toEqual(['Preparar demo', 'Revisar contrato'])
    expect(
      [...modal.querySelectorAll('[data-tabla="Subtareas"] tbody button')].map((b) =>
        b.getAttribute('aria-label'),
      ),
    ).toEqual(['Abrir la tarea Revisar contrato (subtarea Leer anexo)'])
  })

  it('en el tablero, «Hibernada» de la tarjeta abre la modal de tareas hibernadas', async () => {
    await montar()
    await pulsar(document.body, 'Ver como tablero')

    const tarjeta = [...document.body.querySelectorAll('[data-tarjeta]')].find((t) =>
      t.textContent?.includes('Llamar a cliente'),
    )!
    await pulsar(tarjeta, 'Ver tareas: Hibernada')

    expect(tareasDe(dialogoTitulado('Tareas hibernadas'))).toEqual([
      'Preparar demo',
      'Llamar a cliente',
    ])
  })
})
