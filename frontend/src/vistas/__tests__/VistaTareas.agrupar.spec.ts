import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { clienteApi } from '@/api/cliente'
import { colorEtiqueta } from '@/lib/coloresTarea'
import { exportarTablaExcel } from '@/lib/exportarTabla'
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

const BASE = {
  prioridad: null,
  descripcion: 'd',
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
  congelada_en: null,
}

function tarea(id: number, nombre: string, subestado: string | null, completada = false) {
  return {
    ...BASE,
    id,
    nombre,
    subestado,
    completada,
    fecha_creacion: `2026-11-1${id}T09:00:00`,
  }
}

// Orden de entrada distinto del alfabético para comprobar el orden de los grupos.
const TAREAS = [
  tarea(1, 'Carta', 'Revisión'),
  tarea(2, 'Acta', null),
  tarea(3, 'Boletín', 'Bloqueado'),
  tarea(4, 'Dosier', 'Revisión'),
  tarea(5, 'Hecha', 'Bloqueado', true),
]
const SUBESTADOS = [
  { id: 1, nombre: 'Bloqueado' },
  { id: 2, nombre: 'Revisión' },
]
const AGRUPAR = 'gestor-tareas:agrupar-subestado-tareas'
const PLEGADOS = 'gestor-tareas:subestados-plegados-tareas'
const COLUMNAS_OCULTAS = 'gestor-tareas:columnas-ocultas-tareas'
const VISTA = 'gestor-tareas:vista-tareas'
const GRUPOS_PLEGADOS = 'gestor-tareas:grupos-plegados-tareas'
const CLAVES = [AGRUPAR, PLEGADOS, COLUMNAS_OCULTAS, VISTA, GRUPOS_PLEGADOS]

let contenedor: VueWrapper | null = null

async function montar(tareas: unknown[] = TAREAS): Promise<VueWrapper> {
  vi.mocked(clienteApi.obtener).mockImplementation((ruta) => {
    if (ruta === '/subestados') return Promise.resolve(structuredClone(SUBESTADOS))
    if (ruta === '/etiquetas' || ruta === '/personas' || ruta === '/workflows') {
      return Promise.resolve([])
    }
    if (ruta === '/grupos-estados') return Promise.resolve([])
    return Promise.resolve(structuredClone(tareas))
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
  await enrutador.push('/tareas')
  contenedor = mount(VistaTareas, {
    global: { plugins: [pinia, enrutador] },
    attachTo: document.body,
  })
  await flushPromises()
  return contenedor
}

function botonAgrupar(envoltorio: VueWrapper) {
  return envoltorio.get('button[data-testid="agrupar-subestado"]')
}

/** Nombres de las filas de tareas en el orden de la pantalla. */
function nombres(envoltorio: VueWrapper): string[] {
  return envoltorio
    .findAll('tbody tr[data-fila-tarea] [data-nombre-tarea]')
    .map((nombre) => nombre.text())
}

/** Secciones por subestado de un grupo de la tabla: cabecera y filas. */
function secciones(envoltorio: VueWrapper, grupo = 'pendientes') {
  return envoltorio.findAll(`tbody[data-grupo="${grupo}"][data-subgrupo]`).map((cuerpo) => ({
    clave: cuerpo.attributes('data-subgrupo'),
    cabecera: cuerpo.get('th button').text(),
    filas: cuerpo.findAll('[data-nombre-tarea]').map((nombre) => nombre.text()),
  }))
}

function cabeceraSeccion(envoltorio: VueWrapper, clave: string, grupo = 'pendientes') {
  return envoltorio.get(`tbody[data-grupo="${grupo}"][data-subgrupo="${clave}"] th button`)
}

async function agrupar(envoltorio: VueWrapper): Promise<void> {
  await botonAgrupar(envoltorio).trigger('click')
  await flushPromises()
}

beforeEach(() => {
  vi.clearAllMocks()
  for (const clave of CLAVES) localStorage.removeItem(clave)
})

afterEach(() => {
  contenedor?.unmount()
  contenedor = null
  document.body.innerHTML = ''
  for (const clave of CLAVES) localStorage.removeItem(clave)
})

describe('VistaTareas: agrupar por subestado', () => {
  it('sin activar, el botón no está pulsado y la tabla no tiene secciones', async () => {
    const envoltorio = await montar()

    const boton = botonAgrupar(envoltorio)
    expect(boton.text()).toBe('Agrupar por subestado')
    expect(boton.attributes('aria-pressed')).toBe('false')
    expect(envoltorio.findAll('tbody[data-subgrupo]')).toEqual([])
    expect(nombres(envoltorio)).toEqual(['Carta', 'Acta', 'Boletín', 'Dosier', 'Hecha'])
  })

  it('solo se ofrece en la vista de lista', async () => {
    localStorage.setItem(VISTA, 'tablero')
    const envoltorio = await montar()

    expect(envoltorio.find('button[data-testid="agrupar-subestado"]').exists()).toBe(false)
  })

  it('al activarlo, cada grupo se divide en secciones por subestado con su nombre y cuántas tiene', async () => {
    const envoltorio = await montar()
    await agrupar(envoltorio)

    expect(botonAgrupar(envoltorio).attributes('aria-pressed')).toBe('true')
    expect(secciones(envoltorio)).toEqual([
      { clave: 'subestado:Bloqueado', cabecera: 'Bloqueado · 1', filas: ['Boletín'] },
      { clave: 'subestado:Revisión', cabecera: 'Revisión · 2', filas: ['Carta', 'Dosier'] },
      { clave: 'sin', cabecera: 'Sin subestado · 1', filas: ['Acta'] },
    ])
    // Las completadas se agrupan dentro de su propio grupo; sin grupos vacíos.
    expect(secciones(envoltorio, 'completadas')).toEqual([
      { clave: 'subestado:Bloqueado', cabecera: 'Bloqueado · 1', filas: ['Hecha'] },
    ])
    const pildora = cabeceraSeccion(envoltorio, 'subestado:Revisión').get(
      '[data-testid="pildora-subestado"]',
    )
    for (const clase of colorEtiqueta('Revisión').split(' ')) {
      expect(pildora.classes()).toContain(clase)
    }
  })

  it('una línea horizontal separa cada sección de la anterior, sin línea en la primera', async () => {
    const envoltorio = await montar()
    await agrupar(envoltorio)

    const conLinea = envoltorio
      .findAll('tbody[data-grupo="pendientes"][data-subgrupo]')
      .map((cuerpo) => cuerpo.find('tr[data-separador-subestado]').exists())
    expect(conLinea).toEqual([false, true, true])
    const fila = envoltorio.get('tbody[data-subgrupo="sin"] tr[data-separador-subestado]')
    expect(fila.classes()).toEqual(expect.arrayContaining(['border-t-2', 'border-foreground/20']))
    // Un grupo con una sola sección no lleva línea.
    expect(
      envoltorio.find('tbody[data-grupo="completadas"] tr[data-separador-subestado]').exists(),
    ).toBe(false)
  })

  it('la cabecera de la sección es un th de grupo de filas que ocupa todas las columnas visibles', async () => {
    const envoltorio = await montar()
    await agrupar(envoltorio)

    const th = envoltorio.get('tbody[data-subgrupo="sin"] th')
    expect(th.attributes('scope')).toBe('rowgroup')
    // 10 columnas más la de acciones.
    expect(th.attributes('colspan')).toBe('11')
    envoltorio.unmount()
    contenedor = null

    localStorage.setItem(COLUMNAS_OCULTAS, JSON.stringify(['prioridad', 'descripcion']))
    const otro = await montar()
    expect(otro.get('tbody[data-subgrupo="sin"] th').attributes('colspan')).toBe('9')
  })

  it('pliega y despliega una sección con aria-expanded, sin perder el foco', async () => {
    const envoltorio = await montar()
    await agrupar(envoltorio)

    const cabecera = cabeceraSeccion(envoltorio, 'subestado:Revisión')
    expect(cabecera.attributes('aria-expanded')).toBe('true')
    const controlada = document.getElementById(cabecera.attributes('aria-controls')!)
    expect(controlada?.getAttribute('data-subgrupo')).toBe('subestado:Revisión')

    ;(cabecera.element as HTMLButtonElement).focus()
    await cabecera.trigger('click')
    await flushPromises()
    expect(cabecera.attributes('aria-expanded')).toBe('false')
    expect(document.activeElement).toBe(cabecera.element)
    expect(nombres(envoltorio)).toEqual(['Boletín', 'Acta', 'Hecha'])
    // Plegada sigue diciendo cuántas tareas tiene.
    expect(secciones(envoltorio).find((s) => s.clave === 'subestado:Revisión')?.cabecera).toBe(
      'Revisión · 2',
    )

    await cabecera.trigger('click')
    await flushPromises()
    expect(cabecera.attributes('aria-expanded')).toBe('true')
    expect(nombres(envoltorio)).toEqual(['Boletín', 'Carta', 'Dosier', 'Acta', 'Hecha'])
  })

  it('activar y desactivar deja el foco en el botón y vuelve a la tabla sin secciones', async () => {
    const envoltorio = await montar()
    const boton = botonAgrupar(envoltorio)
    ;(boton.element as HTMLButtonElement).focus()

    await agrupar(envoltorio)
    expect(document.activeElement).toBe(boton.element)
    await agrupar(envoltorio)
    expect(document.activeElement).toBe(boton.element)
    expect(boton.attributes('aria-pressed')).toBe('false')
    expect(envoltorio.findAll('tbody[data-subgrupo]')).toEqual([])
    expect(nombres(envoltorio)).toEqual(['Carta', 'Acta', 'Boletín', 'Dosier', 'Hecha'])
  })

  it('la búsqueda y la ordenación se aplican dentro de las secciones', async () => {
    const envoltorio = await montar()
    await agrupar(envoltorio)

    const nombre = envoltorio.findAll('th button').find((b) => b.text() === 'Nombre')!
    await nombre.trigger('click')
    await nombre.trigger('click')
    expect(secciones(envoltorio).find((s) => s.clave === 'subestado:Revisión')?.filas).toEqual([
      'Dosier',
      'Carta',
    ])

    await envoltorio.get('#filtro-buscar').setValue('Carta')
    await flushPromises()
    expect(secciones(envoltorio)).toEqual([
      { clave: 'subestado:Revisión', cabecera: 'Revisión · 1', filas: ['Carta'] },
    ])
    expect(secciones(envoltorio, 'completadas')).toEqual([])
  })

  it('recuerda en este navegador si se agrupa y qué secciones están plegadas', async () => {
    const envoltorio = await montar()
    await agrupar(envoltorio)
    await cabeceraSeccion(envoltorio, 'sin').trigger('click')
    await flushPromises()

    expect(localStorage.getItem(AGRUPAR)).toBe('true')
    expect(JSON.parse(localStorage.getItem(PLEGADOS)!)).toEqual(['pendientes|sin'])
    envoltorio.unmount()
    contenedor = null

    const otro = await montar()
    expect(botonAgrupar(otro).attributes('aria-pressed')).toBe('true')
    expect(cabeceraSeccion(otro, 'sin').attributes('aria-expanded')).toBe('false')
    expect(cabeceraSeccion(otro, 'subestado:Bloqueado').attributes('aria-expanded')).toBe('true')
    expect(nombres(otro)).not.toContain('Acta')
  })

  it('ignora preferencias guardadas desconocidas o mal formadas', async () => {
    localStorage.setItem(AGRUPAR, 'quizá')
    localStorage.setItem(PLEGADOS, JSON.stringify(['pendientes|sin']))
    const sinAgrupar = await montar()
    expect(botonAgrupar(sinAgrupar).attributes('aria-pressed')).toBe('false')
    sinAgrupar.unmount()
    contenedor = null

    localStorage.setItem(AGRUPAR, 'true')
    localStorage.setItem(
      PLEGADOS,
      JSON.stringify(['otro|sin', 'pendientes|nada', 42, 'sin', 'completadas|subestado:Bloqueado']),
    )
    const envoltorio = await montar()
    expect(cabeceraSeccion(envoltorio, 'sin').attributes('aria-expanded')).toBe('true')
    expect(
      cabeceraSeccion(envoltorio, 'subestado:Bloqueado', 'completadas').attributes('aria-expanded'),
    ).toBe('false')
    envoltorio.unmount()
    contenedor = null

    localStorage.setItem(PLEGADOS, '{no es json')
    const roto = await montar()
    expect(nombres(roto)).toEqual(['Boletín', 'Carta', 'Dosier', 'Acta', 'Hecha'])
  })

  it('la exportación sigue siendo la lista de todas las filas filtradas', async () => {
    const envoltorio = await montar()
    await agrupar(envoltorio)
    await cabeceraSeccion(envoltorio, 'subestado:Revisión').trigger('click')
    await flushPromises()

    await envoltorio.get('button[aria-label="Exportar a Excel"]').trigger('click')
    await flushPromises()

    const [, , filas] = vi.mocked(exportarTablaExcel).mock.calls[0]!
    expect((filas as unknown[][]).map((fila) => fila[0])).toEqual([
      'Carta',
      'Acta',
      'Boletín',
      'Dosier',
      'Hecha',
    ])
  })
})
