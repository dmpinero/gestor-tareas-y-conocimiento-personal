import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { clienteApi } from '@/api/cliente'
import { exportarTablaExcel, exportarTablaPDF } from '@/lib/exportarTabla'
import { useTiendaTareas } from '@/stores/tareas'
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
    tipo: null,
    oportunidad: null,
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
    tipo: null,
    oportunidad: null,
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

// Campos de una tarea que el test no rellena: sin vencimiento, etiquetas, personas ni tipo.
const SIN_EXTRAS = {
  fecha_vencimiento: null,
  etiquetas: [],
  asignados: [],
  tipo: null,
  oportunidad: null,
}

const OPORTUNIDAD = {
  codigo: 'OP-1',
  descripcion: 'Contrato de soporte',
  observaciones: 'Primera línea\nSegunda línea',
}
// "Escribir informe" convertida en una oportunidad.
const TAREA_OPORTUNIDAD = { ...TAREAS[0], tipo: 'oportunidad', oportunidad: OPORTUNIDAD }

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

async function elegirTipo(panel: HTMLElement, valor: string): Promise<void> {
  const selector = campo<HTMLSelectElement>(panel, '#tarea-tipo')
  selector.value = valor
  selector.dispatchEvent(new Event('change'))
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
      'Tipo',
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
        '20/11/2026 18:00:00 Vence en 10 d 23 h 14 min 30 s',
        '—',
        '',
      ],
      ['Leer artículo', '—', 'Artículo sobre Vue', '—', '—', '01/12/2026 17:05:09', '—', '—', ''],
    ])
  })

  describe('cuenta atrás del vencimiento', () => {
    function celdaVencimiento(envoltorio: VueWrapper, fila: number) {
      return envoltorio.findAll('tbody tr')[fila]!.findAll('td')[6]!
    }

    it('muestra bajo la fecha de vencimiento cuánto falta, solo en las tareas con vencimiento', async () => {
      const envoltorio = await montar()

      const contador = celdaVencimiento(envoltorio, 0).get('[data-testid="contador-vencimiento"]')
      expect(contador.text()).toBe('Vence en 10 d 23 h 14 min 30 s')
      expect(contador.classes()).toEqual(
        // Faltan más de 48 horas: en verde.
        expect.arrayContaining(['block', 'text-xs', 'text-green-700']),
      )
      expect(contador.classes()).not.toContain('text-destructive')
      expect(celdaVencimiento(envoltorio, 1).text()).toBe('—')
      expect(
        celdaVencimiento(envoltorio, 1).find('[data-testid="contador-vencimiento"]').exists(),
      ).toBe(false)
    })

    it('con el vencimiento pasado muestra cuánto hace que venció en rojo', async () => {
      const envoltorio = await montar([{ ...TAREAS[0], fecha_vencimiento: '2026-11-08T16:40:00' }])

      const contador = celdaVencimiento(envoltorio, 0).get('[data-testid="contador-vencimiento"]')
      expect(contador.text()).toBe('Vencida hace 1 d 02 h 05 min')
      expect(contador.classes()).toContain('text-destructive')
    })

    it('usa un único intervalo para todas las filas', async () => {
      const espiaIntervalo = vi.spyOn(globalThis, 'setInterval')
      await montar([TAREAS[0], { ...TAREAS[1], fecha_vencimiento: '2026-11-25T10:00:00' }])

      expect(espiaIntervalo.mock.calls.filter(([, ms]) => ms === 1000)).toHaveLength(1)
      espiaIntervalo.mockRestore()
    })
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
      ['Con fecha', '—', 'Detalle', '—', '—', '02/01/2027 03:04:05', '—', '—', ''],
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
      tipo: null,
      oportunidad: null,
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
      tipo: null,
      oportunidad: null,
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
        '30/11/2026 12:00:00 Vence en 20 d 17 h 14 min 30 s',
        '—',
        '',
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
      tipo: null,
      oportunidad: null,
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
      tipo: null,
      oportunidad: null,
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
        '—',
        '',
      ],
      ['Leer artículo', '—', 'Artículo sobre Vue', '—', '—', '01/12/2026 17:05:09', '—', '—', ''],
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
      ['Nueva', '1', 'Detalle', '—', '—', AHORA_TEXTO, '—', '—', ''],
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

  describe('tipo de tarea', () => {
    it('el campo "Tipo de tarea" ofrece "Sin tipo" y "Oportunidad", sin tipo por defecto', async () => {
      const panel = await abrirPanel(await montar())

      expect(panel.querySelector('label[for="tarea-tipo"]')?.textContent?.trim()).toBe(
        'Tipo de tarea',
      )
      const selector = campo<HTMLSelectElement>(panel, '#tarea-tipo')
      expect([...selector.options].map((opcion) => [opcion.value, opcion.text])).toEqual([
        ['', 'Sin tipo'],
        ['oportunidad', 'Oportunidad'],
      ])
      expect(selector.value).toBe('')
      expect(panel.querySelector('#oportunidad-codigo')).toBeNull()
    })

    it('al elegir "Oportunidad" muestra sus campos con sus restricciones', async () => {
      const panel = await abrirPanel(await montar())

      await elegirTipo(panel, 'oportunidad')

      expect(panel.querySelector('fieldset legend')?.textContent?.trim()).toBe('Oportunidad')
      const etiquetas = new Map(
        [...panel.querySelectorAll('label[for]')].map((l) => [
          l.getAttribute('for'),
          l.textContent?.trim(),
        ]),
      )
      expect(etiquetas.get('oportunidad-codigo')).toBe('Código de la oportunidad')
      expect(etiquetas.get('oportunidad-descripcion')).toBe('Descripción de la oportunidad')
      expect(etiquetas.get('oportunidad-observaciones')).toBe('Observaciones')
      const codigo = campo<HTMLInputElement>(panel, '#oportunidad-codigo')
      expect(codigo.required).toBe(true)
      expect(codigo.getAttribute('maxlength')).toBe('10')
      const descripcion = campo<HTMLInputElement>(panel, '#oportunidad-descripcion')
      expect(descripcion.required).toBe(false)
      expect(descripcion.getAttribute('maxlength')).toBe('200')
      const observaciones = campo<HTMLTextAreaElement>(panel, '#oportunidad-observaciones')
      expect(observaciones.tagName).toBe('TEXTAREA')
      expect(observaciones.required).toBe(false)
      expect(observaciones.getAttribute('maxlength')).toBe('5000')

      await elegirTipo(panel, '')
      expect(panel.querySelector('#oportunidad-codigo')).toBeNull()
    })

    it('crea una oportunidad enviando su tipo y sus campos, con los opcionales vacíos como null', async () => {
      const envoltorio = await montar([])
      vi.mocked(clienteApi.crear).mockResolvedValue({
        id: 7,
        nombre: 'Venta',
        prioridad: null,
        descripcion: 'Detalle',
        fecha_creacion: AHORA_ISO,
        ...SIN_EXTRAS,
        tipo: 'oportunidad',
        oportunidad: { codigo: 'OP-7', descripcion: null, observaciones: null },
      })
      const panel = await abrirPanel(envoltorio)

      await escribir(campo(panel, 'input[placeholder="Nombre"]'), 'Venta')
      await escribir(campo(panel, 'textarea[placeholder="Descripción"]'), 'Detalle')
      await elegirTipo(panel, 'oportunidad')
      await escribir(campo(panel, '#oportunidad-codigo'), 'OP-7')
      await escribir(campo(panel, '#oportunidad-descripcion'), '   ')
      await enviar(panel)

      expect(clienteApi.crear).toHaveBeenCalledWith('/tareas', {
        nombre: 'Venta',
        prioridad: null,
        descripcion: 'Detalle',
        fecha_creacion: AHORA_ISO,
        ...SIN_EXTRAS,
        tipo: 'oportunidad',
        oportunidad: { codigo: 'OP-7', descripcion: null, observaciones: null },
      })
      expect(filasTabla(envoltorio)).toEqual([
        ['Venta', '—', 'Detalle', '—', '—', AHORA_TEXTO, '—', 'Oportunidad', ''],
      ])
    })

    it('envía la descripción y las observaciones de la oportunidad escritas', async () => {
      const envoltorio = await montar([])
      vi.mocked(clienteApi.crear).mockResolvedValue({
        id: 8,
        nombre: 'Venta',
        prioridad: null,
        descripcion: 'Detalle',
        fecha_creacion: AHORA_ISO,
        ...SIN_EXTRAS,
        tipo: 'oportunidad',
        oportunidad: OPORTUNIDAD,
      })
      const panel = await abrirPanel(envoltorio)

      await escribir(campo(panel, 'input[placeholder="Nombre"]'), 'Venta')
      await escribir(campo(panel, 'textarea[placeholder="Descripción"]'), 'Detalle')
      await elegirTipo(panel, 'oportunidad')
      await escribir(campo(panel, '#oportunidad-codigo'), OPORTUNIDAD.codigo)
      await escribir(campo(panel, '#oportunidad-descripcion'), OPORTUNIDAD.descripcion)
      await escribir(campo(panel, '#oportunidad-observaciones'), OPORTUNIDAD.observaciones)
      await enviar(panel)

      expect(clienteApi.crear).toHaveBeenCalledWith(
        '/tareas',
        expect.objectContaining({ tipo: 'oportunidad', oportunidad: OPORTUNIDAD }),
      )
    })

    it('al editar una oportunidad carga su tipo y sus campos', async () => {
      const panel = await abrirPanelEdicion(
        await montar([TAREA_OPORTUNIDAD, TAREAS[1]]),
        'Escribir informe',
      )

      expect(campo<HTMLSelectElement>(panel, '#tarea-tipo').value).toBe('oportunidad')
      expect(campo<HTMLInputElement>(panel, '#oportunidad-codigo').value).toBe('OP-1')
      expect(campo<HTMLInputElement>(panel, '#oportunidad-descripcion').value).toBe(
        'Contrato de soporte',
      )
      expect(campo<HTMLTextAreaElement>(panel, '#oportunidad-observaciones').value).toBe(
        'Primera línea\nSegunda línea',
      )
    })

    it('al editar una oportunidad sin descripción ni observaciones deja esos campos vacíos', async () => {
      const tarea = {
        ...TAREA_OPORTUNIDAD,
        oportunidad: { codigo: 'OP-1', descripcion: null, observaciones: null },
      }
      const panel = await abrirPanelEdicion(await montar([tarea]), 'Escribir informe')

      expect(campo<HTMLInputElement>(panel, '#oportunidad-descripcion').value).toBe('')
      expect(campo<HTMLTextAreaElement>(panel, '#oportunidad-observaciones').value).toBe('')
    })

    it('al volver a "Sin tipo" oculta el bloque y envía tipo y oportunidad como null', async () => {
      const envoltorio = await montar([TAREA_OPORTUNIDAD])
      vi.mocked(clienteApi.actualizar).mockResolvedValue({ ...TAREAS[0] })
      const panel = await abrirPanelEdicion(envoltorio, 'Escribir informe')

      await elegirTipo(panel, '')
      expect(panel.querySelector('#oportunidad-codigo')).toBeNull()
      await enviar(panel)

      expect(clienteApi.actualizar).toHaveBeenCalledWith(
        '/tareas/1',
        expect.objectContaining({ tipo: null, oportunidad: null }),
      )
      expect(filasTabla(envoltorio)[0]?.[7]).toBe('—')
    })

    it('tras editar una oportunidad, "Crear tarea" vuelve a "Sin tipo" con el bloque vacío', async () => {
      const envoltorio = await montar([TAREA_OPORTUNIDAD])
      await abrirPanelEdicion(envoltorio, 'Escribir informe')

      const panel = await abrirPanel(envoltorio)
      expect(campo<HTMLSelectElement>(panel, '#tarea-tipo').value).toBe('')
      await elegirTipo(panel, 'oportunidad')
      expect(campo<HTMLInputElement>(panel, '#oportunidad-codigo').value).toBe('')
      expect(campo<HTMLInputElement>(panel, '#oportunidad-descripcion').value).toBe('')
      expect(campo<HTMLTextAreaElement>(panel, '#oportunidad-observaciones').value).toBe('')
    })

    it('muestra el tipo en la tabla y "—" en las tareas sin tipo', async () => {
      const envoltorio = await montar([TAREA_OPORTUNIDAD, TAREAS[1]])

      expect(filasTabla(envoltorio).map((fila) => fila[7])).toEqual(['Oportunidad', '—'])
      // Los campos propios de la oportunidad no aparecen en la tabla.
      expect(envoltorio.find('table').text()).not.toContain('OP-1')
      expect(envoltorio.find('table').text()).not.toContain('Contrato de soporte')
    })
  })

  describe('acciones de la fila', () => {
    it('"Editar" y "Detalle" son iconos con nombre accesible y title', async () => {
      const envoltorio = await montar()

      const editar = envoltorio.find('button[aria-label="Editar tarea Escribir informe"]')
      expect(editar.attributes('title')).toBe('Editar')
      expect(editar.text()).toBe('')
      expect(editar.find('svg').exists()).toBe(true)
      const detalle = envoltorio.find(
        'button[aria-label="Ver detalle de la tarea Escribir informe"]',
      )
      expect(detalle.attributes('title')).toBe('Detalle')
      expect(detalle.text()).toBe('')
      expect(detalle.find('svg').exists()).toBe(true)
      expect(
        envoltorio.find('button[aria-label="Ver detalle de la tarea Leer artículo"]').exists(),
      ).toBe(true)
    })

    it('"Detalle" abre la modal con todos los campos de esa tarea y se cierra con "Cerrar"', async () => {
      const envoltorio = await montar([TAREA_OPORTUNIDAD, TAREAS[1]])

      await envoltorio
        .find('button[aria-label="Ver detalle de la tarea Escribir informe"]')
        .trigger('click')
      await flushPromises()

      const modal = panelActual()
      expect(modal.querySelector('h2')?.textContent?.trim()).toBe('Escribir informe')
      expect(modal.textContent).toContain('OP-1')
      expect(modal.textContent).toContain('Contrato de soporte')
      expect(modal.className).toContain('w-[90vw]')

      const cerrar = [...modal.querySelectorAll('button')].find(
        (boton) => boton.textContent?.trim() === 'Cerrar',
      )!
      cerrar.click()
      await flushPromises()
      expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    })

    it('la modal de detalle se cierra con Escape', async () => {
      const envoltorio = await montar()

      await envoltorio
        .find('button[aria-label="Ver detalle de la tarea Leer artículo"]')
        .trigger('click')
      await flushPromises()
      expect(panelActual().querySelector('h2')?.textContent?.trim()).toBe('Leer artículo')

      panelActual().dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
      await flushPromises()
      expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    })
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
        tipo: null,
        oportunidad: null,
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
        tipo: null,
        oportunidad: null,
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
        tipo: null,
        oportunidad: null,
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
        'Tipo',
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

    it('ordena por tipo dejando las tareas sin tipo al final en ambos sentidos', async () => {
      const envoltorio = await montar([
        TAREAS_ORDEN[0],
        { ...TAREAS_ORDEN[1], tipo: 'oportunidad', oportunidad: OPORTUNIDAD },
        TAREAS_ORDEN[2],
      ])

      await cabecera(envoltorio, 'Tipo').trigger('click')
      expect(nombresEnTabla(envoltorio)).toEqual(['Árbol', 'beta', 'casa'])
      expect(thDe(envoltorio, 'Tipo').attributes('aria-sort')).toBe('ascending')
      await cabecera(envoltorio, 'Tipo').trigger('click')
      expect(nombresEnTabla(envoltorio)).toEqual(['Árbol', 'beta', 'casa'])
      expect(thDe(envoltorio, 'Tipo').attributes('aria-sort')).toBe('descending')
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
      'Tipo',
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
          '—',
        ],
        ['Leer artículo', '—', 'Artículo sobre Vue', '—', '—', '01/12/2026 17:05:09', '—', '—'],
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

    it('exporta el tipo con su texto visible y nunca los campos de la oportunidad', async () => {
      const envoltorio = await montar([TAREA_OPORTUNIDAD, TAREAS[1]])

      await botonExportar(envoltorio, 'Exportar a Excel').trigger('click')

      const filas = vi.mocked(exportarTablaExcel).mock.calls[0]![2] as unknown[][]
      expect(filas.map((fila) => fila[7])).toEqual(['Oportunidad', '—'])
      expect(filas[0]).toHaveLength(COLUMNAS.length)
      expect(JSON.stringify(filas)).not.toContain('OP-1')
    })
  })

  describe('filtros', () => {
    const TAREAS_FILTRO = [
      {
        id: 1,
        nombre: 'Preparar reunión',
        prioridad: 1,
        descripcion: 'Agenda del lunes',
        fecha_creacion: '2026-03-10T08:00:00',
        fecha_vencimiento: '2026-03-15T23:59:59',
        etiquetas: ['Backend', 'Urgente'],
        asignados: ['Ana'],
        tipo: null,
        oportunidad: null,
      },
      {
        id: 2,
        nombre: 'Revisar código',
        prioridad: 3,
        descripcion: 'Pull request de Ángela',
        fecha_creacion: '2026-03-11T23:59:59',
        fecha_vencimiento: null,
        etiquetas: ['Backend'],
        asignados: ['Luis'],
        tipo: null,
        oportunidad: null,
      },
      {
        id: 3,
        nombre: 'Comprar café',
        prioridad: null,
        descripcion: 'Oficina',
        fecha_creacion: '2026-03-12T00:00:00',
        fecha_vencimiento: '2026-03-16T00:00:00',
        etiquetas: [],
        asignados: [],
        tipo: null,
        oportunidad: null,
      },
    ]
    const TODAS = ['Preparar reunión', 'Revisar código', 'Comprar café']

    function nombresEnTabla(envoltorio: VueWrapper): string[] {
      return envoltorio.findAll('tbody tr').map((fila) => fila.findAll('td')[0]!.text())
    }

    function entrada(envoltorio: VueWrapper, id: string): HTMLInputElement {
      const elemento = envoltorio.find<HTMLInputElement>(`#${id}`)
      if (!elemento.exists()) throw new Error(`No se encontró #${id}`)
      return elemento.element
    }

    function disparador(envoltorio: VueWrapper, nombre: string) {
      // Los filtros múltiples se nombran "<etiqueta>: <texto visible>"; el resto, con la etiqueta.
      const boton = envoltorio.find(
        `button[aria-label="${nombre}"], button[aria-label^="${nombre}: "]`,
      )
      if (!boton.exists()) throw new Error(`No se encontró el botón "${nombre}"`)
      return boton
    }

    // Casilla de la lista desplegada (que se teletransporta al `body`) asociada a la etiqueta visible.
    function casilla(texto: string): HTMLElement {
      const etiqueta = [
        ...document.body.querySelectorAll<HTMLLabelElement>('[data-slot="popover-content"] label'),
      ].find((label) => label.textContent?.trim() === texto)
      const elemento = etiqueta ? document.getElementById(etiqueta.htmlFor) : null
      if (!elemento) throw new Error(`No se encontró la casilla "${texto}"`)
      return elemento
    }

    async function conDesplegable(
      envoltorio: VueWrapper,
      nombre: string,
      accion: () => Promise<void> | void,
    ): Promise<void> {
      await disparador(envoltorio, nombre).trigger('click')
      await flushPromises()
      await accion()
      await disparador(envoltorio, nombre).trigger('click')
      await flushPromises()
    }

    async function alternar(envoltorio: VueWrapper, nombre: string, opcion: string): Promise<void> {
      await conDesplegable(envoltorio, nombre, async () => {
        casilla(opcion).click()
        await flushPromises()
      })
    }

    it('muestra el panel "Filtros" abierto por defecto y se puede contraer', async () => {
      const envoltorio = await montar(TAREAS_FILTRO)

      const boton = disparador(envoltorio, 'Contraer filtros')
      expect(boton.text()).toBe('Filtros')
      expect(envoltorio.find('#filtro-buscar').exists()).toBe(true)

      await boton.trigger('click')
      await flushPromises()

      expect(disparador(envoltorio, 'Expandir filtros').exists()).toBe(true)
      expect(envoltorio.find('#filtro-buscar').exists()).toBe(false)
      expect(nombresEnTabla(envoltorio)).toEqual(TODAS)
    })

    it('todos los controles del panel tienen nombre accesible', async () => {
      const envoltorio = await montar(TAREAS_FILTRO)

      const etiquetas = new Map(
        envoltorio.findAll('label[for]').map((l) => [l.attributes('for'), l.text()]),
      )
      expect(etiquetas.get('filtro-buscar')).toBe('Buscar')
      expect(entrada(envoltorio, 'filtro-buscar').placeholder).toBe('Buscar tareas…')
      expect(etiquetas.get('filtro-creacion-desde')).toBe('Fecha de creación desde')
      expect(etiquetas.get('filtro-creacion-hasta')).toBe('Fecha de creación hasta')
      expect(etiquetas.get('filtro-vencimiento-desde')).toBe('Fecha de vencimiento desde')
      expect(etiquetas.get('filtro-vencimiento-hasta')).toBe('Fecha de vencimiento hasta')
      for (const id of [
        'filtro-creacion-desde',
        'filtro-creacion-hasta',
        'filtro-vencimiento-desde',
        'filtro-vencimiento-hasta',
      ]) {
        expect(entrada(envoltorio, id).type).toBe('date')
      }
      expect(disparador(envoltorio, 'Filtrar por prioridad').text()).toBe('Todas las prioridades')
      expect(disparador(envoltorio, 'Filtrar por etiquetas').text()).toBe('Todas las etiquetas')
      expect(disparador(envoltorio, 'Filtrar por asignado a').text()).toBe('Todas las personas')
    })

    it('busca en nombre y descripción sin distinguir mayúsculas ni acentos', async () => {
      const envoltorio = await montar(TAREAS_FILTRO)

      await escribir(entrada(envoltorio, 'filtro-buscar'), 'angela')
      expect(nombresEnTabla(envoltorio)).toEqual(['Revisar código'])

      await escribir(entrada(envoltorio, 'filtro-buscar'), 'REUNION')
      expect(nombresEnTabla(envoltorio)).toEqual(['Preparar reunión'])
    })

    it('filtra por prioridad, incluida la opción "Sin prioridad"', async () => {
      const envoltorio = await montar(TAREAS_FILTRO)

      await conDesplegable(envoltorio, 'Filtrar por prioridad', () => {
        const opciones = [
          ...document.body.querySelectorAll('[data-slot="popover-content"] li label'),
        ].map((label) => label.textContent?.trim())
        expect(opciones).toEqual(['1', '2', '3', '4', '5', 'Sin prioridad'])
      })
      await alternar(envoltorio, 'Filtrar por prioridad', 'Sin prioridad')
      expect(nombresEnTabla(envoltorio)).toEqual(['Preparar reunión', 'Revisar código'])

      await alternar(envoltorio, 'Filtrar por prioridad', '1')
      expect(nombresEnTabla(envoltorio)).toEqual(['Revisar código'])
    })

    it('filtra por etiquetas: pasa si tiene alguna marcada o, sin etiquetas, si "Sin etiquetas" lo está', async () => {
      const envoltorio = await montar(TAREAS_FILTRO)

      await alternar(envoltorio, 'Filtrar por etiquetas', 'Urgente')
      expect(nombresEnTabla(envoltorio)).toEqual(TODAS)

      await alternar(envoltorio, 'Filtrar por etiquetas', 'Backend')
      expect(nombresEnTabla(envoltorio)).toEqual(['Comprar café'])

      await alternar(envoltorio, 'Filtrar por etiquetas', 'Sin etiquetas')
      expect(nombresEnTabla(envoltorio)).toEqual([])
    })

    it('filtra por asignado a, incluida la opción "Sin asignar"', async () => {
      const envoltorio = await montar(TAREAS_FILTRO)

      await alternar(envoltorio, 'Filtrar por asignado a', 'Sin asignar')
      expect(nombresEnTabla(envoltorio)).toEqual(['Preparar reunión', 'Revisar código'])

      await alternar(envoltorio, 'Filtrar por asignado a', 'Ana')
      expect(nombresEnTabla(envoltorio)).toEqual(['Revisar código'])
    })

    it('filtra por fecha de creación con ambos extremos incluidos por día', async () => {
      const envoltorio = await montar(TAREAS_FILTRO)

      await escribir(entrada(envoltorio, 'filtro-creacion-desde'), '2026-03-11')
      expect(nombresEnTabla(envoltorio)).toEqual(['Revisar código', 'Comprar café'])

      await escribir(entrada(envoltorio, 'filtro-creacion-hasta'), '2026-03-11')
      expect(nombresEnTabla(envoltorio)).toEqual(['Revisar código'])

      await escribir(entrada(envoltorio, 'filtro-creacion-desde'), '')
      expect(nombresEnTabla(envoltorio)).toEqual(['Preparar reunión', 'Revisar código'])
    })

    it('filtra por fecha de vencimiento con ambos extremos incluidos y excluye las tareas sin vencimiento', async () => {
      const envoltorio = await montar(TAREAS_FILTRO)

      await escribir(entrada(envoltorio, 'filtro-vencimiento-desde'), '2026-03-16')
      expect(nombresEnTabla(envoltorio)).toEqual(['Comprar café'])

      await escribir(entrada(envoltorio, 'filtro-vencimiento-desde'), '')
      await escribir(entrada(envoltorio, 'filtro-vencimiento-hasta'), '2026-03-15')
      expect(nombresEnTabla(envoltorio)).toEqual(['Preparar reunión'])

      await escribir(entrada(envoltorio, 'filtro-vencimiento-hasta'), '')
      expect(nombresEnTabla(envoltorio)).toEqual(TODAS)
    })

    it('"Limpiar filtros" restablece todos los filtros', async () => {
      const envoltorio = await montar(TAREAS_FILTRO)
      await escribir(entrada(envoltorio, 'filtro-buscar'), 'zzz')
      await escribir(entrada(envoltorio, 'filtro-creacion-desde'), '2026-03-11')
      await escribir(entrada(envoltorio, 'filtro-creacion-hasta'), '2026-03-11')
      await escribir(entrada(envoltorio, 'filtro-vencimiento-desde'), '2026-03-16')
      await escribir(entrada(envoltorio, 'filtro-vencimiento-hasta'), '2026-03-16')
      await alternar(envoltorio, 'Filtrar por prioridad', 'Sin prioridad')
      await alternar(envoltorio, 'Filtrar por etiquetas', 'Sin etiquetas')
      await alternar(envoltorio, 'Filtrar por asignado a', 'Sin asignar')

      const boton = envoltorio.findAll('button').find((b) => b.text() === 'Limpiar filtros')!
      await boton.trigger('click')
      await flushPromises()

      expect(nombresEnTabla(envoltorio)).toEqual(TODAS)
      for (const id of [
        'filtro-buscar',
        'filtro-creacion-desde',
        'filtro-creacion-hasta',
        'filtro-vencimiento-desde',
        'filtro-vencimiento-hasta',
      ]) {
        expect(entrada(envoltorio, id).value).toBe('')
      }
      expect(disparador(envoltorio, 'Filtrar por prioridad').text()).toBe('Todas las prioridades')
      expect(disparador(envoltorio, 'Filtrar por etiquetas').text()).toBe('Todas las etiquetas')
      expect(disparador(envoltorio, 'Filtrar por asignado a').text()).toBe('Todas las personas')
    })

    it('sin coincidencias muestra "Ninguna tarea coincide con los filtros." en lugar de la tabla', async () => {
      const envoltorio = await montar(TAREAS_FILTRO)

      await escribir(entrada(envoltorio, 'filtro-buscar'), 'zzz')

      expect(envoltorio.text()).toContain('Ninguna tarea coincide con los filtros.')
      expect(envoltorio.text()).not.toContain('Todavía no hay tareas.')
      expect(envoltorio.find('table').exists()).toBe(false)
    })

    it('sin tareas muestra solo "Todavía no hay tareas."', async () => {
      const envoltorio = await montar([])

      expect(envoltorio.text()).toContain('Todavía no hay tareas.')
      expect(envoltorio.text()).not.toContain('Ninguna tarea coincide con los filtros.')
    })

    it('ordena solo las filas filtradas', async () => {
      const envoltorio = await montar(TAREAS_FILTRO)
      await alternar(envoltorio, 'Filtrar por prioridad', '1')

      const cabecera = envoltorio.findAll('th button').find((b) => b.text() === 'Nombre')!
      await cabecera.trigger('click')
      await cabecera.trigger('click')

      expect(nombresEnTabla(envoltorio)).toEqual(['Revisar código', 'Comprar café'])
    })

    it('exporta solo las filas filtradas', async () => {
      const envoltorio = await montar(TAREAS_FILTRO)
      await escribir(entrada(envoltorio, 'filtro-buscar'), 'cafe')

      await disparador(envoltorio, 'Exportar a Excel').trigger('click')

      const filas = vi.mocked(exportarTablaExcel).mock.calls[0]![2] as unknown[][]
      expect(filas.map((fila) => fila[0])).toEqual(['Comprar café'])
    })

    it('al recargar los catálogos marca los nombres nuevos y conserva los desmarcados', async () => {
      const envoltorio = await montar(TAREAS_FILTRO)
      await alternar(envoltorio, 'Filtrar por etiquetas', 'Urgente')
      await alternar(envoltorio, 'Filtrar por asignado a', 'Luis')
      vi.mocked(clienteApi.obtener).mockImplementation((ruta) => {
        if (ruta === '/etiquetas')
          return Promise.resolve([...ETIQUETAS, { id: 3, nombre: 'Nueva' }])
        if (ruta === '/personas') return Promise.resolve([...PERSONAS, { id: 3, nombre: 'Marta' }])
        return Promise.resolve(structuredClone(TAREAS_FILTRO))
      })

      await useTiendaTareas().cargarCatalogos()
      await flushPromises()

      await conDesplegable(envoltorio, 'Filtrar por etiquetas', () => {
        expect(casilla('Nueva').getAttribute('aria-checked')).toBe('true')
        expect(casilla('Urgente').getAttribute('aria-checked')).toBe('false')
        expect(casilla('Backend').getAttribute('aria-checked')).toBe('true')
      })
      await conDesplegable(envoltorio, 'Filtrar por asignado a', () => {
        expect(casilla('Marta').getAttribute('aria-checked')).toBe('true')
        expect(casilla('Luis').getAttribute('aria-checked')).toBe('false')
      })
      expect(nombresEnTabla(envoltorio)).toEqual(['Preparar reunión', 'Comprar café'])
    })

    it('filtra por tipo, incluida la opción "Sin tipo"', async () => {
      const envoltorio = await montar([
        { ...TAREAS_FILTRO[0], tipo: 'oportunidad', oportunidad: OPORTUNIDAD },
        TAREAS_FILTRO[1],
        TAREAS_FILTRO[2],
      ])
      expect(disparador(envoltorio, 'Filtrar por tipo').text()).toBe('Todos los tipos')

      await conDesplegable(envoltorio, 'Filtrar por tipo', () => {
        const opciones = [
          ...document.body.querySelectorAll('[data-slot="popover-content"] li label'),
        ].map((label) => label.textContent?.trim())
        expect(opciones).toEqual(['Oportunidad', 'Sin tipo'])
      })
      await alternar(envoltorio, 'Filtrar por tipo', 'Sin tipo')
      expect(nombresEnTabla(envoltorio)).toEqual(['Preparar reunión'])
      expect(disparador(envoltorio, 'Filtrar por tipo').text()).toBe('Oportunidad')

      await alternar(envoltorio, 'Filtrar por tipo', 'Oportunidad')
      expect(nombresEnTabla(envoltorio)).toEqual([])

      const boton = envoltorio.findAll('button').find((b) => b.text() === 'Limpiar filtros')!
      await boton.trigger('click')
      await flushPromises()
      expect(nombresEnTabla(envoltorio)).toEqual(TODAS)
      expect(disparador(envoltorio, 'Filtrar por tipo').text()).toBe('Todos los tipos')
    })
  })
})
