import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

import { clienteApi } from '@/api/cliente'
import type { Tarea, TareaSiguiente } from '@/api/tipos'
import { useTiendaSiguientes } from '@/stores/siguientes'
import { useTiendaTareas } from '@/stores/tareas'
import SelectorTareasSiguientes from '../SelectorTareasSiguientes.vue'

vi.mock('@/api/cliente', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('@/api/cliente')>()
  return {
    ...original,
    clienteApi: {
      obtener: vi.fn<(...args: unknown[]) => unknown>(),
      crear: vi.fn<(...args: unknown[]) => unknown>(),
      actualizar: vi.fn<(...args: unknown[]) => unknown>(),
      parchear: vi.fn<(...args: unknown[]) => unknown>(),
      eliminar: vi.fn<(...args: unknown[]) => unknown>(),
    },
  }
})

function tarea(id: number, nombre: string, cambios: Partial<Tarea> = {}): Tarea {
  return {
    id,
    nombre,
    prioridad: null,
    descripcion: '',
    fecha_creacion: '2026-11-20T10:00:00',
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
    ...cambios,
  }
}

const TAREAS = [
  tarea(1, 'En la cola'),
  tarea(2, 'Hecha', { completada: true }),
  tarea(3, 'Revisión técnica'),
  tarea(4, 'Diseño de pantallas'),
  tarea(5, 'Revisar presupuesto'),
  tarea(6, 'Elegida antes'),
]
const sig = (t: Tarea): TareaSiguiente => ({ tarea_id: t.id, tarea_nombre: t.nombre })

let envoltorio: VueWrapper | null = null
const abierto = ref(false)

async function montar(tareas: Tarea[] | null = TAREAS): Promise<void> {
  const pinia = createPinia()
  setActivePinia(pinia)
  if (tareas) useTiendaTareas().tareas = structuredClone(tareas)
  useTiendaSiguientes().cola = [sig(TAREAS[0]!)]
  useTiendaSiguientes().elegidas = [sig(TAREAS[5]!)]
  abierto.value = false
  envoltorio = mount(
    {
      components: { SelectorTareasSiguientes },
      setup: () => ({ abierto }),
      template: `<SelectorTareasSiguientes v-model:abierto="abierto" />`,
    },
    { global: { plugins: [pinia] }, attachTo: document.body },
  )
  abierto.value = true
  await flushPromises()
}

function dialogo(): HTMLElement | null {
  return document.body.querySelector('[role="dialog"]')
}

function casillas(): HTMLInputElement[] {
  return [...(dialogo()?.querySelectorAll<HTMLInputElement>('input[type="checkbox"]') ?? [])]
}

function nombresCasillas(): string[] {
  return casillas().map(
    (c) => c.closest('label')?.querySelector('[data-nombre-eleccion]')?.textContent?.trim() ?? '',
  )
}

function botonPorTexto(texto: string): HTMLButtonElement {
  const boton = [...document.body.querySelectorAll('button')].find(
    (b) => b.textContent?.trim() === texto,
  )
  if (!boton) throw new Error(`No hay botón «${texto}»`)
  return boton
}

async function buscar(texto: string): Promise<void> {
  const campo = dialogo()!.querySelector<HTMLInputElement>('input[type="search"]')!
  campo.value = texto
  campo.dispatchEvent(new Event('input'))
  await flushPromises()
}

async function marcar(nombre: string): Promise<void> {
  casillas()
    .find(
      (c) =>
        c.closest('label')?.querySelector('[data-nombre-eleccion]')?.textContent?.trim() === nombre,
    )!
    .click()
  await flushPromises()
}

beforeEach(() => vi.clearAllMocks())

afterEach(() => {
  envoltorio?.unmount()
  envoltorio = null
  document.body.innerHTML = ''
})

describe('SelectorTareasSiguientes', () => {
  it('se titula «Añadir a siguientes» y ofrece las pendientes por nombre, marcando dónde están ya', async () => {
    await montar()

    expect(dialogo()!.querySelector('h2')?.textContent?.trim()).toBe('Añadir a siguientes')
    expect(dialogo()!.querySelector('[role="group"]')?.getAttribute('aria-label')).toBe(
      'Tareas que se pueden añadir',
    )
    expect(nombresCasillas()).toEqual([
      'Diseño de pantallas',
      'Elegida antes',
      'En la cola',
      'Revisar presupuesto',
      'Revisión técnica',
    ])
    const notas = [...dialogo()!.querySelectorAll('[data-nota-eleccion]')].map((n) =>
      n.textContent?.trim(),
    )
    expect(notas).toEqual(['En sugerencias', 'En A continuación'])
  })

  it('tiene dos acciones, «A continuación» y «Sugerencias», que cuentan solo las que no están ya en su lista', async () => {
    await montar()
    expect(botonPorTexto('A continuación').disabled).toBe(true)
    expect(botonPorTexto('Sugerencias').disabled).toBe(true)

    await marcar('En la cola')
    expect(botonPorTexto('A continuación').disabled).toBe(true)
    expect(botonPorTexto('Sugerencias (1)').disabled).toBe(false)

    await marcar('Elegida antes')
    expect(botonPorTexto('A continuación (1)').disabled).toBe(false)
    expect(botonPorTexto('Sugerencias (1)').disabled).toBe(false)

    await marcar('Revisión técnica')
    expect(botonPorTexto('A continuación (2)').dataset.accionEleccion).toBe('siguientes')
    expect(botonPorTexto('Sugerencias (2)').dataset.accionEleccion).toBe('sugerencias')
  })

  it('«Sugerencias (n)» las añade a las elegidas en el orden en que se marcaron y se cierra', async () => {
    vi.mocked(clienteApi.crear)
      .mockResolvedValueOnce([sig(TAREAS[5]!), sig(TAREAS[4]!)])
      .mockResolvedValueOnce([sig(TAREAS[5]!), sig(TAREAS[4]!), sig(TAREAS[0]!)])
    await montar()

    await marcar('Revisar presupuesto')
    await marcar('Elegida antes')
    await marcar('En la cola')
    botonPorTexto('Sugerencias (2)').click()
    await flushPromises()

    expect(vi.mocked(clienteApi.crear).mock.calls).toEqual([
      ['/sugerencias', { tarea_id: 5 }],
      ['/sugerencias', { tarea_id: 1 }],
    ])
    expect(useTiendaSiguientes().cola).toEqual([])
    expect(dialogo()).toBeNull()
    expect(abierto.value).toBe(false)
  })

  it('filtra por el texto buscado sin distinguir mayúsculas ni acentos', async () => {
    await montar()

    await buscar('REVISION')
    expect(nombresCasillas()).toEqual(['Revisión técnica'])
    await buscar('zzz')
    expect(dialogo()!.textContent).toContain('No hay tareas que coincidan con la búsqueda.')
  })

  it('añade las marcadas al final de la cola, en el orden en que se marcaron, y se cierra', async () => {
    vi.mocked(clienteApi.crear)
      .mockResolvedValueOnce([sig(TAREAS[0]!), sig(TAREAS[4]!)])
      .mockResolvedValueOnce([sig(TAREAS[0]!), sig(TAREAS[4]!), sig(TAREAS[3]!)])
    await montar()

    await marcar('Revisar presupuesto')
    await marcar('Diseño de pantallas')
    botonPorTexto('A continuación (2)').click()
    await flushPromises()

    expect(vi.mocked(clienteApi.crear).mock.calls).toEqual([
      ['/siguientes', { tarea_id: 5 }],
      ['/siguientes', { tarea_id: 4 }],
    ])
    expect(dialogo()).toBeNull()
    expect(abierto.value).toBe(false)
  })

  it.each(['A continuación (1)', 'Sugerencias (1)'])(
    'si la API falla, «%s» lo deja abierto con el error',
    async (texto) => {
      vi.mocked(clienteApi.crear).mockRejectedValue(new Error('La tarea está completada'))
      await montar()
      await marcar('Revisión técnica')

      botonPorTexto(texto).click()
      await flushPromises()

      expect(dialogo()).not.toBeNull()
      expect(dialogo()!.querySelector('[role="alert"]')?.textContent).toBe(
        'La tarea está completada',
      )
    },
  )

  it('sin tareas cargadas las pide al abrirse', async () => {
    vi.mocked(clienteApi.obtener).mockResolvedValue(structuredClone(TAREAS))
    await montar(null)

    expect(clienteApi.obtener).toHaveBeenCalledWith('/tareas')
    expect(nombresCasillas()).toHaveLength(5)
  })
})
