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
