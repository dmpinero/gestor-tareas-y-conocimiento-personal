import { flushPromises, mount, type DOMWrapper, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Editor } from '@tiptap/vue-3'
import { defineComponent, h } from 'vue'

import { clienteApi } from '@/api/cliente'
import type { Subtarea, Tarea } from '@/api/tipos'
import { useTiendaTareas } from '@/stores/tareas'
import EditorComentario from '../EditorComentario.vue'
import SubtareasTarea from '../SubtareasTarea.vue'

vi.mock('@/api/cliente', () => ({
  clienteApi: {
    obtener: vi.fn<(...args: unknown[]) => unknown>(),
    crear: vi.fn<(...args: unknown[]) => unknown>(),
    actualizar: vi.fn<(...args: unknown[]) => unknown>(),
    parchear: vi.fn<(...args: unknown[]) => unknown>(),
    eliminar: vi.fn<(...args: unknown[]) => unknown>(),
  },
}))

// ProseMirror no admite escribir en jsdom: se fija el contenido con el editor
// que expone EditorComentario, lo que dispara su v-model como al escribir.
async function escribirEnEditor(envoltorio: VueWrapper, etiqueta: string, html: string) {
  const editor = envoltorio
    .findAllComponents(EditorComentario)
    .find((componente) => componente.props('etiqueta') === etiqueta)
  if (!editor) throw new Error(`No hay editor «${etiqueta}»`)
  ;(editor.vm as unknown as { editor: Editor }).editor.commands.setContent(html, {
    emitUpdate: true,
  })
  await flushPromises()
}

const SUBTAREAS: Subtarea[] = [
  {
    id: 20,
    nombre: 'Redactar índice',
    asignado: 'Ana',
    prioridad: 2,
    resuelta: false,
    comentarios: 0,
  },
  {
    id: 21,
    nombre: 'Revisar cifras',
    asignado: null,
    prioridad: null,
    resuelta: true,
    comentarios: 2,
  },
  {
    id: 22,
    nombre: 'Enviar borrador',
    asignado: 'Luis',
    prioridad: 5,
    resuelta: false,
    comentarios: 0,
  },
]

const TAREA: Tarea = {
  id: 1,
  nombre: 'Escribir informe',
  prioridad: null,
  descripcion: '',
  fecha_creacion: '2026-11-09T10:00:00',
  fecha_vencimiento: null,
  etiquetas: [],
  asignados: [],
  tipo: null,
  oportunidad: null,
  completada: false,
  subtareas: SUBTAREAS,
  grupo_estados: null,
  estado: null,
  workflow: null,
}

// Comentarios que devuelve la API para cualquier subtarea.
const COMENTARIOS_SUBTAREA = [
  { id: 1, texto: 'Cifras del T1', creado: '2026-04-01T08:05:00Z', editado: null },
  { id: 2, texto: 'Cifras del T2', creado: '2026-04-02T09:15:00Z', editado: null },
]

const PERSONAS = [
  { id: 1, nombre: 'Ana' },
  { id: 2, nombre: 'Luis' },
]

// Pinta el componente con la tarea que tenga el almacén, como hará el detalle:
// así se comprueba que la respuesta de la API llega a la vista.
const ANFITRION = defineComponent({
  setup() {
    const tienda = useTiendaTareas()
    return () => (tienda.tareas[0] ? h(SubtareasTarea, { tarea: tienda.tareas[0] }) : null)
  },
})

let contenedor: VueWrapper | null = null

async function montar(tarea: Tarea = TAREA): Promise<VueWrapper> {
  vi.mocked(clienteApi.obtener).mockImplementation((ruta) => {
    if (ruta === '/personas') return Promise.resolve(PERSONAS)
    if (ruta === '/etiquetas') return Promise.resolve([])
    if (String(ruta).endsWith('/comentarios')) {
      return Promise.resolve(structuredClone(COMENTARIOS_SUBTAREA))
    }
    return Promise.resolve([tarea])
  })
  const tienda = useTiendaTareas()
  await tienda.cargar()
  await tienda.cargarCatalogos()
  contenedor = mount(ANFITRION, { attachTo: document.body })
  await flushPromises()
  return contenedor
}

function filas(envoltorio: VueWrapper): string[][] {
  return envoltorio
    .findAll('tbody tr')
    .map((fila) => fila.findAll('td').map((celda) => celda.text().trim()))
}

function boton(envoltorio: VueWrapper, etiqueta: string) {
  const encontrado = envoltorio.find(`button[aria-label="${etiqueta}"]`)
  if (!encontrado.exists()) throw new Error(`No hay botón «${etiqueta}»`)
  return encontrado
}

function botonPorTexto(envoltorio: VueWrapper, texto: string) {
  const encontrado = envoltorio.findAll('button').find((b) => b.text().trim() === texto)
  if (!encontrado) throw new Error(`No hay botón con el texto «${texto}»`)
  return encontrado
}

async function abrirAlta(envoltorio: VueWrapper): Promise<void> {
  await botonPorTexto(envoltorio, 'Añadir subtarea').trigger('click')
  await flushPromises()
}

async function escribir(envoltorio: VueWrapper, etiqueta: string, valor: string): Promise<void> {
  const id = envoltorio
    .findAll('label')
    .find((l) => l.text().trim() === etiqueta)
    ?.attributes('for')
  if (!id) throw new Error(`No hay campo «${etiqueta}»`)
  await envoltorio.find(`#${id}`).setValue(valor)
  await flushPromises()
}

function campo(envoltorio: VueWrapper, etiqueta: string): HTMLInputElement {
  const id = envoltorio
    .findAll('label')
    .find((l) => l.text().trim() === etiqueta)
    ?.attributes('for')
  if (!id) throw new Error(`No hay campo «${etiqueta}»`)
  return envoltorio.find(`#${id}`).element as HTMLInputElement
}

// jsdom no maqueta ni tiene ResizeObserver, así que el componente no mide nada
// y pinta la tabla. Para probar las tarjetas se sustituye ResizeObserver por uno
// que informa del ancho indicado al observar, y que deja cambiarlo después.
type AvisoTamano = (
  entradas: { borderBoxSize: { inlineSize: number; blockSize: number }[] }[],
) => void
let avisarTamano: AvisoTamano | null = null

function fijarAncho(ancho: number): void {
  vi.stubGlobal(
    'ResizeObserver',
    class {
      constructor(private readonly llamada: AvisoTamano) {
        avisarTamano = llamada
      }
      observe(): void {
        this.llamada([{ borderBoxSize: [{ inlineSize: ancho, blockSize: 200 }] }])
      }
      unobserve(): void {}
      disconnect(): void {}
    },
  )
}

async function cambiarAncho(ancho: number): Promise<void> {
  avisarTamano?.([{ borderBoxSize: [{ inlineSize: ancho, blockSize: 200 }] }])
  await flushPromises()
}

function tarjetas(envoltorio: VueWrapper) {
  return envoltorio.findAll('[data-testid="tarjeta-subtarea"]')
}

describe('SubtareasTarea', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    contenedor?.unmount()
    contenedor = null
    avisarTamano = null
    vi.unstubAllGlobals()
  })

  describe('diseño según el ancho disponible', () => {
    it('sin medida (ancho desconocido) muestra la tabla y no las tarjetas', async () => {
      const envoltorio = await montar()

      expect(envoltorio.find('table').exists()).toBe(true)
      expect(envoltorio.find('[data-testid="tarjetas-subtareas"]').exists()).toBe(false)
    })

    it('con espacio de sobra muestra la tabla y no las tarjetas', async () => {
      fijarAncho(800)
      const envoltorio = await montar()

      expect(envoltorio.find('table').exists()).toBe(true)
      expect(tarjetas(envoltorio)).toHaveLength(0)
    })

    it('en un hueco estrecho muestra una tarjeta por subtarea y ninguna tabla', async () => {
      fijarAncho(360)
      const envoltorio = await montar()

      expect(envoltorio.find('table').exists()).toBe(false)
      expect(tarjetas(envoltorio)).toHaveLength(3)
      // Un solo control por subtarea en el árbol de accesibilidad.
      const nombres = envoltorio.findAll('button').map((b) => b.attributes('aria-label'))
      expect(nombres.filter((n) => n === 'Editar subtarea Redactar índice')).toHaveLength(1)
    })

    it('cada tarjeta muestra el nombre, la persona y la prioridad etiquetadas, o una raya', async () => {
      fijarAncho(360)
      const envoltorio = await montar()

      const datos = tarjetas(envoltorio).map((tarjeta) => ({
        nombre: tarjeta.get('[data-testid="nombre-subtarea"]').text().trim(),
        etiquetas: tarjeta.findAll('dt').map((dt) => dt.text().trim()),
        valores: tarjeta.findAll('dd').map((dd) => dd.text().trim()),
      }))
      expect(datos).toEqual([
        {
          nombre: 'Redactar índice',
          etiquetas: ['Persona asignada', 'Prioridad'],
          valores: ['Ana', '2'],
        },
        {
          nombre: 'Revisar cifras',
          etiquetas: ['Persona asignada', 'Prioridad'],
          valores: ['—', '—'],
        },
        {
          nombre: 'Enviar borrador',
          etiquetas: ['Persona asignada', 'Prioridad'],
          valores: ['Luis', '5'],
        },
      ])
      // La resuelta se tacha (nombre y valores) pero no sus botones.
      const resuelta = tarjetas(envoltorio)[1]!
      expect(resuelta.findAll('.line-through').map((e) => e.text().trim())).toEqual([
        'Revisar cifras',
        '—',
        '—',
      ])
      expect(resuelta.findAll('button').every((b) => !b.element.closest('.line-through'))).toBe(
        true,
      )
    })

    it('pasa a tarjetas cuando el hueco se estrecha (p. ej. al girar el móvil)', async () => {
      fijarAncho(800)
      const envoltorio = await montar()
      expect(envoltorio.find('table').exists()).toBe(true)

      await cambiarAncho(360)

      expect(envoltorio.find('table').exists()).toBe(false)
      expect(tarjetas(envoltorio)).toHaveLength(3)
    })

    describe('en tarjetas', () => {
      beforeEach(() => {
        fijarAncho(360)
      })

      it('marca como resuelta con el mismo nombre accesible', async () => {
        const envoltorio = await montar()
        vi.mocked(clienteApi.parchear).mockResolvedValue({
          ...TAREA,
          subtareas: [{ ...SUBTAREAS[0]!, resuelta: true }, SUBTAREAS[1]!, SUBTAREAS[2]!],
        })

        await boton(envoltorio, 'Marcar como resuelta la subtarea Redactar índice').trigger('click')
        await flushPromises()

        expect(clienteApi.parchear).toHaveBeenCalledWith('/tareas/1/subtareas/20/resuelta', {
          resuelta: true,
        })
        expect(tarjetas(envoltorio)[0]!.findAll('.line-through')).toHaveLength(3)
      })

      it('elimina tras confirmar en la tarjeta y cancelar devuelve el foco', async () => {
        const envoltorio = await montar()
        await boton(envoltorio, 'Eliminar subtarea Revisar cifras').trigger('click')
        await flushPromises()

        const grupo = tarjetas(envoltorio)[1]!.get('[role="group"]')
        expect(grupo.attributes('aria-label')).toBe('¿Eliminar la subtarea Revisar cifras?')
        expect(document.activeElement?.textContent?.trim()).toBe('Cancelar')

        await botonPorTexto(envoltorio, 'Cancelar').trigger('click')
        await flushPromises()
        expect(document.activeElement?.getAttribute('aria-label')).toBe(
          'Eliminar subtarea Revisar cifras',
        )

        vi.mocked(clienteApi.eliminar).mockResolvedValue({
          ...TAREA,
          subtareas: [SUBTAREAS[0]!, SUBTAREAS[2]!],
        })
        await boton(envoltorio, 'Eliminar subtarea Revisar cifras').trigger('click')
        await flushPromises()
        await botonPorTexto(envoltorio, 'Eliminar').trigger('click')
        await flushPromises()

        expect(clienteApi.eliminar).toHaveBeenCalledWith('/tareas/1/subtareas/21')
        expect(tarjetas(envoltorio)).toHaveLength(2)
      })

      it('edita dentro de la tarjeta con confirmación y Escape no se propaga', async () => {
        const envoltorio = await montar()
        vi.mocked(clienteApi.actualizar).mockResolvedValue({
          ...TAREA,
          subtareas: [{ ...SUBTAREAS[0]!, nombre: 'Otro nombre' }, SUBTAREAS[1]!, SUBTAREAS[2]!],
        })
        await boton(envoltorio, 'Editar subtarea Redactar índice').trigger('click')
        await flushPromises()

        const formulario = tarjetas(envoltorio)[0]!.get('form')
        expect(formulario.attributes('aria-label')).toBe('Editar subtarea Redactar índice')
        const nombre = campo(envoltorio, 'Nuevo nombre de la subtarea Redactar índice')
        expect(document.activeElement).toBe(nombre)
        await escribir(envoltorio, 'Nuevo nombre de la subtarea Redactar índice', 'Otro nombre')
        await formulario.trigger('submit')
        await flushPromises()

        const escuchaVentana = vi.fn<(evento: KeyboardEvent) => void>()
        window.addEventListener('keydown', escuchaVentana)
        await envoltorio.get('[role="group"]').trigger('keydown', { key: 'Escape' })
        await flushPromises()
        window.removeEventListener('keydown', escuchaVentana)
        expect(escuchaVentana).not.toHaveBeenCalled()
        expect(envoltorio.find('[role="group"]').exists()).toBe(false)

        await tarjetas(envoltorio)[0]!.get('form').trigger('submit')
        await flushPromises()
        const grupo = envoltorio.get('[role="group"]')
        expect(grupo.attributes('aria-label')).toBe(
          '¿Guardar los cambios de la subtarea Redactar índice?',
        )
        const guardar = grupo.findAll('button').find((b) => b.text().trim() === 'Guardar')!
        await guardar.trigger('click')
        await flushPromises()

        expect(clienteApi.actualizar).toHaveBeenCalledWith('/tareas/1/subtareas/20', {
          nombre: 'Otro nombre',
          asignado: 'Ana',
          prioridad: 2,
        })
        expect(tarjetas(envoltorio)[0]!.find('form').exists()).toBe(false)
        expect(document.activeElement?.getAttribute('aria-label')).toBe(
          'Editar subtarea Otro nombre',
        )
      })
    })
  })

  describe('comentarios de la subtarea', () => {
    // Nombre accesible del botón: su texto (sin aria-label), que incluye el número
    // visible para cumplir WCAG 2.5.3 (la etiqueta visible forma parte del nombre).
    function nombreAccesible(elemento: { text: () => string }): string {
      return elemento.text().replace(/\s+/g, ' ').trim()
    }

    function botonComentarios(envoltorio: VueWrapper, nombre: string) {
      const prefijo = `Comentarios de la subtarea ${nombre}`
      const encontrado = envoltorio.findAll('button').find((b) => {
        const texto = nombreAccesible(b)
        return texto === prefijo || texto.startsWith(`${prefijo}:`)
      })
      if (!encontrado) throw new Error(`No hay botón «${prefijo}»`)
      return encontrado
    }

    it('cada subtarea tiene un botón de comentarios plegado que muestra cuántos tiene si hay alguno', async () => {
      const envoltorio = await montar()

      for (const subtarea of SUBTAREAS) {
        const elemento = botonComentarios(envoltorio, subtarea.nombre)
        expect(elemento.attributes('aria-expanded')).toBe('false')
        expect(elemento.find('svg').exists()).toBe(true)
      }
      const conComentarios = botonComentarios(envoltorio, 'Revisar cifras')
      expect(conComentarios.attributes('aria-label')).toBeUndefined()
      expect(conComentarios.get('[data-testid="numero-comentarios-subtarea"]').text()).toBe('2')
      expect(nombreAccesible(conComentarios)).toBe('Comentarios de la subtarea Revisar cifras: 2')
      const sinComentarios = botonComentarios(envoltorio, 'Redactar índice')
      expect(sinComentarios.find('[data-testid="numero-comentarios-subtarea"]').exists()).toBe(
        false,
      )
      expect(nombreAccesible(sinComentarios)).toBe('Comentarios de la subtarea Redactar índice')
      expect(clienteApi.obtener).not.toHaveBeenCalledWith(expect.stringContaining('/comentarios'))
    })

    it('en la tabla abre los comentarios en una fila a todo lo ancho bajo la subtarea y los vuelve a plegar', async () => {
      const envoltorio = await montar()

      await botonComentarios(envoltorio, 'Revisar cifras').trigger('click')
      await flushPromises()

      const abierto = botonComentarios(envoltorio, 'Revisar cifras')
      expect(abierto.attributes('aria-expanded')).toBe('true')
      expect(clienteApi.obtener).toHaveBeenCalledWith('/tareas/1/subtareas/21/comentarios')
      const panel = document.getElementById(abierto.attributes('aria-controls')!)!
      const celda = panel.closest('td')!
      expect(celda.getAttribute('colspan')).toBe('4')
      // La fila del panel va justo después de la de su subtarea.
      const filasCuerpo = [...envoltorio.element.querySelectorAll('tbody tr')]
      expect(filasCuerpo.indexOf(celda.closest('tr')!)).toBe(2)
      expect(
        panel.querySelector(
          '[role="region"][aria-label="Comentarios anteriores de la subtarea Revisar cifras"]',
        )?.textContent,
      ).toContain('Cifras del T1')

      await botonComentarios(envoltorio, 'Revisar cifras').trigger('click')
      await flushPromises()
      expect(botonComentarios(envoltorio, 'Revisar cifras').attributes('aria-expanded')).toBe(
        'false',
      )
      expect(envoltorio.findAll('tbody tr')).toHaveLength(3)
    })

    it('solo hay un panel abierto a la vez', async () => {
      const envoltorio = await montar()

      await botonComentarios(envoltorio, 'Revisar cifras').trigger('click')
      await flushPromises()
      await botonComentarios(envoltorio, 'Enviar borrador').trigger('click')
      await flushPromises()

      expect(botonComentarios(envoltorio, 'Revisar cifras').attributes('aria-expanded')).toBe(
        'false',
      )
      expect(botonComentarios(envoltorio, 'Enviar borrador').attributes('aria-expanded')).toBe(
        'true',
      )
      expect(envoltorio.findAll('[aria-label^="Comentarios anteriores"]')).toHaveLength(1)
      expect(clienteApi.obtener).toHaveBeenLastCalledWith('/tareas/1/subtareas/22/comentarios')
    })

    it('al añadir un comentario actualiza el número del botón', async () => {
      vi.mocked(clienteApi.crear).mockResolvedValue({
        id: 3,
        texto: 'Revisadas',
        creado: '2026-04-03T10:00:00Z',
        editado: null,
      })
      const envoltorio = await montar()
      await botonComentarios(envoltorio, 'Revisar cifras').trigger('click')
      await flushPromises()

      await escribirEnEditor(
        envoltorio,
        'Escribe un comentario de la subtarea Revisar cifras',
        '<p>Revisadas</p>',
      )
      await boton(envoltorio, 'Enviar comentario de la subtarea Revisar cifras').trigger('click')
      await flushPromises()

      expect(clienteApi.crear).toHaveBeenCalledWith('/tareas/1/subtareas/21/comentarios', {
        texto: '<p>Revisadas</p>',
      })
      expect(nombreAccesible(botonComentarios(envoltorio, 'Revisar cifras'))).toBe(
        'Comentarios de la subtarea Revisar cifras: 3',
      )
      expect(useTiendaTareas().tareas[0]!.subtareas[1]!.comentarios).toBe(3)
    })

    it('en tarjetas abre los comentarios dentro de la tarjeta de su subtarea', async () => {
      fijarAncho(360)
      const envoltorio = await montar()

      await botonComentarios(envoltorio, 'Redactar índice').trigger('click')
      await flushPromises()

      const abierto = botonComentarios(envoltorio, 'Redactar índice')
      expect(abierto.attributes('aria-expanded')).toBe('true')
      const panel = document.getElementById(abierto.attributes('aria-controls')!)!
      expect(panel.closest('[data-testid="tarjeta-subtarea"]')).toBe(
        tarjetas(envoltorio)[0]!.element,
      )
      expect(
        panel.querySelector(
          '[aria-label="Historial de comentarios de la subtarea Redactar índice"]',
        ),
      ).not.toBeNull()
      // Al cargarlos, el número del botón refleja los que hay de verdad.
      expect(nombreAccesible(botonComentarios(envoltorio, 'Redactar índice'))).toBe(
        'Comentarios de la subtarea Redactar índice: 2',
      )
    })
  })

  describe('listado', () => {
    it('muestra el título, el contador de pendientes y las columnas', async () => {
      const envoltorio = await montar()

      expect(envoltorio.find('h3').text()).toBe('Subtareas')
      expect(envoltorio.find('[data-testid="contador-subtareas"]').text()).toBe('2 sin resolver')
      const cabeceras = envoltorio.findAll('thead th').map((th) => th.text().trim())
      expect(cabeceras.slice(0, 3)).toEqual(['Nombre', 'Persona asignada', 'Prioridad'])
    })

    it('pinta cada subtarea en orden de alta con su persona y su prioridad, o una raya si no tiene', async () => {
      const envoltorio = await montar()

      expect(filas(envoltorio).map((celdas) => celdas.slice(0, 3))).toEqual([
        ['Redactar índice', 'Ana', '2'],
        ['Revisar cifras', '—', '—'],
        ['Enviar borrador', 'Luis', '5'],
      ])
    })

    it('tacha los textos de las resueltas pero no sus botones', async () => {
      const envoltorio = await montar()
      const [pendiente, resuelta] = envoltorio.findAll('tbody tr')

      expect(resuelta!.findAll('.line-through').map((e) => e.text().trim())).toEqual([
        'Revisar cifras',
        '—',
        '—',
      ])
      expect(resuelta!.findAll('button.line-through')).toHaveLength(0)
      expect(resuelta!.findAll('button').every((b) => !b.element.closest('.line-through'))).toBe(
        true,
      )
      expect(pendiente!.findAll('.line-through')).toHaveLength(0)
    })

    it('sin subtareas muestra el estado vacío, sin tabla, y el contador a cero', async () => {
      const envoltorio = await montar({ ...TAREA, subtareas: [] })

      expect(envoltorio.text()).toContain('Esta tarea no tiene subtareas.')
      expect(envoltorio.find('table').exists()).toBe(false)
      expect(envoltorio.find('[data-testid="contador-subtareas"]').text()).toBe('0 sin resolver')
    })
  })

  describe('marcar como resuelta', () => {
    it('el botón refleja el estado con aria-pressed y envía el valor negado', async () => {
      const envoltorio = await montar()
      const botonPendiente = boton(envoltorio, 'Marcar como resuelta la subtarea Redactar índice')
      const botonResuelta = boton(envoltorio, 'Marcar como resuelta la subtarea Revisar cifras')
      expect(botonPendiente.attributes('aria-pressed')).toBe('false')
      expect(botonResuelta.attributes('aria-pressed')).toBe('true')

      const actualizada = {
        ...TAREA,
        subtareas: [{ ...SUBTAREAS[0]!, resuelta: true }, SUBTAREAS[1]!, SUBTAREAS[2]!],
      }
      vi.mocked(clienteApi.parchear).mockResolvedValue(actualizada)
      await botonPendiente.trigger('click')
      await flushPromises()

      expect(clienteApi.parchear).toHaveBeenCalledWith('/tareas/1/subtareas/20/resuelta', {
        resuelta: true,
      })
      expect(
        boton(envoltorio, 'Marcar como resuelta la subtarea Redactar índice').attributes(
          'aria-pressed',
        ),
      ).toBe('true')
      expect(envoltorio.find('[data-testid="contador-subtareas"]').text()).toBe('1 sin resolver')
      expect(envoltorio.find('tbody tr').findAll('.line-through')).toHaveLength(3)
    })

    it('pulsar una resuelta la reabre', async () => {
      const envoltorio = await montar()
      vi.mocked(clienteApi.parchear).mockResolvedValue(TAREA)

      await boton(envoltorio, 'Marcar como resuelta la subtarea Revisar cifras').trigger('click')
      await flushPromises()

      expect(clienteApi.parchear).toHaveBeenCalledWith('/tareas/1/subtareas/21/resuelta', {
        resuelta: false,
      })
    })
  })

  describe('eliminar', () => {
    it('pide confirmación y, al confirmar, envía el DELETE y quita la fila', async () => {
      const envoltorio = await montar()
      await boton(envoltorio, 'Eliminar subtarea Redactar índice').trigger('click')
      await flushPromises()

      expect(clienteApi.eliminar).not.toHaveBeenCalled()
      const confirmacion = envoltorio.find('[role="group"]')
      expect(confirmacion.attributes('aria-label')).toBe('¿Eliminar la subtarea Redactar índice?')
      expect(document.activeElement?.textContent?.trim()).toBe('Cancelar')

      vi.mocked(clienteApi.eliminar).mockResolvedValue({
        ...TAREA,
        subtareas: [SUBTAREAS[1]!, SUBTAREAS[2]!],
      })
      await botonPorTexto(envoltorio, 'Eliminar').trigger('click')
      await flushPromises()

      expect(clienteApi.eliminar).toHaveBeenCalledWith('/tareas/1/subtareas/20')
      expect(filas(envoltorio).map((celdas) => celdas[0])).toEqual([
        'Revisar cifras',
        'Enviar borrador',
      ])
      expect(envoltorio.find('[role="group"]').exists()).toBe(false)
    })

    it('al cancelar no borra nada y devuelve el foco al botón de eliminar', async () => {
      const envoltorio = await montar()
      await boton(envoltorio, 'Eliminar subtarea Revisar cifras').trigger('click')
      await flushPromises()

      await botonPorTexto(envoltorio, 'Cancelar').trigger('click')
      await flushPromises()

      expect(clienteApi.eliminar).not.toHaveBeenCalled()
      expect(envoltorio.find('[role="group"]').exists()).toBe(false)
      expect(filas(envoltorio)).toHaveLength(3)
      expect(document.activeElement?.getAttribute('aria-label')).toBe(
        'Eliminar subtarea Revisar cifras',
      )
    })
  })

  describe('añadir', () => {
    it('el botón "Añadir subtarea" abre la fila de alta con sus campos y el foco en Nombre', async () => {
      const envoltorio = await montar()
      expect(envoltorio.find('form').exists()).toBe(false)

      await abrirAlta(envoltorio)

      const nombre = campo(envoltorio, 'Nombre de la subtarea')
      expect(nombre.maxLength).toBe(200)
      expect(document.activeElement).toBe(nombre)
      expect(campo(envoltorio, 'Persona asignada').maxLength).toBe(100)
      const prioridad = campo(envoltorio, 'Prioridad de la subtarea')
      expect([prioridad.type, prioridad.min, prioridad.max]).toEqual(['number', '1', '5'])
      expect(botonPorTexto(envoltorio, 'Guardar').exists()).toBe(true)
      expect(botonPorTexto(envoltorio, 'Cancelar').exists()).toBe(true)
    })

    it('sugiere las personas del catálogo para la persona asignada', async () => {
      const envoltorio = await montar()
      await abrirAlta(envoltorio)

      const lista = campo(envoltorio, 'Persona asignada').getAttribute('list')
      const opciones = envoltorio
        .findAll(`datalist#${lista} option`)
        .map((o) => o.attributes('value'))
      expect(opciones).toEqual(['Ana', 'Luis'])
    })

    it('sin nombre (o solo espacios) muestra un error y no llama a la API', async () => {
      const envoltorio = await montar()
      await abrirAlta(envoltorio)
      await escribir(envoltorio, 'Nombre de la subtarea', '   ')

      await envoltorio.find('form').trigger('submit')
      await flushPromises()

      expect(envoltorio.find('[role="alert"]').text()).toBe(
        'El nombre de la subtarea es obligatorio.',
      )
      expect(clienteApi.crear).not.toHaveBeenCalled()
    })

    it('con una prioridad fuera de 1–5 muestra un error y no llama a la API', async () => {
      const envoltorio = await montar()
      await abrirAlta(envoltorio)
      await escribir(envoltorio, 'Nombre de la subtarea', 'Algo')
      await escribir(envoltorio, 'Prioridad de la subtarea', '7')

      await envoltorio.find('form').trigger('submit')
      await flushPromises()

      expect(envoltorio.find('[role="alert"]').text()).toBe(
        'La prioridad debe ser un número entero del 1 al 5.',
      )
      expect(clienteApi.crear).not.toHaveBeenCalled()
    })

    it('envía solo el nombre recortado si no hay persona ni prioridad', async () => {
      const envoltorio = await montar()
      vi.mocked(clienteApi.crear).mockResolvedValue(TAREA)
      await abrirAlta(envoltorio)
      await escribir(envoltorio, 'Nombre de la subtarea', '  Preparar anexo  ')
      await escribir(envoltorio, 'Persona asignada', '   ')

      await envoltorio.find('form').trigger('submit')
      await flushPromises()

      expect(clienteApi.crear).toHaveBeenCalledWith('/tareas/1/subtareas', {
        nombre: 'Preparar anexo',
      })
    })

    it('envía persona y prioridad, pinta la subtarea nueva y deja la fila vacía para otra', async () => {
      const envoltorio = await montar()
      const nueva = { id: 23, nombre: 'Maquetar', asignado: 'Marta', prioridad: 3, resuelta: false }
      vi.mocked(clienteApi.crear).mockResolvedValue({
        ...TAREA,
        subtareas: [...SUBTAREAS, nueva],
      })
      await abrirAlta(envoltorio)
      await escribir(envoltorio, 'Nombre de la subtarea', 'Maquetar')
      await escribir(envoltorio, 'Persona asignada', ' Marta ')
      await escribir(envoltorio, 'Prioridad de la subtarea', '3')

      await botonPorTexto(envoltorio, 'Guardar').trigger('click')
      await flushPromises()

      expect(clienteApi.crear).toHaveBeenCalledWith('/tareas/1/subtareas', {
        nombre: 'Maquetar',
        asignado: 'Marta',
        prioridad: 3,
      })
      expect(filas(envoltorio)[3]?.slice(0, 3)).toEqual(['Maquetar', 'Marta', '3'])
      expect(envoltorio.find('[data-testid="contador-subtareas"]').text()).toBe('3 sin resolver')
      expect(envoltorio.find('form').exists()).toBe(true)
      expect(campo(envoltorio, 'Nombre de la subtarea').value).toBe('')
      expect(campo(envoltorio, 'Persona asignada').value).toBe('')
      expect(campo(envoltorio, 'Prioridad de la subtarea').value).toBe('')
      expect(document.activeElement).toBe(campo(envoltorio, 'Nombre de la subtarea'))
      // Tras guardar se refresca el catálogo de personas por si "Marta" es nueva.
      expect(clienteApi.obtener).toHaveBeenCalledWith('/personas')
    })

    it('si la API falla conserva lo escrito', async () => {
      const envoltorio = await montar()
      vi.mocked(clienteApi.crear).mockRejectedValue(new Error('Error del servidor'))
      await abrirAlta(envoltorio)
      await escribir(envoltorio, 'Nombre de la subtarea', 'Maquetar')

      await envoltorio.find('form').trigger('submit')
      await flushPromises()

      expect(useTiendaTareas().error).toBe('Error del servidor')
      expect(campo(envoltorio, 'Nombre de la subtarea').value).toBe('Maquetar')
    })

    it('Cancelar cierra la fila sin llamar a la API y la vuelve a abrir vacía', async () => {
      const envoltorio = await montar()
      await abrirAlta(envoltorio)
      await escribir(envoltorio, 'Nombre de la subtarea', 'Borrador')

      await botonPorTexto(envoltorio, 'Cancelar').trigger('click')
      await flushPromises()

      expect(envoltorio.find('form').exists()).toBe(false)
      expect(clienteApi.crear).not.toHaveBeenCalled()
      expect(document.activeElement?.textContent?.trim()).toBe('Añadir subtarea')
      await abrirAlta(envoltorio)
      expect(campo(envoltorio, 'Nombre de la subtarea').value).toBe('')
    })

    it('Escape cancela la fila de alta sin propagarse (no cierra el detalle que la contiene)', async () => {
      const envoltorio = await montar()
      await abrirAlta(envoltorio)
      const escuchaVentana = vi.fn<(evento: KeyboardEvent) => void>()
      window.addEventListener('keydown', escuchaVentana)

      await envoltorio.find('form').trigger('keydown', { key: 'Escape' })
      await flushPromises()
      window.removeEventListener('keydown', escuchaVentana)

      expect(envoltorio.find('form').exists()).toBe(false)
      expect(clienteApi.crear).not.toHaveBeenCalled()
      expect(escuchaVentana).not.toHaveBeenCalled()
    })
  })

  describe('editar', () => {
    async function abrirEdicion(envoltorio: VueWrapper, nombre: string): Promise<void> {
      await boton(envoltorio, `Editar subtarea ${nombre}`).trigger('click')
      await flushPromises()
    }

    function grupoConfirmacion(envoltorio: VueWrapper) {
      return envoltorio.find('[role="group"]')
    }

    function formularioEdicion(envoltorio: VueWrapper) {
      return envoltorio.get('tbody form')
    }

    function botonDe(contenedor: Pick<DOMWrapper<Element>, 'findAll'>, texto: string) {
      const encontrado = contenedor.findAll('button').find((b) => b.text().trim() === texto)
      if (!encontrado) throw new Error(`No hay botón con el texto «${texto}»`)
      return encontrado
    }

    it('cada fila tiene un botón "Editar subtarea" con un nombre accesible único', async () => {
      const envoltorio = await montar()

      const nombres = envoltorio
        .findAll('tbody button')
        .map((b) => b.attributes('aria-label') ?? b.text().replace(/\s+/g, ' ').trim())
      expect(nombres).toContain('Editar subtarea Redactar índice')
      expect(nombres).toContain('Editar subtarea Revisar cifras')
      expect(nombres).toContain('Editar subtarea Enviar borrador')
      expect(new Set(nombres).size).toBe(nombres.length)
    })

    it('convierte la fila en un formulario relleno con sus datos y el foco en el nombre', async () => {
      const envoltorio = await montar()

      await abrirEdicion(envoltorio, 'Redactar índice')

      const nombre = campo(envoltorio, 'Nuevo nombre de la subtarea Redactar índice')
      expect(nombre.value).toBe('Redactar índice')
      expect(nombre.maxLength).toBe(200)
      expect(document.activeElement).toBe(nombre)
      const persona = campo(envoltorio, 'Nueva persona asignada de la subtarea Redactar índice')
      expect(persona.value).toBe('Ana')
      expect(persona.maxLength).toBe(100)
      const opciones = envoltorio
        .findAll(`datalist#${persona.getAttribute('list')} option`)
        .map((o) => o.attributes('value'))
      expect(opciones).toEqual(['Ana', 'Luis'])
      const prioridad = campo(envoltorio, 'Nueva prioridad de la subtarea Redactar índice')
      expect([prioridad.type, prioridad.min, prioridad.max, prioridad.value]).toEqual([
        'number',
        '1',
        '5',
        '2',
      ])
      expect(botonDe(formularioEdicion(envoltorio), 'Guardar').exists()).toBe(true)
      expect(botonDe(formularioEdicion(envoltorio), 'Cancelar').exists()).toBe(true)
      // El resto de filas sigue igual.
      expect(filas(envoltorio)[1]?.slice(0, 3)).toEqual(['Revisar cifras', '—', '—'])
    })

    it('rellena vacíos la persona y la prioridad si la subtarea no las tiene', async () => {
      const envoltorio = await montar()

      await abrirEdicion(envoltorio, 'Revisar cifras')

      expect(campo(envoltorio, 'Nueva persona asignada de la subtarea Revisar cifras').value).toBe(
        '',
      )
      expect(campo(envoltorio, 'Nueva prioridad de la subtarea Revisar cifras').value).toBe('')
    })

    it('los campos de edición no repiten ids ni nombres con la fila de alta abierta', async () => {
      const envoltorio = await montar()
      await abrirAlta(envoltorio)
      await abrirEdicion(envoltorio, 'Redactar índice')

      const ids = [...document.querySelectorAll('[id]')].map((elemento) => elemento.id)
      expect(new Set(ids).size).toBe(ids.length)
      const etiquetas = envoltorio.findAll('label').map((l) => l.text().trim())
      expect(new Set(etiquetas).size).toBe(etiquetas.length)
    })

    it('sin nombre muestra un error y no pide confirmación ni llama a la API', async () => {
      const envoltorio = await montar()
      await abrirEdicion(envoltorio, 'Redactar índice')
      await escribir(envoltorio, 'Nuevo nombre de la subtarea Redactar índice', '  ')

      await formularioEdicion(envoltorio).trigger('submit')
      await flushPromises()

      expect(envoltorio.get('[role="alert"]').text()).toBe(
        'El nombre de la subtarea es obligatorio.',
      )
      expect(grupoConfirmacion(envoltorio).exists()).toBe(false)
      expect(clienteApi.actualizar).not.toHaveBeenCalled()
    })

    it('con una prioridad fuera de 1–5 muestra un error y no llama a la API', async () => {
      const envoltorio = await montar()
      await abrirEdicion(envoltorio, 'Redactar índice')
      await escribir(envoltorio, 'Nueva prioridad de la subtarea Redactar índice', '0')

      await formularioEdicion(envoltorio).trigger('submit')
      await flushPromises()

      expect(envoltorio.get('[role="alert"]').text()).toBe(
        'La prioridad debe ser un número entero del 1 al 5.',
      )
      expect(clienteApi.actualizar).not.toHaveBeenCalled()
    })

    it('Guardar pide confirmación en línea antes de llamar a la API', async () => {
      const envoltorio = await montar()
      await abrirEdicion(envoltorio, 'Redactar índice')

      await botonDe(formularioEdicion(envoltorio), 'Guardar').trigger('click')
      await flushPromises()

      const grupo = grupoConfirmacion(envoltorio)
      expect(grupo.attributes('aria-label')).toBe(
        '¿Guardar los cambios de la subtarea Redactar índice?',
      )
      expect(botonDe(grupo, 'Guardar').exists()).toBe(true)
      expect(botonDe(grupo, 'Cancelar').exists()).toBe(true)
      expect(document.activeElement).toBe(botonDe(grupo, 'Cancelar').element)
      expect(clienteApi.actualizar).not.toHaveBeenCalled()
    })

    it('al confirmar envía el reemplazo completo (vacía persona y prioridad), pinta la fila y devuelve el foco', async () => {
      const envoltorio = await montar()
      const editada = {
        ...SUBTAREAS[0]!,
        nombre: 'Redactar el índice',
        asignado: null,
        prioridad: null,
      }
      vi.mocked(clienteApi.actualizar).mockResolvedValue({
        ...TAREA,
        subtareas: [editada, SUBTAREAS[1]!, SUBTAREAS[2]!],
      })
      await abrirEdicion(envoltorio, 'Redactar índice')
      await escribir(
        envoltorio,
        'Nuevo nombre de la subtarea Redactar índice',
        ' Redactar el índice ',
      )
      await escribir(envoltorio, 'Nueva persona asignada de la subtarea Redactar índice', '  ')
      await escribir(envoltorio, 'Nueva prioridad de la subtarea Redactar índice', '')
      await formularioEdicion(envoltorio).trigger('submit')
      await flushPromises()
      vi.mocked(clienteApi.obtener).mockClear()

      await botonDe(grupoConfirmacion(envoltorio), 'Guardar').trigger('click')
      await flushPromises()

      expect(clienteApi.actualizar).toHaveBeenCalledWith('/tareas/1/subtareas/20', {
        nombre: 'Redactar el índice',
        asignado: null,
        prioridad: null,
      })
      expect(envoltorio.find('tbody form').exists()).toBe(false)
      expect(grupoConfirmacion(envoltorio).exists()).toBe(false)
      expect(filas(envoltorio)[0]?.slice(0, 3)).toEqual(['Redactar el índice', '—', '—'])
      expect(document.activeElement?.getAttribute('aria-label')).toBe(
        'Editar subtarea Redactar el índice',
      )
      expect(clienteApi.obtener).toHaveBeenCalledWith('/personas')
    })

    it('envía la persona y la prioridad editadas', async () => {
      const envoltorio = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue(TAREA)
      await abrirEdicion(envoltorio, 'Revisar cifras')
      await escribir(envoltorio, 'Nueva persona asignada de la subtarea Revisar cifras', ' Marta ')
      await escribir(envoltorio, 'Nueva prioridad de la subtarea Revisar cifras', '4')
      await formularioEdicion(envoltorio).trigger('submit')
      await flushPromises()

      await botonDe(grupoConfirmacion(envoltorio), 'Guardar').trigger('click')
      await flushPromises()

      expect(clienteApi.actualizar).toHaveBeenCalledWith('/tareas/1/subtareas/21', {
        nombre: 'Revisar cifras',
        asignado: 'Marta',
        prioridad: 4,
      })
    })

    it('Cancelar en la confirmación vuelve al formulario con lo escrito y no llama a la API', async () => {
      const envoltorio = await montar()
      await abrirEdicion(envoltorio, 'Redactar índice')
      await escribir(envoltorio, 'Nuevo nombre de la subtarea Redactar índice', 'Otro nombre')
      await formularioEdicion(envoltorio).trigger('submit')
      await flushPromises()

      await botonDe(grupoConfirmacion(envoltorio), 'Cancelar').trigger('click')
      await flushPromises()

      expect(grupoConfirmacion(envoltorio).exists()).toBe(false)
      const nombre = campo(envoltorio, 'Nuevo nombre de la subtarea Redactar índice')
      expect(nombre.value).toBe('Otro nombre')
      expect(document.activeElement).toBe(nombre)
      expect(clienteApi.actualizar).not.toHaveBeenCalled()
    })

    it('Escape en la confirmación vuelve al formulario sin propagarse', async () => {
      const envoltorio = await montar()
      await abrirEdicion(envoltorio, 'Redactar índice')
      await formularioEdicion(envoltorio).trigger('submit')
      await flushPromises()
      const escuchaVentana = vi.fn<(evento: KeyboardEvent) => void>()
      window.addEventListener('keydown', escuchaVentana)

      await grupoConfirmacion(envoltorio).trigger('keydown', { key: 'Escape' })
      await flushPromises()
      window.removeEventListener('keydown', escuchaVentana)

      expect(grupoConfirmacion(envoltorio).exists()).toBe(false)
      expect(envoltorio.find('tbody form').exists()).toBe(true)
      expect(escuchaVentana).not.toHaveBeenCalled()
      expect(clienteApi.actualizar).not.toHaveBeenCalled()
    })

    it('Cancelar en el formulario restaura la fila y devuelve el foco al botón de editar', async () => {
      const envoltorio = await montar()
      await abrirEdicion(envoltorio, 'Redactar índice')
      await escribir(envoltorio, 'Nuevo nombre de la subtarea Redactar índice', 'Otro nombre')

      await botonDe(formularioEdicion(envoltorio), 'Cancelar').trigger('click')
      await flushPromises()

      expect(envoltorio.find('tbody form').exists()).toBe(false)
      expect(filas(envoltorio)[0]?.slice(0, 3)).toEqual(['Redactar índice', 'Ana', '2'])
      expect(document.activeElement?.getAttribute('aria-label')).toBe(
        'Editar subtarea Redactar índice',
      )
      expect(clienteApi.actualizar).not.toHaveBeenCalled()
    })

    it('Escape en el formulario cancela la edición sin propagarse', async () => {
      const envoltorio = await montar()
      await abrirEdicion(envoltorio, 'Redactar índice')
      const escuchaVentana = vi.fn<(evento: KeyboardEvent) => void>()
      window.addEventListener('keydown', escuchaVentana)

      await formularioEdicion(envoltorio).trigger('keydown', { key: 'Escape' })
      await flushPromises()
      window.removeEventListener('keydown', escuchaVentana)

      expect(envoltorio.find('tbody form').exists()).toBe(false)
      expect(escuchaVentana).not.toHaveBeenCalled()
      expect(document.activeElement?.getAttribute('aria-label')).toBe(
        'Editar subtarea Redactar índice',
      )
    })

    it('si la API falla conserva lo escrito en el formulario', async () => {
      const envoltorio = await montar()
      vi.mocked(clienteApi.actualizar).mockRejectedValue(new Error('Error del servidor'))
      await abrirEdicion(envoltorio, 'Redactar índice')
      await escribir(envoltorio, 'Nuevo nombre de la subtarea Redactar índice', 'Otro nombre')
      await formularioEdicion(envoltorio).trigger('submit')
      await flushPromises()

      await botonDe(grupoConfirmacion(envoltorio), 'Guardar').trigger('click')
      await flushPromises()

      expect(useTiendaTareas().error).toBe('Error del servidor')
      expect(grupoConfirmacion(envoltorio).exists()).toBe(false)
      const nombre = campo(envoltorio, 'Nuevo nombre de la subtarea Redactar índice')
      expect(nombre.value).toBe('Otro nombre')
      expect(document.activeElement).toBe(nombre)
    })
  })
})
