import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { clienteApi, ErrorApi } from '@/api/cliente'
import type { PasoWorkflow } from '@/api/tipos'
import VistaWorkflowOportunidades from '../VistaWorkflowOportunidades.vue'

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

const RUTA = '/workflow-oportunidades/pasos'
const PASOS: PasoWorkflow[] = [
  { id: 1, numero: 1, nombre: 'Contacto inicial' },
  { id: 2, numero: 2, nombre: 'Propuesta' },
  { id: 3, numero: 3, nombre: 'Cierre' },
]

// Lista que devolvería `PUT /orden` para los ids dados, con los números recalculados.
function ordenarSegun(ids: number[]): PasoWorkflow[] {
  return ids.map((id, indice) => ({
    ...PASOS.find((paso) => paso.id === id)!,
    numero: indice + 1,
  }))
}

let contenedor: VueWrapper | undefined

async function montar(pasos: PasoWorkflow[] = PASOS): Promise<VueWrapper> {
  vi.mocked(clienteApi.obtener).mockResolvedValue(pasos)
  const enrutador = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/ajustes', component: { template: '<div />' } },
      { path: '/ajustes/workflow-oportunidades', component: VistaWorkflowOportunidades },
    ],
  })
  await enrutador.push('/ajustes/workflow-oportunidades')
  contenedor = mount(VistaWorkflowOportunidades, {
    global: { plugins: [createPinia(), enrutador] },
    attachTo: document.body,
  })
  await flushPromises()
  return contenedor
}

function textosPasos(vista: VueWrapper): string[] {
  return vista.findAll('[data-paso]').map((fila) => fila.get('[data-texto-paso]').text())
}

function boton(vista: VueWrapper, etiqueta: string) {
  return vista.get(`button[aria-label="${etiqueta}"]`)
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

describe('VistaWorkflowOportunidades', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    contenedor?.unmount()
    contenedor = undefined
  })

  it('muestra el título y un enlace de vuelta a Ajustes', async () => {
    const vista = await montar()

    expect(vista.get('h2').text()).toBe('Workflow Oportunidades')
    expect(vista.get('a[href="/ajustes"]').text()).toContain('Ajustes')
  })

  it('lista los pasos por número como "<numero>. <nombre>"', async () => {
    const vista = await montar([PASOS[2]!, PASOS[0]!, PASOS[1]!])

    expect(clienteApi.obtener).toHaveBeenCalledWith(RUTA)
    expect(textosPasos(vista)).toEqual(['1. Contacto inicial', '2. Propuesta', '3. Cierre'])
  })

  it('muestra un estado vacío si no hay pasos', async () => {
    const vista = await montar([])

    expect(vista.text()).toContain('Todavía no hay pasos en el workflow.')
    expect(vista.findAll('[data-paso]')).toHaveLength(0)
  })

  describe('añadir paso', () => {
    it('el campo "Nombre del paso" es obligatorio y admite como mucho 50 caracteres', async () => {
      const vista = await montar()

      const campo = vista.get('input#nombre-paso-nuevo')
      expect(vista.get('label[for="nombre-paso-nuevo"]').text()).toBe('Nombre del paso')
      expect(campo.attributes('required')).toBeDefined()
      expect(campo.attributes('maxlength')).toBe('50')
    })

    it('añade el paso al final de la lista y vacía el campo', async () => {
      const vista = await montar(PASOS.slice(0, 2))
      vi.mocked(clienteApi.crear).mockResolvedValue(PASOS[2])

      await vista.get('input#nombre-paso-nuevo').setValue('  Cierre  ')
      await vista.get('form[aria-label="Añadir paso"]').trigger('submit')
      await flushPromises()

      expect(clienteApi.crear).toHaveBeenCalledWith(RUTA, { nombre: 'Cierre' })
      expect(textosPasos(vista)).toEqual(['1. Contacto inicial', '2. Propuesta', '3. Cierre'])
      expect((vista.get('input#nombre-paso-nuevo').element as HTMLInputElement).value).toBe('')
    })

    it('no envía un nombre vacío y muestra el error', async () => {
      const vista = await montar()

      await vista.get('input#nombre-paso-nuevo').setValue('   ')
      await vista.get('form[aria-label="Añadir paso"]').trigger('submit')
      await flushPromises()

      expect(clienteApi.crear).not.toHaveBeenCalled()
      expect(vista.get('[role="alert"]').text()).toBe('El nombre del paso es obligatorio.')
    })

    it('no envía un nombre de más de 50 caracteres y muestra el error', async () => {
      const vista = await montar()

      await vista.get('input#nombre-paso-nuevo').setValue('a'.repeat(51))
      await vista.get('form[aria-label="Añadir paso"]').trigger('submit')
      await flushPromises()

      expect(clienteApi.crear).not.toHaveBeenCalled()
      expect(vista.get('[role="alert"]').text()).toBe(
        'El nombre del paso no puede superar los 50 caracteres.',
      )
    })

    it('muestra el error de la API en una alerta', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.crear).mockRejectedValue(new ErrorApi(422, 'Nombre inválido'))

      await vista.get('input#nombre-paso-nuevo').setValue('Nuevo')
      await vista.get('form[aria-label="Añadir paso"]').trigger('submit')
      await flushPromises()

      expect(vista.get('[role="alert"]').text()).toBe('Nombre inválido')
      expect(textosPasos(vista)).toHaveLength(3)
    })
  })

  describe('renombrar paso', () => {
    it('edita el nombre en línea y guarda con PUT', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue({ id: 2, numero: 2, nombre: 'Oferta' })

      await boton(vista, 'Renombrar paso Propuesta').trigger('click')
      const campo = vista.get('input[aria-label="Nuevo nombre del paso Propuesta"]')
      expect((campo.element as HTMLInputElement).value).toBe('Propuesta')
      expect(campo.attributes('maxlength')).toBe('50')
      await campo.setValue('Oferta')
      await flushPromises()
      await vista.get('form[aria-label="Renombrar paso Propuesta"]').trigger('submit')
      await flushPromises()

      expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/2`, { nombre: 'Oferta' })
      expect(textosPasos(vista)).toEqual(['1. Contacto inicial', '2. Oferta', '3. Cierre'])
      expect(vista.find('input[aria-label^="Nuevo nombre del paso"]').exists()).toBe(false)
    })

    it('cancelar descarta la edición sin llamar a la API', async () => {
      const vista = await montar()

      await boton(vista, 'Renombrar paso Propuesta').trigger('click')
      await vista.get('input[aria-label="Nuevo nombre del paso Propuesta"]').setValue('Otro')
      await vista
        .findAll('button')
        .find((b) => b.text() === 'Cancelar')!
        .trigger('click')

      expect(clienteApi.actualizar).not.toHaveBeenCalled()
      expect(textosPasos(vista)).toEqual(['1. Contacto inicial', '2. Propuesta', '3. Cierre'])
    })

    it('no guarda un nombre vacío', async () => {
      const vista = await montar()

      await boton(vista, 'Renombrar paso Propuesta').trigger('click')
      await vista.get('input[aria-label="Nuevo nombre del paso Propuesta"]').setValue('  ')
      await vista.get('form[aria-label="Renombrar paso Propuesta"]').trigger('submit')
      await flushPromises()

      expect(clienteApi.actualizar).not.toHaveBeenCalled()
      expect(vista.get('[role="alert"]').text()).toBe('El nombre del paso es obligatorio.')
    })
  })

  describe('eliminar paso', () => {
    it('pide confirmación y, al confirmar, elimina con DELETE y muestra la lista renumerada', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)
      vi.mocked(clienteApi.obtener).mockResolvedValue([
        { id: 1, numero: 1, nombre: 'Contacto inicial' },
        { id: 3, numero: 2, nombre: 'Cierre' },
      ])

      await boton(vista, 'Eliminar paso Propuesta').trigger('click')
      await flushPromises()
      const dialogo = document.body.querySelector('[role="dialog"]')
      expect(dialogo?.textContent).toContain('Propuesta')
      expect(clienteApi.eliminar).not.toHaveBeenCalled()

      const confirmar = [...dialogo!.querySelectorAll('button')].find(
        (b) => b.textContent?.trim() === 'Eliminar',
      )!
      confirmar.click()
      await flushPromises()

      expect(clienteApi.eliminar).toHaveBeenCalledWith(`${RUTA}/2`)
      expect(textosPasos(vista)).toEqual(['1. Contacto inicial', '2. Cierre'])
      expect(document.body.querySelector('[role="dialog"]')).toBeNull()
      // La fila del paso eliminado ya no existe: el foco va al campo de alta.
      expect(document.activeElement?.id).toBe('nombre-paso-nuevo')
    })

    it('cancelar la confirmación no elimina el paso', async () => {
      const vista = await montar()

      await boton(vista, 'Eliminar paso Propuesta').trigger('click')
      await flushPromises()
      const dialogo = document.body.querySelector('[role="dialog"]')!
      const cancelar = [...dialogo.querySelectorAll('button')].find(
        (b) => b.textContent?.trim() === 'Cancelar',
      )!
      cancelar.click()
      await flushPromises()

      expect(clienteApi.eliminar).not.toHaveBeenCalled()
      expect(textosPasos(vista)).toHaveLength(3)
    })
  })

  describe('reordenar con Subir/Bajar', () => {
    it('"Subir" está desactivado en el primer paso y "Bajar" en el último', async () => {
      const vista = await montar()

      expect(boton(vista, 'Subir paso Contacto inicial').attributes('disabled')).toBeDefined()
      expect(boton(vista, 'Bajar paso Contacto inicial').attributes('disabled')).toBeUndefined()
      expect(boton(vista, 'Subir paso Cierre').attributes('disabled')).toBeUndefined()
      expect(boton(vista, 'Bajar paso Cierre').attributes('disabled')).toBeDefined()
    })

    // Regresión (accesibilidad): el botón pulsado se desactiva mientras se guarda
    // y el navegador mandaba el foco al <body>; quien usa teclado perdía su sitio.
    it('tras "Bajar" el foco vuelve al botón "Bajar" del paso movido', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue(ordenarSegun([2, 1, 3]))
      const bajar = boton(vista, 'Bajar paso Contacto inicial')
      ;(bajar.element as HTMLButtonElement).focus()

      await bajar.trigger('click')
      await flushPromises()

      expect(document.activeElement?.getAttribute('aria-label')).toBe('Bajar paso Contacto inicial')
    })

    it('si el paso llega al final, el foco pasa a su botón "Subir"', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue(ordenarSegun([1, 3, 2]))

      await boton(vista, 'Bajar paso Propuesta').trigger('click')
      await flushPromises()

      expect(document.activeElement?.getAttribute('aria-label')).toBe('Subir paso Propuesta')
    })

    it('si el paso llega al principio, el foco pasa a su botón "Bajar"', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue(ordenarSegun([2, 1, 3]))

      await boton(vista, 'Subir paso Propuesta').trigger('click')
      await flushPromises()

      expect(document.activeElement?.getAttribute('aria-label')).toBe('Bajar paso Propuesta')
    })

    it('"Subir" guarda el nuevo orden y muestra los números recalculados', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue(ordenarSegun([1, 3, 2]))

      await boton(vista, 'Subir paso Cierre').trigger('click')
      await flushPromises()

      expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/orden`, { ids: [1, 3, 2] })
      expect(textosPasos(vista)).toEqual(['1. Contacto inicial', '2. Cierre', '3. Propuesta'])
    })

    it('"Bajar" guarda el nuevo orden y lo anuncia a los lectores de pantalla', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue(ordenarSegun([2, 1, 3]))

      await boton(vista, 'Bajar paso Contacto inicial').trigger('click')
      await flushPromises()

      expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/orden`, { ids: [2, 1, 3] })
      expect(textosPasos(vista)).toEqual(['1. Propuesta', '2. Contacto inicial', '3. Cierre'])
      expect(vista.get('[aria-live="polite"]').text()).toBe(
        'Contacto inicial movido a la posición 2',
      )
    })

    it('si la API falla conserva el orden y muestra el error', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockRejectedValue(new ErrorApi(422, 'Orden inválido'))

      await boton(vista, 'Bajar paso Contacto inicial').trigger('click')
      await flushPromises()

      expect(textosPasos(vista)).toEqual(['1. Contacto inicial', '2. Propuesta', '3. Cierre'])
      expect(vista.get('[role="alert"]').text()).toBe('Orden inválido')
      expect(vista.get('[aria-live="polite"]').text()).toBe('')
    })
  })

  describe('reordenar con drag & drop', () => {
    it('las filas son arrastrables y tienen un asa', async () => {
      const vista = await montar()

      const filas = vista.findAll('[data-paso]')
      expect(filas.every((fila) => fila.attributes('draggable') === 'true')).toBe(true)
      expect(filas[0]!.find('[data-asa]').exists()).toBe(true)
    })

    it('soltar un paso sobre otro guarda el nuevo orden y lo anuncia', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue(ordenarSegun([3, 1, 2]))
      const filas = vista.findAll('[data-paso]')
      const dataTransfer = crearDataTransfer()

      lanzarEventoArrastre(filas[2]!.element, 'dragstart', dataTransfer)
      lanzarEventoArrastre(filas[0]!.element, 'dragover', dataTransfer)
      await flushPromises()
      expect(vista.findAll('[data-paso]')[0]!.attributes('data-destino')).toBe('antes')

      lanzarEventoArrastre(filas[0]!.element, 'drop', dataTransfer)
      lanzarEventoArrastre(filas[2]!.element, 'dragend', dataTransfer)
      await flushPromises()

      expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/orden`, { ids: [3, 1, 2] })
      expect(textosPasos(vista)).toEqual(['1. Cierre', '2. Contacto inicial', '3. Propuesta'])
      expect(vista.get('[aria-live="polite"]').text()).toBe('Cierre movido a la posición 1')
      expect(vista.find('[data-destino]').exists()).toBe(false)
    })

    it('el indicador va detrás de la fila al arrastrar hacia abajo', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue(ordenarSegun([2, 3, 1]))
      const filas = vista.findAll('[data-paso]')
      const dataTransfer = crearDataTransfer()

      lanzarEventoArrastre(filas[0]!.element, 'dragstart', dataTransfer)
      lanzarEventoArrastre(filas[2]!.element, 'dragover', dataTransfer)
      await flushPromises()
      expect(vista.findAll('[data-paso]')[2]!.attributes('data-destino')).toBe('despues')

      lanzarEventoArrastre(filas[2]!.element, 'drop', dataTransfer)
      await flushPromises()

      expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/orden`, { ids: [2, 3, 1] })
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
  })
})
