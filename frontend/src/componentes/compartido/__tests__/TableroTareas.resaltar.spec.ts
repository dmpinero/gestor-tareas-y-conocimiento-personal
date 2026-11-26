import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import type { GrupoEstados, Subtarea, Tarea } from '@/api/tipos'
import { useTiendaTareas } from '@/stores/tareas'
import TableroTareas from '../TableroTareas.vue'

vi.mock('@/api/cliente', () => ({
  clienteApi: {
    obtener: vi.fn<(...args: unknown[]) => unknown>(),
    crear: vi.fn<(...args: unknown[]) => unknown>(),
    actualizar: vi.fn<(...args: unknown[]) => unknown>(),
    parchear: vi.fn<(...args: unknown[]) => unknown>(),
    eliminar: vi.fn<(...args: unknown[]) => unknown>(),
  },
}))

const GRUPO: GrupoEstados = {
  id: 1,
  nombre: 'Desarrollo',
  tareas: 3,
  estados: [{ id: 10, nombre: 'Pendiente', posicion: 1, tareas: 3 }],
}

function subtarea(id: number, nombre: string, asignado: string | null): Subtarea {
  return { id, nombre, asignado, prioridad: null, resuelta: false, comentarios: 0 }
}

function tarea(id: number, nombre: string, asignados: string[], subtareas: Subtarea[]): Tarea {
  return {
    id,
    nombre,
    prioridad: null,
    descripcion: '',
    fecha_creacion: '2026-11-10T09:00:00',
    fecha_vencimiento: null,
    etiquetas: [],
    asignados,
    tipo: null,
    oportunidad: null,
    completada: false,
    subtareas,
    grupo_estados: { id: 1, nombre: 'Desarrollo' },
    estado: { id: 10, nombre: 'Pendiente' },
    workflow: null,
    vinculadas: [],
    subestado: null,
    congelada_en: null,
    hibernada_desde: null,
  }
}

const PROPIA = tarea(1, 'Propia de José', ['José Manuel Viega'], [subtarea(10, 'Otra cosa', 'Ana')])
const CON_SUBTAREA = tarea(
  2,
  'Con subtarea de José',
  ['Ana'],
  [subtarea(20, 'Revisar oferta', 'José Manuel Viega'), subtarea(21, 'Llamar', 'Ana')],
)
const AJENA = tarea(3, 'Ajena', ['Ana'], [subtarea(30, 'Preparar', null)])
const TAREAS = [PROPIA, CON_SUBTAREA, AJENA]

let envoltorio: VueWrapper | null = null
const personas = ref<string[]>([])

async function montar(personasResaltadas: string[]): Promise<VueWrapper> {
  const pinia = createPinia()
  setActivePinia(pinia)
  const tienda = useTiendaTareas()
  tienda.tareas = JSON.parse(JSON.stringify(TAREAS)) as Tarea[]
  personas.value = personasResaltadas
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:ruta(.*)*', component: { render: () => null } }],
  })
  const contenedor = defineComponent({
    setup() {
      const idGrupo = ref<number | null>(1)
      return () =>
        h(TableroTareas, {
          tareas: tienda.tareas,
          grupos: [GRUPO],
          personasResaltadas: personas.value,
          idGrupo: idGrupo.value,
          'onUpdate:idGrupo': (id: number | null) => {
            idGrupo.value = id
          },
        })
    },
  })
  envoltorio = mount(contenedor, {
    attachTo: document.body,
    global: { plugins: [pinia, router] },
  })
  await flushPromises()
  return envoltorio
}

// Texto visible: sin lo que solo leen los lectores de pantalla.
function textoVisible(elemento: Element): string {
  const copia = elemento.cloneNode(true) as Element
  copia.querySelectorAll('.sr-only').forEach((oculto) => oculto.remove())
  return copia.textContent!.trim()
}

function tarjetasResaltadas(): string[] {
  return [...document.body.querySelectorAll('[data-tarjeta][data-resaltada]')].map((t) =>
    textoVisible(t.querySelector('[data-nombre-tarjeta]')!),
  )
}

function subtareasVisibles(): string[] {
  return [...document.body.querySelectorAll('[data-nombre-subtarea]')].map(textoVisible)
}

function subtareasResaltadas(): string[] {
  return [...document.body.querySelectorAll('[data-subtarea][data-resaltada]')].map((s) =>
    textoVisible(s.querySelector('[data-nombre-subtarea]')!),
  )
}

afterEach(() => {
  envoltorio?.unmount()
  envoltorio = null
  document.body.innerHTML = ''
})

describe('TableroTareas: resaltar a las personas filtradas', () => {
  it('resalta las tarjetas de las tareas asignadas a la persona filtrada', async () => {
    await montar(['José Manuel Viega'])

    expect(tarjetasResaltadas()).toEqual(['Propia de José'])
    const tarjeta = document.body.querySelector('[data-tarjeta][data-resaltada]')!
    expect(tarjeta.textContent).toContain('Asignada a la persona filtrada')
  })

  it('despliega las subtareas de las tarjetas con subtareas de la persona y resalta esas subtareas', async () => {
    await montar(['José Manuel Viega'])

    expect(subtareasVisibles()).toEqual(['Revisar oferta', 'Llamar'])
    expect(subtareasResaltadas()).toEqual(['Revisar oferta'])
    const resaltada = document.body.querySelector('[data-subtarea][data-resaltada]')!
    expect(resaltada.textContent).toContain('Asignada a la persona filtrada')
    const boton = document.body.querySelector(
      'button[aria-label="2 subtareas de Con subtarea de José"]',
    )!
    expect(boton.getAttribute('aria-expanded')).toBe('true')
  })

  it('sin personas filtradas no resalta nada ni despliega subtareas', async () => {
    await montar([])

    expect(tarjetasResaltadas()).toEqual([])
    expect(subtareasVisibles()).toEqual([])
  })

  it('al quitar el filtro pliega lo que se desplegó por él y deja de resaltar', async () => {
    await montar(['José Manuel Viega'])

    personas.value = []
    await flushPromises()

    expect(tarjetasResaltadas()).toEqual([])
    expect(subtareasVisibles()).toEqual([])
  })

  it('se pueden plegar a mano las subtareas desplegadas por el filtro', async () => {
    await montar(['José Manuel Viega'])

    document.body
      .querySelector<HTMLButtonElement>('button[aria-label="2 subtareas de Con subtarea de José"]')!
      .click()
    await flushPromises()

    expect(subtareasVisibles()).toEqual([])
  })
})
