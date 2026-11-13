import { DOMWrapper, flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { clienteApi } from '@/api/cliente'
import { colorEtiqueta } from '@/lib/coloresTarea'
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
    parchear: vi.fn<(...args: unknown[]) => unknown>(),
    eliminar: vi.fn<(...args: unknown[]) => unknown>(),
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
    completada: false,
    subtareas: [],
    grupo_estados: null,
    estado: null,
    workflow: null,
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
    completada: false,
    subtareas: [],
    grupo_estados: null,
    estado: null,
    workflow: null,
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
  grupo_estados_id: null,
  workflow_id: null,
}

const OPORTUNIDAD = {
  codigo: 'OP-1',
  descripcion: 'Contrato de soporte',
  observaciones: 'Primera línea\nSegunda línea',
}
// "Escribir informe" convertida en una oportunidad.
const TAREA_OPORTUNIDAD = { ...TAREAS[0], tipo: 'oportunidad', oportunidad: OPORTUNIDAD }
// Subtareas de una oportunidad (los pasos del workflow se crean como
// subtareas): 1 de 3 resueltas.
const SUBTAREAS = [
  { id: 10, nombre: 'Contactar', asignado: null, prioridad: null, resuelta: true, comentarios: 0 },
  {
    id: 11,
    nombre: 'Enviar propuesta',
    asignado: null,
    prioridad: null,
    resuelta: false,
    comentarios: 0,
  },
  {
    id: 12,
    nombre: 'Firmar contrato',
    asignado: null,
    prioridad: null,
    resuelta: false,
    comentarios: 0,
  },
]
const OPORTUNIDAD_CON_SUBTAREAS = { ...TAREA_OPORTUNIDAD, subtareas: SUBTAREAS }

// Fecha y hora "actuales" fijas para que el valor por defecto sea determinista.
const AHORA = new Date(2026, 10, 9, 18, 45, 30)
const AHORA_TEXTO = '09/11/2026 18:45:30'
const AHORA_ISO = '2026-11-09T18:45:30'
const SELECTOR_FECHA = '#fecha-creacion'
const SELECTOR_VENCIMIENTO = '#fecha-vencimiento'

let contenedor: VueWrapper | null = null

async function montar(
  tareas: unknown[] = TAREAS,
  grupos: unknown[] = [],
  workflows: unknown[] = [],
): Promise<VueWrapper> {
  // Copia para que los tests que editan no alteren los datos compartidos.
  vi.mocked(clienteApi.obtener).mockImplementation((ruta) => {
    if (ruta === '/etiquetas') return Promise.resolve(structuredClone(ETIQUETAS))
    if (ruta === '/personas') return Promise.resolve(structuredClone(PERSONAS))
    if (ruta === '/grupos-estados') return Promise.resolve(structuredClone(grupos))
    if (ruta === '/workflows') return Promise.resolve(structuredClone(workflows))
    // El detalle carga los comentarios de la tarea abierta.
    if (String(ruta).endsWith('/comentarios')) return Promise.resolve([])
    return Promise.resolve(structuredClone(tareas))
  })
  const pinia = createPinia()
  setActivePinia(pinia)
  // El tablero enlaza con Ajustes cuando no hay grupos de estados.
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

type AccionFila = 'Editar tarea' | 'Ver detalle de la tarea' | 'Eliminar la tarea'

// Las acciones de cada fila están en su menú "⋯", que se teletransporta al `body`:
// se abre el menú y se devuelve la opción con el nombre accesible "<acción> <nombre>".
async function botonAccionFila(
  envoltorio: VueWrapper,
  nombre: string,
  accion: AccionFila,
): Promise<DOMWrapper<HTMLButtonElement>> {
  const menu = envoltorio.find(`button[aria-label="Acciones de la tarea ${nombre}"]`)
  if (!menu.exists()) throw new Error(`No se encontró el menú de acciones de "${nombre}"`)
  await menu.trigger('click')
  await flushPromises()
  const boton = document.body.querySelector<HTMLButtonElement>(
    `[data-slot="popover-content"] button[aria-label="${accion} ${nombre}"]`,
  )
  if (!boton) throw new Error(`No se encontró "${accion} ${nombre}" en el menú`)
  return new DOMWrapper(boton)
}

async function pulsarAccionFila(
  envoltorio: VueWrapper,
  nombre: string,
  accion: AccionFila,
): Promise<void> {
  await (await botonAccionFila(envoltorio, nombre, accion)).trigger('click')
  await flushPromises()
}

async function abrirPanelEdicion(envoltorio: VueWrapper, nombre: string): Promise<HTMLElement> {
  await pulsarAccionFila(envoltorio, nombre, 'Editar tarea')
  return panelActual()
}

// Filas de tareas de la tabla (sin las cabeceras, altas rápidas ni pies de los grupos).
const FILAS_TAREA = 'tbody tr[data-fila-tarea]'

// Las celdas con chips se leen como sus textos unidos por " | ". En el vencimiento,
// el texto une la fecha corta visible, la completa (solo para lectores de
// pantalla) y la cuenta atrás: "20 nov20/11/2026 18:00:00Vence en …".
function filasTabla(envoltorio: VueWrapper): string[][] {
  return envoltorio.findAll(FILAS_TAREA).map((tr) =>
    tr.findAll('td').map((td) => {
      // Las personas se ven como iniciales: se lee el nombre que representa cada chip.
      const chips = td.findAll('[data-testid="chip-tabla"]')
      return chips.length > 0
        ? chips.map((chip) => chip.attributes('data-nombre')).join(' | ')
        : td.text()
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
      'Estado',
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
        '20 nov20/11/2026 18:00:00Vence en 10 d 23 h 14 min 30 s',
        '—',
        '—',
        '',
      ],
      [
        'Leer artículo',
        '—',
        'Artículo sobre Vue',
        '—',
        '—',
        '01/12/2026 17:05:09',
        '—',
        '—',
        '—',
        '',
      ],
    ])
  })

  describe('cuenta atrás del vencimiento', () => {
    function celdaVencimiento(envoltorio: VueWrapper, fila: number) {
      return envoltorio.findAll(FILAS_TAREA)[fila]!.findAll('td')[6]!
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

  it('el botón "Crear tarea" abre una ventana modal centrada, no el panel lateral, con el título "Crear tarea"', async () => {
    const envoltorio = await montar()
    expect(document.body.querySelector('[role="dialog"]')).toBeNull()

    const panel = await abrirPanel(envoltorio)

    expect(panel.querySelector('h2')?.textContent?.trim()).toBe('Crear tarea')
    expect(panel.getAttribute('data-slot')).toBe('dialog-content')
    expect(document.body.querySelector('[data-slot="sheet-content"]')).toBeNull()
    expect(panel.className).toContain('w-[90vw]')
    // El cuerpo del formulario desplaza; los botones quedan fijos al pie.
    expect(campo(panel, '[data-testid="cuerpo-formulario-tarea"]').className).toContain(
      'overflow-y-scroll',
    )
    expect([...panel.querySelectorAll('button')].map((boton) => boton.textContent?.trim())).toEqual(
      expect.arrayContaining(['Guardar', 'Cancelar']),
    )
  })

  it('"Cancelar" cierra la ventana de alta sin crear nada', async () => {
    const panel = await abrirPanel(await montar())

    ;[...panel.querySelectorAll('button')]
      .find((b) => b.textContent?.trim() === 'Cancelar')!
      .click()
    await flushPromises()

    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    expect(clienteApi.crear).not.toHaveBeenCalled()
  })

  it('"Editar" abre una ventana modal como la del alta, no el panel lateral, con el título "Editar tarea"', async () => {
    const panel = await abrirPanelEdicion(await montar(), 'Escribir informe')

    expect(panel.querySelector('h2')?.textContent?.trim()).toBe('Editar tarea')
    expect(panel.getAttribute('data-slot')).toBe('dialog-content')
    expect(document.body.querySelector('[data-slot="sheet-content"]')).toBeNull()
    // Mismos datos de la tarea que antes en el panel.
    expect(panel.querySelector<HTMLInputElement>('#tarea-nombre')?.value).toBe('Escribir informe')
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
    // El asterisco visible marca el campo obligatorio (oculto a lectores de pantalla).
    expect(panel.querySelector('label[for="fecha-creacion"]')?.textContent?.trim()).toBe(
      'Fecha de creación*',
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
      ['Con fecha', '—', 'Detalle', '—', '—', '02/01/2027 03:04:05', '—', '—', '—', ''],
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
      grupo_estados_id: null,
      workflow_id: null,
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
        '30 nov30/11/2026 12:00:00Vence en 20 d 17 h 14 min 30 s',
        '—',
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
      grupo_estados_id: null,
      workflow_id: null,
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
        '—',
        '',
      ],
      [
        'Leer artículo',
        '—',
        'Artículo sobre Vue',
        '—',
        '—',
        '01/12/2026 17:05:09',
        '—',
        '—',
        '—',
        '',
      ],
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
      ['Nueva', '1', 'Detalle', '—', '—', AHORA_TEXTO, '—', '—', '—', ''],
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
    expect(envoltorio.findAll(FILAS_TAREA)).toHaveLength(0)
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
      expect(etiquetas.get('oportunidad-codigo')).toBe('Código de la oportunidad*')
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
        subtareas: [],
        grupo_estados: null,
        estado: null,
        workflow: null,
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
        ['Venta', '—', 'Detalle', '—', '—', AHORA_TEXTO, '—', 'Oportunidad', '—', ''],
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
        subtareas: [],
        grupo_estados: null,
        estado: null,
        workflow: null,
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

    it('junto al tipo muestra cuántas subtareas de la oportunidad están resueltas', async () => {
      const envoltorio = await montar([OPORTUNIDAD_CON_SUBTAREAS, TAREA_OPORTUNIDAD, TAREAS[1]])

      expect(filasTabla(envoltorio).map((fila) => fila[7])).toEqual([
        'Oportunidad · 1/3',
        'Oportunidad',
        '—',
      ])
    })
  })

  describe('acciones de la fila', () => {
    it('cada fila tiene un único menú "⋯" con Editar, Ver detalle y Eliminar, que conservan su nombre accesible', async () => {
      const envoltorio = await montar()

      const menu = envoltorio.get('button[aria-label="Acciones de la tarea Escribir informe"]')
      expect(menu.attributes('title')).toBe('Acciones')
      expect(menu.attributes('aria-haspopup')).toBe('dialog')
      expect(menu.text()).toBe('')
      expect(menu.find('svg').exists()).toBe(true)
      expect(
        envoltorio.find('button[aria-label="Acciones de la tarea Leer artículo"]').exists(),
      ).toBe(true)
      // Las acciones ya no son botones sueltos en la fila.
      expect(envoltorio.find('button[aria-label="Editar tarea Escribir informe"]').exists()).toBe(
        false,
      )

      await menu.trigger('click')
      await flushPromises()
      const opciones = [
        ...document.body.querySelectorAll<HTMLButtonElement>(
          '[data-slot="popover-content"] button',
        ),
      ]
      expect(opciones.map((opcion) => opcion.getAttribute('aria-label'))).toEqual([
        'Editar tarea Escribir informe',
        'Ver detalle de la tarea Escribir informe',
        'Eliminar la tarea Escribir informe',
      ])
      expect(opciones.map((opcion) => opcion.textContent?.trim())).toEqual([
        'Editar',
        'Ver detalle',
        'Eliminar',
      ])
    })

    it('al elegir una acción se cierra el menú', async () => {
      const envoltorio = await montar()

      await pulsarAccionFila(envoltorio, 'Escribir informe', 'Ver detalle de la tarea')

      expect(
        document.body.querySelector('button[aria-label="Editar tarea Escribir informe"]'),
      ).toBeNull()
      expect(panelActual().querySelector('h2')?.textContent?.trim()).toBe('Escribir informe')
    })

    it('"Detalle" abre la modal con todos los campos de esa tarea y se cierra con "Cerrar"', async () => {
      const envoltorio = await montar([TAREA_OPORTUNIDAD, TAREAS[1]])

      await pulsarAccionFila(envoltorio, 'Escribir informe', 'Ver detalle de la tarea')
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

      await pulsarAccionFila(envoltorio, 'Leer artículo', 'Ver detalle de la tarea')
      await flushPromises()
      expect(panelActual().querySelector('h2')?.textContent?.trim()).toBe('Leer artículo')

      panelActual().dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
      await flushPromises()
      expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    })

    describe('completar tarea', () => {
      function botonCompletar(envoltorio: VueWrapper, nombre: string) {
        return envoltorio.get(
          `[role="checkbox"][aria-label="Marcar como completada la tarea ${nombre}"]`,
        )
      }

      function celdasDatos(envoltorio: VueWrapper, fila: number) {
        const celdas = envoltorio.findAll(FILAS_TAREA)[fila]!.findAll('td')
        return celdas.slice(0, celdas.length - 1)
      }

      function celdaAcciones(envoltorio: VueWrapper, fila: number) {
        const celdas = envoltorio.findAll(FILAS_TAREA)[fila]!.findAll('td')
        return celdas[celdas.length - 1]!
      }

      it('al inicio de la fila hay una casilla sin marcar con nombre accesible y title "Pendiente"', async () => {
        const envoltorio = await montar()

        const primeraCelda = envoltorio.findAll(FILAS_TAREA)[0]!.findAll('td')[0]!
        const completar = botonCompletar(envoltorio, 'Escribir informe')
        expect(primeraCelda.element.firstElementChild?.contains(completar.element)).toBe(true)
        expect(primeraCelda.text()).toBe('Escribir informe')
        expect(completar.attributes('aria-checked')).toBe('false')
        expect(completar.attributes('title')).toBe('Pendiente')
        // La celda de acciones solo tiene el menú.
        expect(
          celdaAcciones(envoltorio, 0)
            .findAll('button')
            .map((boton) => boton.attributes('aria-label')),
        ).toEqual(['Acciones de la tarea Escribir informe'])
      })

      it('una tarea completada muestra la casilla marcada con title "Completada"', async () => {
        const envoltorio = await montar([{ ...TAREAS[0], completada: true }])

        const completar = botonCompletar(envoltorio, 'Escribir informe')
        expect(completar.attributes('aria-checked')).toBe('true')
        expect(completar.attributes('title')).toBe('Completada')
      })

      it('tacha las celdas de datos solo de las tareas completadas, cuenta atrás incluida, y nunca los botones', async () => {
        // Las completadas van en su grupo, tras las pendientes.
        const envoltorio = await montar([{ ...TAREAS[0], completada: true }, TAREAS[1]])

        for (const celda of celdasDatos(envoltorio, 1)) {
          expect(celda.classes()).toContain('line-through')
        }
        expect(
          envoltorio.findAll(FILAS_TAREA)[1]!.get('[data-testid="contador-vencimiento"]').classes(),
        ).toContain('line-through')
        expect(celdaAcciones(envoltorio, 1).classes()).not.toContain('line-through')
        expect(celdaAcciones(envoltorio, 1).find('.line-through').exists()).toBe(false)
        for (const celda of celdasDatos(envoltorio, 0)) {
          expect(celda.classes()).not.toContain('line-through')
        }
        expect(envoltorio.findAll(FILAS_TAREA)[0]!.find('.line-through').exists()).toBe(false)
      })

      it('al pulsarlo la marca como completada y al volver a pulsarlo vuelve a pendiente', async () => {
        vi.mocked(clienteApi.parchear).mockImplementation((_ruta, cuerpo) =>
          Promise.resolve({
            ...structuredClone(TAREAS[0]),
            completada: (cuerpo as { completada: boolean }).completada,
          }),
        )
        // Una sola tarea: al completarla pasa al grupo "Completadas" y sigue siendo la primera fila.
        const envoltorio = await montar([TAREAS[0]])

        await botonCompletar(envoltorio, 'Escribir informe').trigger('click')
        await flushPromises()

        expect(clienteApi.parchear).toHaveBeenLastCalledWith('/tareas/1/completada', {
          completada: true,
        })
        expect(botonCompletar(envoltorio, 'Escribir informe').attributes('aria-checked')).toBe(
          'true',
        )
        expect(celdasDatos(envoltorio, 0)[0]!.classes()).toContain('line-through')

        await botonCompletar(envoltorio, 'Escribir informe').trigger('click')
        await flushPromises()

        expect(clienteApi.parchear).toHaveBeenLastCalledWith('/tareas/1/completada', {
          completada: false,
        })
        expect(botonCompletar(envoltorio, 'Escribir informe').attributes('aria-checked')).toBe(
          'false',
        )
        expect(celdasDatos(envoltorio, 0)[0]!.classes()).not.toContain('line-through')
        expect(clienteApi.parchear).toHaveBeenCalledTimes(2)
      })

      it('si la API falla muestra el error y la tarea sigue pendiente', async () => {
        vi.mocked(clienteApi.parchear).mockRejectedValue(new Error('Tarea no encontrada'))
        const envoltorio = await montar()

        await botonCompletar(envoltorio, 'Escribir informe').trigger('click')
        await flushPromises()

        expect(envoltorio.get('[role="alert"]').text()).toBe('Tarea no encontrada')
        expect(botonCompletar(envoltorio, 'Escribir informe').attributes('aria-checked')).toBe(
          'false',
        )
        expect(celdasDatos(envoltorio, 0)[0]!.classes()).not.toContain('line-through')
      })

      it('la modal de detalle muestra el estado de la tarea', async () => {
        const envoltorio = await montar([{ ...TAREAS[0], completada: true }])

        await pulsarAccionFila(envoltorio, 'Escribir informe', 'Ver detalle de la tarea')
        await flushPromises()

        expect(panelActual().textContent).toContain('EstadoCompletada')
      })
    })

    describe('avance de las subtareas', () => {
      async function abrirDetalle(envoltorio: VueWrapper): Promise<HTMLElement> {
        await pulsarAccionFila(envoltorio, 'Escribir informe', 'Ver detalle de la tarea')
        await flushPromises()
        return panelActual()
      }

      it('el detalle no muestra pasos del workflow sino las subtareas', async () => {
        const envoltorio = await montar([OPORTUNIDAD_CON_SUBTAREAS])
        const modal = await abrirDetalle(envoltorio)

        expect(modal.textContent).not.toContain('Pasos del workflow')
        expect(modal.querySelector('[role="checkbox"]')).toBeNull()
        expect(
          modal.querySelector('button[aria-label="Marcar como resuelta la subtarea Contactar"]'),
        ).not.toBeNull()
      })

      it('al resolver una subtarea en el detalle se actualiza el avance de la tabla', async () => {
        vi.mocked(clienteApi.parchear).mockImplementation((ruta, cuerpo) => {
          // Ruta: /tareas/{id}/subtareas/{id_subtarea}/resuelta
          const idSubtarea = Number(String(ruta).split('/')[4])
          const { resuelta } = cuerpo as { resuelta: boolean }
          return Promise.resolve({
            ...structuredClone(OPORTUNIDAD_CON_SUBTAREAS),
            subtareas: SUBTAREAS.map((subtarea) =>
              subtarea.id === idSubtarea ? { ...subtarea, resuelta } : subtarea,
            ),
          })
        })
        const envoltorio = await montar([OPORTUNIDAD_CON_SUBTAREAS])
        const modal = await abrirDetalle(envoltorio)

        modal
          .querySelector<HTMLButtonElement>(
            'button[aria-label="Marcar como resuelta la subtarea Enviar propuesta"]',
          )!
          .click()
        await flushPromises()

        expect(clienteApi.parchear).toHaveBeenCalledWith('/tareas/1/subtareas/11/resuelta', {
          resuelta: true,
        })
        expect(filasTabla(envoltorio)[0]![7]).toBe('Oportunidad · 2/3')
      })
    })

    describe('eliminar tarea', () => {
      function botonEliminar(envoltorio: VueWrapper, nombre: string) {
        return botonAccionFila(envoltorio, nombre, 'Eliminar la tarea')
      }

      function botonMenu(envoltorio: VueWrapper, nombre: string) {
        return envoltorio.get(`button[aria-label="Acciones de la tarea ${nombre}"]`)
      }

      function confirmacion(): HTMLElement {
        const dialogo = document.body.querySelector<HTMLElement>('[role="alertdialog"]')
        if (!dialogo) throw new Error('No se abrió la confirmación')
        return dialogo
      }

      function botonDe(contenedorBotones: HTMLElement, texto: string): HTMLButtonElement {
        const boton = [...contenedorBotones.querySelectorAll('button')].find(
          (b) => b.textContent?.trim() === texto,
        )
        if (!boton) throw new Error(`No se encontró el botón "${texto}"`)
        return boton
      }

      it('el menú de cada fila tiene la opción "Eliminar la tarea X"', async () => {
        const envoltorio = await montar()

        const eliminar = await botonEliminar(envoltorio, 'Escribir informe')
        expect(eliminar.text()).toBe('Eliminar')
        expect(eliminar.find('svg').exists()).toBe(true)
      })

      it('desde la lista pide confirmación y al confirmar la elimina y lleva el foco a la siguiente fila', async () => {
        vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)
        const envoltorio = await montar()

        await (await botonEliminar(envoltorio, 'Escribir informe')).trigger('click')
        await flushPromises()

        const dialogo = confirmacion()
        expect(dialogo.querySelector('h2')?.textContent?.trim()).toBe(
          '¿Eliminar la tarea Escribir informe?',
        )
        expect(dialogo.textContent).toContain('También se eliminarán sus subtareas y comentarios.')
        expect(clienteApi.eliminar).not.toHaveBeenCalled()
        // El foco empieza en "Cancelar", la opción que no destruye nada.
        expect(document.activeElement?.textContent?.trim()).toBe('Cancelar')
        expect(botonDe(dialogo, 'Eliminar').className).toContain('bg-destructive')

        botonDe(dialogo, 'Eliminar').click()
        await flushPromises()

        expect(clienteApi.eliminar).toHaveBeenCalledWith('/tareas/1')
        expect(document.body.querySelector('[role="alertdialog"]')).toBeNull()
        expect(filasTabla(envoltorio).map((fila) => fila[0])).toEqual(['Leer artículo'])
        expect(document.activeElement?.getAttribute('aria-label')).toBe(
          'Acciones de la tarea Leer artículo',
        )
      })

      it('al eliminar la última fila el foco pasa al título de la lista', async () => {
        vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)
        const envoltorio = await montar([TAREAS[0]])

        await (await botonEliminar(envoltorio, 'Escribir informe')).trigger('click')
        await flushPromises()
        botonDe(confirmacion(), 'Eliminar').click()
        await flushPromises()

        expect(envoltorio.text()).toContain('Todavía no hay tareas.')
        expect(document.activeElement?.tagName).toBe('H2')
        expect(document.activeElement?.textContent?.trim()).toBe('Tareas')
      })

      it('"Cancelar" cierra la confirmación sin eliminar y devuelve el foco al menú de la fila', async () => {
        const envoltorio = await montar()
        const eliminar = await botonEliminar(envoltorio, 'Escribir informe')
        eliminar.element.focus()

        await eliminar.trigger('click')
        await flushPromises()
        botonDe(confirmacion(), 'Cancelar').click()
        await flushPromises()

        expect(clienteApi.eliminar).not.toHaveBeenCalled()
        expect(document.body.querySelector('[role="alertdialog"]')).toBeNull()
        expect(filasTabla(envoltorio)).toHaveLength(2)
        expect(document.activeElement).toBe(botonMenu(envoltorio, 'Escribir informe').element)
      })

      it('si la API falla muestra el error en la confirmación y conserva la tarea', async () => {
        vi.mocked(clienteApi.eliminar).mockRejectedValue(new Error('Tarea no encontrada'))
        const envoltorio = await montar()

        await (await botonEliminar(envoltorio, 'Escribir informe')).trigger('click')
        await flushPromises()
        botonDe(confirmacion(), 'Eliminar').click()
        await flushPromises()

        expect(confirmacion().querySelector('[role="alert"]')?.textContent?.trim()).toBe(
          'Tarea no encontrada',
        )
        expect(filasTabla(envoltorio)).toHaveLength(2)
      })

      it('desde el detalle pide confirmación; cancelar mantiene el detalle y confirmar lo cierra', async () => {
        vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)
        const envoltorio = await montar()
        await pulsarAccionFila(envoltorio, 'Escribir informe', 'Ver detalle de la tarea')
        await flushPromises()

        const detalle = panelActual()
        detalle
          .querySelector<HTMLButtonElement>(
            'button[aria-label="Eliminar la tarea Escribir informe"]',
          )!
          .click()
        await flushPromises()
        botonDe(confirmacion(), 'Cancelar').click()
        await flushPromises()

        expect(clienteApi.eliminar).not.toHaveBeenCalled()
        expect(panelActual().querySelector('h2')?.textContent?.trim()).toBe('Escribir informe')

        panelActual()
          .querySelector<HTMLButtonElement>(
            'button[aria-label="Eliminar la tarea Escribir informe"]',
          )!
          .click()
        await flushPromises()
        botonDe(confirmacion(), 'Eliminar').click()
        await flushPromises()

        expect(clienteApi.eliminar).toHaveBeenCalledWith('/tareas/1')
        expect(document.body.querySelector('[role="dialog"]')).toBeNull()
        expect(document.body.querySelector('[role="alertdialog"]')).toBeNull()
        expect(filasTabla(envoltorio).map((fila) => fila[0])).toEqual(['Leer artículo'])
        expect(document.activeElement).not.toBe(document.body)
        expect(document.activeElement?.getAttribute('aria-label')).toBe(
          'Acciones de la tarea Leer artículo',
        )
      })
    })
  })

  describe('grupos Pendientes y Completadas', () => {
    const CLAVE_PLEGADOS = 'gestor-tareas:grupos-plegados-tareas'
    const COMPLETADA = {
      ...TAREAS[1],
      id: 3,
      nombre: 'Archivar facturas',
      prioridad: 1,
      completada: true,
    }

    beforeEach(() => localStorage.removeItem(CLAVE_PLEGADOS))
    afterEach(() => localStorage.removeItem(CLAVE_PLEGADOS))

    function grupo(envoltorio: VueWrapper, id: 'pendientes' | 'completadas') {
      return envoltorio.get(`tbody[data-grupo="${id}"]`)
    }

    function cabeceraGrupo(envoltorio: VueWrapper, id: 'pendientes' | 'completadas') {
      return grupo(envoltorio, id).get('button[aria-expanded]')
    }

    function nombresDe(envoltorio: VueWrapper, id: 'pendientes' | 'completadas'): string[] {
      return grupo(envoltorio, id)
        .findAll('tr[data-fila-tarea]')
        .map((fila) => fila.findAll('td')[0]!.text())
    }

    function altaRapida(envoltorio: VueWrapper, id: 'pendientes' | 'completadas') {
      return grupo(envoltorio, id).get<HTMLInputElement>('input[data-alta-rapida]')
    }

    it('divide la tabla en "Pendientes" y "Completadas", cada una con su número de tareas', async () => {
      const envoltorio = await montar([COMPLETADA, ...TAREAS])

      const grupos = envoltorio.findAll('tbody[data-grupo]')
      expect(grupos.map((g) => g.attributes('data-grupo'))).toEqual(['pendientes', 'completadas'])
      expect(cabeceraGrupo(envoltorio, 'pendientes').text()).toBe('Pendientes 2')
      expect(cabeceraGrupo(envoltorio, 'completadas').text()).toBe('Completadas 1')
      expect(nombresDe(envoltorio, 'pendientes')).toEqual(['Escribir informe', 'Leer artículo'])
      expect(nombresDe(envoltorio, 'completadas')).toEqual(['Archivar facturas'])
    })

    it('cada grupo tiene su color en el borde izquierdo de todas sus filas', async () => {
      const envoltorio = await montar([COMPLETADA, ...TAREAS])

      for (const id of ['pendientes', 'completadas'] as const) {
        const filas = grupo(envoltorio, id).findAll('tr')
        const colores = new Set(
          filas.map((fila) => {
            const clases = fila.findAll('td')[0]!.classes()
            expect(clases).toContain('border-l-4')
            return clases.find((clase) => clase.startsWith('border-l-') && clase !== 'border-l-4')
          }),
        )
        expect(colores.size).toBe(1)
      }
      const colorDe = (id: 'pendientes' | 'completadas') =>
        grupo(envoltorio, id)
          .findAll('td')[0]!
          .classes()
          .find((clase) => clase.startsWith('border-l-') && clase !== 'border-l-4')
      expect(colorDe('pendientes')).not.toBe(colorDe('completadas'))
    })

    it('ambos grupos empiezan desplegados; al pulsar la cabecera se pliega y se recuerda al volver', async () => {
      let envoltorio = await montar([COMPLETADA, ...TAREAS])

      expect(cabeceraGrupo(envoltorio, 'pendientes').attributes('aria-expanded')).toBe('true')
      expect(cabeceraGrupo(envoltorio, 'completadas').attributes('aria-expanded')).toBe('true')

      await cabeceraGrupo(envoltorio, 'completadas').trigger('click')
      expect(cabeceraGrupo(envoltorio, 'completadas').attributes('aria-expanded')).toBe('false')
      expect(nombresDe(envoltorio, 'completadas')).toEqual([])
      expect(grupo(envoltorio, 'completadas').find('input[data-alta-rapida]').exists()).toBe(false)
      expect(nombresDe(envoltorio, 'pendientes')).toEqual(['Escribir informe', 'Leer artículo'])
      expect(JSON.parse(localStorage.getItem(CLAVE_PLEGADOS)!)).toEqual(['completadas'])

      envoltorio.unmount()
      envoltorio = await montar([COMPLETADA, ...TAREAS])
      expect(cabeceraGrupo(envoltorio, 'completadas').attributes('aria-expanded')).toBe('false')
      expect(nombresDe(envoltorio, 'completadas')).toEqual([])

      await cabeceraGrupo(envoltorio, 'completadas').trigger('click')
      expect(nombresDe(envoltorio, 'completadas')).toEqual(['Archivar facturas'])
      expect(JSON.parse(localStorage.getItem(CLAVE_PLEGADOS)!)).toEqual([])
    })

    it('un grupo sin filas sigue mostrando su cabecera (p. ej. con el filtro de estado)', async () => {
      const envoltorio = await montar(TAREAS)

      expect(cabeceraGrupo(envoltorio, 'completadas').text()).toBe('Completadas 0')
      expect(nombresDe(envoltorio, 'completadas')).toEqual([])
    })

    it('"+ Agregar tarea" en Pendientes crea la tarea solo con el nombre', async () => {
      const creada = {
        ...TAREAS[1],
        id: 9,
        nombre: 'Llamar al proveedor',
        descripcion: 'Llamar al proveedor',
        fecha_creacion: AHORA_ISO,
      }
      vi.mocked(clienteApi.crear).mockResolvedValue(structuredClone(creada))
      const envoltorio = await montar()

      const entrada = altaRapida(envoltorio, 'pendientes')
      expect(entrada.attributes('placeholder')).toBe('+ Agregar tarea')
      expect(entrada.attributes('aria-label')).toBe('Agregar tarea a Pendientes')
      await escribir(entrada.element, '  Llamar al proveedor ')
      await pulsarEnter(entrada.element)

      expect(clienteApi.crear).toHaveBeenCalledWith('/tareas', {
        nombre: 'Llamar al proveedor',
        prioridad: null,
        // La API exige descripción: se usa el propio nombre.
        descripcion: 'Llamar al proveedor',
        fecha_creacion: AHORA_ISO,
        ...SIN_EXTRAS,
      })
      expect(clienteApi.parchear).not.toHaveBeenCalled()
      expect(nombresDe(envoltorio, 'pendientes')).toContain('Llamar al proveedor')
      expect(altaRapida(envoltorio, 'pendientes').element.value).toBe('')
    })

    it('"+ Agregar tarea" en Completadas la crea ya completada', async () => {
      const creada = { ...TAREAS[1], id: 9, nombre: 'Hecha', descripcion: 'Hecha' }
      vi.mocked(clienteApi.crear).mockResolvedValue(structuredClone(creada))
      vi.mocked(clienteApi.parchear).mockResolvedValue({
        ...structuredClone(creada),
        completada: true,
      })
      const envoltorio = await montar()

      const entrada = altaRapida(envoltorio, 'completadas')
      expect(entrada.attributes('aria-label')).toBe('Agregar tarea a Completadas')
      await escribir(entrada.element, 'Hecha')
      await pulsarEnter(entrada.element)

      expect(clienteApi.crear).toHaveBeenCalledTimes(1)
      expect(clienteApi.parchear).toHaveBeenCalledWith('/tareas/9/completada', { completada: true })
      expect(nombresDe(envoltorio, 'completadas')).toEqual(['Hecha'])
    })

    it('"+ Agregar tarea" sin nombre no llama a la API y, si la API falla, muestra el error', async () => {
      vi.mocked(clienteApi.crear).mockRejectedValue(new Error('No se pudo crear'))
      const envoltorio = await montar()
      const entrada = altaRapida(envoltorio, 'pendientes')

      await escribir(entrada.element, '   ')
      await pulsarEnter(entrada.element)
      expect(clienteApi.crear).not.toHaveBeenCalled()

      await escribir(entrada.element, 'Nueva')
      await pulsarEnter(entrada.element)
      expect(grupo(envoltorio, 'pendientes').get('[role="alert"]').text()).toBe('No se pudo crear')
      expect(altaRapida(envoltorio, 'pendientes').element.value).toBe('Nueva')
    })

    it('el pie de cada grupo muestra la barra de distribución de prioridades', async () => {
      const envoltorio = await montar([COMPLETADA, ...TAREAS])

      const barra = grupo(envoltorio, 'pendientes').get('[data-testid="barra-prioridades"]')
      expect(barra.attributes('role')).toBe('img')
      expect(barra.attributes('aria-label')).toBe(
        'Distribución de prioridades en Pendientes: prioridad 2, 1 tarea; sin prioridad, 1 tarea',
      )
      const segmentos = barra.findAll('[data-prioridad]')
      expect(segmentos.map((segmento) => segmento.attributes('data-prioridad'))).toEqual([
        '2',
        'sin',
      ])
      expect(segmentos.map((segmento) => segmento.attributes('style'))).toEqual([
        'width: 50%;',
        'width: 50%;',
      ])
      expect(
        grupo(envoltorio, 'completadas')
          .get('[data-testid="barra-prioridades"]')
          .attributes('aria-label'),
      ).toBe('Distribución de prioridades en Completadas: prioridad 1, 1 tarea')
    })

    it('ordenar se aplica dentro de cada grupo y la exportación sigue siendo una lista única', async () => {
      const envoltorio = await montar([...TAREAS, COMPLETADA])

      const cabecera = envoltorio.findAll('th button').find((b) => b.text() === 'Nombre')!
      await cabecera.trigger('click')

      expect(nombresDe(envoltorio, 'pendientes')).toEqual(['Escribir informe', 'Leer artículo'])
      expect(nombresDe(envoltorio, 'completadas')).toEqual(['Archivar facturas'])
      await envoltorio.get('button[aria-label="Exportar a Excel"]').trigger('click')
      const filas = vi.mocked(exportarTablaExcel).mock.calls[0]![2] as unknown[][]
      expect(filas.map((fila) => fila[0])).toEqual([
        'Archivar facturas',
        'Escribir informe',
        'Leer artículo',
      ])
    })
  })

  describe('celdas de color', () => {
    function celda(envoltorio: VueWrapper, fila: number, columna: string) {
      const indice = envoltorio.findAll('thead th').findIndex((th) => th.text().trim() === columna)
      if (indice === -1) throw new Error(`No hay columna "${columna}"`)
      return envoltorio.findAll(FILAS_TAREA)[fila]!.findAll('td')[indice]!
    }

    it('la prioridad es una píldora de color: 1 rojo, 2 naranja, 3 azul, 4 verde azulado y 5 gris', async () => {
      const envoltorio = await montar(
        [1, 2, 3, 4, 5, null].map((prioridad, indice) => ({
          ...TAREAS[1],
          id: indice + 1,
          nombre: `Tarea ${indice + 1}`,
          prioridad,
        })),
      )

      const colores = ['bg-red-100', 'bg-orange-100', 'bg-blue-100', 'bg-teal-100', 'bg-gray-100']
      colores.forEach((color, fila) => {
        const pildora = celda(envoltorio, fila, 'Prioridad').get(
          '[data-testid="pildora-prioridad"]',
        )
        expect(pildora.text()).toBe(String(fila + 1))
        expect(pildora.classes()).toContain(color)
        // Tonos propios en modo oscuro.
        expect(pildora.classes().some((clase) => clase.startsWith('dark:bg-'))).toBe(true)
      })
      const sinPrioridad = celda(envoltorio, 5, 'Prioridad')
      expect(sinPrioridad.text()).toBe('—')
      expect(sinPrioridad.find('[data-testid="pildora-prioridad"]').exists()).toBe(false)
    })

    it('el tipo es una píldora de color con su texto y avance', async () => {
      const envoltorio = await montar([OPORTUNIDAD_CON_SUBTAREAS, TAREAS[1]])

      const pildora = celda(envoltorio, 0, 'Tipo').get('[data-testid="pildora-tipo"]')
      expect(pildora.text()).toBe('Oportunidad · 1/3')
      expect(pildora.classes()).toContain('bg-violet-100')
      expect(celda(envoltorio, 1, 'Tipo').text()).toBe('—')
      expect(celda(envoltorio, 1, 'Tipo').find('[data-testid="pildora-tipo"]').exists()).toBe(false)
    })

    it('muestra el estado del grupo como píldora: el primero gris, el último verde y los intermedios azules', async () => {
      const grupos = [
        {
          id: 1,
          nombre: 'Desarrollo',
          tareas: 3,
          estados: [
            { id: 10, nombre: 'Pendiente', posicion: 1, tareas: 1 },
            { id: 11, nombre: 'En curso', posicion: 2, tareas: 1 },
            { id: 12, nombre: 'Hecho', posicion: 3, tareas: 1 },
          ],
        },
      ]
      const enGrupo = (id: number, nombre: string, idEstado: number, estado: string) => ({
        ...TAREAS[1],
        id,
        nombre,
        grupo_estados: { id: 1, nombre: 'Desarrollo' },
        estado: { id: idEstado, nombre: estado },
      })
      const envoltorio = await montar(
        [
          enGrupo(1, 'A', 10, 'Pendiente'),
          enGrupo(2, 'B', 11, 'En curso'),
          enGrupo(3, 'C', 12, 'Hecho'),
          { ...TAREAS[1], id: 4, nombre: 'D' },
        ],
        grupos,
      )

      const pildora = (fila: number) =>
        celda(envoltorio, fila, 'Estado').get('[data-testid="pildora-estado"]')
      expect([0, 1, 2].map((fila) => pildora(fila).text())).toEqual([
        'Pendiente',
        'En curso',
        'Hecho',
      ])
      expect(pildora(0).classes()).toContain('bg-gray-100')
      expect(pildora(1).classes()).toContain('bg-blue-100')
      expect(pildora(2).classes()).toContain('bg-emerald-100')
      expect(celda(envoltorio, 3, 'Estado').text()).toBe('—')

      // Se ordena y se exporta por el nombre del estado.
      const cabecera = envoltorio.findAll('th button').find((b) => b.text() === 'Estado')!
      await cabecera.trigger('click')
      expect(envoltorio.findAll(FILAS_TAREA).map((f) => f.findAll('td')[0]!.text())).toEqual([
        'B',
        'C',
        'A',
        'D',
      ])
      await envoltorio.get('button[aria-label="Exportar a Excel"]').trigger('click')
      const [, columnas, filas] = vi.mocked(exportarTablaExcel).mock.calls[0]!
      const indice = (columnas as string[]).indexOf('Estado')
      expect((filas as unknown[][]).map((fila) => fila[indice])).toEqual([
        'En curso',
        'Hecho',
        'Pendiente',
        '—',
      ])
    })

    describe('vencimiento', () => {
      it('muestra la fecha corta con la completa en el title y para lectores de pantalla, y conserva la cuenta atrás', async () => {
        const envoltorio = await montar()

        const corto = celda(envoltorio, 0, 'Fecha de vencimiento').get(
          '[data-testid="vencimiento-corto"]',
        )
        const fecha = corto.get('time')
        expect(fecha.attributes('datetime')).toBe('2026-11-20T18:00:00')
        expect(fecha.attributes('title')).toBe('20/11/2026 18:00:00')
        expect(fecha.get('[aria-hidden="true"]').text()).toBe('20 nov')
        expect(fecha.get('.sr-only').text()).toBe('20/11/2026 18:00:00')
        expect(corto.attributes('data-icono')).toBeUndefined()
        expect(
          celda(envoltorio, 0, 'Fecha de vencimiento')
            .get('[data-testid="contador-vencimiento"]')
            .text(),
        ).toBe('Vence en 10 d 23 h 14 min 30 s')
      })

      it('con la tarea completada muestra un ✓ y con el vencimiento pasado un ! rojo', async () => {
        const envoltorio = await montar([
          { ...TAREAS[0], id: 1, nombre: 'Vencida', fecha_vencimiento: '2026-11-01T10:00:00' },
          { ...TAREAS[0], id: 2, nombre: 'Hecha', completada: true },
        ])

        const vencida = celda(envoltorio, 0, 'Fecha de vencimiento').get(
          '[data-testid="vencimiento-corto"]',
        )
        expect(vencida.attributes('data-icono')).toBe('vencida')
        expect(vencida.get('svg').classes()).toContain('text-destructive')
        expect(vencida.get('time [aria-hidden="true"]').text()).toBe('1 nov')
        const hecha = celda(envoltorio, 1, 'Fecha de vencimiento').get(
          '[data-testid="vencimiento-corto"]',
        )
        expect(hecha.attributes('data-icono')).toBe('completada')
        expect(hecha.get('svg').attributes('aria-hidden')).toBe('true')
      })
    })
  })

  describe('avatares y etiquetas', () => {
    const CON_EQUIPO = { ...TAREAS[0], asignados: ['Ana', 'Luis Pérez'] }

    function celda(envoltorio: VueWrapper, columna: string) {
      const indice = envoltorio.findAll('thead th').findIndex((th) => th.text().trim() === columna)
      return envoltorio.findAll(FILAS_TAREA)[0]!.findAll('td')[indice]!
    }

    it('muestra cada persona como un círculo con sus iniciales y su nombre en el tooltip', async () => {
      const envoltorio = await montar([CON_EQUIPO])

      const avatares = celda(envoltorio, 'Asignado a').findAll('[data-testid="avatar-persona"]')
      expect(avatares.map((avatar) => avatar.get('[aria-hidden="true"]').text())).toEqual([
        'A',
        'LP',
      ])
      expect(avatares.map((avatar) => avatar.attributes('title'))).toEqual(['Ana', 'Luis Pérez'])
      expect(avatares[0]!.classes()).toContain('rounded-full')
      // El nombre completo sigue en el texto para los lectores de pantalla y las búsquedas.
      expect(avatares[0]!.get('.sr-only').text()).toBe('Ana')
    })

    it('el avatar sigue abriendo las tareas de la persona con el mismo nombre accesible', async () => {
      const envoltorio = await montar([CON_EQUIPO])

      const boton = celda(envoltorio, 'Asignado a').get(
        'button[aria-label="Ver tareas y subtareas de Ana"]',
      )
      expect(boton.find('[data-testid="avatar-persona"]').exists()).toBe(true)
      await boton.trigger('click')
      await flushPromises()

      const titulos = [...document.body.querySelectorAll('[role="dialog"] h2')].map((h) =>
        h.textContent?.trim(),
      )
      expect(titulos).toContain('Persona: Ana')
    })

    it('cada etiqueta tiene un color estable derivado de su nombre y sigue abriendo sus tareas', async () => {
      const envoltorio = await montar([TAREAS[0], { ...TAREAS[1], etiquetas: ['Backend'] }])

      const chip = (fila: number, nombre: string) =>
        envoltorio
          .findAll(FILAS_TAREA)
          [fila]!.get(`[data-testid="chip-tabla"][data-nombre="${nombre}"]`)
      const colorDe = (fila: number, nombre: string) =>
        chip(fila, nombre)
          .classes()
          .filter((clase) => /^(dark:)?(bg|text)-/.test(clase))
      expect(colorDe(0, 'Backend').length).toBeGreaterThan(0)
      // El mismo nombre, el mismo color en cualquier fila.
      expect(colorDe(1, 'Backend')).toEqual(colorDe(0, 'Backend'))
      expect(chip(0, 'Backend').text()).toBe('Backend')

      await chip(0, 'Urgente')
        .get('button[aria-label="Ver tareas con la etiqueta Urgente"]')
        .trigger('click')
      await flushPromises()
      const titulos = [...document.body.querySelectorAll('[role="dialog"] h2')].map((h) =>
        h.textContent?.trim(),
      )
      expect(titulos).toContain('Etiqueta: Urgente')
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
        completada: false,
        subtareas: [],
        grupo_estados: null,
        estado: null,
        workflow: null,
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
        completada: false,
        subtareas: [],
        grupo_estados: null,
        estado: null,
        workflow: null,
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
        completada: false,
        subtareas: [],
        grupo_estados: null,
        estado: null,
        workflow: null,
      },
    ]

    function nombresEnTabla(envoltorio: VueWrapper): string[] {
      return envoltorio.findAll(FILAS_TAREA).map((fila) => fila.findAll('td')[0]!.text())
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
        'Estado',
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

    it('ordena por tipo usando solo su texto, sin tener en cuenta el avance de las subtareas', async () => {
      const envoltorio = await montar([
        // Con el avance, "Oportunidad · 1/3" iría detrás de "Oportunidad"; empatan y
        // se conserva el orden de llegada.
        {
          ...TAREAS_ORDEN[0],
          tipo: 'oportunidad',
          oportunidad: OPORTUNIDAD,
          subtareas: SUBTAREAS,
        },
        TAREAS_ORDEN[1],
        { ...TAREAS_ORDEN[2], tipo: 'oportunidad', oportunidad: OPORTUNIDAD },
      ])

      await cabecera(envoltorio, 'Tipo').trigger('click')
      expect(nombresEnTabla(envoltorio)).toEqual(['beta', 'casa', 'Árbol'])
      await cabecera(envoltorio, 'Tipo').trigger('click')
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
      'Tipo',
      'Estado',
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
          '—',
        ],
        [
          'Leer artículo',
          '—',
          'Artículo sobre Vue',
          '—',
          '—',
          '01/12/2026 17:05:09',
          '—',
          '—',
          '—',
        ],
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

    it('exporta solo el texto del tipo, sin el avance de las subtareas', async () => {
      const envoltorio = await montar([OPORTUNIDAD_CON_SUBTAREAS, TAREAS[1]])

      await botonExportar(envoltorio, 'Exportar a Excel').trigger('click')

      const filas = vi.mocked(exportarTablaExcel).mock.calls[0]![2] as unknown[][]
      expect(filas.map((fila) => fila[7])).toEqual(['Oportunidad', '—'])
      expect(JSON.stringify(filas)).not.toContain('Contactar')
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
        completada: false,
        subtareas: [],
        grupo_estados: null,
        estado: null,
        workflow: null,
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
        completada: false,
        subtareas: [],
        grupo_estados: null,
        estado: null,
        workflow: null,
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
        completada: false,
        subtareas: [],
        grupo_estados: null,
        estado: null,
        workflow: null,
      },
    ]
    const TODAS = ['Preparar reunión', 'Revisar código', 'Comprar café']

    function nombresEnTabla(envoltorio: VueWrapper): string[] {
      return envoltorio.findAll(FILAS_TAREA).map((fila) => fila.findAll('td')[0]!.text())
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

    function botonFiltrar(envoltorio: VueWrapper) {
      const boton = envoltorio.findAll('button').find((b) => b.text() === 'Filtrar')
      if (!boton) throw new Error('No se encontró el botón "Filtrar"')
      return boton
    }

    // Monta la vista y despliega el panel de filtros, que empieza plegado.
    async function montarConFiltros(tareas: unknown[]): Promise<VueWrapper> {
      const envoltorio = await montar(tareas)
      await botonFiltrar(envoltorio).trigger('click')
      await flushPromises()
      return envoltorio
    }

    it('muestra una barra de una línea con Buscar, Persona, Filtrar, Columnas y exportar', async () => {
      const envoltorio = await montar(TAREAS_FILTRO)

      const barra = envoltorio.get('[data-testid="barra-tareas"]')
      const controles = [
        barra.get('#filtro-buscar'),
        barra.get('button[aria-label^="Filtrar por persona: "]'),
        botonFiltrar(envoltorio),
        barra.get('button[aria-label="Elegir columnas visibles"]'),
        barra.get('button[aria-label="Exportar a Excel"]'),
        barra.get('button[aria-label="Exportar a PDF"]'),
      ]
      // En el orden del documento.
      for (let i = 1; i < controles.length; i++) {
        const posicion = controles[i - 1]!.element.compareDocumentPosition(controles[i]!.element)
        expect(posicion & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
      }
      expect(barra.classes()).toContain('flex')
    })

    it('el panel de filtros empieza plegado y "Filtrar" lo despliega y lo pliega', async () => {
      const envoltorio = await montar(TAREAS_FILTRO)

      const boton = botonFiltrar(envoltorio)
      expect(boton.attributes('aria-expanded')).toBe('false')
      expect(envoltorio.find('#filtro-creacion-desde').exists()).toBe(false)
      // El buscador está en la barra, siempre visible.
      expect(envoltorio.find('#filtro-buscar').exists()).toBe(true)

      await boton.trigger('click')
      await flushPromises()
      expect(botonFiltrar(envoltorio).attributes('aria-expanded')).toBe('true')
      expect(envoltorio.find('#filtro-creacion-desde').exists()).toBe(true)
      for (const nombre of [
        'Filtrar por prioridad',
        'Filtrar por etiquetas',
        'Filtrar por asignado a',
        'Filtrar por tipo',
      ]) {
        expect(disparador(envoltorio, nombre).exists()).toBe(true)
      }
      expect(envoltorio.find('#filtro-estado-titulo').exists()).toBe(true)

      await botonFiltrar(envoltorio).trigger('click')
      await flushPromises()
      expect(envoltorio.find('#filtro-creacion-desde').exists()).toBe(false)
      expect(nombresEnTabla(envoltorio)).toEqual(TODAS)
    })

    it('"Persona" es un atajo del filtro "Asignado a"', async () => {
      const envoltorio = await montarConFiltros(TAREAS_FILTRO)

      expect(disparador(envoltorio, 'Filtrar por persona').text()).toBe('Todas las personas')
      await alternar(envoltorio, 'Filtrar por persona', 'Sin asignar')
      expect(nombresEnTabla(envoltorio)).toEqual(['Preparar reunión', 'Revisar código'])
      // Es el mismo filtro: el del panel refleja el cambio.
      expect(disparador(envoltorio, 'Filtrar por asignado a').text()).toBe('2 personas')
    })

    it('"Limpiar filtros" solo aparece en la barra con algún filtro activo', async () => {
      const envoltorio = await montar(TAREAS_FILTRO)
      const limpiar = () => envoltorio.findAll('button').find((b) => b.text() === 'Limpiar filtros')

      expect(limpiar()).toBeUndefined()
      await escribir(entrada(envoltorio, 'filtro-buscar'), 'café')
      expect(limpiar()).toBeDefined()
    })

    it('el botón "Filtros" indica cuántos filtros hay activos', async () => {
      const envoltorio = await montarConFiltros(TAREAS_FILTRO)
      const contador = () => envoltorio.find('[data-testid="filtros-activos"]')

      expect(contador().exists()).toBe(false)
      await escribir(entrada(envoltorio, 'filtro-buscar'), 'café')
      expect(contador().text()).toBe('1 activo')
      await escribir(entrada(envoltorio, 'filtro-creacion-desde'), '2026-03-11')
      await alternar(envoltorio, 'Filtrar por prioridad', 'Sin prioridad')
      expect(contador().text()).toBe('3 activos')

      const boton = envoltorio.findAll('button').find((b) => b.text() === 'Limpiar filtros')!
      await boton.trigger('click')
      await flushPromises()
      expect(contador().exists()).toBe(false)
    })

    it('agrupa las fechas por tipo con "Desde" y "Hasta" visibles', async () => {
      const envoltorio = await montarConFiltros(TAREAS_FILTRO)

      const grupos = envoltorio.findAll('fieldset').map((f) => f.get('legend').text())
      expect(grupos).toEqual(expect.arrayContaining(['Fecha de creación', 'Fecha de vencimiento']))
      const creacion = envoltorio
        .findAll('fieldset')
        .find((f) => f.get('legend').text() === 'Fecha de creación')!
      expect(creacion.find('#filtro-creacion-desde').exists()).toBe(true)
      expect(creacion.find('#filtro-creacion-hasta').exists()).toBe(true)
      // Texto visible corto; el nombre accesible completo lleva el grupo.
      expect(creacion.get('label[for="filtro-creacion-desde"] .sr-only').text().trim()).toBe(
        'Fecha de creación',
      )
    })

    it('todos los controles del panel tienen nombre accesible', async () => {
      const envoltorio = await montarConFiltros(TAREAS_FILTRO)

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
      const envoltorio = await montarConFiltros(TAREAS_FILTRO)

      await escribir(entrada(envoltorio, 'filtro-buscar'), 'angela')
      expect(nombresEnTabla(envoltorio)).toEqual(['Revisar código'])

      await escribir(entrada(envoltorio, 'filtro-buscar'), 'REUNION')
      expect(nombresEnTabla(envoltorio)).toEqual(['Preparar reunión'])
    })

    it('filtra por prioridad, incluida la opción "Sin prioridad"', async () => {
      const envoltorio = await montarConFiltros(TAREAS_FILTRO)

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
      const envoltorio = await montarConFiltros(TAREAS_FILTRO)

      await alternar(envoltorio, 'Filtrar por etiquetas', 'Urgente')
      expect(nombresEnTabla(envoltorio)).toEqual(TODAS)

      await alternar(envoltorio, 'Filtrar por etiquetas', 'Backend')
      expect(nombresEnTabla(envoltorio)).toEqual(['Comprar café'])

      await alternar(envoltorio, 'Filtrar por etiquetas', 'Sin etiquetas')
      expect(nombresEnTabla(envoltorio)).toEqual([])
    })

    it('filtra por asignado a, incluida la opción "Sin asignar"', async () => {
      const envoltorio = await montarConFiltros(TAREAS_FILTRO)

      await alternar(envoltorio, 'Filtrar por asignado a', 'Sin asignar')
      expect(nombresEnTabla(envoltorio)).toEqual(['Preparar reunión', 'Revisar código'])

      await alternar(envoltorio, 'Filtrar por asignado a', 'Ana')
      expect(nombresEnTabla(envoltorio)).toEqual(['Revisar código'])
    })

    it('filtra por fecha de creación con ambos extremos incluidos por día', async () => {
      const envoltorio = await montarConFiltros(TAREAS_FILTRO)

      await escribir(entrada(envoltorio, 'filtro-creacion-desde'), '2026-03-11')
      expect(nombresEnTabla(envoltorio)).toEqual(['Revisar código', 'Comprar café'])

      await escribir(entrada(envoltorio, 'filtro-creacion-hasta'), '2026-03-11')
      expect(nombresEnTabla(envoltorio)).toEqual(['Revisar código'])

      await escribir(entrada(envoltorio, 'filtro-creacion-desde'), '')
      expect(nombresEnTabla(envoltorio)).toEqual(['Preparar reunión', 'Revisar código'])
    })

    it('filtra por fecha de vencimiento con ambos extremos incluidos y excluye las tareas sin vencimiento', async () => {
      const envoltorio = await montarConFiltros(TAREAS_FILTRO)

      await escribir(entrada(envoltorio, 'filtro-vencimiento-desde'), '2026-03-16')
      expect(nombresEnTabla(envoltorio)).toEqual(['Comprar café'])

      await escribir(entrada(envoltorio, 'filtro-vencimiento-desde'), '')
      await escribir(entrada(envoltorio, 'filtro-vencimiento-hasta'), '2026-03-15')
      expect(nombresEnTabla(envoltorio)).toEqual(['Preparar reunión'])

      await escribir(entrada(envoltorio, 'filtro-vencimiento-hasta'), '')
      expect(nombresEnTabla(envoltorio)).toEqual(TODAS)
    })

    it('"Limpiar filtros" restablece todos los filtros', async () => {
      const envoltorio = await montarConFiltros(TAREAS_FILTRO)
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
      const envoltorio = await montarConFiltros(TAREAS_FILTRO)

      await escribir(entrada(envoltorio, 'filtro-buscar'), 'zzz')

      expect(envoltorio.text()).toContain('Ninguna tarea coincide con los filtros.')
      expect(envoltorio.text()).not.toContain('Todavía no hay tareas.')
      expect(envoltorio.find('table').exists()).toBe(false)
    })

    it('sin tareas muestra solo "Todavía no hay tareas."', async () => {
      const envoltorio = await montarConFiltros([])

      expect(envoltorio.text()).toContain('Todavía no hay tareas.')
      expect(envoltorio.text()).not.toContain('Ninguna tarea coincide con los filtros.')
    })

    it('ordena solo las filas filtradas', async () => {
      const envoltorio = await montarConFiltros(TAREAS_FILTRO)
      await alternar(envoltorio, 'Filtrar por prioridad', '1')

      const cabecera = envoltorio.findAll('th button').find((b) => b.text() === 'Nombre')!
      await cabecera.trigger('click')
      await cabecera.trigger('click')

      expect(nombresEnTabla(envoltorio)).toEqual(['Revisar código', 'Comprar café'])
    })

    it('exporta solo las filas filtradas', async () => {
      const envoltorio = await montarConFiltros(TAREAS_FILTRO)
      await escribir(entrada(envoltorio, 'filtro-buscar'), 'cafe')

      await disparador(envoltorio, 'Exportar a Excel').trigger('click')

      const filas = vi.mocked(exportarTablaExcel).mock.calls[0]![2] as unknown[][]
      expect(filas.map((fila) => fila[0])).toEqual(['Comprar café'])
    })

    it('al recargar los catálogos marca los nombres nuevos y conserva los desmarcados', async () => {
      const envoltorio = await montarConFiltros(TAREAS_FILTRO)
      await alternar(envoltorio, 'Filtrar por etiquetas', 'Urgente')
      await alternar(envoltorio, 'Filtrar por asignado a', 'Luis')
      vi.mocked(clienteApi.obtener).mockImplementation((ruta) => {
        if (ruta === '/etiquetas')
          return Promise.resolve([...ETIQUETAS, { id: 3, nombre: 'Nueva' }])
        if (ruta === '/personas') return Promise.resolve([...PERSONAS, { id: 3, nombre: 'Marta' }])
        if (ruta === '/grupos-estados' || ruta === '/workflows') return Promise.resolve([])
        if (String(ruta).endsWith('/comentarios')) return Promise.resolve([])
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
      const envoltorio = await montarConFiltros([
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

    describe('estado', () => {
      // "Revisar código" está completada; las otras dos, no.
      const CON_COMPLETADA = TAREAS_FILTRO.map((tarea) =>
        tarea.id === 2 ? { ...tarea, completada: true } : tarea,
      )

      // Con los grupos, la completada se muestra tras las pendientes.
      const TODAS_AGRUPADAS = ['Preparar reunión', 'Comprar café', 'Revisar código']

      function opcionEstado(envoltorio: VueWrapper, etiqueta: string) {
        const grupo = envoltorio.get('[role="radiogroup"][aria-labelledby="filtro-estado-titulo"]')
        const opcion = grupo
          .findAll('input[type="radio"]')
          .find(
            (radio) => envoltorio.get(`label[for="${radio.attributes('id')}"]`).text() === etiqueta,
          )
        if (!opcion) throw new Error(`No hay opción de estado «${etiqueta}»`)
        return opcion
      }

      it('por defecto muestra todas las tareas, completadas o no', async () => {
        const envoltorio = await montarConFiltros(CON_COMPLETADA)

        expect(envoltorio.get('#filtro-estado-titulo').text()).toBe('Estado')
        expect((opcionEstado(envoltorio, 'Todas').element as HTMLInputElement).checked).toBe(true)
        expect((opcionEstado(envoltorio, 'Completadas').element as HTMLInputElement).checked).toBe(
          false,
        )
        expect(
          (opcionEstado(envoltorio, 'No completadas').element as HTMLInputElement).checked,
        ).toBe(false)
        expect(nombresEnTabla(envoltorio)).toEqual(TODAS_AGRUPADAS)
      })

      it('"Completadas" muestra solo las tareas completadas', async () => {
        const envoltorio = await montarConFiltros(CON_COMPLETADA)

        await opcionEstado(envoltorio, 'Completadas').setValue(true)
        await flushPromises()

        expect(nombresEnTabla(envoltorio)).toEqual(['Revisar código'])
      })

      it('"No completadas" muestra solo las tareas sin completar', async () => {
        const envoltorio = await montarConFiltros(CON_COMPLETADA)

        await opcionEstado(envoltorio, 'No completadas').setValue(true)
        await flushPromises()

        expect(nombresEnTabla(envoltorio)).toEqual(['Preparar reunión', 'Comprar café'])
      })

      it('se combina con los demás filtros', async () => {
        const envoltorio = await montarConFiltros(CON_COMPLETADA)

        await opcionEstado(envoltorio, 'No completadas').setValue(true)
        await escribir(entrada(envoltorio, 'filtro-buscar'), 'café')

        expect(nombresEnTabla(envoltorio)).toEqual(['Comprar café'])
      })

      it('"Limpiar filtros" vuelve a "Todas"', async () => {
        const envoltorio = await montarConFiltros(CON_COMPLETADA)
        await opcionEstado(envoltorio, 'Completadas').setValue(true)
        await flushPromises()

        const boton = envoltorio.findAll('button').find((b) => b.text() === 'Limpiar filtros')!
        await boton.trigger('click')
        await flushPromises()

        expect((opcionEstado(envoltorio, 'Todas').element as HTMLInputElement).checked).toBe(true)
        expect(nombresEnTabla(envoltorio)).toEqual(TODAS_AGRUPADAS)
      })
    })
  })

  describe('columnas visibles', () => {
    const CLAVE = 'gestor-tareas:columnas-ocultas-tareas'

    beforeEach(() => localStorage.removeItem(CLAVE))
    afterEach(() => localStorage.removeItem(CLAVE))

    function botonColumnas(envoltorio: VueWrapper) {
      const boton = envoltorio.find('button[aria-label="Elegir columnas visibles"]')
      if (!boton.exists()) throw new Error('No se encontró el botón de columnas')
      return boton
    }

    // Casilla del desplegable (teletransportado al `body`) con esa etiqueta visible.
    function casillaColumna(texto: string): HTMLElement {
      const etiqueta = [
        ...document.body.querySelectorAll<HTMLLabelElement>('[data-slot="popover-content"] label'),
      ].find((label) => label.textContent?.trim() === texto)
      const elemento = etiqueta ? document.getElementById(etiqueta.htmlFor) : null
      if (!elemento) throw new Error(`No se encontró la casilla "${texto}"`)
      return elemento
    }

    function cabeceras(envoltorio: VueWrapper): string[] {
      return envoltorio
        .findAll('thead th')
        .map((th) => th.text().trim())
        .filter((texto) => texto !== '' && texto !== 'Acciones')
    }

    async function abrirColumnas(envoltorio: VueWrapper): Promise<void> {
      await botonColumnas(envoltorio).trigger('click')
      await flushPromises()
    }

    const TODAS_LAS_COLUMNAS = [
      'Nombre',
      'Prioridad',
      'Descripción',
      'Etiquetas',
      'Asignado a',
      'Fecha de creación',
      'Fecha de vencimiento',
      'Tipo',
      'Estado',
    ]

    it('por defecto muestra todas las columnas y las lista marcadas; "Nombre" no se puede ocultar', async () => {
      const envoltorio = await montar()

      expect(cabeceras(envoltorio)).toEqual(TODAS_LAS_COLUMNAS)
      await abrirColumnas(envoltorio)
      for (const columna of TODAS_LAS_COLUMNAS) {
        expect(casillaColumna(columna).getAttribute('data-state')).toBe('checked')
      }
      expect(casillaColumna('Nombre').hasAttribute('disabled')).toBe(true)
    })

    it('al desmarcar una columna se ocultan su cabecera y sus celdas, y al marcarla vuelve', async () => {
      const envoltorio = await montar()
      const celdasPorFila = filasTabla(envoltorio)[0]!.length

      await abrirColumnas(envoltorio)
      casillaColumna('Descripción').click()
      await flushPromises()

      expect(cabeceras(envoltorio)).toEqual(TODAS_LAS_COLUMNAS.filter((c) => c !== 'Descripción'))
      expect(filasTabla(envoltorio)[0]!.length).toBe(celdasPorFila - 1)
      expect(envoltorio.text()).not.toContain(TAREAS[0]!.descripcion)

      casillaColumna('Descripción').click()
      await flushPromises()
      expect(cabeceras(envoltorio)).toEqual(TODAS_LAS_COLUMNAS)
      expect(filasTabla(envoltorio)[0]!.length).toBe(celdasPorFila)
    })

    it('oculta también las columnas de chips (etiquetas y asignados)', async () => {
      const envoltorio = await montar()

      await abrirColumnas(envoltorio)
      casillaColumna('Etiquetas').click()
      casillaColumna('Asignado a').click()
      await flushPromises()

      expect(cabeceras(envoltorio)).toEqual(
        TODAS_LAS_COLUMNAS.filter((c) => c !== 'Etiquetas' && c !== 'Asignado a'),
      )
      expect(envoltorio.findAll('[data-testid="chip-tabla"]')).toHaveLength(0)
    })

    it('"Mostrar todas" vuelve a mostrar todas las columnas', async () => {
      const envoltorio = await montar()
      await abrirColumnas(envoltorio)
      casillaColumna('Prioridad').click()
      casillaColumna('Tipo').click()
      await flushPromises()

      const mostrarTodas = [
        ...document.body.querySelectorAll<HTMLButtonElement>(
          '[data-slot="popover-content"] button',
        ),
      ].find((b) => b.textContent?.trim() === 'Mostrar todas')!
      mostrarTodas.click()
      await flushPromises()

      expect(cabeceras(envoltorio)).toEqual(TODAS_LAS_COLUMNAS)
    })

    it('recuerda las columnas ocultas al volver a la vista', async () => {
      const primera = await montar()
      await abrirColumnas(primera)
      casillaColumna('Descripción').click()
      await flushPromises()
      expect(JSON.parse(localStorage.getItem(CLAVE)!)).toEqual(['descripcion'])
      primera.unmount()
      document.body.innerHTML = ''

      const segunda = await montar()
      expect(cabeceras(segunda)).toEqual(TODAS_LAS_COLUMNAS.filter((c) => c !== 'Descripción'))
    })

    it('ignora un valor guardado no válido y muestra todas las columnas', async () => {
      localStorage.setItem(CLAVE, '{no es json')
      const envoltorio = await montar()

      expect(cabeceras(envoltorio)).toEqual(TODAS_LAS_COLUMNAS)
    })

    it('exporta solo las columnas visibles, en el mismo orden', async () => {
      const envoltorio = await montar()
      await abrirColumnas(envoltorio)
      casillaColumna('Descripción').click()
      casillaColumna('Tipo').click()
      await flushPromises()
      await botonColumnas(envoltorio).trigger('click')
      await flushPromises()

      await envoltorio.get('button[aria-label="Exportar a Excel"]').trigger('click')
      await flushPromises()

      const [, columnas, filas] = vi.mocked(exportarTablaExcel).mock.calls[0]!
      const esperadas = TODAS_LAS_COLUMNAS.filter((c) => c !== 'Descripción' && c !== 'Tipo')
      expect(columnas).toEqual(esperadas)
      for (const fila of filas as unknown[][]) expect(fila).toHaveLength(esperadas.length)
    })
  })

  describe('grupos de estados', () => {
    const CLAVE_VISTA = 'gestor-tareas:vista-tareas'
    const CLAVE_GRUPO = 'gestor-tareas:grupo-tablero'

    const DESARROLLO = {
      id: 1,
      nombre: 'Desarrollo',
      tareas: 2,
      estados: [
        { id: 10, nombre: 'Pendiente', posicion: 1, tareas: 1 },
        { id: 11, nombre: 'En curso', posicion: 2, tareas: 1 },
        { id: 12, nombre: 'Hecho', posicion: 3, tareas: 0 },
      ],
    }
    const SOPORTE = {
      id: 2,
      nombre: 'Soporte',
      tareas: 0,
      estados: [{ id: 20, nombre: 'Abierta', posicion: 1, tareas: 0 }],
    }
    const SIN_ESTADOS = { id: 3, nombre: 'Vacío', tareas: 0, estados: [] }
    const GRUPOS = [DESARROLLO, SOPORTE, SIN_ESTADOS]

    const EN_DESARROLLO = { id: 1, nombre: 'Desarrollo' }
    const INFORME = {
      ...TAREAS[0],
      grupo_estados: EN_DESARROLLO,
      estado: { id: 10, nombre: 'Pendiente' },
    }
    const ARTICULO = {
      ...TAREAS[1],
      grupo_estados: EN_DESARROLLO,
      estado: { id: 11, nombre: 'En curso' },
    }
    const SUELTA = { ...TAREAS[1], id: 3, nombre: 'Sin grupo' }
    const TAREAS_GRUPO = [INFORME, ARTICULO, SUELTA]

    beforeEach(() => {
      localStorage.removeItem(CLAVE_VISTA)
      localStorage.removeItem(CLAVE_GRUPO)
    })
    afterEach(() => {
      localStorage.removeItem(CLAVE_VISTA)
      localStorage.removeItem(CLAVE_GRUPO)
    })

    function botonVista(etiqueta: 'Ver como lista' | 'Ver como tablero'): HTMLButtonElement {
      const boton = document.body.querySelector<HTMLButtonElement>(
        `button[aria-label="${etiqueta}"]`,
      )
      if (!boton) throw new Error(`No se encontró el botón "${etiqueta}"`)
      return boton
    }

    async function montarTablero(tareas: unknown[] = TAREAS_GRUPO, grupos: unknown[] = GRUPOS) {
      const envoltorio = await montar(tareas, grupos)
      botonVista('Ver como tablero').click()
      await flushPromises()
      return envoltorio
    }

    function columna(nombre: string): HTMLElement {
      const elemento = document.body.querySelector<HTMLElement>(
        `section[aria-label="Estado ${nombre}"]`,
      )
      if (!elemento) throw new Error(`No se encontró la columna "${nombre}"`)
      return elemento
    }

    function columnas(): string[] {
      return [...document.body.querySelectorAll('section[aria-label^="Estado "]')].map((c) =>
        c.getAttribute('aria-label')!,
      )
    }

    function tarjetas(nombre: string): string[] {
      return [...columna(nombre).querySelectorAll('[data-tarjeta] [data-nombre-tarjeta]')].map(
        (t) => t.textContent!.trim(),
      )
    }

    function contador(nombre: string): string {
      return columna(nombre).querySelector('[data-contador]')!.textContent!.trim()
    }

    function botonEn(raiz: ParentNode, etiqueta: string): HTMLButtonElement {
      const boton = raiz.querySelector<HTMLButtonElement>(`button[aria-label="${etiqueta}"]`)
      if (!boton) throw new Error(`No se encontró el botón "${etiqueta}"`)
      return boton
    }

    function crearDataTransfer() {
      const datos: Record<string, string> = {}
      return {
        effectAllowed: 'none',
        dropEffect: 'none',
        setData: (tipo: string, valor: string) => {
          datos[tipo] = valor
        },
        getData: (tipo: string) => datos[tipo] ?? '',
      }
    }

    function lanzarEventoArrastre(elemento: Element, tipo: string, dataTransfer: object): void {
      const evento = new Event(tipo, { bubbles: true, cancelable: true })
      Object.defineProperty(evento, 'dataTransfer', { value: dataTransfer })
      elemento.dispatchEvent(evento)
    }

    async function elegirGrupo(panel: HTMLElement, valor: string): Promise<void> {
      const selector = campo<HTMLSelectElement>(panel, '#tarea-grupo-estados')
      selector.value = valor
      selector.dispatchEvent(new Event('change'))
      await flushPromises()
    }

    describe('formulario', () => {
      it('ofrece "Grupo de estados" con "Sin grupo" y los grupos; los grupos sin estados no se pueden elegir', async () => {
        const envoltorio = await montar([], GRUPOS)
        const panel = await abrirPanel(envoltorio)

        expect(campo(panel, 'label[for="tarea-grupo-estados"]').textContent?.trim()).toBe(
          'Grupo de estados',
        )
        const opciones = [...campo<HTMLSelectElement>(panel, '#tarea-grupo-estados').options]
        expect(opciones.map((o) => o.textContent?.trim())).toEqual([
          'Sin grupo',
          'Desarrollo',
          'Soporte',
          'Vacío (sin estados)',
        ])
        expect(opciones.map((o) => o.disabled)).toEqual([false, false, false, true])
        expect(campo<HTMLSelectElement>(panel, '#tarea-grupo-estados').value).toBe('')
      })

      it('al crear envía el grupo elegido en grupo_estados_id', async () => {
        const envoltorio = await montar([], GRUPOS)
        vi.mocked(clienteApi.crear).mockResolvedValue({ ...INFORME, id: 9, nombre: 'Nueva' })
        const panel = await abrirPanel(envoltorio)

        await escribir(campo(panel, 'input[placeholder="Nombre"]'), 'Nueva')
        await escribir(campo(panel, 'textarea[placeholder="Descripción"]'), 'Detalle')
        await elegirGrupo(panel, '1')
        await enviar(panel)

        expect(clienteApi.crear).toHaveBeenCalledWith(
          '/tareas',
          expect.objectContaining({ grupo_estados_id: 1 }),
        )
        expect(clienteApi.parchear).not.toHaveBeenCalled()
      })

      it('al editar carga el grupo de la tarea y "Sin grupo" envía null', async () => {
        const envoltorio = await montar(TAREAS_GRUPO, GRUPOS)
        vi.mocked(clienteApi.actualizar).mockResolvedValue({
          ...INFORME,
          grupo_estados: null,
          estado: null,
          workflow: null,
        })
        const panel = await abrirPanelEdicion(envoltorio, 'Escribir informe')

        expect(campo<HTMLSelectElement>(panel, '#tarea-grupo-estados').value).toBe('1')
        await elegirGrupo(panel, '')
        await enviar(panel)

        expect(clienteApi.actualizar).toHaveBeenCalledWith(
          '/tareas/1',
          expect.objectContaining({ grupo_estados_id: null }),
        )
      })

      it('al editar sin cambiar el grupo lo vuelve a enviar', async () => {
        const envoltorio = await montar(TAREAS_GRUPO, GRUPOS)
        vi.mocked(clienteApi.actualizar).mockResolvedValue(INFORME)
        const panel = await abrirPanelEdicion(envoltorio, 'Escribir informe')

        await enviar(panel)

        expect(clienteApi.actualizar).toHaveBeenCalledWith(
          '/tareas/1',
          expect.objectContaining({ grupo_estados_id: 1 }),
        )
      })
    })

    describe('Lista / Tablero', () => {
      it('en una tarjeta se pulsan las personas y las etiquetas para ver sus tareas', async () => {
        await montarTablero()
        const tarjeta = columna('Pendiente').querySelector<HTMLElement>('[data-tarjeta]')!
        expect(
          tarjeta.querySelector('ul[aria-label="Asignados"] [data-testid="avatar-persona"]')
            ?.textContent,
        ).toContain('Ana')

        tarjeta
          .querySelector<HTMLButtonElement>('button[aria-label="Ver tareas y subtareas de Ana"]')!
          .click()
        await flushPromises()
        const modal = [...document.body.querySelectorAll('[role="dialog"]')].find(
          (d) => d.querySelector('h2')?.textContent?.trim() === 'Persona: Ana',
        )
        expect(modal?.querySelector('ul[aria-label="Tareas"]')?.textContent).toContain(
          'Escribir informe',
        )
        expect(
          tarjeta.querySelector('button[aria-label="Ver tareas con la etiqueta Backend"]'),
        ).not.toBeNull()
      })

      it('muestra la lista por defecto con "Ver como lista" pulsado', async () => {
        await montar(TAREAS_GRUPO, GRUPOS)

        expect(botonVista('Ver como lista').getAttribute('aria-pressed')).toBe('true')
        expect(botonVista('Ver como tablero').getAttribute('aria-pressed')).toBe('false')
        expect(botonVista('Ver como lista').getAttribute('title')).toBe('Ver como lista')
        expect(botonVista('Ver como tablero').getAttribute('title')).toBe('Ver como tablero')
        expect(document.body.querySelector('table')).not.toBeNull()
        expect(columnas()).toEqual([])
      })

      it('"Ver como tablero" cambia al tablero, oculta la tabla y recuerda la elección', async () => {
        const envoltorio = await montarTablero()

        expect(botonVista('Ver como tablero').getAttribute('aria-pressed')).toBe('true')
        expect(botonVista('Ver como lista').getAttribute('aria-pressed')).toBe('false')
        expect(document.body.querySelector('table')).toBeNull()
        expect(columnas()).toEqual(['Estado Pendiente', 'Estado En curso', 'Estado Hecho'])
        expect(localStorage.getItem(CLAVE_VISTA)).toBe('tablero')

        envoltorio.unmount()
        contenedor = null
        document.body.innerHTML = ''
        await montar(TAREAS_GRUPO, GRUPOS)
        expect(botonVista('Ver como tablero').getAttribute('aria-pressed')).toBe('true')
        expect(columnas()).toHaveLength(3)

        botonVista('Ver como lista').click()
        await flushPromises()
        expect(document.body.querySelector('table')).not.toBeNull()
        expect(localStorage.getItem(CLAVE_VISTA)).toBe('lista')
      })

      it('con una preferencia no válida muestra la lista', async () => {
        localStorage.setItem(CLAVE_VISTA, 'mosaico')
        await montar(TAREAS_GRUPO, GRUPOS)

        expect(botonVista('Ver como lista').getAttribute('aria-pressed')).toBe('true')
      })
    })

    describe('tablero', () => {
      it('muestra una columna por estado, en orden, con su contador y las tareas del grupo', async () => {
        await montarTablero()

        expect(tarjetas('Pendiente')).toEqual(['Escribir informe'])
        expect(tarjetas('En curso')).toEqual(['Leer artículo'])
        expect(tarjetas('Hecho')).toEqual([])
        expect([contador('Pendiente'), contador('En curso'), contador('Hecho')]).toEqual([
          '1',
          '1',
          '0',
        ])
        expect(columna('Pendiente').querySelector('ul')?.getAttribute('aria-label')).toBe(
          'Tareas en Pendiente',
        )
        // La tarea sin grupo no aparece en el tablero.
        expect(document.body.textContent).not.toContain('Sin grupo')
      })

      it('cada tarjeta muestra asignados, vencimiento y etiquetas', async () => {
        await montarTablero()

        const tarjeta = columna('Pendiente').querySelector('[data-tarjeta]')!
        expect(tarjeta.textContent).toContain('Ana')
        expect(tarjeta.textContent).toContain('20/11/2026 18:00:00')
        expect(tarjeta.textContent).toContain('Vence en')
        const chips = [...tarjeta.querySelectorAll('ul[aria-label="Etiquetas"] li')].map((c) =>
          c.textContent?.trim(),
        )
        expect(chips).toEqual(['Backend', 'Urgente'])
      })

      it('"Grupo del tablero" empieza en el primer grupo, cambia de grupo y lo recuerda', async () => {
        await montarTablero()

        const selector = document.body.querySelector<HTMLSelectElement>('#tablero-grupo')!
        expect(document.body.querySelector('label[for="tablero-grupo"]')?.textContent?.trim()).toBe(
          'Grupo del tablero',
        )
        expect(selector.value).toBe('1')
        selector.value = '2'
        selector.dispatchEvent(new Event('change'))
        await flushPromises()

        expect(columnas()).toEqual(['Estado Abierta'])
        expect(document.body.textContent).toContain('No hay tareas en este grupo.')
        expect(localStorage.getItem(CLAVE_GRUPO)).toBe('2')
      })

      it('recuerda el grupo elegido al volver y, si ya no existe, usa el primero', async () => {
        localStorage.setItem(CLAVE_VISTA, 'tablero')
        localStorage.setItem(CLAVE_GRUPO, '2')
        await montar(TAREAS_GRUPO, GRUPOS)
        expect(columnas()).toEqual(['Estado Abierta'])

        contenedor?.unmount()
        contenedor = null
        document.body.innerHTML = ''
        localStorage.setItem(CLAVE_GRUPO, '99')
        await montar(TAREAS_GRUPO, GRUPOS)
        expect(columnas()).toEqual(['Estado Pendiente', 'Estado En curso', 'Estado Hecho'])
      })

      it('un grupo sin estados lo indica', async () => {
        localStorage.setItem(CLAVE_GRUPO, '3')
        await montarTablero()

        expect(columnas()).toEqual([])
        expect(document.body.textContent).toContain('Este grupo no tiene estados.')
      })

      it('sin grupos invita a crear uno en Ajustes', async () => {
        await montarTablero(TAREAS_GRUPO, [])

        const enlace = document.body.querySelector('a[href="/ajustes/grupos-estados"]')
        expect(enlace?.textContent).toContain('Crea un grupo de estados en Ajustes')
        expect(document.body.querySelector('#tablero-grupo')).toBeNull()
      })

      it('pulsar la tarjeta abre el detalle de la tarea', async () => {
        await montarTablero()

        columna('Pendiente').querySelector<HTMLButtonElement>('[data-nombre-tarjeta]')!.click()
        await flushPromises()

        expect(panelActual().querySelector('h2')?.textContent?.trim()).toBe('Escribir informe')
      })

      it('los filtros y la búsqueda se aplican al tablero', async () => {
        await montarTablero()

        await escribir(campo<HTMLInputElement>(document.body, '#filtro-buscar'), 'informe')

        expect(tarjetas('Pendiente')).toEqual(['Escribir informe'])
        expect(tarjetas('En curso')).toEqual([])
        expect(contador('En curso')).toBe('0')
      })

      describe('aspecto kanban', () => {
        const CON_SUBTAREAS = {
          ...INFORME,
          subtareas: [{ ...SUBTAREAS[0]!, asignado: 'Luis' }, SUBTAREAS[1]!, SUBTAREAS[2]!],
        }
        const NUEVA_SUBTAREA = {
          id: 13,
          nombre: 'Revisar',
          asignado: null,
          prioridad: null,
          resuelta: false,
          comentarios: 0,
        }

        function cabecera(nombre: string): HTMLElement {
          return columna(nombre).querySelector<HTMLElement>('h3')!
        }

        function tarjeta(nombre: string): HTMLElement {
          return columna(nombre).querySelector<HTMLElement>('[data-tarjeta]')!
        }

        async function desplegarSubtareas(): Promise<HTMLButtonElement> {
          const boton = botonEn(columna('Pendiente'), '3 subtareas de Escribir informe')
          boton.click()
          await flushPromises()
          return boton
        }

        function nombresSubtareas(): string[] {
          const lista = document.body.querySelector(
            'ul[aria-label="Subtareas de Escribir informe"]',
          )
          return [...(lista?.querySelectorAll('[data-nombre-subtarea]') ?? [])].map((s) =>
            s.firstChild!.textContent!.trim(),
          )
        }

        it('cada columna tiene una cabecera de color con el nombre del estado y su contador', async () => {
          await montarTablero()

          expect(cabecera('Pendiente').className).toContain('bg-gray-600')
          expect(cabecera('En curso').className).toContain('bg-blue-700')
          expect(cabecera('Hecho').className).toContain('bg-emerald-700')
          for (const nombre of ['Pendiente', 'En curso', 'Hecho']) {
            expect(cabecera(nombre).className).toContain('text-white')
            expect(cabecera(nombre).textContent).toContain(nombre)
          }
          expect(cabecera('Pendiente').querySelector('[data-contador]')?.textContent?.trim()).toBe(
            '1',
          )
          expect(cabecera('Hecho').textContent).toContain('(0 tareas)')
        })

        it('la tarjeta muestra avatares, vencimiento corto y etiquetas de color', async () => {
          await montarTablero()

          const persona = botonEn(tarjeta('Pendiente'), 'Ver tareas y subtareas de Ana')
          expect(persona.querySelector('[data-testid="avatar-persona"]')).not.toBeNull()
          expect(
            tarjeta('Pendiente').querySelector('[data-testid="vencimiento-corto"]'),
          ).not.toBeNull()
          const etiqueta = [
            ...tarjeta('Pendiente').querySelectorAll('ul[aria-label="Etiquetas"] li'),
          ]
          expect(etiqueta[0]?.className).toContain(colorEtiqueta('Backend'))
          expect(etiqueta[1]?.className).toContain(colorEtiqueta('Urgente'))
        })

        it('el botón de comentarios abre el detalle de la tarea', async () => {
          await montarTablero()

          botonEn(tarjeta('Pendiente'), 'Comentarios de Escribir informe').click()
          await flushPromises()

          expect(panelActual().querySelector('h2')?.textContent?.trim()).toBe('Escribir informe')
        })

        it('el botón de subtareas muestra cuántas tiene la tarea', async () => {
          await montarTablero([CON_SUBTAREAS, ARTICULO])

          // El número visible forma parte del nombre accesible (WCAG 2.5.3).
          const boton = botonEn(tarjeta('Pendiente'), '3 subtareas de Escribir informe')
          expect(boton.textContent?.trim()).toBe('3')
          expect(boton.getAttribute('aria-expanded')).toBe('false')
          expect(
            botonEn(tarjeta('En curso'), '0 subtareas de Leer artículo').textContent?.trim(),
          ).toBe('0')
        })

        it('el botón de subtareas las despliega bajo la tarjeta y las vuelve a plegar', async () => {
          await montarTablero([CON_SUBTAREAS, ARTICULO])

          const boton = await desplegarSubtareas()
          expect(boton.getAttribute('aria-expanded')).toBe('true')
          const panel = document.getElementById(boton.getAttribute('aria-controls')!)
          expect(panel).not.toBeNull()
          expect(tarjeta('Pendiente').contains(panel)).toBe(false)
          expect(columna('Pendiente').contains(panel)).toBe(true)
          expect(nombresSubtareas()).toEqual(['Contactar', 'Enviar propuesta', 'Firmar contrato'])
          const resuelta = panel!.querySelector<HTMLElement>('[data-nombre-subtarea]')!
          expect(resuelta.className).toContain('line-through')
          expect(resuelta.textContent).toContain('(resuelta)')
          expect(
            panel!.querySelector('button[aria-label="Ver tareas y subtareas de Luis"]'),
          ).not.toBeNull()
          // Las subtareas no son tarjetas de tarea.
          expect(tarjetas('Pendiente')).toEqual(['Escribir informe'])

          boton.click()
          await flushPromises()
          expect(boton.getAttribute('aria-expanded')).toBe('false')
          expect(nombresSubtareas()).toEqual([])
        })

        it('pulsar una subtarea abre el detalle de su tarea', async () => {
          await montarTablero([CON_SUBTAREAS, ARTICULO])
          await desplegarSubtareas()

          document.body.querySelector<HTMLButtonElement>('[data-nombre-subtarea]')!.click()
          await flushPromises()

          expect(panelActual().querySelector('h2')?.textContent?.trim()).toBe('Escribir informe')
        })

        it('"+ Agregar subtarea" crea una subtarea solo con su nombre', async () => {
          await montarTablero([CON_SUBTAREAS, ARTICULO])
          vi.mocked(clienteApi.crear).mockResolvedValue({
            ...CON_SUBTAREAS,
            subtareas: [...CON_SUBTAREAS.subtareas, NUEVA_SUBTAREA],
          })
          const boton = await desplegarSubtareas()

          const agregar = botonEn(columna('Pendiente'), 'Agregar subtarea a Escribir informe')
          expect(agregar.textContent?.trim()).toBe('Agregar subtarea')
          agregar.click()
          await flushPromises()
          const entrada = campo<HTMLInputElement>(
            columna('Pendiente'),
            'input[name="nombre-subtarea"]',
          )
          expect(document.activeElement).toBe(entrada)
          expect(
            document.body.querySelector(`label[for="${entrada.id}"]`)?.textContent?.trim(),
          ).toBe('Nombre de la subtarea')
          await escribir(entrada, '  Revisar  ')
          botonEn(columna('Pendiente'), 'Guardar subtarea').click()
          await flushPromises()

          expect(clienteApi.crear).toHaveBeenCalledWith('/tareas/1/subtareas', {
            nombre: 'Revisar',
          })
          expect(nombresSubtareas()).toEqual([
            'Contactar',
            'Enviar propuesta',
            'Firmar contrato',
            'Revisar',
          ])
          expect(boton.textContent?.trim()).toBe('4')
          // Se queda abierto y vacío para añadir otra.
          expect(entrada.value).toBe('')
          expect(document.activeElement).toBe(entrada)
        })

        it('"+ Agregar subtarea" valida el nombre sin llamar a la API y Cancelar lo cierra', async () => {
          await montarTablero([CON_SUBTAREAS, ARTICULO])
          await desplegarSubtareas()
          botonEn(columna('Pendiente'), 'Agregar subtarea a Escribir informe').click()
          await flushPromises()
          const entrada = campo<HTMLInputElement>(
            columna('Pendiente'),
            'input[name="nombre-subtarea"]',
          )

          await escribir(entrada, '   ')
          botonEn(columna('Pendiente'), 'Guardar subtarea').click()
          await flushPromises()
          expect(columna('Pendiente').querySelector('[role="alert"]')?.textContent).toContain(
            'El nombre de la subtarea es obligatorio.',
          )
          await escribir(entrada, 'x'.repeat(201))
          botonEn(columna('Pendiente'), 'Guardar subtarea').click()
          await flushPromises()
          expect(columna('Pendiente').querySelector('[role="alert"]')?.textContent).toContain(
            'El nombre de la subtarea no puede superar 200 caracteres.',
          )
          expect(clienteApi.crear).not.toHaveBeenCalled()

          botonEn(columna('Pendiente'), 'Cancelar subtarea').click()
          await flushPromises()
          expect(columna('Pendiente').querySelector('input[name="nombre-subtarea"]')).toBeNull()
          expect(document.activeElement?.getAttribute('aria-label')).toBe(
            'Agregar subtarea a Escribir informe',
          )
        })

        it('la barra de distribución refleja las tareas del tablero por estado', async () => {
          await montarTablero()

          const barra = document.body.querySelector<HTMLElement>('[data-testid="barra-estados"]')!
          expect(barra.getAttribute('role')).toBe('img')
          expect(barra.getAttribute('aria-label')).toBe(
            'Distribución de estados en Desarrollo: Pendiente, 1 tarea; En curso, 1 tarea',
          )
          const segmentos = [...barra.querySelectorAll<HTMLElement>('[data-estado]')]
          expect(segmentos.map((s) => s.dataset.estado)).toEqual(['Pendiente', 'En curso'])
          expect(segmentos.map((s) => s.style.width)).toEqual(['50%', '50%'])
          expect(segmentos[0]!.className).toContain('bg-gray-600')
          expect(segmentos[1]!.className).toContain('bg-blue-700')

          await escribir(campo<HTMLInputElement>(document.body, '#filtro-buscar'), 'informe')
          expect(barra.getAttribute('aria-label')).toBe(
            'Distribución de estados en Desarrollo: Pendiente, 1 tarea',
          )
          await escribir(campo<HTMLInputElement>(document.body, '#filtro-buscar'), 'nada')
          expect(barra.getAttribute('aria-label')).toBe(
            'Distribución de estados en Desarrollo: sin tareas',
          )
        })
      })

      describe('mover tareas', () => {
        const MOVIDA = { ...INFORME, estado: { id: 12, nombre: 'Hecho' } }

        it('"Mover a…" ofrece los otros estados y mueve la tarjeta con PATCH, sin perder el foco', async () => {
          await montarTablero()
          vi.mocked(clienteApi.parchear).mockResolvedValue(structuredClone(MOVIDA))

          const mover = botonEn(columna('Pendiente'), 'Mover a… (Escribir informe)')
          expect(mover.textContent?.trim()).toBe('Mover a…')
          mover.focus()
          mover.click()
          await flushPromises()
          const menu = document.body.querySelector<HTMLElement>('[data-menu-mover]')!
          const opciones = [...menu.querySelectorAll('button')].map((b) => b.textContent?.trim())
          expect(opciones).toEqual(['En curso', 'Hecho'])
          ;[...menu.querySelectorAll('button')]
            .find((b) => b.textContent?.trim() === 'Hecho')!
            .click()
          await flushPromises()

          expect(clienteApi.parchear).toHaveBeenCalledWith('/tareas/1/estado', { estado_id: 12 })
          expect(tarjetas('Pendiente')).toEqual([])
          expect(tarjetas('Hecho')).toEqual(['Escribir informe'])
          expect(contador('Hecho')).toBe('1')
          expect(document.activeElement?.getAttribute('aria-label')).toBe(
            'Mover a… (Escribir informe)',
          )
          expect(columna('Hecho').contains(document.activeElement)).toBe(true)
          expect(document.body.querySelector('[data-anuncio-tablero]')?.textContent).toBe(
            'Escribir informe movida a Hecho',
          )
        })

        it('arrastrar una tarjeta a otra columna la mueve con PATCH', async () => {
          await montarTablero()
          vi.mocked(clienteApi.parchear).mockResolvedValue(structuredClone(MOVIDA))
          const tarjeta = columna('Pendiente').querySelector('[data-tarjeta]')!
          expect(tarjeta.getAttribute('draggable')).toBe('true')
          const dataTransfer = crearDataTransfer()

          lanzarEventoArrastre(tarjeta, 'dragstart', dataTransfer)
          lanzarEventoArrastre(columna('Hecho'), 'dragover', dataTransfer)
          await flushPromises()
          expect(columna('Hecho').getAttribute('data-destino')).toBe('true')
          lanzarEventoArrastre(columna('Hecho'), 'drop', dataTransfer)
          lanzarEventoArrastre(tarjeta, 'dragend', dataTransfer)
          await flushPromises()

          expect(clienteApi.parchear).toHaveBeenCalledWith('/tareas/1/estado', { estado_id: 12 })
          expect(tarjetas('Hecho')).toEqual(['Escribir informe'])
          expect(document.body.querySelector('[data-destino="true"]')).toBeNull()
        })

        it('soltar en la misma columna no llama a la API', async () => {
          await montarTablero()
          const tarjeta = columna('Pendiente').querySelector('[data-tarjeta]')!
          const dataTransfer = crearDataTransfer()

          lanzarEventoArrastre(tarjeta, 'dragstart', dataTransfer)
          lanzarEventoArrastre(columna('Pendiente'), 'dragover', dataTransfer)
          lanzarEventoArrastre(columna('Pendiente'), 'drop', dataTransfer)
          await flushPromises()

          expect(clienteApi.parchear).not.toHaveBeenCalled()
        })

        it('si la API falla, la tarjeta se queda donde estaba y se muestra el error', async () => {
          await montarTablero()
          vi.mocked(clienteApi.parchear).mockRejectedValue(new Error('El estado no es del grupo'))

          botonEn(columna('Pendiente'), 'Mover a… (Escribir informe)').click()
          await flushPromises()
          const menu = document.body.querySelector<HTMLElement>('[data-menu-mover]')!
          ;[...menu.querySelectorAll('button')]
            .find((b) => b.textContent?.trim() === 'Hecho')!
            .click()
          await flushPromises()

          expect(tarjetas('Pendiente')).toEqual(['Escribir informe'])
          expect(document.body.querySelector('[role="alert"]')?.textContent).toContain(
            'El estado no es del grupo',
          )
        })
      })

      describe('"Añadir tarea" en una columna', () => {
        it('abre el alta con el grupo del tablero y, en la primera columna, no recoloca la tarea', async () => {
          const envoltorio = await montarTablero()
          vi.mocked(clienteApi.crear).mockResolvedValue({ ...INFORME, id: 9, nombre: 'Nueva' })

          botonEn(columna('Pendiente'), 'Añadir tarea en Pendiente').click()
          await flushPromises()
          const panel = panelActual()
          expect(panel.textContent).toContain('Crear tarea')
          expect(campo<HTMLSelectElement>(panel, '#tarea-grupo-estados').value).toBe('1')
          await escribir(campo(panel, 'input[placeholder="Nombre"]'), 'Nueva')
          await escribir(campo(panel, 'textarea[placeholder="Descripción"]'), 'Detalle')
          await enviar(panel)

          expect(clienteApi.crear).toHaveBeenCalledWith(
            '/tareas',
            expect.objectContaining({ grupo_estados_id: 1 }),
          )
          expect(clienteApi.parchear).not.toHaveBeenCalled()
          expect(tarjetas('Pendiente')).toEqual(['Escribir informe', 'Nueva'])
          expect(envoltorio.exists()).toBe(true)
        })

        it('en otra columna, tras crearla, la coloca en ese estado con PATCH', async () => {
          await montarTablero()
          const creada = { ...INFORME, id: 9, nombre: 'Nueva' }
          vi.mocked(clienteApi.crear).mockResolvedValue(creada)
          vi.mocked(clienteApi.parchear).mockResolvedValue({
            ...creada,
            estado: { id: 11, nombre: 'En curso' },
          })

          botonEn(columna('En curso'), 'Añadir tarea en En curso').click()
          await flushPromises()
          const panel = panelActual()
          await escribir(campo(panel, 'input[placeholder="Nombre"]'), 'Nueva')
          await escribir(campo(panel, 'textarea[placeholder="Descripción"]'), 'Detalle')
          await enviar(panel)

          expect(clienteApi.parchear).toHaveBeenCalledWith('/tareas/9/estado', { estado_id: 11 })
          expect(tarjetas('En curso')).toEqual(['Leer artículo', 'Nueva'])
        })

        it('si se cambia el grupo en el formulario, no la recoloca', async () => {
          await montarTablero()
          vi.mocked(clienteApi.crear).mockResolvedValue({
            ...INFORME,
            id: 9,
            nombre: 'Nueva',
            grupo_estados: { id: 2, nombre: 'Soporte' },
            estado: { id: 20, nombre: 'Abierta' },
          })

          botonEn(columna('En curso'), 'Añadir tarea en En curso').click()
          await flushPromises()
          const panel = panelActual()
          await escribir(campo(panel, 'input[placeholder="Nombre"]'), 'Nueva')
          await escribir(campo(panel, 'textarea[placeholder="Descripción"]'), 'Detalle')
          await elegirGrupo(panel, '2')
          await enviar(panel)

          expect(clienteApi.parchear).not.toHaveBeenCalled()
        })
      })
    })
  })

  describe('workflow', () => {
    const OPORTUNIDADES = {
      id: 1,
      nombre: 'Workflow Oportunidades',
      pasos: [{ id: 10, numero: 1, nombre: 'Contacto', comentarios: 0 }],
    }
    const ALTAS = { id: 2, nombre: 'Altas', pasos: [] }
    const WORKFLOWS = [OPORTUNIDADES, ALTAS]

    async function elegirWorkflow(panel: HTMLElement, valor: string): Promise<void> {
      const selector = campo<HTMLSelectElement>(panel, '#tarea-workflow')
      selector.value = valor
      selector.dispatchEvent(new Event('change'))
      await flushPromises()
    }

    async function rellenarObligatorios(panel: HTMLElement): Promise<void> {
      await escribir(campo(panel, 'input[placeholder="Nombre"]'), 'Nueva')
      await escribir(campo(panel, 'textarea[placeholder="Descripción"]'), 'Detalle')
    }

    it('carga los workflows y los ofrece en el campo "Workflow" del alta', async () => {
      const envoltorio = await montar([], [], WORKFLOWS)
      const panel = await abrirPanel(envoltorio)

      expect(clienteApi.obtener).toHaveBeenCalledWith('/workflows')
      expect(campo(panel, 'label[for="tarea-workflow"]').textContent?.trim()).toBe('Workflow')
      const opciones = [...campo<HTMLSelectElement>(panel, '#tarea-workflow').options]
      expect(opciones.map((o) => o.textContent?.trim())).toEqual([
        'Sin workflow',
        'Workflow Oportunidades',
        'Altas',
      ])
    })

    it('al crear envía el workflow elegido en workflow_id', async () => {
      const envoltorio = await montar([], [], WORKFLOWS)
      vi.mocked(clienteApi.crear).mockResolvedValue({ ...TAREAS[0], id: 9, nombre: 'Nueva' })
      const panel = await abrirPanel(envoltorio)

      await rellenarObligatorios(panel)
      await elegirWorkflow(panel, '2')
      await enviar(panel)

      expect(clienteApi.crear).toHaveBeenCalledWith(
        '/tareas',
        expect.objectContaining({ workflow_id: 2 }),
      )
    })

    it('al crear una oportunidad sin workflow preselecciona "Workflow Oportunidades" y lo envía', async () => {
      const envoltorio = await montar([], [], WORKFLOWS)
      vi.mocked(clienteApi.crear).mockResolvedValue({ ...TAREAS[0], id: 9, nombre: 'Nueva' })
      const panel = await abrirPanel(envoltorio)

      await rellenarObligatorios(panel)
      await elegirTipo(panel, 'oportunidad')
      expect(campo<HTMLSelectElement>(panel, '#tarea-workflow').value).toBe('1')
      await escribir(campo(panel, '#oportunidad-codigo'), 'OP-9')
      await enviar(panel)

      expect(clienteApi.crear).toHaveBeenCalledWith(
        '/tareas',
        expect.objectContaining({ tipo: 'oportunidad', workflow_id: 1 }),
      )
    })

    it('al editar carga el workflow de la tarea y lo vuelve a enviar', async () => {
      const conWorkflow = { ...TAREAS[0], workflow: { id: 2, nombre: 'Altas' } }
      const envoltorio = await montar([conWorkflow], [], WORKFLOWS)
      vi.mocked(clienteApi.actualizar).mockResolvedValue(conWorkflow)
      const panel = await abrirPanelEdicion(envoltorio, 'Escribir informe')

      expect(campo<HTMLSelectElement>(panel, '#tarea-workflow').value).toBe('2')
      await enviar(panel)

      expect(clienteApi.actualizar).toHaveBeenCalledWith(
        '/tareas/1',
        expect.objectContaining({ workflow_id: 2 }),
      )
    })

    it('al editar se puede cambiar o quitar el workflow', async () => {
      const conWorkflow = { ...TAREAS[0], workflow: { id: 2, nombre: 'Altas' } }
      const envoltorio = await montar([conWorkflow], [], WORKFLOWS)
      vi.mocked(clienteApi.actualizar).mockResolvedValue({ ...conWorkflow, workflow: null })
      const panel = await abrirPanelEdicion(envoltorio, 'Escribir informe')

      await elegirWorkflow(panel, '')
      await enviar(panel)

      expect(clienteApi.actualizar).toHaveBeenCalledWith(
        '/tareas/1',
        expect.objectContaining({ workflow_id: null }),
      )
    })

    it('al editar y elegir el tipo Oportunidad no preselecciona ningún workflow', async () => {
      const envoltorio = await montar(TAREAS, [], WORKFLOWS)
      vi.mocked(clienteApi.actualizar).mockResolvedValue(TAREA_OPORTUNIDAD)
      const panel = await abrirPanelEdicion(envoltorio, 'Escribir informe')

      await elegirTipo(panel, 'oportunidad')
      expect(campo<HTMLSelectElement>(panel, '#tarea-workflow').value).toBe('')
      await escribir(campo(panel, '#oportunidad-codigo'), 'OP-1')
      await enviar(panel)

      expect(clienteApi.actualizar).toHaveBeenCalledWith(
        '/tareas/1',
        expect.objectContaining({ tipo: 'oportunidad', workflow_id: null }),
      )
    })
  })

  describe('calendario', () => {
    const CLAVE_VISTA = 'gestor-tareas:vista-tareas'

    // Hoy (AHORA) es el lunes 9 de noviembre de 2026.
    const NOCHE = {
      ...TAREAS[1],
      id: 5,
      nombre: 'Cerrar caja',
      fecha_vencimiento: '2026-11-11T23:59:00',
    }
    const MADRUGADA = {
      ...TAREAS[1],
      id: 6,
      nombre: 'Copia de seguridad',
      fecha_vencimiento: '2026-11-12T00:30:00',
      completada: true,
    }
    const DICIEMBRE = {
      ...TAREAS[1],
      id: 7,
      nombre: 'Cena de empresa',
      fecha_vencimiento: '2026-12-18T21:00:00',
    }
    // TAREAS[0] vence el 20/11/2026 a las 18:00; TAREAS[1] no tiene vencimiento.
    const TAREAS_CALENDARIO = [TAREAS[0], TAREAS[1], NOCHE, MADRUGADA, DICIEMBRE]

    type AvisoTamano = (
      entradas: { borderBoxSize: { inlineSize: number; blockSize: number }[] }[],
    ) => void

    // jsdom no maqueta: se sustituye ResizeObserver por uno que informa del ancho dado.
    function fijarAncho(ancho: number): void {
      vi.stubGlobal(
        'ResizeObserver',
        class {
          constructor(private readonly llamada: AvisoTamano) {}
          observe(): void {
            this.llamada([{ borderBoxSize: [{ inlineSize: ancho, blockSize: 600 }] }])
          }
          unobserve(): void {}
          disconnect(): void {}
        },
      )
    }

    beforeEach(() => localStorage.removeItem(CLAVE_VISTA))
    afterEach(() => {
      localStorage.removeItem(CLAVE_VISTA)
      vi.unstubAllGlobals()
    })

    function botonPorEtiqueta(etiqueta: string): HTMLButtonElement {
      const boton = document.body.querySelector<HTMLButtonElement>(
        `button[aria-label="${etiqueta}"]`,
      )
      if (!boton) throw new Error(`No se encontró el botón "${etiqueta}"`)
      return boton
    }

    function botonPorTexto(texto: string): HTMLButtonElement {
      const boton = [...document.body.querySelectorAll('button')].find(
        (b) => b.textContent?.trim() === texto,
      )
      if (!boton) throw new Error(`No se encontró el botón "${texto}"`)
      return boton
    }

    async function montarCalendario(tareas: unknown[] = TAREAS_CALENDARIO) {
      const envoltorio = await montar(tareas)
      botonPorEtiqueta('Ver como calendario').click()
      await flushPromises()
      return envoltorio
    }

    function dia(nombre: string): HTMLElement {
      const elemento = document.body.querySelector<HTMLElement>(`[aria-label="${nombre}"]`)
      if (!elemento) throw new Error(`No se encontró el día "${nombre}"`)
      return elemento
    }

    function tareasDe(nombre: string): string[] {
      return [...dia(nombre).querySelectorAll('[data-tarea-calendario]')].map((t) =>
        t.textContent!.replace(/\s+/g, ' ').trim(),
      )
    }

    function titulo(): string {
      return document.body.querySelector('[data-titulo-mes]')!.textContent!.trim()
    }

    it('"Ver como calendario" muestra el calendario y recuerda la elección', async () => {
      const envoltorio = await montarCalendario()

      const boton = botonPorEtiqueta('Ver como calendario')
      expect(boton.getAttribute('title')).toBe('Ver como calendario')
      expect(boton.getAttribute('aria-pressed')).toBe('true')
      expect(botonPorEtiqueta('Ver como lista').getAttribute('aria-pressed')).toBe('false')
      expect(botonPorEtiqueta('Ver como tablero').getAttribute('aria-pressed')).toBe('false')
      expect(document.body.querySelector('[data-testid="calendario-tareas"]')).not.toBeNull()
      expect(localStorage.getItem(CLAVE_VISTA)).toBe('calendario')

      envoltorio.unmount()
      contenedor = null
      document.body.innerHTML = ''
      await montar(TAREAS_CALENDARIO)
      expect(botonPorEtiqueta('Ver como calendario').getAttribute('aria-pressed')).toBe('true')
      expect(titulo()).toBe('noviembre de 2026')
    })

    it('abre en el mes de hoy, con semanas de lunes a domingo y hoy marcado', async () => {
      await montarCalendario()

      expect(titulo()).toBe('noviembre de 2026')
      const cabeceras = [...document.body.querySelectorAll('thead th')].map((th) =>
        th.textContent?.trim(),
      )
      expect(cabeceras).toEqual([
        'lunes',
        'martes',
        'miércoles',
        'jueves',
        'viernes',
        'sábado',
        'domingo',
      ])
      // El 1 de noviembre de 2026 es domingo: última columna de la primera semana.
      const primeraSemana = document.body.querySelectorAll('tbody tr')[0]!.querySelectorAll('td')
      expect(primeraSemana[6]!.querySelector('[aria-label]')?.getAttribute('aria-label')).toBe(
        'domingo, 1 de noviembre de 2026',
      )
      expect(primeraSemana[0]!.querySelector('[aria-label]')).toBeNull()
      const hoy = document.body.querySelectorAll('[aria-current="date"]')
      expect(hoy).toHaveLength(1)
      expect(hoy[0]!.getAttribute('aria-label')).toBe('lunes, 9 de noviembre de 2026')
    })

    it('coloca cada tarea en el día local de su vencimiento y muestra la hora', async () => {
      await montarCalendario()

      expect(tareasDe('miércoles, 11 de noviembre de 2026')).toEqual(['23:59 Cerrar caja'])
      expect(tareasDe('jueves, 12 de noviembre de 2026')).toEqual(['00:30 Copia de seguridad'])
      expect(tareasDe('viernes, 20 de noviembre de 2026')).toEqual(['18:00 Escribir informe'])
      expect(
        dia('miércoles, 11 de noviembre de 2026').querySelector('ul')?.getAttribute('aria-label'),
      ).toBe('Tareas del miércoles, 11 de noviembre de 2026')
    })

    it('las tareas completadas aparecen tachadas', async () => {
      await montarCalendario()

      const completada = dia('jueves, 12 de noviembre de 2026').querySelector(
        '[data-tarea-calendario]',
      )!
      const pendiente = dia('miércoles, 11 de noviembre de 2026').querySelector(
        '[data-tarea-calendario]',
      )!
      expect(completada.className).toContain('line-through')
      expect(pendiente.className).not.toContain('line-through')
    })

    it('avisa de las tareas sin fecha de vencimiento', async () => {
      await montarCalendario()

      expect(document.body.textContent).toContain('1 tarea sin fecha de vencimiento')
    })

    it('"Mes siguiente", "Mes anterior" y "Hoy" cambian el mes mostrado', async () => {
      await montarCalendario()

      botonPorTexto('Mes siguiente').click()
      await flushPromises()
      expect(titulo()).toBe('diciembre de 2026')
      expect(tareasDe('viernes, 18 de diciembre de 2026')).toEqual(['21:00 Cena de empresa'])
      expect(document.body.querySelector('[aria-current="date"]')).toBeNull()

      botonPorTexto('Mes siguiente').click()
      await flushPromises()
      expect(titulo()).toBe('enero de 2027')

      for (let vez = 0; vez < 3; vez++) botonPorTexto('Mes anterior').click()
      await flushPromises()
      expect(titulo()).toBe('octubre de 2026')

      botonPorTexto('Hoy').click()
      await flushPromises()
      expect(titulo()).toBe('noviembre de 2026')
    })

    it('un día con más de 3 tareas muestra 3 y "+N más" despliega el resto', async () => {
      const mismoDia = [1, 2, 3, 4, 5].map((numero) => ({
        ...TAREAS[1],
        id: 20 + numero,
        nombre: `Tarea ${numero}`,
        fecha_vencimiento: `2026-11-16T0${numero}:00:00`,
      }))
      await montarCalendario(mismoDia)
      const lunes = 'lunes, 16 de noviembre de 2026'

      expect(tareasDe(lunes)).toEqual(['01:00 Tarea 1', '02:00 Tarea 2', '03:00 Tarea 3'])
      const mas = botonPorEtiqueta(`+2 más (${lunes})`)
      expect(mas.textContent?.trim()).toBe('+2 más')
      mas.focus()
      mas.click()
      await flushPromises()

      expect(tareasDe(lunes)).toHaveLength(5)
      // El botón desaparece: el foco va a la primera tarea que estaba oculta.
      expect(document.activeElement?.textContent?.replace(/\s+/g, ' ').trim()).toBe('04:00 Tarea 4')
    })

    it('los filtros y la búsqueda se aplican al calendario', async () => {
      await montarCalendario()

      await escribir(campo<HTMLInputElement>(document.body, '#filtro-buscar'), 'caja')

      expect(tareasDe('miércoles, 11 de noviembre de 2026')).toEqual(['23:59 Cerrar caja'])
      expect(tareasDe('viernes, 20 de noviembre de 2026')).toEqual([])
      expect(document.body.textContent).not.toContain('sin fecha de vencimiento')
    })

    it('pulsar una tarea abre su detalle', async () => {
      await montarCalendario()

      dia('viernes, 20 de noviembre de 2026')
        .querySelector<HTMLButtonElement>('[data-tarea-calendario]')!
        .click()
      await flushPromises()

      expect(panelActual().querySelector('h2')?.textContent?.trim()).toBe('Escribir informe')
    })

    it('en un contenedor estrecho muestra una agenda con los días del mes que tienen tareas', async () => {
      fijarAncho(500)
      await montarCalendario()

      expect(document.body.querySelector('[data-testid="calendario-tareas"] table')).toBeNull()
      const encabezados = [...document.body.querySelectorAll('[data-agenda] h3')].map((h) =>
        h.textContent?.trim(),
      )
      expect(encabezados).toEqual([
        'miércoles, 11 de noviembre de 2026',
        'jueves, 12 de noviembre de 2026',
        'viernes, 20 de noviembre de 2026',
      ])
      expect(tareasDe('miércoles, 11 de noviembre de 2026')).toEqual(['23:59 Cerrar caja'])
    })

    it('con ancho suficiente muestra la cuadrícula', async () => {
      fijarAncho(900)
      await montarCalendario()

      expect(document.body.querySelector('[data-testid="calendario-tareas"] table')).not.toBeNull()
      expect(document.body.querySelector('[data-agenda]')).toBeNull()
    })
  })

  describe('editar desde el detalle', () => {
    const GRUPO = {
      id: 1,
      nombre: 'Desarrollo',
      tareas: 1,
      estados: [
        { id: 10, nombre: 'Pendiente', posicion: 1, tareas: 1 },
        { id: 11, nombre: 'En curso', posicion: 2, tareas: 0 },
      ],
    }
    const EN_GRUPO = {
      ...TAREAS[0],
      grupo_estados: { id: 1, nombre: 'Desarrollo' },
      estado: { id: 10, nombre: 'Pendiente' },
    }

    async function abrirDetalle(envoltorio: VueWrapper, nombre: string): Promise<HTMLElement> {
      await pulsarAccionFila(envoltorio, nombre, 'Ver detalle de la tarea')
      await flushPromises()
      return panelActual()
    }

    function boton(modal: HTMLElement, texto: string): HTMLButtonElement {
      const encontrado = [...modal.querySelectorAll('button')].find(
        (b) => b.textContent?.trim() === texto,
      )
      if (!encontrado) throw new Error(`No se encontró el botón "${texto}"`)
      return encontrado
    }

    async function pulsar(modal: HTMLElement, texto: string): Promise<void> {
      boton(modal, texto).click()
      await flushPromises()
    }

    it('"Editar" cambia los datos por el formulario cargado, sin cerrar el detalle', async () => {
      const modal = await abrirDetalle(await montar(), 'Escribir informe')
      expect(modal.querySelector('[data-testid="campos-tarea"]')).not.toBeNull()

      await pulsar(modal, 'Editar')

      const editando = panelActual()
      expect(editando.querySelector('h2')?.textContent?.trim()).toBe('Escribir informe')
      expect(editando.querySelector('[data-testid="campos-tarea"]')).toBeNull()
      expect(campo<HTMLInputElement>(editando, 'input[placeholder="Nombre"]').value).toBe(
        'Escribir informe',
      )
      expect(campo<HTMLInputElement>(editando, 'input[placeholder="Prioridad"]').value).toBe('2')
      expect(campo<HTMLInputElement>(editando, SELECTOR_FECHA).value).toBe('10/11/2026 09:30:00')
      expect(chipsDe(editando, 'Etiquetas')).toEqual(['Backend', 'Urgente'])
      // Los comentarios siguen a la vista mientras se edita.
      expect(editando.querySelector('[data-testid="columna-comentarios"]')).not.toBeNull()
      // Mientras se edita, el pie no ofrece "Editar" otra vez.
      expect(
        [...editando.querySelectorAll('button')].some((b) => b.textContent?.trim() === 'Editar'),
      ).toBe(false)
    })

    it('"Cancelar" vuelve a los datos sin guardar', async () => {
      const modal = await abrirDetalle(await montar(), 'Escribir informe')
      await pulsar(modal, 'Editar')
      await escribir(campo(panelActual(), 'input[placeholder="Nombre"]'), 'Otro nombre')

      await pulsar(panelActual(), 'Cancelar')

      expect(clienteApi.actualizar).not.toHaveBeenCalled()
      expect(panelActual().querySelector('[data-testid="campos-tarea"]')?.textContent).toContain(
        'Escribir informe',
      )
    })

    it('"Guardar" actualiza la tarea y vuelve a los datos ya cambiados', async () => {
      const envoltorio = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue({ ...TAREAS[0], nombre: 'Informe final' })
      const modal = await abrirDetalle(envoltorio, 'Escribir informe')
      await pulsar(modal, 'Editar')

      await escribir(campo(panelActual(), 'input[placeholder="Nombre"]'), 'Informe final')
      await enviar(panelActual())

      expect(clienteApi.actualizar).toHaveBeenCalledWith('/tareas/1', {
        nombre: 'Informe final',
        prioridad: 2,
        descripcion: 'Informe trimestral',
        fecha_creacion: '2026-11-10T09:30:00',
        fecha_vencimiento: '2026-11-20T18:00:00',
        etiquetas: ['Backend', 'Urgente'],
        asignados: ['Ana'],
        tipo: null,
        oportunidad: null,
        grupo_estados_id: null,
        workflow_id: null,
      })
      expect(clienteApi.parchear).not.toHaveBeenCalled()
      const despues = panelActual()
      expect(despues.querySelector('h2')?.textContent?.trim()).toBe('Informe final')
      expect(despues.querySelector('[data-testid="campos-tarea"]')).not.toBeNull()
    })

    it('si falla al guardar, sigue editando y muestra el error', async () => {
      const envoltorio = await montar()
      vi.mocked(clienteApi.actualizar).mockRejectedValue(new Error('Tarea no encontrada'))
      const modal = await abrirDetalle(envoltorio, 'Escribir informe')
      await pulsar(modal, 'Editar')

      await enviar(panelActual())

      expect(panelActual().querySelector('input[placeholder="Nombre"]')).not.toBeNull()
      expect(panelActual().textContent).toContain('Tarea no encontrada')
    })

    it('también edita si está completada y el estado del grupo', async () => {
      const envoltorio = await montar([EN_GRUPO, TAREAS[1]], [GRUPO])
      vi.mocked(clienteApi.actualizar).mockResolvedValue(structuredClone(EN_GRUPO))
      vi.mocked(clienteApi.parchear).mockImplementation((ruta, cuerpo) =>
        Promise.resolve(
          String(ruta).endsWith('/estado')
            ? { ...EN_GRUPO, estado: { id: 11, nombre: 'En curso' } }
            : { ...EN_GRUPO, ...(cuerpo as object) },
        ),
      )
      const modal = await abrirDetalle(envoltorio, 'Escribir informe')
      await pulsar(modal, 'Editar')
      const editando = panelActual()

      const completada = campo<HTMLInputElement>(editando, '#tarea-completada')
      expect(completada.checked).toBe(false)
      completada.click()
      const estado = campo<HTMLSelectElement>(editando, '#tarea-estado')
      expect(estado.value).toBe('10')
      expect([...estado.options].map((o) => o.text)).toEqual(['Pendiente', 'En curso'])
      estado.value = '11'
      estado.dispatchEvent(new Event('change'))
      await flushPromises()
      await enviar(editando)

      expect(clienteApi.actualizar).toHaveBeenCalledWith(
        '/tareas/1',
        expect.objectContaining({ grupo_estados_id: 1 }),
      )
      expect(clienteApi.parchear).toHaveBeenCalledWith('/tareas/1/completada', {
        completada: true,
      })
      expect(clienteApi.parchear).toHaveBeenCalledWith('/tareas/1/estado', { estado_id: 11 })
      expect(panelActual().querySelector('[data-testid="campos-tarea"]')).not.toBeNull()
    })

    it('al cambiar de grupo, el estado pasa al primero del grupo nuevo', async () => {
      const OTRO = {
        id: 2,
        nombre: 'Soporte',
        tareas: 0,
        estados: [
          { id: 20, nombre: 'Abierta', posicion: 1, tareas: 0 },
          { id: 21, nombre: 'Cerrada', posicion: 2, tareas: 0 },
        ],
      }
      const envoltorio = await montar([EN_GRUPO], [GRUPO, OTRO])
      const modal = await abrirDetalle(envoltorio, 'Escribir informe')
      await pulsar(modal, 'Editar')
      const editando = panelActual()

      const grupo = campo<HTMLSelectElement>(editando, '#tarea-grupo-estados')
      grupo.value = '2'
      grupo.dispatchEvent(new Event('change'))
      await flushPromises()

      const estado = campo<HTMLSelectElement>(editando, '#tarea-estado')
      expect(estado.value).toBe('20')
      expect([...estado.options].map((o) => o.text)).toEqual(['Abierta', 'Cerrada'])
    })

    it('sin grupo de estados no muestra el estado del grupo', async () => {
      const modal = await abrirDetalle(await montar(), 'Escribir informe')
      await pulsar(modal, 'Editar')

      expect(panelActual().querySelector('#tarea-estado')).toBeNull()
      expect(panelActual().querySelector('#tarea-completada')).not.toBeNull()
    })
  })

  describe('tareas relacionadas de una etiqueta o persona', () => {
    // "Leer artículo" no tiene a Ana asignada, pero sí una de sus subtareas.
    const CON_SUBTAREA_DE_ANA = {
      ...TAREAS[1],
      subtareas: [{ ...SUBTAREAS[1], asignado: 'Ana' }],
    }

    function dialogoTitulado(titulo: string): HTMLElement {
      const dialogo = [...document.body.querySelectorAll<HTMLElement>('[role="dialog"]')].find(
        (d) => d.querySelector('h2')?.textContent?.trim() === titulo,
      )
      if (!dialogo) throw new Error(`No se encontró el diálogo "${titulo}"`)
      return dialogo
    }

    function textosLista(dialogo: HTMLElement, lista: string): string[] {
      return [...dialogo.querySelectorAll(`ul[aria-label="${lista}"] li button`)].map(
        (b) => b.getAttribute('aria-label') ?? '',
      )
    }

    it('pulsar una etiqueta de la tabla abre la modal con las tareas que la llevan', async () => {
      const envoltorio = await montar()

      await envoltorio
        .find('button[aria-label="Ver tareas con la etiqueta Urgente"]')
        .trigger('click')
      await flushPromises()

      const modal = dialogoTitulado('Etiqueta: Urgente')
      expect(textosLista(modal, 'Tareas')).toEqual(['Abrir la tarea Escribir informe'])
      expect(modal.querySelector('ul[aria-label="Subtareas"]')).toBeNull()
    })

    it('pulsar una persona de la tabla lista sus tareas y las subtareas que tiene asignadas', async () => {
      const envoltorio = await montar([TAREAS[0], CON_SUBTAREA_DE_ANA])

      await envoltorio.find('button[aria-label="Ver tareas y subtareas de Ana"]').trigger('click')
      await flushPromises()

      const modal = dialogoTitulado('Persona: Ana')
      expect(textosLista(modal, 'Tareas')).toEqual(['Abrir la tarea Escribir informe'])
      expect(textosLista(modal, 'Subtareas')).toEqual([
        'Abrir la tarea Leer artículo (subtarea Enviar propuesta)',
      ])
    })

    it('en el detalle se pulsan las etiquetas, las personas y la persona de una subtarea', async () => {
      const envoltorio = await montar([TAREAS[0], CON_SUBTAREA_DE_ANA])

      await pulsarAccionFila(envoltorio, 'Escribir informe', 'Ver detalle de la tarea')
      await flushPromises()
      const detalle = dialogoTitulado('Escribir informe')
      const campos = detalle.querySelector('[data-testid="campos-tarea"]')
      campos
        ?.querySelector<HTMLButtonElement>(
          'button[aria-label="Ver tareas con la etiqueta Backend"]',
        )
        ?.click()
      await flushPromises()
      expect(textosLista(dialogoTitulado('Etiqueta: Backend'), 'Tareas')).toEqual([
        'Abrir la tarea Escribir informe',
      ])

      // Se cambia al detalle de la otra tarea para pulsar la persona de su subtarea.
      await pulsarAccionFila(envoltorio, 'Leer artículo', 'Ver detalle de la tarea')
      await flushPromises()
      dialogoTitulado('Leer artículo')
        .querySelector<HTMLButtonElement>('button[aria-label="Ver tareas y subtareas de Ana"]')
        ?.click()
      await flushPromises()
      expect(textosLista(dialogoTitulado('Persona: Ana'), 'Subtareas')).toEqual([
        'Abrir la tarea Leer artículo (subtarea Enviar propuesta)',
      ])
    })

    it('pulsar una tarea de la modal cierra la modal y abre el detalle de esa tarea', async () => {
      const envoltorio = await montar([TAREAS[0], CON_SUBTAREA_DE_ANA])

      await envoltorio.find('button[aria-label="Ver tareas y subtareas de Ana"]').trigger('click')
      await flushPromises()
      dialogoTitulado('Persona: Ana')
        .querySelector<HTMLButtonElement>(
          'button[aria-label="Abrir la tarea Leer artículo (subtarea Enviar propuesta)"]',
        )
        ?.click()
      await flushPromises()

      const dialogos = [...document.body.querySelectorAll('[role="dialog"]')]
      expect(dialogos.map((d) => d.querySelector('h2')?.textContent?.trim())).toEqual([
        'Leer artículo',
      ])
    })
  })

  describe('clic en la fila', () => {
    function fila(nombre: string): HTMLElement {
      const encontrada = [
        ...document.body.querySelectorAll<HTMLElement>('tr[data-fila-tarea]'),
      ].find((tr) => tr.textContent?.includes(nombre))
      if (!encontrada) throw new Error(`No se encontró la fila "${nombre}"`)
      return encontrada
    }

    function titulosDialogos(): string[] {
      return [...document.body.querySelectorAll('[role="dialog"]')].map(
        (d) => d.querySelector('h2')?.textContent?.trim() ?? '',
      )
    }

    it('pulsar cualquier celda de la fila abre el detalle de esa tarea', async () => {
      await montar()

      fila('Leer artículo').querySelectorAll('td')[3]!.click()
      await flushPromises()

      expect(titulosDialogos()).toEqual(['Leer artículo'])
    })

    it('la fila indica con el cursor que se puede pulsar', async () => {
      await montar()
      expect(fila('Escribir informe').className).toContain('cursor-pointer')
    })

    it('la casilla de completada y el menú de acciones no abren el detalle', async () => {
      const envoltorio = await montar()

      fila('Escribir informe')
        .querySelector<HTMLElement>(
          '[role="checkbox"][aria-label="Marcar como completada la tarea Escribir informe"]',
        )!
        .click()
      await flushPromises()
      await envoltorio
        .get('button[aria-label="Acciones de la tarea Escribir informe"]')
        .trigger('click')
      await flushPromises()

      expect(titulosDialogos()).not.toContain('Escribir informe')
    })

    it('pulsar una etiqueta de la fila abre solo la modal de tareas relacionadas', async () => {
      await montar()

      fila('Escribir informe')
        .querySelector<HTMLButtonElement>(
          'button[aria-label="Ver tareas con la etiqueta Urgente"]',
        )!
        .click()
      await flushPromises()

      expect(titulosDialogos()).toEqual(['Etiqueta: Urgente'])
    })

    it('no abre el detalle si se está seleccionando texto de la fila', async () => {
      await montar()
      const celda = fila('Leer artículo').querySelectorAll('td')[3]!
      const seleccion = window.getSelection()!
      seleccion.selectAllChildren(celda)

      celda.click()
      await flushPromises()

      expect(titulosDialogos()).toEqual([])
      seleccion.removeAllRanges()
    })
  })

  describe('aviso de vencimiento con campanas', () => {
    // La vista elegida (lista, tablero o calendario) se recuerda entre montajes.
    beforeEach(() => {
      localStorage.clear()
    })

    // AHORA es el 09/11/2026 a las 18:45:30.
    const GRUPO = {
      id: 1,
      nombre: 'Desarrollo',
      tareas: 3,
      estados: [{ id: 10, nombre: 'Pendiente', posicion: 1, tareas: 3 }],
    }
    const EN_GRUPO = {
      grupo_estados: { id: 1, nombre: 'Desarrollo' },
      estado: { id: 10, nombre: 'Pendiente' },
    }
    // Menos de 1 día: dos campanas.
    const URGENTE = {
      ...TAREAS[1],
      ...EN_GRUPO,
      id: 21,
      nombre: 'Urgente hoy',
      fecha_vencimiento: '2026-11-10T10:00:00',
    }
    // Entre 1 y 2 días: una campana.
    const PRONTO = {
      ...TAREAS[1],
      ...EN_GRUPO,
      id: 22,
      nombre: 'Pronto',
      fecha_vencimiento: '2026-11-11T10:00:00',
    }
    // 2 días o más: sin campana.
    const HOLGADA = {
      ...TAREAS[1],
      ...EN_GRUPO,
      id: 23,
      nombre: 'Holgada',
      fecha_vencimiento: '2026-11-20T10:00:00',
    }
    const TAREAS_AVISO = [URGENTE, PRONTO, HOLGADA]

    function avisos(): Record<string, string> {
      const resultado: Record<string, string> = {}
      for (const aviso of document.body.querySelectorAll('[data-aviso-vencimiento]')) {
        const contenedor = aviso.closest('tr, [data-tarjeta], li, [role="dialog"]')
        const nombre = ['Urgente hoy', 'Pronto', 'Holgada'].find((n) =>
          contenedor?.textContent?.includes(n),
        )
        resultado[nombre ?? '?'] =
          `${aviso.getAttribute('aria-label')} (${aviso.querySelectorAll('[data-campana]').length})`
      }
      return resultado
    }

    function pulsarVista(etiqueta: string): void {
      document.body.querySelector<HTMLButtonElement>(`button[aria-label="${etiqueta}"]`)!.click()
    }

    const ESPERADO = {
      'Urgente hoy': 'Vence en menos de 1 día (2)',
      Pronto: 'Vence en menos de 2 días (1)',
    }

    it('la lista muestra una campana con menos de 2 días y dos con menos de 1 día', async () => {
      await montar(TAREAS_AVISO, [GRUPO])
      expect(avisos()).toEqual(ESPERADO)
    })

    it('el tablero muestra las campanas en las tarjetas', async () => {
      await montar(TAREAS_AVISO, [GRUPO])
      pulsarVista('Ver como tablero')
      await flushPromises()
      expect(avisos()).toEqual(ESPERADO)
    })

    it('el calendario muestra las campanas junto a cada tarea', async () => {
      await montar(TAREAS_AVISO, [GRUPO])
      pulsarVista('Ver como calendario')
      await flushPromises()
      expect(avisos()).toEqual(ESPERADO)
    })

    it('el detalle muestra las campanas junto al título', async () => {
      await montar(TAREAS_AVISO, [GRUPO])
      const fila = [...document.body.querySelectorAll<HTMLElement>('tr[data-fila-tarea]')].find(
        (tr) => tr.textContent?.includes('Urgente hoy'),
      )!
      fila.querySelectorAll('td')[2]!.click()
      await flushPromises()
      const dialogo = document.body.querySelector('[role="dialog"]')!
      expect(dialogo.querySelector('h2')?.textContent?.trim()).toBe('Urgente hoy')
      expect(dialogo.querySelector('[data-aviso-vencimiento]')?.getAttribute('aria-label')).toBe(
        'Vence en menos de 1 día',
      )
    })
  })
})
