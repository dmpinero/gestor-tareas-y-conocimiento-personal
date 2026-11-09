import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { clienteApi } from '@/api/cliente'
import VistaTareas from '../VistaTareas.vue'

vi.mock('@/api/cliente', () => ({
  clienteApi: {
    obtener: vi.fn<(...args: unknown[]) => unknown>(),
    crear: vi.fn<(...args: unknown[]) => unknown>(),
  },
}))

const TAREAS = [
  { id: 1, nombre: 'Escribir informe', prioridad: 2, descripcion: 'Informe trimestral' },
  { id: 2, nombre: 'Leer artículo', prioridad: null, descripcion: 'Artículo sobre Vue' },
]

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

async function abrirPanel(envoltorio: VueWrapper): Promise<HTMLElement> {
  await botonCrear(envoltorio).trigger('click')
  await flushPromises()
  const panel = document.body.querySelector<HTMLElement>('[role="dialog"]')
  if (!panel) throw new Error('El panel lateral no se abrió')
  return panel
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
  })

  afterEach(() => {
    contenedor?.unmount()
    contenedor = null
    document.body.innerHTML = ''
  })

  it('carga las tareas al montar y las muestra en la tabla', async () => {
    const envoltorio = await montar()

    expect(clienteApi.obtener).toHaveBeenCalledWith('/tareas')
    const cabeceras = envoltorio.findAll('th').map((th) => th.text())
    expect(cabeceras).toEqual(['Nombre', 'Prioridad', 'Descripción'])
    const filas = envoltorio
      .findAll('tbody tr')
      .map((tr) => tr.findAll('td').map((td) => td.text()))
    expect(filas).toEqual([
      ['Escribir informe', '2', 'Informe trimestral'],
      ['Leer artículo', '—', 'Artículo sobre Vue'],
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
  })

  it('al guardar crea la tarea, cierra el panel y la muestra en la tabla', async () => {
    const envoltorio = await montar([])
    vi.mocked(clienteApi.crear).mockResolvedValue({
      id: 3,
      nombre: 'Nueva',
      prioridad: 1,
      descripcion: 'Detalle',
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
    })
    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    const filas = envoltorio
      .findAll('tbody tr')
      .map((tr) => tr.findAll('td').map((td) => td.text()))
    expect(filas).toEqual([['Nueva', '1', 'Detalle']])

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
    })
    const panel = await abrirPanel(envoltorio)

    await escribir(campo(panel, 'input[placeholder="Nombre"]'), 'Sin prioridad')
    await escribir(campo(panel, 'textarea[placeholder="Descripción"]'), 'Detalle')
    await enviar(panel)

    expect(clienteApi.crear).toHaveBeenCalledWith('/tareas', {
      nombre: 'Sin prioridad',
      prioridad: null,
      descripcion: 'Detalle',
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
