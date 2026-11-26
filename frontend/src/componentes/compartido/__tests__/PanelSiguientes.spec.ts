import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { clienteApi } from '@/api/cliente'
import type { Foco, Tarea, TareaSiguiente } from '@/api/tipos'
import { useTiendaFoco } from '@/stores/foco'
import PanelSiguientes from '../PanelSiguientes.vue'

vi.mock('@/api/cliente', async (original) => ({
  ...(await original()),
  clienteApi: {
    obtener: vi.fn<(...args: unknown[]) => unknown>(),
    crear: vi.fn<(...args: unknown[]) => unknown>(),
    actualizar: vi.fn<(...args: unknown[]) => unknown>(),
    eliminar: vi.fn<(...args: unknown[]) => unknown>(),
  },
}))

function tarea(id: number, nombre: string, extra: Partial<Tarea> = {}): Tarea {
  return {
    id,
    nombre,
    prioridad: null,
    descripcion: '',
    fecha_creacion: '2026-11-10T09:00:00',
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
    subestado: null,
    congelada_en: null,
    hibernada_desde: null,
    vinculadas: [],
    ...extra,
  }
}

const TAREAS = [
  tarea(1, 'Informe'),
  tarea(2, 'Llamar'),
  tarea(3, 'Revisar oferta', { fecha_vencimiento: '2026-11-27T10:00:00' }),
  tarea(4, 'Hecha', { completada: true }),
]

const sig = (t: Tarea): TareaSiguiente => ({ tarea_id: t.id, tarea_nombre: t.nombre })

let envoltorio: VueWrapper | null = null
let router: Router

async function montar(
  cola: TareaSiguiente[],
  tareas: Tarea[] = TAREAS,
  foco: Foco | null = null,
): Promise<VueWrapper> {
  vi.mocked(clienteApi.obtener).mockImplementation(async (ruta) => {
    if (ruta === '/siguientes') return cola
    if (ruta === '/tareas') return tareas
    return null
  })
  const pinia = createPinia()
  setActivePinia(pinia)
  useTiendaFoco().foco = foco
  router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:ruta(.*)*', component: { render: () => null } }],
  })
  await router.push('/')
  envoltorio = mount(PanelSiguientes, { global: { plugins: [pinia, router] } })
  await flushPromises()
  return envoltorio
}

const filas = (w: VueWrapper) => w.findAll('[data-fila-siguiente]').map((f) => f.get('a').text())
const sugerencias = (w: VueWrapper) => w.findAll('[data-sugerencia]').map((f) => f.get('a').text())

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

beforeEach(() => vi.clearAllMocks())
afterEach(() => {
  envoltorio?.unmount()
  envoltorio = null
})

describe('PanelSiguientes', () => {
  it('se titula «A continuación» y carga la cola y las tareas al montarse', async () => {
    const wrapper = await montar([])

    expect(wrapper.get('h3').text()).toBe('A continuación')
    expect(clienteApi.obtener).toHaveBeenCalledWith('/siguientes')
    expect(clienteApi.obtener).toHaveBeenCalledWith('/tareas')
  })

  it('con la cola vacía dice «No hay tareas en la cola.»', async () => {
    const wrapper = await montar([])

    expect(wrapper.text()).toContain('No hay tareas en la cola.')
    expect(wrapper.findAll('[data-fila-siguiente]')).toHaveLength(0)
  })

  it('muestra la cola en orden y el nombre abre la tarea', async () => {
    const wrapper = await montar([sig(TAREAS[1]!), sig(TAREAS[0]!)])

    expect(filas(wrapper)).toEqual(['Llamar', 'Informe'])
    await wrapper.get('[data-fila-siguiente] a').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/tareas')
    expect(router.currentRoute.value.query).toEqual({ tarea: '2' })
  })

  it('cada tarea de la cola muestra su contador, o «Sin vencimiento», y su prioridad', async () => {
    const tareas = [tarea(1, 'Informe', { prioridad: 2 }), TAREAS[2]!]
    const wrapper = await montar([sig(tareas[1]!), sig(tareas[0]!)], tareas)

    const [conVencimiento, sinVencimiento] = wrapper.findAll('[data-fila-siguiente]')
    expect(conVencimiento!.find('[role="timer"]').exists()).toBe(true)
    expect(conVencimiento!.find('[data-prioridad-sugerencia]').exists()).toBe(false)
    expect(sinVencimiento!.find('[role="timer"]').exists()).toBe(false)
    expect(sinVencimiento!.get('[data-sin-vencimiento]').text()).toBe('Sin vencimiento')
    expect(sinVencimiento!.get('[data-prioridad-sugerencia]').text()).toBe('Prioridad 2')
  })

  it('explica el criterio de la cola', async () => {
    const wrapper = await montar([])

    expect(wrapper.get('[data-criterio-cola]').text()).toBe(
      'Las tareas que has elegido, en el orden en que quieres abordarlas: añádelas con «Añadir a siguientes» y ordénalas arrastrándolas o con las flechas. Al ponerlas en foco salen de la cola.',
    )
  })

  it('subir y bajar reordenan con PUT /siguientes; los extremos están desactivados', async () => {
    const cola = [sig(TAREAS[0]!), sig(TAREAS[1]!)]
    vi.mocked(clienteApi.actualizar).mockResolvedValue([cola[1], cola[0]])
    const wrapper = await montar(cola)

    expect(wrapper.get('button[aria-label="Subir Informe"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('button[aria-label="Bajar Llamar"]').attributes('disabled')).toBeDefined()

    await wrapper.get('button[aria-label="Subir Llamar"]').trigger('click')
    await flushPromises()

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/siguientes', { ids: [2, 1] })
    expect(filas(wrapper)).toEqual(['Llamar', 'Informe'])
  })

  it('arrastrar una tarea de la cola sobre otra la lleva a su posición', async () => {
    const cola = [sig(TAREAS[0]!), sig(TAREAS[1]!), sig(TAREAS[2]!)]
    vi.mocked(clienteApi.actualizar).mockResolvedValue([cola[2]!, cola[0]!, cola[1]!])
    const wrapper = await montar(cola)
    const filasCola = wrapper.findAll('[data-fila-siguiente]')
    expect(filasCola.every((fila) => fila.attributes('draggable') === 'true')).toBe(true)

    await arrastrar(filasCola[2]!.element, filasCola[0]!.element)

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/siguientes', { ids: [3, 1, 2] })
    expect(filas(wrapper)).toEqual(['Revisar oferta', 'Informe', 'Llamar'])
  })

  it('mientras se arrastra marca dónde quedará la tarea', async () => {
    const cola = [sig(TAREAS[0]!), sig(TAREAS[1]!), sig(TAREAS[2]!)]
    const wrapper = await montar(cola)
    const filasCola = wrapper.findAll('[data-fila-siguiente]')
    const dataTransfer = crearDataTransfer()

    lanzarEventoArrastre(filasCola[0]!.element, 'dragstart', dataTransfer)
    lanzarEventoArrastre(filasCola[2]!.element, 'dragover', dataTransfer)
    await flushPromises()

    expect(filasCola[2]!.attributes('data-destino')).toBe('despues')
    expect(filasCola[0]!.attributes('data-arrastrada')).toBe('true')
    lanzarEventoArrastre(filasCola[0]!.element, 'dragend', dataTransfer)
    await flushPromises()
    expect(filasCola[2]!.attributes('data-destino')).toBeUndefined()
    expect(clienteApi.actualizar).not.toHaveBeenCalled()
  })

  it('bajar mueve la tarea una posición hacia abajo', async () => {
    const cola = [sig(TAREAS[0]!), sig(TAREAS[1]!)]
    vi.mocked(clienteApi.actualizar).mockResolvedValue([cola[1], cola[0]])
    const wrapper = await montar(cola)

    await wrapper.get('button[aria-label="Bajar Informe"]').trigger('click')
    await flushPromises()

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/siguientes', { ids: [2, 1] })
  })

  it('quitar la saca de la cola con DELETE /siguientes/{id}', async () => {
    vi.mocked(clienteApi.eliminar).mockResolvedValue([])
    const wrapper = await montar([sig(TAREAS[0]!)])

    await wrapper.get('button[aria-label="Quitar Informe de siguientes"]').trigger('click')
    await flushPromises()

    expect(clienteApi.eliminar).toHaveBeenCalledWith('/siguientes/1')
    expect(wrapper.text()).toContain('No hay tareas en la cola.')
  })

  it('«Trabajar en esta» pone la tarea en foco y la saca de la cola', async () => {
    vi.mocked(clienteApi.actualizar).mockResolvedValue({
      tarea_id: 1,
      tarea_nombre: 'Informe',
      subtarea_id: null,
      subtarea_nombre: null,
      desde: '2026-11-26T10:00:00',
    })
    const wrapper = await montar([sig(TAREAS[0]!), sig(TAREAS[1]!)])

    await wrapper
      .get('[data-fila-siguiente] button[aria-label="Trabajar en esta (Informe)"]')
      .trigger('click')
    await flushPromises()

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/foco', { tarea_id: 1, subtarea_id: null })
    expect(useTiendaFoco().foco?.tarea_id).toBe(1)
    expect(filas(wrapper)).toEqual(['Llamar'])
  })

  it('las sugerencias excluyen la cola, las completadas y el foco, ordenadas por S5', async () => {
    const foco: Foco = {
      tarea_id: 2,
      tarea_nombre: 'Llamar',
      subtarea_id: null,
      subtarea_nombre: null,
      desde: '2026-11-26T10:00:00',
    }
    const wrapper = await montar([], TAREAS, foco)

    expect(wrapper.get('h4').text()).toBe('Sugerencias')
    expect(sugerencias(wrapper)).toEqual(['Revisar oferta', 'Informe'])
  })

  it('cada sugerencia muestra el contador hasta su vencimiento, o «Sin vencimiento»', async () => {
    const wrapper = await montar([])

    const [conVencimiento, sinVencimiento] = wrapper.findAll('[data-sugerencia]')
    expect(conVencimiento!.get('a').text()).toBe('Revisar oferta')
    const contador = conVencimiento!.get('[role="timer"][data-testid="contador-vencimiento"]')
    expect(contador.get('[data-testid="contador-texto"]').text()).not.toBe('')
    expect(sinVencimiento!.get('a').text()).toBe('Informe')
    expect(sinVencimiento!.find('[role="timer"]').exists()).toBe(false)
    expect(sinVencimiento!.get('[data-sin-vencimiento]').text()).toBe('Sin vencimiento')
  })

  it('cada sugerencia muestra su prioridad, si la tiene', async () => {
    const wrapper = await montar(
      [],
      [tarea(1, 'Urgente', { prioridad: 1 }), tarea(2, 'Sin prioridad')],
    )

    const [conPrioridad, sinPrioridad] = wrapper.findAll('[data-sugerencia]')
    expect(conPrioridad!.get('[data-prioridad-sugerencia]').text()).toBe('Prioridad 1')
    expect(sinPrioridad!.find('[data-prioridad-sugerencia]').exists()).toBe(false)
  })

  it('explica el criterio de las sugerencias', async () => {
    const wrapper = await montar([])

    expect(wrapper.get('[data-criterio-sugerencias]').text()).toBe(
      'Tareas pendientes que vencen antes; a igual vencimiento, por prioridad y después por antigüedad. No incluye las hibernadas, las que están en DONE, las de la cola ni la que está en foco.',
    )
  })

  it('«Añadir a siguientes» en una sugerencia la sube al final de la cola', async () => {
    const cola = [sig(TAREAS[0]!)]
    vi.mocked(clienteApi.crear).mockResolvedValue([...cola, sig(TAREAS[2]!)])
    const wrapper = await montar(cola)

    await wrapper
      .get('[data-sugerencia] button[aria-label="Añadir a siguientes (Revisar oferta)"]')
      .trigger('click')
    await flushPromises()

    expect(clienteApi.crear).toHaveBeenCalledWith('/siguientes', { tarea_id: 3 })
    expect(filas(wrapper)).toEqual(['Informe', 'Revisar oferta'])
    expect(sugerencias(wrapper)).toEqual(['Llamar'])
  })

  it('sin sugerencias dice «No hay sugerencias.»', async () => {
    const wrapper = await montar([], [tarea(4, 'Hecha', { completada: true })])

    expect(wrapper.text()).toContain('No hay sugerencias.')
  })

  it('muestra el error de la cola', async () => {
    vi.mocked(clienteApi.eliminar).mockRejectedValue(new Error('caído'))
    const wrapper = await montar([sig(TAREAS[0]!)])

    await wrapper.get('button[aria-label="Quitar Informe de siguientes"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe('caído')
  })
})
