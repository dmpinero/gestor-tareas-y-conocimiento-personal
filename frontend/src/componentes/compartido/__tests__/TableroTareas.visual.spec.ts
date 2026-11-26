import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import type { GrupoEstados, Tarea } from '@/api/tipos'
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
  tareas: 5,
  estados: [
    { id: 10, nombre: 'Pendiente', posicion: 1, tareas: 4 },
    { id: 11, nombre: 'En curso', posicion: 2, tareas: 0 },
    { id: 12, nombre: 'Hecho', posicion: 3, tareas: 1 },
  ],
}

const PENDIENTE = { id: 10, nombre: 'Pendiente' }
const HECHO = { id: 12, nombre: 'Hecho' }

function tarea(
  id: number,
  nombre: string,
  estado: { id: number; nombre: string },
  subestado: string | null,
): Tarea {
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
    grupo_estados: { id: 1, nombre: 'Desarrollo' },
    estado,
    workflow: null,
    subestado,
    congelada_en: null,
    hibernada_desde: null,
  }
}

const INFORME = tarea(1, 'Informe', PENDIENTE, 'En espera')
const ARTICULO = tarea(2, 'Artículo', PENDIENTE, 'Bloqueado')
const DESPLIEGUE = tarea(5, 'Despliegue', HECHO, 'Bloqueado')
const TAREAS = [
  {
    ...INFORME,
    asignados: ['Ana Pérez', 'Luis Gómez'],
    fecha_vencimiento: '2026-11-30T12:00:00',
    etiquetas: ['Backend'],
  },
  { ...DESPLIEGUE, completada: true, fecha_vencimiento: '2026-11-13T12:00:00' },
  { ...ARTICULO, hibernada_desde: '2026-11-20T10:00:00Z' },
]

let envoltorio: VueWrapper | null = null

async function montar(tareas: Tarea[] = TAREAS): Promise<VueWrapper> {
  const pinia = createPinia()
  setActivePinia(pinia)
  const tienda = useTiendaTareas()
  tienda.tareas = structuredClone(tareas)
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

function tarjeta(nombre: string): HTMLElement {
  const encontrada = [...document.body.querySelectorAll<HTMLElement>('[data-tarjeta]')].find(
    (t) => t.querySelector('[data-nombre-tarjeta]')?.textContent?.trim() === nombre,
  )
  if (!encontrada) throw new Error(`No hay tarjeta «${nombre}»`)
  return encontrada
}

beforeEach(() => {
  localStorage.clear()
  vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
  vi.setSystemTime(new Date(2026, 10, 20, 17, 0, 0))
})

afterEach(() => {
  vi.useRealTimers()
  envoltorio?.unmount()
  envoltorio = null
  document.body.innerHTML = ''
  localStorage.clear()
})

describe('tablero: legibilidad de las tarjetas', () => {
  it('los avatares apenas se solapan y llevan un borde del color de la tarjeta', async () => {
    await montar()
    const lista = tarjeta('Informe').querySelector('ul[aria-label="Asignados"]')
    expect(lista?.className).toContain('-space-x-0.5')
    expect(lista?.className).not.toContain('-space-x-1.5')
    expect(lista?.className).toContain('[&_[data-testid=avatar-persona]]:ring-card')
  })

  it('una tarjeta completada se atenúa y no muestra la cuenta atrás, solo la fecha', async () => {
    await montar()
    const completada = tarjeta('Despliegue')
    expect(completada.className).toContain('bg-muted/50')
    expect(completada.querySelector('[data-testid="vencimiento-corto"]')).not.toBeNull()
    expect(completada.querySelector('[data-testid="contador-vencimiento"]')).toBeNull()
    // Las pendientes conservan la cuenta atrás y el fondo de tarjeta.
    expect(tarjeta('Informe').className).toContain('bg-card')
    expect(tarjeta('Informe').querySelector('[data-testid="contador-vencimiento"]')).not.toBeNull()
  })

  it('las acciones sin información se ocultan hasta pasar el ratón o enfocar la tarjeta', async () => {
    await montar()
    const discretas = tarjeta('Informe').querySelector('[data-acciones-discretas]')
    expect(discretas?.className).toContain('[@media(hover:hover)]:opacity-0')
    expect(discretas?.className).toContain('group-hover/tarjeta:opacity-100')
    expect(discretas?.className).toContain('group-focus-within/tarjeta:opacity-100')
    expect(tarjeta('Informe').className).toContain('group/tarjeta')
    expect(discretas?.querySelector('button[aria-label="Comentarios de Informe"]')).not.toBeNull()
    // El número de subtareas y "Mover a…" informan: quedan siempre a la vista.
    expect(discretas?.textContent).not.toContain('Mover a')
  })

  it('una tarjeta hibernada deja sus acciones a la vista', async () => {
    await montar()
    const discretas = tarjeta('Artículo').querySelector('[data-acciones-discretas]')
    expect(discretas?.className).not.toContain('opacity-0')
  })

  it('la barra de colores del grupo tiene un título visible', async () => {
    await montar()
    const barra = document.body.querySelector('[data-testid="barra-estados"]')
    const titulo = document.body.querySelector('#tablero-reparto-estados')
    expect(titulo?.textContent?.trim()).toBe('Tareas por estado')
    expect(barra?.parentElement?.contains(titulo)).toBe(true)
  })

  it('el subestado se distingue de las etiquetas por su contorno y su icono', async () => {
    await montar()
    const subestado = tarjeta('Informe').querySelector('[data-testid="subestado-tablero"]')
    expect(subestado?.className).toContain('ring-1')
    expect(subestado?.querySelector('svg')).not.toBeNull()
    const etiqueta = tarjeta('Informe').querySelector('ul[aria-label="Etiquetas"] li')
    expect(etiqueta?.className).not.toContain('ring-1')
  })
})
