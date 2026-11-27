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
const AJENA = tarea(3, 'Ajena', ['Ana'], [subtarea(30, 'Buscar persona fuera de KMM', null)])
const TAREAS = [PROPIA, CON_SUBTAREA, AJENA]

let envoltorio: VueWrapper | null = null
const busqueda = ref('')

async function montar(texto: string): Promise<VueWrapper> {
  const pinia = createPinia()
  setActivePinia(pinia)
  const tienda = useTiendaTareas()
  tienda.tareas = JSON.parse(JSON.stringify(TAREAS)) as Tarea[]
  busqueda.value = texto
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
          busqueda: busqueda.value,
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

function textoVisible(elemento: Element): string {
  const copia = elemento.cloneNode(true) as Element
  copia.querySelectorAll('.sr-only').forEach((oculto) => oculto.remove())
  return copia.textContent!.trim()
}

function subtareasVisibles(): string[] {
  return [...document.body.querySelectorAll('[data-nombre-subtarea]')].map(textoVisible)
}

function subtareasCoincidentes(): string[] {
  return [...document.body.querySelectorAll('[data-subtarea][data-coincide-busqueda]')].map((s) =>
    textoVisible(s.querySelector('[data-nombre-subtarea]')!),
  )
}

afterEach(() => {
  envoltorio?.unmount()
  envoltorio = null
  document.body.innerHTML = ''
})

describe('TableroTareas: subtareas que coinciden con la búsqueda', () => {
  it('despliega las tarjetas con subtareas que coinciden (sin mayúsculas ni acentos) y las marca', async () => {
    await montar('BÚSCAR persona fuera de kmm')

    expect(subtareasVisibles()).toEqual(['Buscar persona fuera de KMM'])
    expect(subtareasCoincidentes()).toEqual(['Buscar persona fuera de KMM'])
    const marcada = document.body.querySelector('[data-subtarea][data-coincide-busqueda]')!
    expect(marcada.textContent).toContain('Coincide con la búsqueda')
    expect(
      document.body
        .querySelector('button[aria-label="1 subtareas de Ajena"]')!
        .getAttribute('aria-expanded'),
    ).toBe('true')
  })

  it('marca solo las subtareas que coinciden dentro de una tarjeta desplegada', async () => {
    await montar('llamar')

    expect(subtareasVisibles()).toEqual(['Revisar oferta', 'Llamar'])
    expect(subtareasCoincidentes()).toEqual(['Llamar'])
  })

  it('sin búsqueda no despliega ni marca nada; al vaciarla pliega lo desplegado por ella', async () => {
    await montar('')
    expect(subtareasVisibles()).toEqual([])

    busqueda.value = 'llamar'
    await flushPromises()
    expect(subtareasCoincidentes()).toEqual(['Llamar'])

    busqueda.value = ''
    await flushPromises()
    expect(subtareasVisibles()).toEqual([])
    expect(subtareasCoincidentes()).toEqual([])
  })
})
