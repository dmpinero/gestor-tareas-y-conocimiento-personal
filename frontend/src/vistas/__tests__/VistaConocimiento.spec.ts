import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import * as api from '@/api/conocimiento'
import type { EstadoConocimiento, OpcionesPreguntar } from '@/api/conocimiento'
import type { ResultadoBusquedaConocimiento } from '@/api/tipos'
import VistaConocimiento from '../VistaConocimiento.vue'

vi.mock('@/api/conocimiento', async (original) => ({
  ...(await original()),
  obtenerEstado: vi.fn(),
  sincronizar: vi.fn(),
  preguntar: vi.fn(),
  buscar: vi.fn(),
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

  it('sin credenciales avisa solo de NOTION_TOKEN, desactiva sincronizar y no muestra el chat', async () => {
    const vista = await montar({
      ...CONFIGURADO,
      configurado: { notion: false, anthropic: false },
    })
    expect(vista.get('[data-testid="falta-notion"]').text()).toContain(
      'Falta configurar NOTION_TOKEN en backend/.env',
    )
    expect(vista.text()).not.toContain('ANTHROPIC_API_KEY')
    expect(vista.find('[data-testid="falta-anthropic"]').exists()).toBe(false)
    expect(boton(vista, 'Sincronizar con Notion').attributes('disabled')).toBeDefined()
    expect(vista.find('[data-testid="chat-conocimiento"]').exists()).toBe(false)
    expect(vista.find('textarea').exists()).toBe(false)
    expect(vista.findAll('button').some((b) => b.text() === 'Enviar')).toBe(false)
    // El buscador sí está: no necesita credenciales.
    await vista.get('#busqueda-conocimiento').setValue('paella')
    expect(boton(vista, 'Buscar').attributes('disabled')).toBeUndefined()
  })

  it('con ANTHROPIC_API_KEY muestra el chat debajo del buscador', async () => {
    const vista = await montar()
    const chat = vista.get('[data-testid="chat-conocimiento"]')
    expect(chat.text()).toContain('Pregunta lo que quieras sobre tus notas de Notion.')
    const buscador = vista.get('[data-testid="buscador-conocimiento"]').element
    expect(
      buscador.compareDocumentPosition(chat.element) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
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

  describe('buscador', () => {
    const SIN_CHAT: EstadoConocimiento = {
      ...CONFIGURADO,
      configurado: { notion: true, anthropic: false },
      ultima_sincronizacion: '2026-11-26T10:00:00Z',
    }

    function resultado(
      id: string,
      orden: number,
      fragmento: string,
      url = `https://www.notion.so/${id}`,
    ): ResultadoBusquedaConocimiento {
      return { pagina_id: id, titulo: `Página ${id}`, url, fragmento, orden }
    }

    async function buscar(vista: VueWrapper, texto: string, conEnter = false): Promise<void> {
      const campo = vista.get('#busqueda-conocimiento')
      await campo.setValue(texto)
      if (conEnter) await vista.get('[data-testid="buscador-conocimiento"] form').trigger('submit')
      else await boton(vista, 'Buscar').trigger('click')
      await flushPromises()
    }

    it('tiene el campo «Buscar en tus notas» y el botón Buscar, desactivado si está vacío', async () => {
      const vista = await montar(SIN_CHAT)
      expect(vista.get('label[for="busqueda-conocimiento"]').text()).toBe('Buscar en tus notas')
      expect(boton(vista, 'Buscar').attributes('disabled')).toBeDefined()
      await vista.get('#busqueda-conocimiento').setValue('   ')
      expect(boton(vista, 'Buscar').attributes('disabled')).toBeDefined()
      expect(vista.get('#busqueda-conocimiento').attributes('maxlength')).toBe('200')
    })

    it('Enter busca', async () => {
      vi.mocked(api.buscar).mockResolvedValue([])
      const vista = await montar(SIN_CHAT)
      await vista.get('#busqueda-conocimiento').setValue('paella')
      await vista.get('[data-testid="buscador-conocimiento"] form').trigger('submit')
      await flushPromises()
      expect(api.buscar).toHaveBeenCalledWith('paella')
    })

    it('agrupa los resultados por página con el título enlazado a Notion en una pestaña nueva', async () => {
      vi.mocked(api.buscar).mockResolvedValue([
        resultado('b', 2, 'Segundo trozo con paella'),
        resultado('a', 0, 'La paella de la abuela'),
        resultado('b', 0, 'Primer trozo con paella'),
      ])
      const vista = await montar(SIN_CHAT)
      await buscar(vista, 'paella', true)

      expect(api.buscar).toHaveBeenCalledWith('paella')
      const grupos = vista.findAll('[data-testid="resultado-pagina"]')
      expect(grupos).toHaveLength(2)
      const enlace = grupos[0]!.get('a')
      expect(enlace.text()).toBe('Página b')
      expect(enlace.attributes('href')).toBe('https://www.notion.so/b')
      expect(enlace.attributes('target')).toBe('_blank')
      expect(enlace.attributes('rel')).toBe('noopener noreferrer')
      expect(
        grupos[0]!.findAll('[data-testid="fragmento-resultado"]').map((f) => f.text()),
      ).toEqual(['Primer trozo con paella', 'Segundo trozo con paella'])
      expect(grupos[1]!.text()).toContain('La paella de la abuela')
    })

    it('el título de una página con una URL que no es http(s) no es un enlace', async () => {
      vi.mocked(api.buscar).mockResolvedValue([resultado('a', 0, 'paella', 'javascript:alert(1)')])
      const vista = await montar(SIN_CHAT)
      await buscar(vista, 'paella')

      const grupo = vista.get('[data-testid="resultado-pagina"]')
      expect(grupo.find('a').exists()).toBe(false)
      expect(grupo.text()).toContain('Página a')
    })

    it('resalta las palabras buscadas sin distinguir mayúsculas ni tildes', async () => {
      vi.mocked(api.buscar).mockResolvedValue([
        resultado('a', 0, 'La PAELLA lleva azafrán y arroz.'),
      ])
      const vista = await montar(SIN_CHAT)
      await buscar(vista, 'paella Azafran')

      const marcas = vista.findAll('[data-testid="fragmento-resultado"] mark')
      expect(marcas.map((m) => m.text())).toEqual(['PAELLA', 'azafrán'])
      // Sin espacios de más: el trozo se pinta con `white-space: pre-wrap`.
      expect(vista.get('[data-testid="fragmento-resultado"]').element.textContent).toBe(
        'La PAELLA lleva azafrán y arroz.',
      )
    })

    it('el HTML de un fragmento se muestra como texto', async () => {
      vi.mocked(api.buscar).mockResolvedValue([
        resultado('a', 0, '<img src=x onerror="alert(1)"><b>paella</b>'),
      ])
      const vista = await montar(SIN_CHAT)
      await buscar(vista, 'paella')

      const fragmento = vista.get('[data-testid="fragmento-resultado"]')
      expect(fragmento.find('img').exists()).toBe(false)
      expect(fragmento.find('b').exists()).toBe(false)
      expect(fragmento.text()).toBe('<img src=x onerror="alert(1)"><b>paella</b>')
      expect(fragmento.get('mark').text()).toBe('paella')
    })

    it('resalta lo que se buscó, no lo que se está escribiendo después', async () => {
      vi.mocked(api.buscar).mockResolvedValue([resultado('a', 0, 'paella y arroz')])
      const vista = await montar(SIN_CHAT)
      await buscar(vista, 'paella')
      await vista.get('#busqueda-conocimiento').setValue('arroz')

      expect(vista.findAll('mark').map((m) => m.text())).toEqual(['paella'])
    })

    it('sin resultados lo dice', async () => {
      vi.mocked(api.buscar).mockResolvedValue([])
      const vista = await montar(SIN_CHAT)
      expect(vista.text()).not.toContain('No he encontrado nada')
      await buscar(vista, 'dentista')

      expect(vista.get('[data-testid="sin-resultados"]').text()).toBe(
        'No he encontrado nada sobre eso en tus notas de Notion.',
      )
      expect(vista.find('[data-testid="resultado-pagina"]').exists()).toBe(false)
    })

    it('sin sincronizar nunca invita a «Sincronizar con Notion»', async () => {
      const vista = await montar({
        ...SIN_CHAT,
        paginas: 0,
        fragmentos: 0,
        ultima_sincronizacion: null,
      })
      expect(vista.get('[data-testid="invitar-sincronizar"]').text()).toContain(
        '«Sincronizar con Notion»',
      )
    })

    it('ya sincronizado no invita a sincronizar', async () => {
      const vista = await montar(SIN_CHAT)
      expect(vista.find('[data-testid="invitar-sincronizar"]').exists()).toBe(false)
    })

    it('si la búsqueda falla muestra el error como alerta', async () => {
      vi.mocked(api.buscar).mockRejectedValue(new Error('La API no responde'))
      const vista = await montar(SIN_CHAT)
      await buscar(vista, 'paella')

      expect(vista.get('[data-testid="buscador-conocimiento"] [role="alert"]').text()).toContain(
        'La API no responde',
      )
    })
  })
})
