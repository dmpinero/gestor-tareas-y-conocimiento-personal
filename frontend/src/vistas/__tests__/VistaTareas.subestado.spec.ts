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
  // El grupo de estados es obligatorio al guardar desde el formulario.
  grupo_estados: { id: 50, nombre: 'General' },
  estado: { id: 500, nombre: 'Por hacer' },
  workflow: null,
  vinculadas: [],
  congelada_en: null,
}

const GRUPO_GENERAL = {
  id: 50,
  nombre: 'General',
  tareas: 3,
  estados: [{ id: 500, nombre: 'Por hacer', posicion: 1, tareas: 3 }],
}
const BLOQUEADA = {
  ...BASE,
  id: 1,
  nombre: 'Bloqueada',
  fecha_creacion: '2026-11-10T09:00:00',
  subestado: 'Bloqueado',
}
const EN_PAUSA = {
  ...BASE,
  id: 2,
  nombre: 'En pausa',
  fecha_creacion: '2026-11-11T09:00:00',
  subestado: 'En espera',
}
const SIN_SUBESTADO = {
  ...BASE,
  id: 3,
  nombre: 'Sin subestado',
  fecha_creacion: '2026-11-12T09:00:00',
  subestado: null,
}
const TAREAS = [BLOQUEADA, EN_PAUSA, SIN_SUBESTADO]
const SUBESTADOS = [
  { id: 1, nombre: 'Bloqueado' },
  { id: 2, nombre: 'En espera' },
]
const COLUMNAS_OCULTAS = 'gestor-tareas:columnas-ocultas-tareas'
const VISTA = 'gestor-tareas:vista-tareas'

let contenedor: VueWrapper | null = null

async function montar(
  tareas: unknown[] = TAREAS,
  grupos: unknown[] = [GRUPO_GENERAL],
): Promise<VueWrapper> {
  vi.mocked(clienteApi.obtener).mockImplementation((ruta) => {
    if (ruta === '/subestados') return Promise.resolve(structuredClone(SUBESTADOS))
    if (ruta === '/etiquetas' || ruta === '/personas' || ruta === '/workflows') {
      return Promise.resolve([])
    }
    if (ruta === '/grupos-estados') return Promise.resolve(structuredClone(grupos))
    if (String(ruta).endsWith('/comentarios')) return Promise.resolve([])
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

function cabeceras(envoltorio: VueWrapper): string[] {
  return envoltorio
    .findAll('thead th')
    .map((th) => th.text().trim())
    .filter((texto) => texto !== '' && texto !== 'Acciones')
}

function nombres(envoltorio: VueWrapper): string[] {
  return envoltorio.findAll('tbody tr[data-fila-tarea]').map((fila) => fila.get('td').text())
}

function celdasSubestado(envoltorio: VueWrapper): string[] {
  return envoltorio.findAll('td[data-columna="subestado"]').map((celda) => celda.text())
}

function boton(envoltorio: VueWrapper, texto: string) {
  const encontrado = envoltorio.findAll('button').find((b) => b.text() === texto)
  if (!encontrado) throw new Error(`No se encontró el botón "${texto}"`)
  return encontrado
}

function panel(): HTMLElement {
  const elemento = document.body.querySelector<HTMLElement>('[role="dialog"]')
  if (!elemento) throw new Error('No se abrió el panel')
  return elemento
}

async function escribir(elemento: HTMLInputElement, valor: string): Promise<void> {
  elemento.value = valor
  elemento.dispatchEvent(new Event('input'))
  await flushPromises()
}

async function pulsarEnter(elemento: HTMLInputElement): Promise<void> {
  elemento.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
  await flushPromises()
}

async function enviar(): Promise<void> {
  panel().querySelector('form')!.dispatchEvent(new Event('submit'))
  await flushPromises()
}

function chipsSubestado(): string[] {
  const lista = panel().querySelector('ul[aria-label="Subestado"]')
  return lista
    ? [...lista.querySelectorAll('[data-testid="chip"]')].map((c) => c.textContent!.trim())
    : []
}

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.removeItem(COLUMNAS_OCULTAS)
  localStorage.removeItem(VISTA)
})

afterEach(() => {
  contenedor?.unmount()
  contenedor = null
  document.body.innerHTML = ''
  localStorage.removeItem(COLUMNAS_OCULTAS)
  localStorage.removeItem(VISTA)
})

describe('VistaTareas: subestado en la tabla', () => {
  it('muestra la columna "Subestado" con una píldora de su color, o "—" sin subestado', async () => {
    const envoltorio = await montar()

    expect(cabeceras(envoltorio)).toContain('Subestado')
    expect(cabeceras(envoltorio).indexOf('Subestado')).toBe(
      cabeceras(envoltorio).indexOf('Asignado a') + 1,
    )
    expect(celdasSubestado(envoltorio)).toEqual(['Bloqueado', 'En espera', '—'])
    const pildora = envoltorio.get('[data-testid="pildora-subestado"]')
    for (const clase of colorEtiqueta('Bloqueado').split(' ')) {
      expect(pildora.classes()).toContain(clase)
    }
  })

  it('la columna se puede ocultar como las demás', async () => {
    localStorage.setItem(COLUMNAS_OCULTAS, JSON.stringify(['subestado']))
    const envoltorio = await montar()

    expect(cabeceras(envoltorio)).not.toContain('Subestado')
    expect(celdasSubestado(envoltorio)).toEqual([])
  })

  it('ordena por subestado, con las tareas sin subestado al final', async () => {
    const envoltorio = await montar([SIN_SUBESTADO, EN_PAUSA, BLOQUEADA])

    const cabecera = envoltorio.findAll('th button').find((b) => b.text() === 'Subestado')!
    await cabecera.trigger('click')
    expect(nombres(envoltorio)).toEqual(['Bloqueada', 'En pausa', 'Sin subestado'])
    await cabecera.trigger('click')
    expect(nombres(envoltorio)).toEqual(['En pausa', 'Bloqueada', 'Sin subestado'])
  })

  it('filtra por subestado, incluida la opción "Sin subestado"', async () => {
    const envoltorio = await montar()
    await boton(envoltorio, 'Filtrar').trigger('click')
    await flushPromises()

    async function alternar(opcion: string): Promise<void> {
      const disparador = envoltorio.get('button[aria-label^="Filtrar por subestado: "]')
      expect(disparador.attributes('aria-label')).toBeTruthy()
      await disparador.trigger('click')
      await flushPromises()
      const etiqueta = [
        ...document.body.querySelectorAll<HTMLLabelElement>('[data-slot="popover-content"] label'),
      ].find((label) => label.textContent?.trim() === opcion)!
      document.getElementById(etiqueta.htmlFor)!.click()
      await flushPromises()
      await disparador.trigger('click')
      await flushPromises()
    }

    expect(envoltorio.get('button[aria-label^="Filtrar por subestado: "]').text()).toBe(
      'Todos los subestados',
    )
    await alternar('Bloqueado')
    expect(nombres(envoltorio)).toEqual(['En pausa', 'Sin subestado'])
    await alternar('Sin subestado')
    expect(nombres(envoltorio)).toEqual(['En pausa'])
    expect(envoltorio.get('[data-testid="filtros-activos"]').text()).toBe('1 activo')

    await boton(envoltorio, 'Limpiar filtros').trigger('click')
    await flushPromises()
    expect(nombres(envoltorio)).toEqual(['Bloqueada', 'En pausa', 'Sin subestado'])
  })

  it('exporta el subestado como texto, o "—" sin subestado', async () => {
    const envoltorio = await montar()

    await envoltorio.get('button[aria-label="Exportar a Excel"]').trigger('click')

    const [, columnas, filas] = vi.mocked(exportarTablaExcel).mock.calls[0]!
    const indice = (columnas as string[]).indexOf('Subestado')
    expect(indice).toBeGreaterThan(0)
    expect((filas as unknown[][]).map((fila) => fila[indice])).toEqual([
      'Bloqueado',
      'En espera',
      '—',
    ])
  })
})

describe('VistaTareas: subestado en el formulario', () => {
  it('el alta envía el subestado elegido (creándolo si es nuevo) y null sin subestado', async () => {
    const envoltorio = await montar([])
    vi.mocked(clienteApi.crear).mockResolvedValue({ ...BLOQUEADA, id: 9 })

    await boton(envoltorio, 'Crear tarea').trigger('click')
    await flushPromises()
    await escribir(panel().querySelector('input[placeholder="Nombre"]')!, 'Nueva')
    await escribir(panel().querySelector('textarea[placeholder="Descripción"]')!, 'd')
    const campo = panel().querySelector<HTMLInputElement>('#subestado')!
    await escribir(campo, 'Esperando cliente')
    await pulsarEnter(campo)
    expect(chipsSubestado()).toEqual(['Esperando cliente'])
    await enviar()

    expect(clienteApi.crear).toHaveBeenCalledWith(
      '/tareas',
      expect.objectContaining({ nombre: 'Nueva', subestado: 'Esperando cliente' }),
    )
    // Tras guardar se vuelve a pedir el catálogo por si el subestado es nuevo.
    expect(clienteApi.obtener).toHaveBeenCalledWith('/subestados')
  })

  it('la edición carga el subestado de la tarea y quitarlo envía null', async () => {
    const envoltorio = await montar()
    vi.mocked(clienteApi.actualizar).mockResolvedValue({ ...BLOQUEADA, subestado: null })

    await envoltorio.get('button[aria-label="Acciones de la tarea Bloqueada"]').trigger('click')
    await flushPromises()
    document.body
      .querySelector<HTMLButtonElement>('button[aria-label="Editar tarea Bloqueada"]')!
      .click()
    await flushPromises()
    expect(chipsSubestado()).toEqual(['Bloqueado'])
    panel().querySelector<HTMLButtonElement>('button[aria-label="Quitar Bloqueado"]')!.click()
    await flushPromises()
    await enviar()

    expect(clienteApi.actualizar).toHaveBeenCalledWith(
      '/tareas/1',
      expect.objectContaining({ subestado: null }),
    )
    expect(celdasSubestado(envoltorio)[0]).toBe('—')
  })

  it('la edición sin tocar el subestado lo conserva', async () => {
    const envoltorio = await montar()
    vi.mocked(clienteApi.actualizar).mockResolvedValue(BLOQUEADA)

    await envoltorio.get('button[aria-label="Acciones de la tarea Bloqueada"]').trigger('click')
    await flushPromises()
    document.body
      .querySelector<HTMLButtonElement>('button[aria-label="Editar tarea Bloqueada"]')!
      .click()
    await flushPromises()
    await enviar()

    expect(clienteApi.actualizar).toHaveBeenCalledWith(
      '/tareas/1',
      expect.objectContaining({ subestado: 'Bloqueado' }),
    )
  })
})

describe('VistaTareas: subestado en el tablero', () => {
  it('la tarjeta muestra el subestado como una píldora de su color', async () => {
    const grupo = {
      id: 1,
      nombre: 'Desarrollo',
      tareas: 1,
      estados: [{ id: 10, nombre: 'Pendiente', posicion: 1, tareas: 1 }],
    }
    const enGrupo = {
      ...BLOQUEADA,
      grupo_estados: { id: 1, nombre: 'Desarrollo' },
      estado: { id: 10, nombre: 'Pendiente' },
    }
    const envoltorio = await montar([enGrupo], [grupo])
    document.body.querySelector<HTMLButtonElement>('button[aria-label="Ver como tablero"]')!.click()
    await flushPromises()

    const pildora = envoltorio.get('[data-testid="subestado-tablero"]')
    expect(pildora.text()).toBe('Bloqueado')
    for (const clase of colorEtiqueta('Bloqueado').split(' ')) {
      expect(pildora.classes()).toContain(clase)
    }
  })
})

describe('VistaTareas: pulsar un subestado abre sus tareas, como las etiquetas', () => {
  function tituloModal(): string[] {
    return [...document.body.querySelectorAll('[role="dialog"] h2')].map(
      (h) => h.textContent?.trim() ?? '',
    )
  }

  function tareasDelModal(): string[] {
    const dialogo = [...document.body.querySelectorAll<HTMLElement>('[role="dialog"]')].find(
      (d) => d.querySelector('h2')?.textContent?.trim() === 'Subestado: Bloqueado',
    )
    if (!dialogo) throw new Error('No se abrió el modal del subestado')
    return [...dialogo.querySelectorAll('[data-tabla="Tareas"] tbody button')].map(
      (li) => li.textContent?.trim() ?? '',
    )
  }

  const OTRA_BLOQUEADA = { ...EN_PAUSA, id: 3, nombre: 'Otra bloqueada', subestado: 'Bloqueado' }

  it('desde la columna de la lista', async () => {
    const envoltorio = await montar([BLOQUEADA, EN_PAUSA, OTRA_BLOQUEADA])

    await envoltorio
      .get('[data-columna="subestado"] button[aria-label="Ver tareas con el subestado Bloqueado"]')
      .trigger('click')
    await flushPromises()

    expect(tituloModal()).toContain('Subestado: Bloqueado')
    expect(tareasDelModal().join(' | ')).toContain('Bloqueada')
    expect(tareasDelModal().join(' | ')).toContain('Otra bloqueada')
    expect(tareasDelModal().join(' | ')).not.toContain('En pausa')
  })

  it('desde la tarjeta del tablero', async () => {
    const grupo = {
      id: 1,
      nombre: 'Desarrollo',
      tareas: 1,
      estados: [{ id: 10, nombre: 'Pendiente', posicion: 1, tareas: 1 }],
    }
    const enGrupo = {
      ...BLOQUEADA,
      grupo_estados: { id: 1, nombre: 'Desarrollo' },
      estado: { id: 10, nombre: 'Pendiente' },
    }
    const envoltorio = await montar([enGrupo, OTRA_BLOQUEADA], [grupo])
    document.body.querySelector<HTMLButtonElement>('button[aria-label="Ver como tablero"]')!.click()
    await flushPromises()

    const boton = envoltorio.get('button[aria-label="Ver tareas con el subestado Bloqueado"]')
    expect(boton.find('[data-testid="subestado-tablero"]').exists()).toBe(true)
    await boton.trigger('click')
    await flushPromises()

    expect(tituloModal()).toContain('Subestado: Bloqueado')
    expect(tareasDelModal().join(' | ')).toContain('Otra bloqueada')
  })

  it('desde el detalle de la tarea', async () => {
    const envoltorio = await montar([BLOQUEADA, OTRA_BLOQUEADA])
    await envoltorio.get('button[aria-label="Acciones de la tarea Bloqueada"]').trigger('click')
    await flushPromises()
    document.body
      .querySelector<HTMLButtonElement>('button[aria-label="Ver detalle de la tarea Bloqueada"]')!
      .click()
    await flushPromises()

    const detalle = [...document.body.querySelectorAll<HTMLElement>('[role="dialog"]')].find((d) =>
      d.querySelector('[data-testid="subestado-detalle"]'),
    )!
    const boton = detalle.querySelector<HTMLButtonElement>(
      'button[aria-label="Ver tareas con el subestado Bloqueado"]',
    )
    expect(boton).not.toBeNull()
    boton!.click()
    await flushPromises()

    expect(tituloModal()).toContain('Subestado: Bloqueado')
  })
})
