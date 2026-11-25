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
  tareas: 2,
  estados: [{ id: 10, nombre: 'Pendiente', posicion: 1, tareas: 2 }],
}

// Instante en UTC, como lo da la API ("YYYY-MM-DDTHH:MM:SSZ"), de una hora local.
function instanteUtc(fechaLocal: Date): string {
  return fechaLocal.toISOString().replace(/\.\d{3}Z$/, 'Z')
}

function tarea(id: number, nombre: string, hibernadaDesde: string | null): Tarea {
  return {
    id,
    nombre,
    prioridad: null,
    descripcion: '',
    fecha_creacion: '2026-11-10T09:00:00',
    // Vence en 1 h: sin congelar muestra la campana urgente.
    fecha_vencimiento: '2026-11-20T18:00:00',
    etiquetas: [],
    asignados: [],
    tipo: null,
    oportunidad: null,
    completada: false,
    subtareas: [],
    grupo_estados: { id: 1, nombre: 'Desarrollo' },
    estado: { id: 10, nombre: 'Pendiente' },
    workflow: null,
    subestado: null,
    congelada_en: null,
    hibernada_desde: hibernadaDesde,
  }
}

const HIBERNADA = tarea(1, 'Hibernada', instanteUtc(new Date(2026, 10, 20, 16, 0, 0)))
const NORMAL = tarea(2, 'Normal', null)

let envoltorio: VueWrapper | null = null

async function montar(): Promise<void> {
  const pinia = createPinia()
  setActivePinia(pinia)
  const tienda = useTiendaTareas()
  tienda.tareas = structuredClone([HIBERNADA, NORMAL])
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
          personasResaltadas: [],
          idGrupo: idGrupo.value,
          'onUpdate:idGrupo': (id: number | null) => {
            idGrupo.value = id
          },
        })
    },
  })
  envoltorio = mount(contenedor, { attachTo: document.body, global: { plugins: [pinia, router] } })
  await flushPromises()
}

function tarjeta(nombre: string): Element {
  const encontrada = [...document.body.querySelectorAll('[data-tarjeta]')].find((t) =>
    t.querySelector('[data-nombre-tarjeta]')?.textContent?.includes(nombre),
  )
  if (!encontrada) throw new Error(`No hay tarjeta «${nombre}»`)
  return encontrada
}

describe('TableroTareas: tareas hibernadas', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    vi.setSystemTime(new Date(2026, 10, 20, 17, 0, 0))
  })

  afterEach(() => {
    vi.useRealTimers()
    envoltorio?.unmount()
    envoltorio = null
    document.body.innerHTML = ''
  })

  it('la tarjeta de una tarea hibernada muestra "Hibernada", sin campanas y con el contador detenido', async () => {
    await montar()

    const hibernada = tarjeta('Hibernada')
    expect(hibernada.querySelector('[data-insignia-hibernada]')?.textContent?.trim()).toBe(
      'Hibernada',
    )
    expect(hibernada.querySelector('[data-aviso-vencimiento]')).toBeNull()
    const contador = hibernada.querySelector('[data-testid="contador-vencimiento"]')!
    expect(contador.getAttribute('data-congelado')).toBe('true')
    expect(contador.querySelector('[data-testid="contador-texto"]')?.textContent).toBe(
      'Vence en 02 h 00 min 00 s',
    )
  })

  it('la tarjeta de una tarea normal sigue igual: sin insignia, con campana y el contador en marcha', async () => {
    await montar()

    const normal = tarjeta('Normal')
    expect(normal.querySelector('[data-insignia-hibernada]')).toBeNull()
    expect(normal.querySelector('[data-aviso-vencimiento]')).not.toBeNull()
    const contador = normal.querySelector('[data-testid="contador-vencimiento"]')!
    expect(contador.getAttribute('data-congelado')).toBeNull()
    expect(contador.querySelector('[data-testid="contador-texto"]')?.textContent).toBe(
      'Vence en 01 h 00 min 00 s',
    )
    vi.advanceTimersByTime(1000)
    await flushPromises()
    expect(contador.querySelector('[data-testid="contador-texto"]')?.textContent).toBe(
      'Vence en 00 h 59 min 59 s',
    )
  })
})
