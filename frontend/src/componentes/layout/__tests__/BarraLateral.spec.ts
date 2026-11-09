import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SidebarProvider } from '@/componentes/ui/sidebar'
import BarraLateral from '../BarraLateral.vue'

function definirMatchMedia(): void {
  window.matchMedia = vi.fn<(consulta: string) => unknown>().mockImplementation((consulta) => ({
    matches: false,
    media: consulta,
    addEventListener: vi.fn<() => void>(),
    removeEventListener: vi.fn<() => void>(),
  })) as unknown as typeof window.matchMedia
}

const vistaVacia = { template: '<div />' }

function crearRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: ['/', '/tareas', '/conocimiento', '/ajustes'].map((path) => ({
      path,
      component: vistaVacia,
    })),
  })
}

async function montarEn(ruta: string) {
  const router = crearRouter()
  await router.push(ruta)
  await router.isReady()
  const wrapper = mount(
    {
      components: { SidebarProvider, BarraLateral },
      template: '<SidebarProvider><BarraLateral /></SidebarProvider>',
    },
    { global: { plugins: [router] } },
  )
  return wrapper
}

beforeEach(() => {
  definirMatchMedia()
})

describe('BarraLateral', () => {
  it('muestra los grupos General y Configuración', async () => {
    const wrapper = await montarEn('/')

    expect(wrapper.text()).toContain('General')
    expect(wrapper.text()).toContain('Configuración')
  })

  it.each([
    ['Inicio', '/'],
    ['Tareas', '/tareas'],
    ['Conocimiento', '/conocimiento'],
    ['Ajustes', '/ajustes'],
  ])('muestra el enlace "%s" que apunta a %s', async (etiqueta, destino) => {
    const wrapper = await montarEn('/')

    const enlace = wrapper.findAll('a').find((a) => a.text() === etiqueta)
    expect(enlace).toBeDefined()
    expect(enlace?.attributes('href')).toBe(destino)
  })

  it('marca con aria-current="page" solo el enlace de la ruta activa', async () => {
    const wrapper = await montarEn('/tareas')

    const actuales = wrapper.findAll('a[aria-current="page"]')
    expect(actuales).toHaveLength(1)
    expect(actuales[0]?.text()).toBe('Tareas')
  })
})
