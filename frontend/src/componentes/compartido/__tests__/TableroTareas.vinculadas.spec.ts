import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'
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
  tareas: 2,
  estados: [{ id: 10, nombre: 'Pendiente', posicion: 1, tareas: 2 }],
}

function tarea(id: number, nombre: string, cambios: Partial<Tarea> = {}): Tarea {
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
    estado: { id: 10, nombre: 'Pendiente' },
    workflow: null,
    vinculadas: [],
    subestado: null,
    congelada_en: null,
    hibernada_desde: null,
    ...cambios,
  }
}

// «Fuera del tablero» es de otro grupo: el tablero no la pinta, pero el árbol
// de relacionadas la muestra igual (sale del almacén de tareas).
const PRINCIPAL = tarea(1, 'Principal', { vinculadas: [2, 3, 4] })
const SUELTA = tarea(2, 'Suelta', { vinculadas: [1] })
const HECHA = tarea(3, 'Hecha', { vinculadas: [1], completada: true })
const FUERA = tarea(4, 'Fuera del tablero', {
  vinculadas: [1],
  grupo_estados: { id: 2, nombre: 'Otro' },
  estado: null,
})

let envoltorio: VueWrapper | null = null
const verDetalle = vi.fn<(id: number) => void>()

async function montar(): Promise<void> {
  const pinia = createPinia()
  setActivePinia(pinia)
  const tienda = useTiendaTareas()
  tienda.tareas = structuredClone([PRINCIPAL, SUELTA, HECHA, FUERA])
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:ruta(.*)*', component: { render: () => null } }],
  })
  const contenedor = defineComponent({
    setup() {
      const idGrupo = ref<number | null>(1)
      return () =>
        h(TableroTareas, {
          tareas: tienda.tareas.filter((t) => t.grupo_estados?.id === 1),
          grupos: [GRUPO],
          personasResaltadas: [],
          idGrupo: idGrupo.value,
          'onUpdate:idGrupo': (id: number | null) => {
            idGrupo.value = id
          },
          onVerDetalle: verDetalle,
        })
    },
  })
  envoltorio = mount(contenedor, { attachTo: document.body, global: { plugins: [pinia, router] } })
  await flushPromises()
}

function tarjeta(nombre: string): Element {
  const encontrada = [...document.body.querySelectorAll('[data-tarjeta]')].find(
    (t) => t.querySelector('[data-nombre-tarjeta]')?.textContent?.trim() === nombre,
  )
  if (!encontrada) throw new Error(`No hay tarjeta «${nombre}»`)
  return encontrada
}

function botonRelacionadas(nombre: string): HTMLButtonElement | null {
  return tarjeta(nombre).querySelector<HTMLButtonElement>('[data-boton-relacionadas]')
}

function arbol(nombre: string): HTMLElement | null {
  return document.body.querySelector<HTMLElement>(`[aria-label="Tareas relacionadas de ${nombre}"]`)
}

afterEach(() => {
  envoltorio?.unmount()
  envoltorio = null
  document.body.innerHTML = ''
  verDetalle.mockClear()
})

describe('TableroTareas: árbol de tareas relacionadas', () => {
  it('junto a «Hibernar» hay un botón siempre visible con el número de relacionadas, plegado', async () => {
    await montar()

    const boton = botonRelacionadas('Principal')!
    expect(boton.textContent?.trim()).toBe('3')
    expect(boton.getAttribute('aria-label')).toBe('3 tareas relacionadas de Principal')
    expect(boton.getAttribute('aria-expanded')).toBe('false')
    // Justo después del grupo de acciones que termina en «Hibernar» y fuera de
    // él: esas se ocultan hasta pasar el ratón; el número de relacionadas no.
    const acciones = tarjeta('Principal').querySelector('[data-acciones-discretas]')!
    expect(acciones.lastElementChild?.hasAttribute('data-hibernar')).toBe(true)
    expect(acciones.nextElementSibling).toBe(boton)
    expect(arbol('Principal')).toBeNull()
  })

  it('una tarea sin relacionadas no muestra el botón', async () => {
    await montar()
    const sinRelacion = tarea(9, 'Sola')
    useTiendaTareas().tareas.push(sinRelacion)
    await flushPromises()

    expect(botonRelacionadas('Sola')).toBeNull()
  })

  it('al pulsarlo despliega el árbol con las relacionadas (también de otros grupos) y lo pliega', async () => {
    await montar()

    botonRelacionadas('Principal')!.click()
    await flushPromises()

    const panel = arbol('Principal')!
    expect(botonRelacionadas('Principal')!.getAttribute('aria-expanded')).toBe('true')
    const nombres = [...panel.querySelectorAll('[data-nombre-relacionada]')].map((n) =>
      n.textContent?.trim(),
    )
    expect(nombres).toEqual(['Suelta', 'Hecha (completada)', 'Fuera del tablero'])
    const hecha = [...panel.querySelectorAll('[data-nombre-relacionada]')][1]!
    expect(hecha.className).toContain('line-through')

    botonRelacionadas('Principal')!.click()
    await flushPromises()
    expect(arbol('Principal')).toBeNull()
  })

  it('pulsar una relacionada abre su detalle', async () => {
    await montar()
    botonRelacionadas('Principal')!.click()
    await flushPromises()

    const fuera = [
      ...arbol('Principal')!.querySelectorAll<HTMLButtonElement>('[data-nombre-relacionada]'),
    ].find((b) => b.textContent?.includes('Fuera del tablero'))!
    fuera.click()

    expect(verDetalle).toHaveBeenCalledWith(4)
  })
})
