import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import * as api from '@/api/conocimiento'
import type { EstadoConocimiento, OpcionesPreguntar } from '@/api/conocimiento'
import VistaConocimiento from '../VistaConocimiento.vue'

vi.mock('@/api/conocimiento', async (original) => ({
  ...(await original()),
  obtenerEstado: vi.fn(),
  sincronizar: vi.fn(),
  preguntar: vi.fn(),
}))

const CONFIGURADO: EstadoConocimiento = {
  configurado: { notion: true, anthropic: true },
  paginas: 12,
  fragmentos: 340,
  ultima_sincronizacion: null,
}

const FUENTE = { pagina_id: 'p1', titulo: 'Recetas', url: 'https://www.notion.so/p1' }

let envoltorio: VueWrapper | null = null

async function montar(estado: EstadoConocimiento = CONFIGURADO): Promise<VueWrapper> {
  vi.mocked(api.obtenerEstado).mockResolvedValue(estado)
  envoltorio = mount(VistaConocimiento, { attachTo: document.body })
  await flushPromises()
  return envoltorio
}

function boton(envoltorio: VueWrapper, texto: string) {
  const encontrado = envoltorio.findAll('button').find((b) => b.text() === texto)
  if (!encontrado) throw new Error(`No hay botón «${texto}»`)
  return encontrado
}

describe('VistaConocimiento', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    envoltorio?.unmount()
    envoltorio = null
  })

  it('muestra el encabezado y la pista del chat vacío', async () => {
    const vista = await montar()
    expect(vista.find('h2').text()).toBe('Conocimiento')
    expect(vista.text()).toContain('Pregunta lo que quieras sobre tus notas de Notion.')
  })

  it('sin credenciales explica qué falta y desactiva sincronizar y enviar', async () => {
    const vista = await montar({
      ...CONFIGURADO,
      configurado: { notion: false, anthropic: false },
    })
    expect(vista.text()).toContain('Falta configurar NOTION_TOKEN en backend/.env')
    expect(vista.text()).toContain('Falta configurar ANTHROPIC_API_KEY en backend/.env')
    expect(boton(vista, 'Sincronizar con Notion').attributes('disabled')).toBeDefined()
    await vista.find('textarea').setValue('Hola')
    expect(boton(vista, 'Enviar').attributes('disabled')).toBeDefined()
  })

  it('solo sin NOTION_TOKEN: avisa de ese y permite preguntar', async () => {
    const vista = await montar({ ...CONFIGURADO, configurado: { notion: false, anthropic: true } })
    expect(vista.text()).toContain('Falta configurar NOTION_TOKEN en backend/.env')
    expect(vista.text()).not.toContain('ANTHROPIC_API_KEY')
    expect(boton(vista, 'Sincronizar con Notion').attributes('disabled')).toBeDefined()
    await vista.find('textarea').setValue('Hola')
    expect(boton(vista, 'Enviar').attributes('disabled')).toBeUndefined()
  })

  it('muestra los recuentos y la última sincronización', async () => {
    const vista = await montar({
      ...CONFIGURADO,
      ultima_sincronizacion: new Date(2026, 10, 26, 9, 5, 7).toISOString(),
    })
    const resumen = vista.get('[data-testid="estado-conocimiento"]').text()
    expect(resumen).toContain('12 páginas')
    expect(resumen).toContain('340 fragmentos')
    expect(resumen).toContain('Última sincronización: 26/11/2026 09:05:07')
  })

  it('sin sincronizar nunca lo dice', async () => {
    const vista = await montar()
    expect(vista.text()).toContain('Última sincronización: nunca')
  })

  it('sincronizar desactiva el botón mientras dura y muestra el resultado', async () => {
    const vista = await montar()
    let resolver!: (valor: api.ResultadoSincronizacion) => void
    vi.mocked(api.sincronizar).mockReturnValue(new Promise((r) => (resolver = r)))

    await boton(vista, 'Sincronizar con Notion').trigger('click')
    expect(boton(vista, 'Sincronizando…').attributes('disabled')).toBeDefined()

    resolver({
      paginas: 13,
      fragmentos: 350,
      nuevas: 1,
      actualizadas: 2,
      eliminadas: 0,
      ultima_sincronizacion: new Date(2026, 10, 26, 10, 0, 0).toISOString(),
    })
    await flushPromises()

    const resultado = vista.get('[data-testid="resultado-sincronizacion"]').text()
    expect(resultado).toContain('1 nuevas')
    expect(resultado).toContain('2 actualizadas')
    expect(resultado).toContain('0 eliminadas')
    expect(vista.get('[data-testid="estado-conocimiento"]').text()).toContain('13 páginas')
    expect(boton(vista, 'Sincronizar con Notion').attributes('disabled')).toBeUndefined()
  })

  it('si sincronizar falla muestra el error como alerta', async () => {
    const vista = await montar()
    vi.mocked(api.sincronizar).mockRejectedValue(new Error('Notion no responde'))
    await boton(vista, 'Sincronizar con Notion').trigger('click')
    await flushPromises()
    expect(vista.get('[role="alert"]').text()).toContain('Notion no responde')
  })

  it('Enviar está desactivado con la pregunta vacía', async () => {
    const vista = await montar()
    expect(boton(vista, 'Enviar').attributes('disabled')).toBeDefined()
    await vista.find('textarea').setValue('   ')
    expect(boton(vista, 'Enviar').attributes('disabled')).toBeDefined()
  })

  it('Enter envía la pregunta, muestra la respuesta en streaming y vacía el campo', async () => {
    const vista = await montar()
    let opciones!: OpcionesPreguntar
    let terminar!: () => void
    vi.mocked(api.preguntar).mockImplementation((_m, o) => {
      opciones = o
      return new Promise<void>((r) => (terminar = r))
    })
    const campo = vista.find('textarea')
    expect(vista.find('label[for="pregunta-conocimiento"]').text()).toBe('Pregunta')
    await campo.setValue('¿Qué receta tengo?')
    await campo.trigger('keydown', { key: 'Enter' })

    expect(api.preguntar).toHaveBeenCalledTimes(1)
    expect((campo.element as HTMLTextAreaElement).value).toBe('')
    expect(boton(vista, 'Enviar').attributes('disabled')).toBeDefined()

    const lista = vista.get('[data-testid="conversacion-conocimiento"]')
    expect(lista.attributes('aria-live')).toBe('polite')
    expect(lista.attributes('aria-busy')).toBe('true')

    opciones.onFuentes([FUENTE])
    opciones.onTexto('Tienes **lentejas**')
    await flushPromises()
    await vi.waitFor(() =>
      expect(vista.get('[data-rol="asistente"] strong').text()).toBe('lentejas'),
    )
    expect(vista.get('[data-rol="usuario"]').text()).toContain('¿Qué receta tengo?')

    terminar()
    await flushPromises()
    expect(lista.attributes('aria-busy')).toBe('false')
    expect(vista.text()).not.toContain('Pregunta lo que quieras sobre tus notas de Notion.')
  })

  it('Shift+Enter no envía', async () => {
    const vista = await montar()
    const campo = vista.find('textarea')
    await campo.setValue('Hola')
    await campo.trigger('keydown', { key: 'Enter', shiftKey: true })
    expect(api.preguntar).not.toHaveBeenCalled()
  })

  it('las fuentes son enlaces a Notion en una pestaña nueva', async () => {
    const vista = await montar()
    vi.mocked(api.preguntar).mockImplementation(async (_m, o) => {
      o.onFuentes([FUENTE])
      o.onTexto('Respuesta')
    })
    await vista.find('textarea').setValue('Hola')
    await boton(vista, 'Enviar').trigger('click')
    await flushPromises()

    const fuentes = vista.get('[data-testid="fuentes-respuesta"]')
    expect(fuentes.text()).toContain('Fuentes:')
    const enlace = fuentes.get('a')
    expect(enlace.text()).toBe('Recetas')
    expect(enlace.attributes('href')).toBe('https://www.notion.so/p1')
    expect(enlace.attributes('target')).toBe('_blank')
    expect(enlace.attributes('rel')).toBe('noopener noreferrer')
  })

  it('una fuente con una URL que no es http(s) se muestra sin enlace', async () => {
    const vista = await montar()
    vi.mocked(api.preguntar).mockImplementation(async (_m, o) => {
      o.onFuentes([{ ...FUENTE, url: 'javascript:alert(1)' }])
      o.onTexto('Respuesta')
    })
    await vista.find('textarea').setValue('Hola')
    await boton(vista, 'Enviar').trigger('click')
    await flushPromises()

    const fuentes = vista.get('[data-testid="fuentes-respuesta"]')
    expect(fuentes.find('a').exists()).toBe(false)
    expect(fuentes.text()).toContain('Recetas')
  })

  it('el Markdown de la respuesta se pinta saneado', async () => {
    const vista = await montar()
    vi.mocked(api.preguntar).mockImplementation(async (_m, o) => {
      o.onTexto(
        'Hola <img src=x onerror="alert(1)"><script>alert(2)</script> [enlace](https://ejemplo.com)',
      )
    })
    await vista.find('textarea').setValue('Hola')
    await boton(vista, 'Enviar').trigger('click')
    await flushPromises()

    const respuesta = vista.get('[data-rol="asistente"]')
    await vi.waitFor(() => expect(respuesta.find('a').exists()).toBe(true))
    expect(respuesta.html()).not.toContain('onerror')
    expect(respuesta.find('script').exists()).toBe(false)
    const enlace = respuesta.get('a')
    expect(enlace.attributes('target')).toBe('_blank')
    expect(enlace.attributes('rel')).toBe('noopener noreferrer')
  })

  it('si la pregunta falla muestra el error como alerta', async () => {
    const vista = await montar()
    vi.mocked(api.preguntar).mockRejectedValue(new Error('Falló Claude'))
    await vista.find('textarea').setValue('Hola')
    await boton(vista, 'Enviar').trigger('click')
    await flushPromises()
    expect(vista.get('[role="alert"]').text()).toContain('Falló Claude')
  })

  it('Nueva conversación vacía el chat', async () => {
    const vista = await montar()
    vi.mocked(api.preguntar).mockImplementation(async (_m, o) => o.onTexto('R'))
    await vista.find('textarea').setValue('Hola')
    await boton(vista, 'Enviar').trigger('click')
    await flushPromises()
    expect(vista.findAll('[data-rol]')).toHaveLength(2)

    await boton(vista, 'Nueva conversación').trigger('click')
    expect(vista.findAll('[data-rol]')).toHaveLength(0)
    expect(vista.text()).toContain('Pregunta lo que quieras sobre tus notas de Notion.')
  })
})
