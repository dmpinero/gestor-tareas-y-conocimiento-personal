import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { clienteApi } from '@/api/cliente'
import type { Foco, TareaSiguiente } from '@/api/tipos'
import { useTiendaFoco } from '@/stores/foco'
import { useTiendaSiguientes } from '@/stores/siguientes'
import IndicadorFoco from '../IndicadorFoco.vue'

vi.mock('@/api/cliente', async (original) => ({
  ...(await original()),
  clienteApi: {
    obtener: vi.fn<(...args: unknown[]) => unknown>(),
    actualizar: vi.fn<(...args: unknown[]) => unknown>(),
    eliminar: vi.fn<(...args: unknown[]) => unknown>(),
  },
}))

const FOCO_TAREA: Foco = {
  tarea_id: 7,
  tarea_nombre: 'Migración portal',
  subtarea_id: null,
  subtarea_nombre: null,
  desde: '2026-11-24T10:00:00',
}

const COLA: TareaSiguiente[] = [
  { tarea_id: 1, tarea_nombre: 'Informe', subtarea_id: null, subtarea_nombre: null },
  { tarea_id: 2, tarea_nombre: 'Llamar', subtarea_id: null, subtarea_nombre: null },
  { tarea_id: 3, tarea_nombre: 'Revisar oferta', subtarea_id: null, subtarea_nombre: null },
  { tarea_id: 4, tarea_nombre: 'Cuarta', subtarea_id: null, subtarea_nombre: null },
]

const SUB_DE_INFORME: TareaSiguiente = {
  tarea_id: 1,
  tarea_nombre: 'Informe',
  subtarea_id: 10,
  subtarea_nombre: 'Redactar',
}

const FOCO_SUBTAREA: Foco = {
  ...FOCO_TAREA,
  subtarea_id: 70,
  subtarea_nombre: 'Probar login',
}

let envoltorio: VueWrapper | null = null
let router: Router

async function montar(foco: Foco | null, cola: TareaSiguiente[] = []): Promise<VueWrapper> {
  vi.mocked(clienteApi.obtener).mockImplementation(async (ruta) =>
    ruta === '/siguientes' ? cola : ruta === '/tareas' ? [] : foco,
  )
  const pinia = createPinia()
  setActivePinia(pinia)
  router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:ruta(.*)*', component: { render: () => null } }],
  })
  await router.push('/')
  envoltorio = mount(IndicadorFoco, {
    attachTo: document.body,
    global: { plugins: [pinia, router] },
  })
  await flushPromises()
  return envoltorio
}

// Arrastre nativo simulado: jsdom no trae DataTransfer.
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

async function arrastrar(origen: Element, destino: Element): Promise<void> {
  const dataTransfer = crearDataTransfer()
  lanzarEventoArrastre(origen, 'dragstart', dataTransfer)
  lanzarEventoArrastre(destino, 'dragover', dataTransfer)
  await flushPromises()
  lanzarEventoArrastre(destino, 'drop', dataTransfer)
  lanzarEventoArrastre(origen, 'dragend', dataTransfer)
  await flushPromises()
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] })
  vi.setSystemTime(new Date(2026, 10, 24, 11, 20, 0))
})

afterEach(() => {
  envoltorio?.unmount()
  envoltorio = null
  document.body.innerHTML = ''
  vi.useRealTimers()
})

describe('IndicadorFoco', () => {
  it('carga el foco con GET /foco al montarse', async () => {
    await montar(null)

    expect(clienteApi.obtener).toHaveBeenCalledWith('/foco')
  })

  it('sin foco no se muestra', async () => {
    const wrapper = await montar(null)

    expect(wrapper.find('[data-indicador-foco]').exists()).toBe(false)
  })

  it('con una tarea en foco muestra su nombre y el tiempo', async () => {
    const wrapper = await montar(FOCO_TAREA)

    expect(wrapper.get('[data-abrir-foco]').text()).toBe(
      'Trabajando en: Migración portal · 1 h 20 min',
    )
  })

  it('en pantallas estrechas oculta a la vista "Trabajando en:" para que quepa el nombre', async () => {
    const wrapper = await montar(FOCO_TAREA)

    const prefijo = wrapper.get('[data-prefijo-foco]')
    expect(prefijo.text()).toBe('Trabajando en:')
    expect(prefijo.classes()).toContain('max-sm:sr-only')
    expect(wrapper.get('[data-abrir-foco]').text()).toContain('Migración portal')
  })

  it('con una subtarea en foco muestra "Tarea › Subtarea"', async () => {
    const wrapper = await montar(FOCO_SUBTAREA)

    expect(wrapper.get('[data-abrir-foco]').text()).toBe(
      'Trabajando en: Migración portal › Probar login · 1 h 20 min',
    )
  })

  it('refresca el tiempo cada minuto', async () => {
    const wrapper = await montar(FOCO_TAREA)

    vi.advanceTimersByTime(60_000)
    await flushPromises()

    expect(wrapper.get('[data-abrir-foco]').text()).toContain('· 1 h 21 min')
  })

  it('al pulsarla abre la tarea en /tareas?tarea=<id>', async () => {
    const wrapper = await montar(FOCO_SUBTAREA)

    await wrapper.get('[data-abrir-foco]').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/tareas')
    expect(router.currentRoute.value.query).toEqual({ tarea: '7' })
  })

  it('el ✕ deja de trabajar: DELETE /foco y la píldora desaparece', async () => {
    vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)
    const wrapper = await montar(FOCO_TAREA)

    await wrapper.get('button[aria-label="Dejar de trabajar"]').trigger('click')
    await flushPromises()

    expect(clienteApi.eliminar).toHaveBeenCalledWith('/foco')
    expect(useTiendaFoco().foco).toBeNull()
    expect(wrapper.find('[data-indicador-foco]').exists()).toBe(false)
  })

  it('al desmontarse detiene el reloj', async () => {
    const wrapper = await montar(FOCO_TAREA)

    wrapper.unmount()
    envoltorio = null

    expect(vi.getTimerCount()).toBe(0)
  })

  it('carga la cola con GET /siguientes al montarse', async () => {
    await montar(null)

    expect(clienteApi.obtener).toHaveBeenCalledWith('/siguientes')
  })

  it('sin cola no ofrece el desplegable de siguientes', async () => {
    const wrapper = await montar(FOCO_TAREA)

    expect(wrapper.find('[data-siguientes]').exists()).toBe(false)
  })

  it('con cola, el desplegable «Siguientes» muestra las 3 primeras y «Pasar a la siguiente»', async () => {
    const wrapper = await montar(FOCO_TAREA, COLA)

    await wrapper.get('[data-siguientes]').trigger('click')
    await flushPromises()

    const contenido = document.body.querySelector('[data-slot="popover-content"]')!
    const nombres = [...contenido.querySelectorAll('[data-siguiente] [data-nombre-siguiente]')].map(
      (a) => a.textContent?.trim(),
    )
    expect(nombres).toEqual(['Informe', 'Llamar', 'Revisar oferta'])
    expect(contenido.querySelector('[data-pasar-siguiente]')?.textContent?.trim()).toBe(
      'Pasar a la siguiente: Informe',
    )
  })

  it('en el desplegable se reordenan las siguientes arrastrándolas', async () => {
    vi.mocked(clienteApi.actualizar).mockResolvedValue([COLA[1]!, COLA[0]!, ...COLA.slice(2)])
    const wrapper = await montar(FOCO_TAREA, COLA)
    await wrapper.get('[data-siguientes]').trigger('click')
    await flushPromises()
    const contenido = document.body.querySelector('[data-slot="popover-content"]')!
    const filas = [...contenido.querySelectorAll('[data-siguiente]')]
    expect(filas.every((fila) => fila.getAttribute('draggable') === 'true')).toBe(true)

    await arrastrar(filas[1]!, filas[0]!)

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/siguientes', {
      entradas: [COLA[1]!, COLA[0]!, ...COLA.slice(2)].map((e) => ({
        tarea_id: e.tarea_id,
        subtarea_id: null,
      })),
    })
    const nombres = [...contenido.querySelectorAll('[data-nombre-siguiente]')].map((n) =>
      n.textContent?.trim(),
    )
    expect(nombres.slice(0, 2)).toEqual(['Llamar', 'Informe'])
  })

  it('desde el desplegable se abre el buscador para añadir a siguientes', async () => {
    const wrapper = await montar(FOCO_TAREA, COLA)
    await wrapper.get('[data-siguientes]').trigger('click')
    await flushPromises()

    document.body.querySelector<HTMLButtonElement>('[data-buscar-siguientes]')!.click()
    await flushPromises()

    expect(document.body.querySelector('[data-slot="popover-content"]')).toBeNull()
    expect(document.body.querySelector('[role="dialog"] h2')?.textContent?.trim()).toBe(
      'Añadir a siguientes',
    )
  })

  it('sin foco pero con cola se muestra el acceso «Pasar a la siguiente»', async () => {
    const wrapper = await montar(null, COLA)

    expect(wrapper.find('[data-indicador-foco]').exists()).toBe(false)
    expect(wrapper.find('[data-siguientes]').exists()).toBe(true)
  })

  it('«Pasar a la siguiente» fija el foco en la primera y recarga la cola', async () => {
    vi.mocked(clienteApi.actualizar).mockResolvedValue({
      ...FOCO_TAREA,
      tarea_id: 1,
      tarea_nombre: 'Informe',
    })
    const wrapper = await montar(FOCO_TAREA, COLA)
    await wrapper.get('[data-siguientes]').trigger('click')
    await flushPromises()
    vi.mocked(clienteApi.obtener).mockResolvedValue(COLA.slice(1))

    document.body.querySelector<HTMLButtonElement>('[data-pasar-siguiente]')!.click()
    await flushPromises()

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/foco', { tarea_id: 1, subtarea_id: null })
    expect(useTiendaFoco().foco?.tarea_nombre).toBe('Informe')
    expect(useTiendaSiguientes().cola.map((t) => t.tarea_id)).toEqual([2, 3, 4])
  })

  it('con una subtarea en la cola la muestra como «Tarea › Subtarea» y «Pasar a la siguiente» la pone en foco', async () => {
    const SUB: TareaSiguiente = {
      tarea_id: 7,
      tarea_nombre: 'Migración portal',
      subtarea_id: 70,
      subtarea_nombre: 'Probar login',
    }
    vi.mocked(clienteApi.actualizar).mockResolvedValue(FOCO_SUBTAREA)
    const wrapper = await montar(null, [SUB, COLA[0]!, SUB_DE_INFORME])
    await wrapper.get('[data-siguientes]').trigger('click')
    await flushPromises()

    const contenido = document.body.querySelector('[data-slot="popover-content"]')!
    const nombres = [...contenido.querySelectorAll('[data-nombre-siguiente]')].map((n) =>
      n.textContent?.trim(),
    )
    expect(nombres).toEqual(['Migración portal › Probar login', 'Informe', 'Informe › Redactar'])
    expect(contenido.querySelector('[data-pasar-siguiente]')?.textContent?.trim()).toBe(
      'Pasar a la siguiente: Migración portal › Probar login',
    )

    vi.mocked(clienteApi.obtener).mockResolvedValue([COLA[0]!])
    contenido.querySelector<HTMLButtonElement>('[data-pasar-siguiente]')!.click()
    await flushPromises()
    expect(clienteApi.actualizar).toHaveBeenCalledWith('/foco', { tarea_id: 7, subtarea_id: 70 })
  })

  it('arrastrar una subtarea en el desplegable envía su entrada', async () => {
    const cola = [COLA[0]!, SUB_DE_INFORME]
    vi.mocked(clienteApi.actualizar).mockResolvedValue([SUB_DE_INFORME, COLA[0]!])
    const wrapper = await montar(FOCO_TAREA, cola)
    await wrapper.get('[data-siguientes]').trigger('click')
    await flushPromises()
    const filas = [...document.body.querySelectorAll('[data-siguiente]')]

    await arrastrar(filas[1]!, filas[0]!)

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/siguientes', {
      entradas: [
        { tarea_id: 1, subtarea_id: 10 },
        { tarea_id: 1, subtarea_id: null },
      ],
    })
  })
})
