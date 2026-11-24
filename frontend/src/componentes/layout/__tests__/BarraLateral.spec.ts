import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { obtenerConfiguracionAlta, obtenerConfiguracionAxasMs3 } from '@/api/altaOportunidades'
import { SidebarProvider } from '@/componentes/ui/sidebar'
import BarraLateral from '../BarraLateral.vue'

vi.mock('@/api/altaOportunidades', () => ({
  obtenerConfiguracionAlta: vi.fn<() => Promise<unknown>>(),
  obtenerConfiguracionAxasMs3: vi.fn<() => Promise<unknown>>(),
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
    routes: [
      '/',
      '/tareas',
      '/oportunidades',
      '/oportunidades/anes',
      '/oportunidades/axas-ms3',
      '/conocimiento',
      '/ajustes',
    ].map((path) => ({
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
  vi.mocked(obtenerConfiguracionAxasMs3).mockResolvedValue({
    valores: null,
    error: null,
    fecha_limite: null,
    fecha_inicio: '28/02/2026',
    nombre_menu: 'AXAS Ejemplo',
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
    ['Mi trabajo', '/tareas'],
    ['Oportunidades', '/oportunidades'],
    ['Oportunidades Ejemplo', '/oportunidades/anes'],
    ['AXAS Ejemplo', '/oportunidades/axas-ms3'],
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
    expect(actuales[0]?.text()).toBe('Mi trabajo')
  })

  it('"Oportunidades" es un elemento del primer nivel, fuera de "Mi trabajo", con las dos altas debajo', async () => {
    const wrapper = await montarEn('/oportunidades/anes')

    const enlaces = wrapper.findAll('a')
    const oportunidades = enlaces.find((a) => a.text() === 'Oportunidades')!
    const trabajo = enlaces.find((a) => a.text() === 'Mi trabajo')!
    const itemOportunidades = oportunidades.element.closest('li')!
    expect(trabajo.element.closest('li')!.contains(oportunidades.element)).toBe(false)
    expect(itemOportunidades.parentElement).toBe(trabajo.element.closest('li')!.parentElement)
    for (const alta of ['Oportunidades Ejemplo', 'AXAS Ejemplo']) {
      const enlace = enlaces.find((a) => a.text() === alta)!
      expect(itemOportunidades.contains(enlace.element)).toBe(true)
    }
    const actuales = wrapper.findAll('a[aria-current="page"]')
    expect(actuales.map((a) => a.text())).toEqual(['Oportunidades Ejemplo'])
  })

  it('si no se puede leer la configuración, la entrada del alta usa el nombre predeterminado', async () => {
    vi.mocked(obtenerConfiguracionAlta).mockRejectedValue(new Error('Bad Gateway'))
    const wrapper = await montarEn('/')

    const alta = wrapper.findAll('a').find((a) => a.text() === 'Alta de oportunidades')
    expect(alta?.attributes('href')).toBe('/oportunidades/anes')
  })

  it('en la ruta del alta AXAS MS3 solo se marca su enlace', async () => {
    const wrapper = await montarEn('/oportunidades/axas-ms3')

    const actuales = wrapper.findAll('a[aria-current="page"]')
    expect(actuales.map((a) => a.text())).toEqual(['AXAS Ejemplo'])
  })

  it('si no se puede leer la configuración de AXAS MS3, su entrada usa el nombre predeterminado', async () => {
    vi.mocked(obtenerConfiguracionAxasMs3).mockRejectedValue(new Error('Bad Gateway'))
    const wrapper = await montarEn('/')

    const alta = wrapper.findAll('a').find((a) => a.text() === 'Oportunidades AXAS MS3')
    expect(alta?.attributes('href')).toBe('/oportunidades/axas-ms3')
  })
})
