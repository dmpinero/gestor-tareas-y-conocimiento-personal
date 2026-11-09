import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { clienteApi } from '@/api/cliente'
import VistaTareas from '../VistaTareas.vue'

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
    fecha_hora: '2026-11-10T09:30:00',
  },
  {
    id: 2,
    nombre: 'Leer artículo',
    prioridad: null,
    descripcion: 'Artículo sobre Vue',
    fecha_hora: '2026-12-01T17:05:09',
  },
]

// Fecha y hora "actuales" fijas para que el valor por defecto sea determinista.
const AHORA = new Date(2026, 10, 9, 18, 45, 30)
const AHORA_TEXTO = '09/11/2026 18:45:30'
const AHORA_ISO = '2026-11-09T18:45:30'
const SELECTOR_FECHA = 'input[placeholder="dd/mm/aaaa hh:mm:ss"]'

let contenedor: VueWrapper | null = null

async function montar(tareas: unknown[] = TAREAS): Promise<VueWrapper> {
  vi.mocked(clienteApi.obtener).mockResolvedValue(tareas)
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

function filasTabla(envoltorio: VueWrapper): string[][] {
  return envoltorio.findAll('tbody tr').map((tr) => tr.findAll('td').map((td) => td.text()))
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
    expect(cabeceras).toEqual(['Nombre', 'Prioridad', 'Descripción', 'Fecha y hora', 'Acciones'])
    expect(filasTabla(envoltorio)).toEqual([
      ['Escribir informe', '2', 'Informe trimestral', '10/11/2026 09:30:00', 'Editar'],
      ['Leer artículo', '—', 'Artículo sobre Vue', '01/12/2026 17:05:09', 'Editar'],
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

    const fechaHora = campo<HTMLInputElement>(panel, SELECTOR_FECHA)
    expect(fechaHora.type).toBe('text')
    expect(fechaHora.required).toBe(true)
    expect(fechaHora.getAttribute('pattern')).toBe('\\d{2}/\\d{2}/\\d{4} \\d{2}:\\d{2}:\\d{2}')
    expect(panel.querySelector('label[for="tarea-fecha-hora"]')?.textContent?.trim()).toBe(
      'Fecha y hora',
    )
  })

  it('en modo crear rellena la fecha y hora con la actual, segundos incluidos', async () => {
    const panel = await abrirPanel(await montar())

    expect(campo<HTMLInputElement>(panel, SELECTOR_FECHA).value).toBe(AHORA_TEXTO)
  })

  it('con una fecha y hora inválida muestra el error y no llama a la API', async () => {
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

  it('envía la fecha y hora escrita en formato ISO', async () => {
    const envoltorio = await montar([])
    vi.mocked(clienteApi.crear).mockResolvedValue({
      id: 5,
      nombre: 'Con fecha',
      prioridad: null,
      descripcion: 'Detalle',
      fecha_hora: '2027-01-02T03:04:05',
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
      fecha_hora: '2027-01-02T03:04:05',
    })
    expect(filasTabla(envoltorio)).toEqual([
      ['Con fecha', '—', 'Detalle', '02/01/2027 03:04:05', 'Editar'],
    ])
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
  })

  it('al guardar en modo editar actualiza la tarea, cierra el panel y refresca la fila', async () => {
    const envoltorio = await montar()
    vi.mocked(clienteApi.actualizar).mockResolvedValue({
      id: 1,
      nombre: 'Informe final',
      prioridad: null,
      descripcion: 'Informe trimestral',
      fecha_hora: '2026-11-11T08:00:00',
    })
    const panel = await abrirPanelEdicion(envoltorio, 'Escribir informe')

    await escribir(campo(panel, 'input[placeholder="Nombre"]'), 'Informe final')
    await escribir(campo(panel, 'input[placeholder="Prioridad"]'), '')
    await escribir(campo(panel, SELECTOR_FECHA), '11/11/2026 08:00:00')
    await enviar(panel)

    expect(clienteApi.crear).not.toHaveBeenCalled()
    expect(clienteApi.actualizar).toHaveBeenCalledWith('/tareas/1', {
      nombre: 'Informe final',
      prioridad: null,
      descripcion: 'Informe trimestral',
      fecha_hora: '2026-11-11T08:00:00',
    })
    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    expect(filasTabla(envoltorio)).toEqual([
      ['Informe final', '—', 'Informe trimestral', '11/11/2026 08:00:00', 'Editar'],
      ['Leer artículo', '—', 'Artículo sobre Vue', '01/12/2026 17:05:09', 'Editar'],
    ])

    // Tras editar, "Crear tarea" vuelve al modo crear con el formulario limpio.
    const panelCrear = await abrirPanel(envoltorio)
    expect(panelCrear.querySelector('h2')?.textContent?.trim()).toBe('Crear tarea')
    expect(campo<HTMLInputElement>(panelCrear, 'input[placeholder="Nombre"]').value).toBe('')
    expect(campo<HTMLInputElement>(panelCrear, SELECTOR_FECHA).value).toBe(AHORA_TEXTO)
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
      fecha_hora: '2026-12-01T17:05:09',
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
      fecha_hora: AHORA_ISO,
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
      fecha_hora: AHORA_ISO,
    })
    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    expect(filasTabla(envoltorio)).toEqual([['Nueva', '1', 'Detalle', AHORA_TEXTO, 'Editar']])

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
      fecha_hora: AHORA_ISO,
    })
    const panel = await abrirPanel(envoltorio)

    await escribir(campo(panel, 'input[placeholder="Nombre"]'), 'Sin prioridad')
    await escribir(campo(panel, 'textarea[placeholder="Descripción"]'), 'Detalle')
    await enviar(panel)

    expect(clienteApi.crear).toHaveBeenCalledWith('/tareas', {
      nombre: 'Sin prioridad',
      prioridad: null,
      descripcion: 'Detalle',
      fecha_hora: AHORA_ISO,
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
})
