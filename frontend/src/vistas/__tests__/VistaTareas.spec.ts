import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { clienteApi } from '@/api/cliente'
import { exportarTablaExcel, exportarTablaPDF } from '@/lib/exportarTabla'
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
  },
}))

const TAREAS = [
  {
    id: 1,
    nombre: 'Escribir informe',
    prioridad: 2,
    descripcion: 'Informe trimestral',
    fecha_creacion: '2026-11-10T09:30:00',
    fecha_vencimiento: '2026-11-20T18:00:00',
    etiquetas: ['Backend', 'Urgente'],
    asignados: ['Ana'],
  },
  {
    id: 2,
    nombre: 'Leer artículo',
    prioridad: null,
    descripcion: 'Artículo sobre Vue',
    fecha_creacion: '2026-12-01T17:05:09',
    fecha_vencimiento: null,
    etiquetas: [],
    asignados: [],
  },
]

const ETIQUETAS = [
  { id: 1, nombre: 'Backend' },
  { id: 2, nombre: 'Urgente' },
]
const PERSONAS = [
  { id: 1, nombre: 'Ana' },
  { id: 2, nombre: 'Luis' },
]

// Campos de una tarea que el test no rellena: sin vencimiento, etiquetas ni personas.
const SIN_EXTRAS = { fecha_vencimiento: null, etiquetas: [], asignados: [] }

// Fecha y hora "actuales" fijas para que el valor por defecto sea determinista.
const AHORA = new Date(2026, 10, 9, 18, 45, 30)
const AHORA_TEXTO = '09/11/2026 18:45:30'
const AHORA_ISO = '2026-11-09T18:45:30'
const SELECTOR_FECHA = '#fecha-creacion'
const SELECTOR_VENCIMIENTO = '#fecha-vencimiento'

let contenedor: VueWrapper | null = null

async function montar(tareas: unknown[] = TAREAS): Promise<VueWrapper> {
  // Copia para que los tests que editan no alteren los datos compartidos.
  vi.mocked(clienteApi.obtener).mockImplementation((ruta) => {
    if (ruta === '/etiquetas') return Promise.resolve(structuredClone(ETIQUETAS))
    if (ruta === '/personas') return Promise.resolve(structuredClone(PERSONAS))
    return Promise.resolve(structuredClone(tareas))
  })
  const pinia = createPinia()
  setActivePinia(pinia)
  contenedor = mount(VistaTareas, { global: { plugins: [pinia] }, attachTo: document.body })
  await flushPromises()
  return contenedor
}

function botonCrear(envoltorio: VueWrapper) {
  const boton = envoltorio.findAll('button').find((b) => b.text() === 'Crear tarea')
  if (!boton) throw new Error('No se encontró el botón "Crear tarea"')
  return boton
}

function panelActual(): HTMLElement {
  const panel = document.body.querySelector<HTMLElement>('[role="dialog"]')
  if (!panel) throw new Error('El panel lateral no se abrió')
  return panel
}

async function abrirPanel(envoltorio: VueWrapper): Promise<HTMLElement> {
  await botonCrear(envoltorio).trigger('click')
  await flushPromises()
  return panelActual()
}

async function abrirPanelEdicion(envoltorio: VueWrapper, nombre: string): Promise<HTMLElement> {
  const boton = envoltorio.find(`button[aria-label="Editar tarea ${nombre}"]`)
  if (!boton.exists()) throw new Error(`No se encontró el botón de editar de "${nombre}"`)
  await boton.trigger('click')
  await flushPromises()
  return panelActual()
}

// Las celdas con chips se leen como sus textos unidos por " | ".
function filasTabla(envoltorio: VueWrapper): string[][] {
  return envoltorio.findAll('tbody tr').map((tr) =>
    tr.findAll('td').map((td) => {
      const chips = td.findAll('[data-testid="chip-tabla"]')
      return chips.length > 0 ? chips.map((chip) => chip.text()).join(' | ') : td.text()
    }),
  )
}

function campo<T extends HTMLElement>(panel: HTMLElement, selector: string): T {
  const elemento = panel.querySelector<T>(selector)
  if (!elemento) throw new Error(`No se encontró ${selector}`)
  return elemento
}

// `useVModel` en modo pasivo emite `update:modelValue` desde un watcher, así
// que hay que esperar a que Vue lo procese antes de enviar el formulario.
async function escribir(
  elemento: HTMLInputElement | HTMLTextAreaElement,
  valor: string,
): Promise<void> {
  elemento.value = valor
  elemento.dispatchEvent(new Event('input'))
  await flushPromises()
}

async function pulsarEnter(elemento: HTMLInputElement): Promise<void> {
  elemento.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
  await flushPromises()
}

function textosOpciones(panel: HTMLElement): string[] {
  return [...panel.querySelectorAll('[role="option"]')].map((opcion) => opcion.textContent!.trim())
}

async function elegirPrimeraOpcion(panel: HTMLElement): Promise<void> {
  campo<HTMLElement>(panel, '[role="option"]').click()
  await flushPromises()
}

function chipsDe(panel: HTMLElement, etiqueta: string): string[] {
  const lista = panel.querySelector(`ul[aria-label="${etiqueta}"]`)
  if (!lista) return []
  return [...lista.querySelectorAll('[data-testid="chip"]')].map((chip) => chip.textContent!.trim())
}

async function enviar(panel: HTMLElement): Promise<void> {
  campo<HTMLFormElement>(panel, 'form').dispatchEvent(new Event('submit'))
  await flushPromises()
}

describe('VistaTareas', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Solo se simula `Date`: `flushPromises` depende de los temporizadores reales.
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(AHORA)
  })

  afterEach(() => {
    vi.useRealTimers()
    contenedor?.unmount()
    contenedor = null
    document.body.innerHTML = ''
  })

  it('carga las tareas al montar y las muestra en la tabla', async () => {
    const envoltorio = await montar()

    expect(clienteApi.obtener).toHaveBeenCalledWith('/tareas')
    const cabeceras = envoltorio.findAll('th').map((th) => th.text())
    expect(cabeceras).toEqual([
      'Nombre',
      'Prioridad',
      'Descripción',
      'Etiquetas',
      'Asignado a',
      'Fecha de creación',
      'Fecha de vencimiento',
      'Acciones',
    ])
    expect(filasTabla(envoltorio)).toEqual([
      [
        'Escribir informe',
        '2',
        'Informe trimestral',
        'Backend | Urgente',
        'Ana',
        '10/11/2026 09:30:00',
        '20/11/2026 18:00:00',
        'Editar',
      ],
      ['Leer artículo', '—', 'Artículo sobre Vue', '—', '—', '01/12/2026 17:05:09', '—', 'Editar'],
    ])
  })

  it('muestra un mensaje cuando no hay tareas', async () => {
    const envoltorio = await montar([])

    expect(envoltorio.text()).toContain('Todavía no hay tareas.')
    expect(envoltorio.find('table').exists()).toBe(false)
  })

  it('el botón "Crear tarea" abre el panel lateral con el título "Crear tarea"', async () => {
    const envoltorio = await montar()
    expect(document.body.querySelector('[role="dialog"]')).toBeNull()

    const panel = await abrirPanel(envoltorio)

    expect(panel.querySelector('h2')?.textContent?.trim()).toBe('Crear tarea')
  })

  it('los campos del formulario tienen sus restricciones', async () => {
    const panel = await abrirPanel(await montar())

    const nombre = campo<HTMLInputElement>(panel, 'input[placeholder="Nombre"]')
    expect(nombre.required).toBe(true)
    expect(nombre.getAttribute('maxlength')).toBe('200')

    const prioridad = campo<HTMLInputElement>(panel, 'input[placeholder="Prioridad"]')
    expect(prioridad.type).toBe('number')
    expect(prioridad.getAttribute('min')).toBe('1')
    expect(prioridad.getAttribute('max')).toBe('5')
    expect(prioridad.required).toBe(false)

    const descripcion = campo<HTMLTextAreaElement>(panel, 'textarea[placeholder="Descripción"]')
    expect(descripcion.required).toBe(true)
    expect(descripcion.getAttribute('maxlength')).toBe('500')

    const fechaCreacion = campo<HTMLInputElement>(panel, SELECTOR_FECHA)
    expect(fechaCreacion.type).toBe('text')
    expect(fechaCreacion.required).toBe(true)
    expect(fechaCreacion.getAttribute('placeholder')).toBe('dd/mm/aaaa hh:mm:ss')
    expect(fechaCreacion.getAttribute('pattern')).toBe('\\d{2}/\\d{2}/\\d{4} \\d{2}:\\d{2}:\\d{2}')
    expect(panel.querySelector('label[for="fecha-creacion"]')?.textContent?.trim()).toBe(
      'Fecha de creación',
    )

    const vencimiento = campo<HTMLInputElement>(panel, SELECTOR_VENCIMIENTO)
    expect(vencimiento.required).toBe(false)
    expect(vencimiento.value).toBe('')
    expect(vencimiento.getAttribute('placeholder')).toBe('dd/mm/aaaa hh:mm:ss')
    expect(panel.querySelector('label[for="fecha-vencimiento"]')?.textContent?.trim()).toBe(
      'Fecha de vencimiento',
    )
    expect(
      panel.querySelector('button[aria-label="Abrir calendario de Fecha de creación"]'),
    ).not.toBeNull()
    expect(
      panel.querySelector('button[aria-label="Abrir calendario de Fecha de vencimiento"]'),
    ).not.toBeNull()
    // Solo el vencimiento se puede dejar vacío.
    expect(panel.querySelectorAll('button[aria-label="Borrar fecha"]')).toHaveLength(1)

    expect(panel.querySelector('label[for="etiquetas"]')?.textContent?.trim()).toBe('Etiquetas')
    expect(panel.querySelector('label[for="asignados"]')?.textContent?.trim()).toBe('Asignado a')
  })

  it('en modo crear rellena la fecha de creación con la actual, segundos incluidos', async () => {
    const panel = await abrirPanel(await montar())

    expect(campo<HTMLInputElement>(panel, SELECTOR_FECHA).value).toBe(AHORA_TEXTO)
  })

  it('con una fecha de creación inválida muestra el error y no llama a la API', async () => {
    const envoltorio = await montar([])
    const panel = await abrirPanel(envoltorio)

    await escribir(campo(panel, 'input[placeholder="Nombre"]'), 'Nueva')
    await escribir(campo(panel, 'textarea[placeholder="Descripción"]'), 'Detalle')
    await escribir(campo(panel, SELECTOR_FECHA), '31/02/2026 10:00:00')
    await enviar(panel)

    expect(clienteApi.crear).not.toHaveBeenCalled()
    const panelAbierto = panelActual()
    expect(panelAbierto.querySelector('[role="alert"]')?.textContent?.trim()).toBe(
      'La fecha y hora debe tener el formato dd/mm/aaaa hh:mm:ss y ser válida.',
    )
  })

  it('envía la fecha de creación escrita en formato ISO', async () => {
    const envoltorio = await montar([])
    vi.mocked(clienteApi.crear).mockResolvedValue({
      id: 5,
      nombre: 'Con fecha',
      prioridad: null,
      descripcion: 'Detalle',
      fecha_creacion: '2027-01-02T03:04:05',
      ...SIN_EXTRAS,
    })
    const panel = await abrirPanel(envoltorio)

    await escribir(campo(panel, 'input[placeholder="Nombre"]'), 'Con fecha')
    await escribir(campo(panel, 'textarea[placeholder="Descripción"]'), 'Detalle')
    await escribir(campo(panel, SELECTOR_FECHA), '02/01/2027 03:04:05')
    await enviar(panel)

    expect(clienteApi.crear).toHaveBeenCalledWith('/tareas', {
      nombre: 'Con fecha',
      prioridad: null,
      descripcion: 'Detalle',
      fecha_creacion: '2027-01-02T03:04:05',
      ...SIN_EXTRAS,
    })
    expect(filasTabla(envoltorio)).toEqual([
      ['Con fecha', '—', 'Detalle', '—', '—', '02/01/2027 03:04:05', '—', 'Editar'],
    ])
  })

  it('envía vencimiento, etiquetas y personas, sugiriendo las existentes y creando las nuevas', async () => {
    const envoltorio = await montar([])
    expect(clienteApi.obtener).toHaveBeenCalledWith('/etiquetas')
    expect(clienteApi.obtener).toHaveBeenCalledWith('/personas')
    vi.mocked(clienteApi.crear).mockResolvedValue({
      id: 6,
      nombre: 'Con catálogos',
      prioridad: null,
      descripcion: 'Detalle',
      fecha_creacion: AHORA_ISO,
      fecha_vencimiento: '2026-11-30T12:00:00',
      etiquetas: ['Frontend', 'Urgente'],
      asignados: ['Luis'],
    })
    const panel = await abrirPanel(envoltorio)

    await escribir(campo(panel, 'input[placeholder="Nombre"]'), 'Con catálogos')
    await escribir(campo(panel, 'textarea[placeholder="Descripción"]'), 'Detalle')
    await escribir(campo(panel, SELECTOR_VENCIMIENTO), '30/11/2026 12:00:00')

    const etiquetas = campo<HTMLInputElement>(panel, '#etiquetas')
    await escribir(etiquetas, 'urg')
    expect(textosOpciones(panel)).toEqual(['Urgente', 'Crear etiqueta "urg"'])
    await elegirPrimeraOpcion(panel)
    await escribir(etiquetas, 'Frontend')
    await pulsarEnter(etiquetas)

    const asignados = campo<HTMLInputElement>(panel, '#asignados')
    await escribir(asignados, 'lu')
    expect(textosOpciones(panel)).toEqual(['Luis', 'Añadir persona "lu"'])
    await elegirPrimeraOpcion(panel)

    expect(chipsDe(panel, 'Etiquetas')).toEqual(['Urgente', 'Frontend'])
    expect(chipsDe(panel, 'Asignado a')).toEqual(['Luis'])
    vi.mocked(clienteApi.obtener).mockClear()
    await enviar(panel)

    expect(clienteApi.crear).toHaveBeenCalledWith('/tareas', {
      nombre: 'Con catálogos',
      prioridad: null,
      descripcion: 'Detalle',
      fecha_creacion: AHORA_ISO,
      fecha_vencimiento: '2026-11-30T12:00:00',
      etiquetas: ['Urgente', 'Frontend'],
      asignados: ['Luis'],
    })
    // Tras guardar se vuelven a pedir los catálogos por si hay nombres nuevos.
    expect(clienteApi.obtener).toHaveBeenCalledWith('/etiquetas')
    expect(clienteApi.obtener).toHaveBeenCalledWith('/personas')
    expect(filasTabla(envoltorio)).toEqual([
      [
        'Con catálogos',
        '—',
        'Detalle',
        'Frontend | Urgente',
        'Luis',
        AHORA_TEXTO,
        '30/11/2026 12:00:00',
        'Editar',
      ],
    ])
  })

  it('con una fecha de vencimiento inválida muestra el error y no llama a la API', async () => {
    const panel = await abrirPanel(await montar([]))

    await escribir(campo(panel, 'input[placeholder="Nombre"]'), 'Nueva')
    await escribir(campo(panel, 'textarea[placeholder="Descripción"]'), 'Detalle')
    await escribir(campo(panel, SELECTOR_VENCIMIENTO), '31/04/2026 10:00:00')
    await enviar(panel)

    expect(clienteApi.crear).not.toHaveBeenCalled()
    expect(panelActual().querySelector('[role="alert"]')?.textContent?.trim()).toBe(
      'La fecha de vencimiento debe tener el formato dd/mm/aaaa hh:mm:ss y ser válida.',
    )
  })

  it('con un vencimiento anterior a la creación muestra el error y no llama a la API', async () => {
    const panel = await abrirPanelEdicion(await montar(), 'Escribir informe')

    await escribir(campo(panel, SELECTOR_VENCIMIENTO), '10/11/2026 09:29:59')
    await enviar(panel)

    expect(clienteApi.actualizar).not.toHaveBeenCalled()
    expect(panelActual().querySelector('[role="alert"]')?.textContent?.trim()).toBe(
      'La fecha de vencimiento no puede ser anterior a la fecha de creación.',
    )
  })

  it('acepta un vencimiento igual a la creación', async () => {
    const envoltorio = await montar()
    vi.mocked(clienteApi.actualizar).mockResolvedValue({
      ...TAREAS[0],
      fecha_vencimiento: '2026-11-10T09:30:00',
    })
    const panel = await abrirPanelEdicion(envoltorio, 'Escribir informe')

    await escribir(campo(panel, SELECTOR_VENCIMIENTO), '10/11/2026 09:30:00')
    await enviar(panel)

    expect(clienteApi.actualizar).toHaveBeenCalledWith(
      '/tareas/1',
      expect.objectContaining({ fecha_vencimiento: '2026-11-10T09:30:00' }),
    )
  })

  it('el botón "Editar" abre el panel "Editar tarea" con los datos cargados', async () => {
    const panel = await abrirPanelEdicion(await montar(), 'Escribir informe')

    expect(panel.querySelector('h2')?.textContent?.trim()).toBe('Editar tarea')
    expect(campo<HTMLInputElement>(panel, 'input[placeholder="Nombre"]').value).toBe(
      'Escribir informe',
    )
    expect(campo<HTMLInputElement>(panel, 'input[placeholder="Prioridad"]').value).toBe('2')
    expect(campo<HTMLTextAreaElement>(panel, 'textarea[placeholder="Descripción"]').value).toBe(
      'Informe trimestral',
    )
    expect(campo<HTMLInputElement>(panel, SELECTOR_FECHA).value).toBe('10/11/2026 09:30:00')
    expect(campo<HTMLInputElement>(panel, SELECTOR_VENCIMIENTO).value).toBe('20/11/2026 18:00:00')
    expect(chipsDe(panel, 'Etiquetas')).toEqual(['Backend', 'Urgente'])
    expect(chipsDe(panel, 'Asignado a')).toEqual(['Ana'])
  })

  it('al guardar en modo editar actualiza la tarea, cierra el panel y refresca la fila', async () => {
    const envoltorio = await montar()
    vi.mocked(clienteApi.actualizar).mockResolvedValue({
      id: 1,
      nombre: 'Informe final',
      prioridad: null,
      descripcion: 'Informe trimestral',
      fecha_creacion: '2026-11-11T08:00:00',
      fecha_vencimiento: null,
      etiquetas: ['Urgente'],
      asignados: ['Ana'],
    })
    const panel = await abrirPanelEdicion(envoltorio, 'Escribir informe')

    await escribir(campo(panel, 'input[placeholder="Nombre"]'), 'Informe final')
    await escribir(campo(panel, 'input[placeholder="Prioridad"]'), '')
    await escribir(campo(panel, SELECTOR_FECHA), '11/11/2026 08:00:00')
    await escribir(campo(panel, SELECTOR_VENCIMIENTO), '')
    campo<HTMLElement>(panel, 'button[aria-label="Quitar Backend"]').click()
    await flushPromises()
    await enviar(panel)

    expect(clienteApi.crear).not.toHaveBeenCalled()
    expect(clienteApi.actualizar).toHaveBeenCalledWith('/tareas/1', {
      nombre: 'Informe final',
      prioridad: null,
      descripcion: 'Informe trimestral',
      fecha_creacion: '2026-11-11T08:00:00',
      fecha_vencimiento: null,
      etiquetas: ['Urgente'],
      asignados: ['Ana'],
    })
    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    expect(filasTabla(envoltorio)).toEqual([
      [
        'Informe final',
        '—',
        'Informe trimestral',
        'Urgente',
        'Ana',
        '11/11/2026 08:00:00',
        '—',
        'Editar',
      ],
      ['Leer artículo', '—', 'Artículo sobre Vue', '—', '—', '01/12/2026 17:05:09', '—', 'Editar'],
    ])

    // Tras editar, "Crear tarea" vuelve al modo crear con el formulario limpio.
    const panelCrear = await abrirPanel(envoltorio)
    expect(panelCrear.querySelector('h2')?.textContent?.trim()).toBe('Crear tarea')
    expect(campo<HTMLInputElement>(panelCrear, 'input[placeholder="Nombre"]').value).toBe('')
    expect(campo<HTMLInputElement>(panelCrear, SELECTOR_FECHA).value).toBe(AHORA_TEXTO)
    expect(campo<HTMLInputElement>(panelCrear, SELECTOR_VENCIMIENTO).value).toBe('')
    expect(chipsDe(panelCrear, 'Etiquetas')).toEqual([])
    expect(chipsDe(panelCrear, 'Asignado a')).toEqual([])
  })

  it('si la API falla al editar muestra el error y mantiene el panel abierto', async () => {
    const envoltorio = await montar()
    vi.mocked(clienteApi.actualizar).mockRejectedValue(new Error('Tarea no encontrada'))
    const panel = await abrirPanelEdicion(envoltorio, 'Leer artículo')

    await enviar(panel)

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/tareas/2', {
      nombre: 'Leer artículo',
      prioridad: null,
      descripcion: 'Artículo sobre Vue',
      fecha_creacion: '2026-12-01T17:05:09',
      ...SIN_EXTRAS,
    })
    const panelAbierto = panelActual()
    expect(panelAbierto.querySelector('h2')?.textContent?.trim()).toBe('Editar tarea')
    expect(panelAbierto.querySelector('[role="alert"]')?.textContent?.trim()).toBe(
      'Tarea no encontrada',
    )
    expect(filasTabla(envoltorio)[1]?.[0]).toBe('Leer artículo')
  })

  it('al guardar crea la tarea, cierra el panel y la muestra en la tabla', async () => {
    const envoltorio = await montar([])
    vi.mocked(clienteApi.crear).mockResolvedValue({
      id: 3,
      nombre: 'Nueva',
      prioridad: 1,
      descripcion: 'Detalle',
      fecha_creacion: AHORA_ISO,
      ...SIN_EXTRAS,
    })
    const panel = await abrirPanel(envoltorio)

    await escribir(campo(panel, 'input[placeholder="Nombre"]'), 'Nueva')
    await escribir(campo(panel, 'input[placeholder="Prioridad"]'), '1')
    await escribir(campo(panel, 'textarea[placeholder="Descripción"]'), 'Detalle')
    await enviar(panel)

    expect(clienteApi.crear).toHaveBeenCalledWith('/tareas', {
      nombre: 'Nueva',
      prioridad: 1,
      descripcion: 'Detalle',
      fecha_creacion: AHORA_ISO,
      ...SIN_EXTRAS,
    })
    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    expect(filasTabla(envoltorio)).toEqual([
      ['Nueva', '1', 'Detalle', '—', '—', AHORA_TEXTO, '—', 'Editar'],
    ])

    const panelReabierto = await abrirPanel(envoltorio)
    expect(campo<HTMLInputElement>(panelReabierto, 'input[placeholder="Nombre"]').value).toBe('')
    expect(campo<HTMLInputElement>(panelReabierto, 'input[placeholder="Prioridad"]').value).toBe('')
    expect(
      campo<HTMLTextAreaElement>(panelReabierto, 'textarea[placeholder="Descripción"]').value,
    ).toBe('')
  })

  it('envía la prioridad vacía como null', async () => {
    const envoltorio = await montar([])
    vi.mocked(clienteApi.crear).mockResolvedValue({
      id: 4,
      nombre: 'Sin prioridad',
      prioridad: null,
      descripcion: 'Detalle',
      fecha_creacion: AHORA_ISO,
      ...SIN_EXTRAS,
    })
    const panel = await abrirPanel(envoltorio)

    await escribir(campo(panel, 'input[placeholder="Nombre"]'), 'Sin prioridad')
    await escribir(campo(panel, 'textarea[placeholder="Descripción"]'), 'Detalle')
    await enviar(panel)

    expect(clienteApi.crear).toHaveBeenCalledWith('/tareas', {
      nombre: 'Sin prioridad',
      prioridad: null,
      descripcion: 'Detalle',
      fecha_creacion: AHORA_ISO,
      ...SIN_EXTRAS,
    })
  })

  it('si la API falla muestra el error y mantiene el panel abierto', async () => {
    const envoltorio = await montar([])
    vi.mocked(clienteApi.crear).mockRejectedValue(new Error('El nombre es demasiado largo'))
    const panel = await abrirPanel(envoltorio)

    await escribir(campo(panel, 'input[placeholder="Nombre"]'), 'Nombre')
    await escribir(campo(panel, 'textarea[placeholder="Descripción"]'), 'Detalle')
    await enviar(panel)

    const panelAbierto = document.body.querySelector<HTMLElement>('[role="dialog"]')
    expect(panelAbierto).not.toBeNull()
    expect(panelAbierto?.querySelector('[role="alert"]')?.textContent?.trim()).toBe(
      'El nombre es demasiado largo',
    )
    expect(envoltorio.findAll('tbody tr')).toHaveLength(0)
  })

  describe('ordenación', () => {
    const TAREAS_ORDEN = [
      {
        id: 1,
        nombre: 'beta',
        prioridad: 3,
        descripcion: 'b',
        fecha_creacion: '2026-05-01T10:00:00',
        fecha_vencimiento: '2026-06-01T10:00:00',
        etiquetas: ['Urgente'],
        asignados: [],
      },
      {
        id: 2,
        nombre: 'Árbol',
        prioridad: null,
        descripcion: 'c',
        fecha_creacion: '2026-01-01T10:00:00',
        fecha_vencimiento: null,
        etiquetas: [],
        asignados: ['Luis'],
      },
      {
        id: 3,
        nombre: 'casa',
        prioridad: 1,
        descripcion: 'a',
        fecha_creacion: '2026-12-31T23:59:59',
        fecha_vencimiento: '2026-02-01T10:00:00',
        // Desordenadas a propósito: se ordena por el texto alfabético "Backend, Urgente".
        etiquetas: ['Urgente', 'Backend'],
        asignados: ['Luis', 'Ana'],
      },
    ]

    function nombresEnTabla(envoltorio: VueWrapper): string[] {
      return envoltorio.findAll('tbody tr').map((fila) => fila.findAll('td')[0]!.text())
    }

    function cabecera(envoltorio: VueWrapper, etiqueta: string) {
      const boton = envoltorio.findAll('th button').find((b) => b.text() === etiqueta)
      if (!boton) throw new Error(`No se encontró la cabecera ordenable "${etiqueta}"`)
      return boton
    }

    function thDe(envoltorio: VueWrapper, etiqueta: string) {
      const th = envoltorio.findAll('th').find((t) => t.text() === etiqueta)
      if (!th) throw new Error(`No se encontró la columna "${etiqueta}"`)
      return th
    }

    it('muestra las filas en el orden original y todas las columnas de datos son ordenables', async () => {
      const envoltorio = await montar(TAREAS_ORDEN)

      expect(nombresEnTabla(envoltorio)).toEqual(['beta', 'Árbol', 'casa'])
      for (const etiqueta of [
        'Nombre',
        'Prioridad',
        'Descripción',
        'Etiquetas',
        'Asignado a',
        'Fecha de creación',
        'Fecha de vencimiento',
      ]) {
        expect(cabecera(envoltorio, etiqueta).attributes('type')).toBe('button')
        expect(thDe(envoltorio, etiqueta).attributes('aria-sort')).toBeUndefined()
      }
      expect(envoltorio.findAll('th button').map((b) => b.text())).not.toContain('Acciones')
    })

    it('ordena por nombre ascendente y descendente respetando los acentos', async () => {
      const envoltorio = await montar(TAREAS_ORDEN)

      await cabecera(envoltorio, 'Nombre').trigger('click')
      expect(nombresEnTabla(envoltorio)).toEqual(['Árbol', 'beta', 'casa'])
      expect(thDe(envoltorio, 'Nombre').attributes('aria-sort')).toBe('ascending')

      await cabecera(envoltorio, 'Nombre').trigger('click')
      expect(nombresEnTabla(envoltorio)).toEqual(['casa', 'beta', 'Árbol'])
      expect(thDe(envoltorio, 'Nombre').attributes('aria-sort')).toBe('descending')
    })

    it('ordena por prioridad dejando las vacías al final en ambos sentidos', async () => {
      const envoltorio = await montar(TAREAS_ORDEN)

      await cabecera(envoltorio, 'Prioridad').trigger('click')
      expect(nombresEnTabla(envoltorio)).toEqual(['casa', 'beta', 'Árbol'])
      expect(thDe(envoltorio, 'Nombre').attributes('aria-sort')).toBeUndefined()

      await cabecera(envoltorio, 'Prioridad').trigger('click')
      expect(nombresEnTabla(envoltorio)).toEqual(['beta', 'casa', 'Árbol'])
    })

    it('ordena por descripción y por fecha de creación', async () => {
      const envoltorio = await montar(TAREAS_ORDEN)

      await cabecera(envoltorio, 'Descripción').trigger('click')
      expect(nombresEnTabla(envoltorio)).toEqual(['casa', 'beta', 'Árbol'])

      await cabecera(envoltorio, 'Fecha de creación').trigger('click')
      expect(nombresEnTabla(envoltorio)).toEqual(['Árbol', 'beta', 'casa'])
      await cabecera(envoltorio, 'Fecha de creación').trigger('click')
      expect(nombresEnTabla(envoltorio)).toEqual(['casa', 'beta', 'Árbol'])
    })

    it('ordena por etiquetas dejando las tareas sin etiquetas al final en ambos sentidos', async () => {
      const envoltorio = await montar(TAREAS_ORDEN)

      await cabecera(envoltorio, 'Etiquetas').trigger('click')
      expect(nombresEnTabla(envoltorio)).toEqual(['casa', 'beta', 'Árbol'])
      expect(thDe(envoltorio, 'Etiquetas').attributes('aria-sort')).toBe('ascending')
      await cabecera(envoltorio, 'Etiquetas').trigger('click')
      expect(nombresEnTabla(envoltorio)).toEqual(['beta', 'casa', 'Árbol'])
    })

    it('ordena por asignados dejando las tareas sin personas al final en ambos sentidos', async () => {
      const envoltorio = await montar(TAREAS_ORDEN)

      await cabecera(envoltorio, 'Asignado a').trigger('click')
      expect(nombresEnTabla(envoltorio)).toEqual(['casa', 'Árbol', 'beta'])
      await cabecera(envoltorio, 'Asignado a').trigger('click')
      expect(nombresEnTabla(envoltorio)).toEqual(['Árbol', 'casa', 'beta'])
    })

    it('ordena por fecha de vencimiento dejando las vacías al final en ambos sentidos', async () => {
      const envoltorio = await montar(TAREAS_ORDEN)

      await cabecera(envoltorio, 'Fecha de vencimiento').trigger('click')
      expect(nombresEnTabla(envoltorio)).toEqual(['casa', 'beta', 'Árbol'])
      await cabecera(envoltorio, 'Fecha de vencimiento').trigger('click')
      expect(nombresEnTabla(envoltorio)).toEqual(['beta', 'casa', 'Árbol'])
    })
  })

  describe('exportación', () => {
    const COLUMNAS = [
      'Nombre',
      'Prioridad',
      'Descripción',
      'Etiquetas',
      'Asignado a',
      'Fecha de creación',
      'Fecha de vencimiento',
    ]

    function botonExportar(envoltorio: VueWrapper, nombre: string) {
      const boton = envoltorio.find(`button[aria-label="${nombre}"]`)
      if (!boton.exists()) throw new Error(`No se encontró el botón "${nombre}"`)
      return boton
    }

    it('no muestra los botones de exportar si no hay tareas', async () => {
      const envoltorio = await montar([])

      expect(envoltorio.find('button[aria-label="Exportar a Excel"]').exists()).toBe(false)
      expect(envoltorio.find('button[aria-label="Exportar a PDF"]').exists()).toBe(false)
    })

    it('exporta a Excel todas las filas tal como se muestran, sin la columna de acciones', async () => {
      const envoltorio = await montar()

      await botonExportar(envoltorio, 'Exportar a Excel').trigger('click')

      expect(exportarTablaExcel).toHaveBeenCalledTimes(1)
      const [nombreFichero, columnas, filas] = vi.mocked(exportarTablaExcel).mock.calls[0]!
      expect(nombreFichero).toMatch(/^Tareas_\d{8}_\d{6}\.xlsx$/)
      expect(columnas).toEqual(COLUMNAS)
      expect(filas).toEqual([
        [
          'Escribir informe',
          2,
          'Informe trimestral',
          'Backend, Urgente',
          'Ana',
          '10/11/2026 09:30:00',
          '20/11/2026 18:00:00',
        ],
        ['Leer artículo', '—', 'Artículo sobre Vue', '—', '—', '01/12/2026 17:05:09', '—'],
      ])
    })

    it('exporta etiquetas y personas unidas por ", " en orden alfabético', async () => {
      const envoltorio = await montar([
        { ...TAREAS[0], etiquetas: ['Urgente', 'Backend'], asignados: ['Luis', 'Ana'] },
      ])

      await botonExportar(envoltorio, 'Exportar a Excel').trigger('click')

      const filas = vi.mocked(exportarTablaExcel).mock.calls[0]![2] as unknown[][]
      expect(filas[0]?.slice(3, 5)).toEqual(['Backend, Urgente', 'Ana, Luis'])
    })

    it('exporta a PDF con el título "Tareas" respetando el orden actual', async () => {
      const envoltorio = await montar()
      const boton = envoltorio.findAll('th button').find((b) => b.text() === 'Nombre')!
      await boton.trigger('click')
      await boton.trigger('click')

      await botonExportar(envoltorio, 'Exportar a PDF').trigger('click')

      expect(exportarTablaPDF).toHaveBeenCalledTimes(1)
      const [nombreFichero, titulo, columnas, filas] = vi.mocked(exportarTablaPDF).mock.calls[0]!
      expect(nombreFichero).toMatch(/^Tareas_\d{8}_\d{6}\.pdf$/)
      expect(titulo).toBe('Tareas')
      expect(columnas).toEqual(COLUMNAS)
      expect((filas as unknown[][]).map((f) => f[0])).toEqual(['Leer artículo', 'Escribir informe'])
    })
  })
})
