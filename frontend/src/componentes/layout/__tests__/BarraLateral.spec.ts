import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { obtenerConfiguracionAlta } from '@/api/altaOportunidades'
import { SidebarProvider } from '@/componentes/ui/sidebar'
import BarraLateral from '../BarraLateral.vue'

vi.mock('@/api/altaOportunidades', () => ({
  obtenerConfiguracionAlta: vi.fn<() => Promise<unknown>>(),
}))

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
    routes: ['/', '/tareas', '/tareas/oportunidades', '/conocimiento', '/ajustes'].map((path) => ({
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
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  definirMatchMedia()
  vi.mocked(obtenerConfiguracionAlta).mockResolvedValue({
    valores: null,
    error: null,
    fecha_limite: null,
    fecha_inicio: '28/02/2026',
    nombre_menu: 'Oportunidades Ejemplo',
  })
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
    ['Oportunidades Ejemplo', '/tareas/oportunidades'],
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

  it('"Oportunidades" es un grupo dentro de "Tareas" y la entrada del alta cuelga de él', async () => {
    const wrapper = await montarEn('/tareas/oportunidades')

    const grupo = wrapper.find('[data-grupo-menu="Oportunidades"]')
    expect(grupo.exists()).toBe(true)
    expect(grupo.element.tagName).not.toBe('A')
    expect(wrapper.findAll('a').some((a) => a.text() === 'Oportunidades')).toBe(false)
    const tareas = wrapper.findAll('a').find((a) => a.text() === 'Tareas')
    expect(tareas?.element.closest('li')?.contains(grupo.element)).toBe(true)
    const alta = wrapper.findAll('a').find((a) => a.text() === 'Oportunidades Ejemplo')
    expect(grupo.element.closest('li')?.contains(alta!.element)).toBe(true)
    const actuales = wrapper.findAll('a[aria-current="page"]')
    expect(actuales.map((a) => a.text())).toEqual(['Oportunidades Ejemplo'])
  })

  it('si no se puede leer la configuración, la entrada del alta usa el nombre predeterminado', async () => {
    vi.mocked(obtenerConfiguracionAlta).mockRejectedValue(new Error('Bad Gateway'))
    const wrapper = await montarEn('/')

    const alta = wrapper.findAll('a').find((a) => a.text() === 'Alta de oportunidades')
    expect(alta?.attributes('href')).toBe('/tareas/oportunidades')
  })
})
