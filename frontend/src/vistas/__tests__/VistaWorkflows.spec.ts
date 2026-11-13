import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { clienteApi, ErrorApi } from '@/api/cliente'
import type { Workflow } from '@/api/tipos'
import VistaWorkflows from '../VistaWorkflows.vue'

vi.mock('@/api/cliente', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('@/api/cliente')>()
  return {
    ...original,
    clienteApi: {
      obtener: vi.fn<(...args: unknown[]) => unknown>(),
      crear: vi.fn<(...args: unknown[]) => unknown>(),
      actualizar: vi.fn<(...args: unknown[]) => unknown>(),
      eliminar: vi.fn<(...args: unknown[]) => unknown>(),
    },
  }
})

const RUTA = '/workflows'

const OPORTUNIDADES: Workflow = {
  id: 1,
  nombre: 'Workflow Oportunidades',
  pasos: [
    { id: 10, numero: 1, nombre: 'Contacto inicial' },
    { id: 11, numero: 2, nombre: 'Propuesta' },
    { id: 12, numero: 3, nombre: 'Cierre' },
  ],
}
const ALTAS: Workflow = { id: 2, nombre: 'Altas', pasos: [] }

// Workflow "Workflow Oportunidades" con los pasos en el orden de los ids dados.
function oportunidadesSegun(ids: number[]): Workflow {
  return {
    ...OPORTUNIDADES,
    pasos: ids.map((id, indice) => ({
      ...OPORTUNIDADES.pasos.find((paso) => paso.id === id)!,
      numero: indice + 1,
    })),
  }
}

let contenedor: VueWrapper | undefined

async function montar(workflows: Workflow[] = [OPORTUNIDADES, ALTAS]): Promise<VueWrapper> {
  vi.mocked(clienteApi.obtener).mockResolvedValue(structuredClone(workflows))
  const enrutador = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/ajustes', component: { template: '<div />' } },
      { path: '/ajustes/workflows', component: VistaWorkflows },
    ],
  })
  await enrutador.push('/ajustes/workflows')
  contenedor = mount(VistaWorkflows, {
    global: { plugins: [createPinia(), enrutador] },
    attachTo: document.body,
  })
  await flushPromises()
  return contenedor
}

function boton(vista: VueWrapper, etiqueta: string) {
  return vista.get(`button[aria-label="${etiqueta}"]`)
}

function textosPasos(vista: VueWrapper, workflow: string): string[] {
  return vista
    .get(`ol[aria-label="Pasos de ${workflow}"]`)
    .findAll('[data-paso]')
    .map((fila) => fila.get('[data-texto-paso]').text())
}

function dialogo(): HTMLElement {
  const elemento = document.body.querySelector<HTMLElement>('[role="alertdialog"]')
  if (!elemento) throw new Error('No se abrió la confirmación')
  return elemento
}

function botonDialogo(texto: string): HTMLButtonElement {
  const encontrado = [...dialogo().querySelectorAll('button')].find(
    (b) => b.textContent?.trim() === texto,
  )
  if (!encontrado) throw new Error(`No se encontró el botón "${texto}"`)
  return encontrado
}

// jsdom no tiene `DataTransfer`: basta con un objeto con lo que usa la vista.
function crearDataTransfer() {
  const datos: Record<string, string> = {}
  return {
    effectAllowed: 'none',
    dropEffect: 'none',
    setData: (tipo: string, valor: string) => {
      datos[tipo] = valor
    },
    getData: (tipo: string) => datos[tipo] ?? '',
  }
}

function lanzarEventoArrastre(elemento: Element, tipo: string, dataTransfer: object): void {
  const evento = new Event(tipo, { bubbles: true, cancelable: true })
  Object.defineProperty(evento, 'dataTransfer', { value: dataTransfer })
  elemento.dispatchEvent(evento)
}

describe('VistaWorkflows', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    contenedor?.unmount()
    contenedor = undefined
    document.body.innerHTML = ''
  })

  it('muestra el título y un enlace de vuelta a Ajustes', async () => {
    const vista = await montar()

    expect(vista.get('h2').text()).toBe('Workflows')
    expect(vista.get('a[href="/ajustes"]').text()).toContain('Ajustes')
  })

  it('lista los workflows con sus pasos por número como "<numero>. <nombre>"', async () => {
    const desordenado = { ...OPORTUNIDADES, pasos: [...OPORTUNIDADES.pasos].reverse() }
    const vista = await montar([desordenado, ALTAS])

    expect(clienteApi.obtener).toHaveBeenCalledWith(RUTA)
    const workflows = vista.get('ul[aria-label="Workflows"]').findAll('[data-workflow]')
    expect(workflows.map((w) => w.get('h3').text())).toEqual(['Workflow Oportunidades', 'Altas'])
    expect(textosPasos(vista, 'Workflow Oportunidades')).toEqual([
      '1. Contacto inicial',
      '2. Propuesta',
      '3. Cierre',
    ])
    expect(workflows[1]!.text()).toContain('Este workflow todavía no tiene pasos.')
  })

  it('muestra un estado vacío si no hay workflows', async () => {
    const vista = await montar([])

    expect(vista.text()).toContain('Todavía no hay workflows.')
    expect(vista.findAll('[data-workflow]')).toHaveLength(0)
  })

  describe('workflows', () => {
    it('el campo "Nombre del workflow" es obligatorio y admite como mucho 50 caracteres', async () => {
      const vista = await montar()

      const campo = vista.get('input#nombre-workflow-nuevo')
      expect(vista.get('label[for="nombre-workflow-nuevo"]').text()).toBe('Nombre del workflow')
      expect(campo.attributes('required')).toBeDefined()
      expect(campo.attributes('maxlength')).toBe('50')
    })

    it('crea un workflow con POST y vacía el campo', async () => {
      const vista = await montar([OPORTUNIDADES])
      vi.mocked(clienteApi.crear).mockResolvedValue(structuredClone(ALTAS))

      await vista.get('input#nombre-workflow-nuevo').setValue('  Altas  ')
      await vista.get('form[aria-label="Añadir workflow"]').trigger('submit')
      await flushPromises()

      expect(clienteApi.crear).toHaveBeenCalledWith(RUTA, { nombre: 'Altas' })
      const nombres = vista.findAll('[data-workflow] h3').map((h) => h.text())
      expect(nombres).toEqual(['Workflow Oportunidades', 'Altas'])
      expect((vista.get('input#nombre-workflow-nuevo').element as HTMLInputElement).value).toBe('')
    })

    it('no envía un nombre de workflow vacío y muestra el error', async () => {
      const vista = await montar()

      await vista.get('input#nombre-workflow-nuevo').setValue('   ')
      await vista.get('form[aria-label="Añadir workflow"]').trigger('submit')
      await flushPromises()

      expect(clienteApi.crear).not.toHaveBeenCalled()
      expect(vista.get('[role="alert"]').text()).toBe('El nombre del workflow es obligatorio.')
    })

    it('no envía un nombre de workflow de más de 50 caracteres', async () => {
      const vista = await montar()

      await vista.get('input#nombre-workflow-nuevo').setValue('a'.repeat(51))
      await vista.get('form[aria-label="Añadir workflow"]').trigger('submit')
      await flushPromises()

      expect(clienteApi.crear).not.toHaveBeenCalled()
      expect(vista.get('[role="alert"]').text()).toBe(
        'El nombre del workflow no puede superar los 50 caracteres.',
      )
    })

    it('muestra el error de la API en una alerta', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.crear).mockRejectedValue(new ErrorApi(409, 'Ya existe un workflow'))

      await vista.get('input#nombre-workflow-nuevo').setValue('altas')
      await vista.get('form[aria-label="Añadir workflow"]').trigger('submit')
      await flushPromises()

      expect(vista.get('[role="alert"]').text()).toBe('Ya existe un workflow')
      expect(vista.findAll('[data-workflow]')).toHaveLength(2)
    })

    it('renombra un workflow en línea con PUT', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue({ ...ALTAS, nombre: 'Bajas' })

      await boton(vista, 'Renombrar workflow Altas').trigger('click')
      await flushPromises()
      expect(document.activeElement?.id).toBe('nombre-workflow-2')
      const campo = vista.get('input[aria-label="Nuevo nombre del workflow Altas"]')
      expect((campo.element as HTMLInputElement).value).toBe('Altas')
      await campo.setValue('Bajas')
      await flushPromises()
      await vista.get('form[aria-label="Renombrar workflow Altas"]').trigger('submit')
      await flushPromises()

      expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/2`, { nombre: 'Bajas' })
      expect(vista.findAll('[data-workflow] h3').map((h) => h.text())).toEqual([
        'Workflow Oportunidades',
        'Bajas',
      ])
    })

    it('al eliminar un workflow avisa de que las tareas conservan sus subtareas y lo borra al confirmar', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)

      await boton(vista, 'Eliminar workflow Workflow Oportunidades').trigger('click')
      await flushPromises()
      expect(dialogo().textContent).toContain('¿Eliminar el workflow Workflow Oportunidades?')
      expect(dialogo().textContent).toContain(
        'Las tareas con este workflow quedarán sin workflow y conservarán sus subtareas.',
      )
      expect(clienteApi.eliminar).not.toHaveBeenCalled()

      botonDialogo('Eliminar').click()
      await flushPromises()

      expect(clienteApi.eliminar).toHaveBeenCalledWith(`${RUTA}/1`)
      expect(vista.findAll('[data-workflow] h3').map((h) => h.text())).toEqual(['Altas'])
      expect(document.body.querySelector('[role="alertdialog"]')).toBeNull()
      expect(document.activeElement?.id).toBe('nombre-workflow-nuevo')
    })

    it('cancelar la confirmación no elimina el workflow', async () => {
      const vista = await montar()

      await boton(vista, 'Eliminar workflow Altas').trigger('click')
      await flushPromises()
      botonDialogo('Cancelar').click()
      await flushPromises()

      expect(clienteApi.eliminar).not.toHaveBeenCalled()
      expect(vista.findAll('[data-workflow]')).toHaveLength(2)
    })

    it('si la API rechaza el borrado, muestra el error dentro de la confirmación', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.eliminar).mockRejectedValue(new ErrorApi(404, 'No existe'))

      await boton(vista, 'Eliminar workflow Altas').trigger('click')
      await flushPromises()
      botonDialogo('Eliminar').click()
      await flushPromises()

      expect(dialogo().querySelector('[role="alert"]')?.textContent).toBe('No existe')
      expect(vista.findAll('[data-workflow]')).toHaveLength(2)
    })
  })

  describe('pasos', () => {
    it('añade un paso al workflow con POST y vacía el campo', async () => {
      const vista = await montar()
      const conPaso: Workflow = { ...ALTAS, pasos: [{ id: 20, numero: 1, nombre: 'Alta' }] }
      vi.mocked(clienteApi.crear).mockResolvedValue(conPaso)

      const campo = vista.get('input[aria-label="Nuevo paso de Altas"]')
      expect(campo.attributes('required')).toBeDefined()
      expect(campo.attributes('maxlength')).toBe('50')
      await campo.setValue('  Alta  ')
      await flushPromises()
      await vista.get('form[aria-label="Añadir paso a Altas"]').trigger('submit')
      await flushPromises()

      expect(clienteApi.crear).toHaveBeenCalledWith(`${RUTA}/2/pasos`, { nombre: 'Alta' })
      expect(textosPasos(vista, 'Altas')).toEqual(['1. Alta'])
      expect(
        (vista.get('input[aria-label="Nuevo paso de Altas"]').element as HTMLInputElement).value,
      ).toBe('')
    })

    it('el botón de añadir paso tiene un nombre accesible único que contiene su texto', async () => {
      const vista = await montar()

      const anadir = boton(vista, 'Añadir paso a Altas')
      expect(anadir.text()).toBe('Añadir paso')
      expect(vista.findAll('button[aria-label="Añadir paso a Altas"]')).toHaveLength(1)
    })

    it('no envía un nombre de paso vacío y muestra el error', async () => {
      const vista = await montar()

      await vista.get('input[aria-label="Nuevo paso de Altas"]').setValue('  ')
      await vista.get('form[aria-label="Añadir paso a Altas"]').trigger('submit')
      await flushPromises()

      expect(clienteApi.crear).not.toHaveBeenCalled()
      expect(vista.get('[role="alert"]').text()).toBe('El nombre del paso es obligatorio.')
    })

    it('renombra un paso en línea con PUT', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue({
        ...OPORTUNIDADES,
        pasos: OPORTUNIDADES.pasos.map((paso) =>
          paso.id === 11 ? { ...paso, nombre: 'Oferta' } : paso,
        ),
      })

      await boton(vista, 'Renombrar paso Propuesta de Workflow Oportunidades').trigger('click')
      await flushPromises()
      const campo = vista.get(
        'input[aria-label="Nuevo nombre del paso Propuesta de Workflow Oportunidades"]',
      )
      expect(document.activeElement).toBe(campo.element)
      await campo.setValue('Oferta')
      await flushPromises()
      await vista
        .get('form[aria-label="Renombrar paso Propuesta de Workflow Oportunidades"]')
        .trigger('submit')
      await flushPromises()

      expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/1/pasos/11`, {
        nombre: 'Oferta',
      })
      expect(textosPasos(vista, 'Workflow Oportunidades')).toEqual([
        '1. Contacto inicial',
        '2. Oferta',
        '3. Cierre',
      ])
    })

    it('cancelar descarta la edición del paso sin llamar a la API', async () => {
      const vista = await montar()

      await boton(vista, 'Renombrar paso Propuesta de Workflow Oportunidades').trigger('click')
      await vista
        .get('input[aria-label="Nuevo nombre del paso Propuesta de Workflow Oportunidades"]')
        .setValue('Otro')
      await vista
        .findAll('button')
        .find((b) => b.text() === 'Cancelar')!
        .trigger('click')

      expect(clienteApi.actualizar).not.toHaveBeenCalled()
      expect(textosPasos(vista, 'Workflow Oportunidades')).toHaveLength(3)
    })

    it('pide confirmación y elimina el paso con DELETE, mostrando el workflow renumerado', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.eliminar).mockResolvedValue({
        ...OPORTUNIDADES,
        pasos: [
          { id: 10, numero: 1, nombre: 'Contacto inicial' },
          { id: 12, numero: 2, nombre: 'Cierre' },
        ],
      })

      await boton(vista, 'Eliminar paso Propuesta de Workflow Oportunidades').trigger('click')
      await flushPromises()
      expect(dialogo().textContent).toContain('¿Eliminar el paso Propuesta?')
      expect(clienteApi.eliminar).not.toHaveBeenCalled()
      botonDialogo('Eliminar').click()
      await flushPromises()

      expect(clienteApi.eliminar).toHaveBeenCalledWith(`${RUTA}/1/pasos/11`)
      expect(textosPasos(vista, 'Workflow Oportunidades')).toEqual([
        '1. Contacto inicial',
        '2. Cierre',
      ])
      expect(document.activeElement?.getAttribute('aria-label')).toBe(
        'Nuevo paso de Workflow Oportunidades',
      )
    })
  })

  describe('ordenar pasos', () => {
    it('"Subir" está desactivado en el primer paso y "Bajar" en el último', async () => {
      const vista = await montar()
      const de = 'de Workflow Oportunidades'

      expect(boton(vista, `Subir paso Contacto inicial ${de}`).attributes('disabled')).toBeDefined()
      expect(
        boton(vista, `Bajar paso Contacto inicial ${de}`).attributes('disabled'),
      ).toBeUndefined()
      expect(boton(vista, `Subir paso Cierre ${de}`).attributes('disabled')).toBeUndefined()
      expect(boton(vista, `Bajar paso Cierre ${de}`).attributes('disabled')).toBeDefined()
    })

    it('"Bajar" guarda el nuevo orden con PUT /orden, lo anuncia y deja el foco en el paso movido', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue(oportunidadesSegun([11, 10, 12]))
      const bajar = boton(vista, 'Bajar paso Contacto inicial de Workflow Oportunidades')
      ;(bajar.element as HTMLButtonElement).focus()

      await bajar.trigger('click')
      await flushPromises()

      expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/1/orden`, { ids: [11, 10, 12] })
      expect(textosPasos(vista, 'Workflow Oportunidades')).toEqual([
        '1. Propuesta',
        '2. Contacto inicial',
        '3. Cierre',
      ])
      expect(vista.get('[aria-live="polite"]').text()).toBe(
        'Contacto inicial movido a la posición 2',
      )
      expect(document.activeElement?.getAttribute('aria-label')).toBe(
        'Bajar paso Contacto inicial de Workflow Oportunidades',
      )
    })

    it('si el paso llega al final, el foco pasa a su botón "Subir"', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue(oportunidadesSegun([10, 12, 11]))

      await boton(vista, 'Bajar paso Propuesta de Workflow Oportunidades').trigger('click')
      await flushPromises()

      expect(document.activeElement?.getAttribute('aria-label')).toBe(
        'Subir paso Propuesta de Workflow Oportunidades',
      )
    })

    it('si el paso llega al principio, el foco pasa a su botón "Bajar"', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue(oportunidadesSegun([11, 10, 12]))

      await boton(vista, 'Subir paso Propuesta de Workflow Oportunidades').trigger('click')
      await flushPromises()

      expect(document.activeElement?.getAttribute('aria-label')).toBe(
        'Bajar paso Propuesta de Workflow Oportunidades',
      )
    })

    it('arrastrar y soltar un paso sobre otro del workflow guarda el nuevo orden', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue(oportunidadesSegun([12, 10, 11]))
      const filas = vista
        .get('ol[aria-label="Pasos de Workflow Oportunidades"]')
        .findAll('[data-paso]')
      expect(filas.every((fila) => fila.attributes('draggable') === 'true')).toBe(true)
      const dataTransfer = crearDataTransfer()

      lanzarEventoArrastre(filas[2]!.element, 'dragstart', dataTransfer)
      lanzarEventoArrastre(filas[0]!.element, 'dragover', dataTransfer)
      await flushPromises()
      expect(vista.findAll('[data-paso]')[0]!.attributes('data-destino')).toBe('antes')

      lanzarEventoArrastre(filas[0]!.element, 'drop', dataTransfer)
      lanzarEventoArrastre(filas[2]!.element, 'dragend', dataTransfer)
      await flushPromises()

      expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/1/orden`, { ids: [12, 10, 11] })
      expect(textosPasos(vista, 'Workflow Oportunidades')).toEqual([
        '1. Cierre',
        '2. Contacto inicial',
        '3. Propuesta',
      ])
      expect(vista.get('[aria-live="polite"]').text()).toBe('Cierre movido a la posición 1')
      expect(vista.find('[data-destino]').exists()).toBe(false)
    })

    it('soltar un paso sobre sí mismo no llama a la API', async () => {
      const vista = await montar()
      const filas = vista.findAll('[data-paso]')
      const dataTransfer = crearDataTransfer()

      lanzarEventoArrastre(filas[1]!.element, 'dragstart', dataTransfer)
      lanzarEventoArrastre(filas[1]!.element, 'drop', dataTransfer)
      await flushPromises()

      expect(clienteApi.actualizar).not.toHaveBeenCalled()
    })

    it('si la API falla conserva el orden y muestra el error', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockRejectedValue(new ErrorApi(422, 'Orden inválido'))

      await boton(vista, 'Bajar paso Contacto inicial de Workflow Oportunidades').trigger('click')
      await flushPromises()

      expect(textosPasos(vista, 'Workflow Oportunidades')).toEqual([
        '1. Contacto inicial',
        '2. Propuesta',
        '3. Cierre',
      ])
      expect(vista.get('[role="alert"]').text()).toBe('Orden inválido')
      expect(vista.get('[aria-live="polite"]').text()).toBe('')
    })
  })
})
