import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter, RouterView, type Router } from 'vue-router'

import { clienteApi, ErrorApi } from '@/api/cliente'
import type { CambiosDeLasTareas, Workflow } from '@/api/tipos'
import VistaWorkflows from '../VistaWorkflows.vue'

vi.mock('@/api/cliente', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('@/api/cliente')>()
  return {
    ...original,
    clienteApi: {
      obtener: vi.fn<(...args: unknown[]) => unknown>(),
      crear: vi.fn<(...args: unknown[]) => unknown>(),
      actualizar: vi.fn<(...args: unknown[]) => unknown>(),
      eliminar: vi.fn<(...args: unknown[]) => unknown>(),
    },
  }
})

const OPORTUNIDADES: Workflow = {
  id: 1,
  nombre: 'Workflow Oportunidades',
  pasos: [
    { id: 10, numero: 1, nombre: 'Contacto inicial', comentarios: 0 },
    { id: 11, numero: 2, nombre: 'Propuesta', comentarios: 0 },
  ],
}
const CON_PASO_NUEVO: Workflow = {
  ...OPORTUNIDADES,
  pasos: [
    ...OPORTUNIDADES.pasos,
    { id: 12, numero: 3, nombre: 'Crear oferta técnica', comentarios: 0 },
  ],
}
const SINCRONIZACION = '/workflows/1/sincronizacion'

const PENDIENTES: CambiosDeLasTareas = {
  tareas: [
    {
      id: 11,
      nombre: 'Oportunidad A',
      subtareas_a_anadir: ['Crear oferta técnica'],
      subtareas_a_renombrar: [
        { id: 5, nombre_actual: 'Contacto', nombre_nuevo: 'Contacto inicial' },
      ],
    },
    {
      id: 12,
      nombre: 'Oportunidad B',
      subtareas_a_anadir: ['Crear oferta técnica'],
      subtareas_a_renombrar: [],
    },
  ],
}

let contenedor: VueWrapper | undefined
let enrutador: Router

// La vista se monta dentro de un RouterView, como en la aplicación: así se
// registra su guarda de salida.
async function montar(pendientes: CambiosDeLasTareas): Promise<VueWrapper> {
  vi.mocked(clienteApi.obtener).mockImplementation(async (ruta: unknown) =>
    ruta === SINCRONIZACION ? structuredClone(pendientes) : [structuredClone(OPORTUNIDADES)],
  )
  enrutador = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/ajustes', component: { render: () => h('p', 'Ajustes') } },
      { path: '/tareas', component: { render: () => h('p', 'Tareas') } },
      { path: '/ajustes/workflows', component: VistaWorkflows },
    ],
  })
  await enrutador.push('/ajustes/workflows')
  const raiz = defineComponent({ render: () => h(RouterView) })
  contenedor = mount(raiz, {
    global: { plugins: [createPinia(), enrutador] },
    attachTo: document.body,
  })
  await flushPromises()
  return contenedor
}

async function anadirPaso(vista: VueWrapper): Promise<void> {
  vi.mocked(clienteApi.crear).mockResolvedValueOnce(structuredClone(CON_PASO_NUEVO))
  await vista
    .get('input[aria-label="Nuevo paso de Workflow Oportunidades"]')
    .setValue('Crear oferta técnica')
  await vista.get('form[aria-label="Añadir paso a Workflow Oportunidades"]').trigger('submit')
  await flushPromises()
}

async function pulsarVolver(vista: VueWrapper): Promise<void> {
  await vista.get('a[href="/ajustes"]').trigger('click')
  await flushPromises()
}

function dialogo(): HTMLElement | null {
  return document.body.querySelector<HTMLElement>('[role="alertdialog"]')
}

async function pulsarEnDialogo(texto: string): Promise<void> {
  const encontrado = [...(dialogo()?.querySelectorAll('button') ?? [])].find(
    (b) => b.textContent?.trim() === texto,
  )
  if (!encontrado) throw new Error(`No se encontró el botón "${texto}"`)
  encontrado.click()
  await flushPromises()
}

function llamadasDeSincronizacion(): unknown[][] {
  return vi.mocked(clienteApi.crear).mock.calls.filter(([ruta]) => ruta === SINCRONIZACION)
}

describe('VistaWorkflows: actualizar las tareas al salir', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    contenedor?.unmount()
    contenedor = undefined
    document.body.innerHTML = ''
  })

  it('sin editar ningún paso sale sin preguntar ni consultar', async () => {
    const vista = await montar(PENDIENTES)

    await pulsarVolver(vista)

    expect(enrutador.currentRoute.value.path).toBe('/ajustes')
    expect(dialogo()).toBeNull()
    expect(clienteApi.obtener).not.toHaveBeenCalledWith(SINCRONIZACION)
  })

  it('si ninguna tarea cambiaría, sale sin preguntar', async () => {
    const vista = await montar({ tareas: [] })
    await anadirPaso(vista)

    await pulsarVolver(vista)

    expect(clienteApi.obtener).toHaveBeenCalledWith(SINCRONIZACION)
    expect(enrutador.currentRoute.value.path).toBe('/ajustes')
    expect(dialogo()).toBeNull()
  })

  it('pregunta antes de salir y dice qué workflow, cuántas tareas y qué cambia', async () => {
    const vista = await montar(PENDIENTES)
    await anadirPaso(vista)

    await pulsarVolver(vista)

    expect(enrutador.currentRoute.value.path).toBe('/ajustes/workflows')
    expect(dialogo()?.textContent).toContain('¿Actualizar las tareas existentes?')
    expect(dialogo()?.querySelector('li')?.textContent).toBe(
      'Workflow Oportunidades: 2 tareas (2 subtareas nuevas y 1 subtarea renombrada)',
    )
    expect(llamadasDeSincronizacion()).toHaveLength(0)
  })

  it('pregunta también al salir por otra navegación', async () => {
    const vista = await montar(PENDIENTES)
    await anadirPaso(vista)

    await enrutador.push('/tareas')
    await flushPromises()

    expect(enrutador.currentRoute.value.path).toBe('/ajustes/workflows')
    expect(dialogo()).not.toBeNull()
  })

  it('"Actualizar tareas" aplica los cambios y después sale al destino', async () => {
    const vista = await montar(PENDIENTES)
    await anadirPaso(vista)
    await enrutador.push('/tareas')
    await flushPromises()
    vi.mocked(clienteApi.crear).mockResolvedValueOnce(structuredClone(PENDIENTES))

    await pulsarEnDialogo('Actualizar tareas')

    expect(llamadasDeSincronizacion()).toEqual([[SINCRONIZACION, undefined]])
    expect(enrutador.currentRoute.value.path).toBe('/tareas')
    expect(vista.text()).toContain('Tareas')
  })

  it('si la actualización falla, muestra el error y no sale', async () => {
    const vista = await montar(PENDIENTES)
    await anadirPaso(vista)
    await pulsarVolver(vista)
    vi.mocked(clienteApi.crear).mockRejectedValueOnce(new ErrorApi(500, 'Fallo del servidor'))

    await pulsarEnDialogo('Actualizar tareas')

    expect(dialogo()?.querySelector('[role="alert"]')?.textContent).toBe('Fallo del servidor')
    expect(enrutador.currentRoute.value.path).toBe('/ajustes/workflows')
  })

  it('"Salir sin actualizar" sale sin cambiar ninguna tarea', async () => {
    const vista = await montar(PENDIENTES)
    await anadirPaso(vista)
    await pulsarVolver(vista)

    await pulsarEnDialogo('Salir sin actualizar')

    expect(llamadasDeSincronizacion()).toHaveLength(0)
    expect(enrutador.currentRoute.value.path).toBe('/ajustes')
  })

  it('"Cancelar" se queda en la página sin cambiar nada', async () => {
    const vista = await montar(PENDIENTES)
    await anadirPaso(vista)
    await pulsarVolver(vista)

    await pulsarEnDialogo('Cancelar')

    expect(dialogo()).toBeNull()
    expect(llamadasDeSincronizacion()).toHaveLength(0)
    expect(enrutador.currentRoute.value.path).toBe('/ajustes/workflows')
  })
})
