import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter, RouterView, type Router } from 'vue-router'

import { clienteApi } from '@/api/cliente'
import type { EntradaHistorialFoco } from '@/api/tipos'
import { useTiendaFoco } from '@/stores/foco'
import VistaHistorialFoco from '../VistaHistorialFoco.vue'

vi.mock('@/api/cliente', async (original) => ({
  ...(await original()),
  clienteApi: { obtener: vi.fn<(...args: unknown[]) => unknown>() },
}))

// Instantes en hora local (los tests no dependen de la zona horaria).
function local(dia: number, hora: number, minuto = 0): string {
  return new Date(2026, 10, dia, hora, minuto).toISOString()
}

const HOY: EntradaHistorialFoco[] = [
  {
    id: 3,
    tarea_id: 2,
    tarea_nombre: 'Informe',
    subtarea_id: 9,
    subtarea_nombre: 'Revisar',
    desde: local(24, 11),
    hasta: null,
  },
  {
    id: 2,
    tarea_id: null,
    tarea_nombre: 'Borrada',
    subtarea_id: null,
    subtarea_nombre: null,
    desde: local(24, 10),
    hasta: local(24, 10, 30),
  },
  {
    id: 1,
    tarea_id: 1,
    tarea_nombre: 'Portal',
    subtarea_id: null,
    subtarea_nombre: null,
    desde: local(24, 9),
    hasta: local(24, 9, 45),
  },
]

const AYER: EntradaHistorialFoco = {
  id: 0,
  tarea_id: 1,
  tarea_nombre: 'Portal',
  subtarea_id: null,
  subtarea_nombre: null,
  desde: local(23, 16),
  hasta: local(23, 17),
}

let historial: EntradaHistorialFoco[] = [...HOY, AYER]

function responder(ruta: string): Promise<unknown> {
  if (ruta === '/foco/historial') return Promise.resolve(historial)
  const consulta = new URLSearchParams(ruta.split('?')[1])
  const desde = new Date(consulta.get('desde') ?? '').getTime()
  const hasta = new Date(consulta.get('hasta') ?? '').getTime()
  return Promise.resolve(
    historial.filter((e) => {
      const t = new Date(e.desde).getTime()
      return t >= desde && t < hasta
    }),
  )
}

let router: Router
let wrapper: VueWrapper

async function montar(url = '/foco/historial'): Promise<VueWrapper> {
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/foco/historial', name: 'historial-foco', component: VistaHistorialFoco },
      { path: '/tareas', name: 'tareas', component: { render: () => h('p', 'tareas') } },
    ],
  })
  await router.push(url)
  await router.isReady()
  wrapper = mount(defineComponent({ render: () => h(RouterView) }), {
    global: { plugins: [router] },
  })
  await flushPromises()
  return wrapper
}

function filas(): string[] {
  return wrapper.findAll('[data-entrada-historial]').map((f) => f.text())
}

function boton(nombre: string) {
  const encontrado = wrapper.findAll('button').find((b) => b.text() === nombre)
  if (!encontrado) throw new Error(`No hay botón "${nombre}"`)
  return encontrado
}

describe('VistaHistorialFoco', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.useFakeTimers({
      now: new Date(2026, 10, 24, 12, 0),
      toFake: ['Date', 'setInterval', 'clearInterval'],
    })
    historial = [...HOY, AYER]
    vi.mocked(clienteApi.obtener).mockImplementation((ruta: string) => responder(ruta))
  })

  afterEach(() => {
    wrapper?.unmount()
    vi.useRealTimers()
  })

  describe('Por día', () => {
    it('por defecto muestra hoy, con las entradas más recientes primero', async () => {
      await montar()

      expect(wrapper.get('h2').text()).toBe('Historial de foco')
      expect(wrapper.get('h3').text()).toContain('24 de noviembre de 2026')
      expect(boton('Por día').attributes('aria-pressed')).toBe('true')
      const texto = filas()
      expect(texto).toHaveLength(3)
      expect(texto[0]).toContain('Informe › Revisar')
      expect(texto[1]).toContain('Borrada')
      expect(texto[2]).toContain('Portal')
      expect(texto[2]).toContain('09:00')
      expect(texto[2]).toContain('09:45')
      expect(texto[2]).toContain('45 min')
    })

    it('la entrada abierta dice "en curso" y su duración avanza cada minuto', async () => {
      await montar()

      expect(filas()[0]).toContain('11:00')
      expect(filas()[0]).toContain('en curso')
      expect(filas()[0]).toContain('1 h')

      vi.advanceTimersByTime(30 * 60_000)
      await flushPromises()

      expect(filas()[0]).toContain('1 h 30 min')
    })

    it('muestra el tiempo total del día', async () => {
      await montar()

      expect(wrapper.get('[data-total-dia]').text()).toContain('2 h 15 min')
    })

    it('"Día anterior" cambia la URL y recarga ese día', async () => {
      await montar()

      await boton('Día anterior').trigger('click')
      await flushPromises()

      expect(router.currentRoute.value.query).toEqual({ vista: 'dia', dia: '2026-11-23' })
      expect(wrapper.get('h3').text()).toContain('23 de noviembre de 2026')
      expect(filas()).toHaveLength(1)
    })

    it('"Día siguiente" está desactivado hoy y avanza un día antes', async () => {
      await montar('/foco/historial?dia=2026-11-23')
      expect(boton('Día siguiente').attributes('disabled')).toBeUndefined()

      await boton('Día siguiente').trigger('click')
      await flushPromises()

      expect(router.currentRoute.value.query.dia).toBe('2026-11-24')
      expect(boton('Día siguiente').attributes('disabled')).toBeDefined()
    })

    it('"Hoy" vuelve al día de hoy', async () => {
      await montar('/foco/historial?dia=2026-11-20')

      await boton('Hoy').trigger('click')
      await flushPromises()

      expect(router.currentRoute.value.query.dia).toBe('2026-11-24')
      expect(filas()).toHaveLength(3)
    })

    it('el selector de fecha cambia el día', async () => {
      await montar()

      await wrapper.get('input[type="date"]').setValue('2026-11-23')
      await flushPromises()

      expect(router.currentRoute.value.query.dia).toBe('2026-11-23')
      expect(filas()).toHaveLength(1)
    })

    it('un día sin entradas muestra el aviso', async () => {
      await montar('/foco/historial?dia=2026-11-10')

      expect(filas()).toHaveLength(0)
      expect(wrapper.text()).toContain('No hubo foco este día.')
    })

    it('atrás en el navegador recupera el día anterior', async () => {
      await montar()
      await boton('Día anterior').trigger('click')
      await flushPromises()

      router.back()
      await flushPromises()

      expect(wrapper.get('h3').text()).toContain('24 de noviembre de 2026')
    })
  })

  describe('Todo', () => {
    it('la URL restaura la vista y lista todo el historial más reciente primero', async () => {
      await montar('/foco/historial?vista=todo')

      expect(clienteApi.obtener).toHaveBeenCalledWith('/foco/historial')
      expect(boton('Todo').attributes('aria-pressed')).toBe('true')
      expect(wrapper.findAll('th').map((th) => th.text())).toEqual([
        'Fecha',
        'Inicio',
        'Fin',
        'Duración',
        'Tarea',
      ])
      const texto = filas()
      expect(texto).toHaveLength(4)
      expect(texto[0]).toContain('en curso')
      expect(texto[3]).toContain('23/11/2026')
      expect(texto[3]).toContain('16:00')
      expect(texto[3]).toContain('17:00')
      expect(texto[3]).toContain('1 h')
    })

    it('pasar a "Todo" guarda la vista en la URL', async () => {
      await montar()

      await boton('Todo').trigger('click')
      await flushPromises()

      expect(router.currentRoute.value.query.vista).toBe('todo')
      expect(filas()).toHaveLength(4)
    })

    it('sin historial muestra el aviso', async () => {
      historial = []
      await montar('/foco/historial?vista=todo')

      expect(wrapper.text()).toContain('Todavía no hay historial de foco.')
    })
  })

  it('una entrada con tarea lleva a su detalle', async () => {
    await montar()

    const enlace = wrapper.findAll('a').find((a) => a.text().includes('Portal'))
    expect(enlace).toBeDefined()
    await enlace!.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/tareas?tarea=1')
  })

  it('una entrada de una tarea borrada no es un enlace y lo indica', async () => {
    await montar()

    const fila = wrapper.findAll('[data-entrada-historial]')[1]!
    expect(fila.find('a').exists()).toBe(false)
    expect(fila.get('[data-tarea-eliminada]').text()).toContain('(tarea eliminada)')
  })

  it('al cambiar el foco recarga el historial', async () => {
    await montar()
    const llamadas = vi.mocked(clienteApi.obtener).mock.calls.length

    useTiendaFoco().foco = {
      tarea_id: 1,
      tarea_nombre: 'Portal',
      subtarea_id: null,
      subtarea_nombre: null,
      desde: local(24, 12),
    }
    await flushPromises()

    expect(vi.mocked(clienteApi.obtener).mock.calls.length).toBe(llamadas + 1)
  })
})
