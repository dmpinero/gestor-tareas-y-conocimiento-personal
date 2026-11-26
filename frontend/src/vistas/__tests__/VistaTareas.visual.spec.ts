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

// Ancho medido de la vista: 0 (como jsdom) pinta la tabla; estrecho, tarjetas.
const ancho = vi.hoisted(() => ({ valor: 0 }))
vi.mock('@vueuse/core', async (original) => {
  const modulo = await original<typeof import('@vueuse/core')>()
  const { ref } = await import('vue')
  return {
    ...modulo,
    useElementSize: () => ({ width: ref(ancho.valor), height: ref(0), stop: () => {} }),
  }
})

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
    descripcion: 'Una descripción larga que no debe alargar la fila más de dos líneas',
    subestado: 'Pendiente recibir RFP AXA',
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
  ancho.valor = 0
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

describe('lista: legibilidad de las filas', () => {
  it('las insignias van debajo del nombre, no a su lado', async () => {
    await montar()
    const fila = filaDe('Preparar demo')
    const insignias = fila.querySelector('[data-insignias-tarea]')
    expect(insignias?.querySelector('[data-insignia-hibernada]')).not.toBeNull()
    // Nombre e insignias comparten columna: el nombre ocupa todo el ancho.
    expect(insignias?.parentElement).toBe(fila.querySelector('[data-nombre-tarea]')?.parentElement)
    expect(insignias?.parentElement?.className).not.toContain('flex ')
  })

  it('sin insignias no deja hueco bajo el nombre', async () => {
    await montar()
    expect(filaDe('Revisar contrato').querySelector('[data-insignias-tarea]')).toBeNull()
  })

  it('la descripción se corta en dos líneas y se lee entera al pasar el ratón', async () => {
    await montar()
    const descripcion = filaDe('Preparar demo').querySelector('[data-descripcion-tarea]')
    expect(descripcion?.className).toContain('line-clamp-2')
    expect(descripcion?.getAttribute('title')).toBe(
      'Una descripción larga que no debe alargar la fila más de dos líneas',
    )
  })

  it('la columna Nombre queda fija al desplazar la tabla en horizontal', async () => {
    await montar()
    const cabecera = document.body.querySelector('thead th')
    expect(cabecera?.className).toMatch(/\bsticky\b/)
    expect(cabecera?.className).toContain('left-0')
    const celda = filaDe('Preparar demo').querySelector('td')
    expect(celda?.className).toMatch(/\bsticky\b/)
    // Hereda el fondo (opaco) de su fila para tapar lo que pasa por debajo.
    expect(celda?.className).toContain('bg-inherit')
    expect(filaDe('Preparar demo').className).not.toContain('/40')
  })

  it('la columna de acciones queda fija a la derecha para que la fija del nombre no la tape', async () => {
    await montar()
    const cabeceras = document.body.querySelectorAll('thead th')
    const cabecera = cabeceras[cabeceras.length - 1]
    expect(cabecera?.className).toMatch(/\bsticky\b/)
    expect(cabecera?.className).toContain('right-0')
    const celdas = filaDe('Preparar demo').querySelectorAll('td')
    const acciones = celdas[celdas.length - 1]
    expect(acciones?.className).toMatch(/\bsticky\b/)
    expect(acciones?.className).toContain('right-0')
    expect(acciones?.className).toContain('bg-inherit')
  })

  it('la fecha de creación es corta y la completa sale al pasar el ratón', async () => {
    await montar()
    const fecha = filaDe('Preparar demo').querySelector('[data-fecha-creacion]')
    expect(fecha?.querySelector('[aria-hidden="true"]')?.textContent).toBe('10 nov')
    expect(fecha?.querySelector('.sr-only')?.textContent).toBe('10/11/2026 09:30:00')
    expect(fecha?.getAttribute('title')).toBe('10/11/2026 09:30:00')
  })

  it('el subestado no parte línea: se trunca y se lee entero al pasar el ratón', async () => {
    await montar()
    const pildora = filaDe('Preparar demo').querySelector('[data-testid="pildora-subestado"]')
    expect(pildora?.className).toContain('whitespace-nowrap')
    expect(pildora?.className).toContain('max-w-48')
    expect(pildora?.className).not.toContain('max-w-full')
    const boton = pildora?.querySelector('button')
    expect(boton?.className).toContain('truncate')
    expect(boton?.getAttribute('title')).toBe('Pendiente recibir RFP AXA')
  })
})

describe('lista en pantallas estrechas', () => {
  it('con la vista estrecha muestra tarjetas en vez de la tabla', async () => {
    ancho.valor = 390
    await montar()
    expect(document.body.querySelector('[data-testid="superficie-tabla"] table')).toBeNull()
    const tarjetas = [...document.body.querySelectorAll('[data-tarjeta-tarea]')]
    expect(
      tarjetas.map((t) => t.querySelector('[data-nombre-tarea]')?.textContent?.trim()),
    ).toEqual(['Preparar demo', 'Llamar a cliente', 'Revisar contrato'])
    const primera = tarjetas[0]!
    expect(primera.querySelector('[data-testid="pildora-estado"]')?.textContent?.trim()).toBe(
      'En curso',
    )
    expect(primera.querySelector('[data-testid="pildora-prioridad"]')?.textContent?.trim()).toBe(
      '2',
    )
    expect(primera.querySelector('[data-insignia-hibernada]')).not.toBeNull()
  })

  it('pulsar una tarjeta abre el detalle de su tarea', async () => {
    ancho.valor = 390
    await montar()
    const tarjeta = document.body.querySelector<HTMLElement>('[data-tarjeta-tarea]')!
    tarjeta.click()
    await flushPromises()
    const dialogo = document.body.querySelector('[role="dialog"]')
    expect(dialogo?.textContent).toContain('Preparar demo')
  })

  it('las tarjetas mantienen los grupos plegables y el alta rápida', async () => {
    ancho.valor = 390
    await montar()
    expect(document.body.querySelector('[data-alta-rapida]')).not.toBeNull()
    const grupo = [...document.body.querySelectorAll('button[aria-expanded]')].find((b) =>
      b.textContent?.includes('Pendientes'),
    )
    expect(grupo).toBeDefined()
  })
})
