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
  // Copia para que los tests que editan no alteren los datos compartidos.
  vi.mocked(clienteApi.obtener).mockResolvedValue(structuredClone(tareas))
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

  describe('ordenación', () => {
    const TAREAS_ORDEN = [
      { id: 1, nombre: 'beta', prioridad: 3, descripcion: 'b', fecha_hora: '2026-05-01T10:00:00' },
      {
        id: 2,
        nombre: 'Árbol',
        prioridad: null,
        descripcion: 'c',
        fecha_hora: '2026-01-01T10:00:00',
      },
      { id: 3, nombre: 'casa', prioridad: 1, descripcion: 'a', fecha_hora: '2026-12-31T23:59:59' },
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
      for (const etiqueta of ['Nombre', 'Prioridad', 'Descripción', 'Fecha y hora']) {
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

    it('ordena por descripción y por fecha y hora', async () => {
      const envoltorio = await montar(TAREAS_ORDEN)

      await cabecera(envoltorio, 'Descripción').trigger('click')
      expect(nombresEnTabla(envoltorio)).toEqual(['casa', 'beta', 'Árbol'])

      await cabecera(envoltorio, 'Fecha y hora').trigger('click')
      expect(nombresEnTabla(envoltorio)).toEqual(['Árbol', 'beta', 'casa'])
      await cabecera(envoltorio, 'Fecha y hora').trigger('click')
      expect(nombresEnTabla(envoltorio)).toEqual(['casa', 'beta', 'Árbol'])
    })
  })

  describe('exportación', () => {
    const COLUMNAS = ['Nombre', 'Prioridad', 'Descripción', 'Fecha y hora']

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
        ['Escribir informe', 2, 'Informe trimestral', '10/11/2026 09:30:00'],
        ['Leer artículo', '—', 'Artículo sobre Vue', '01/12/2026 17:05:09'],
      ])
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
