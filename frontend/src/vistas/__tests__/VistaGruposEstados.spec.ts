import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { clienteApi, ErrorApi } from '@/api/cliente'
import type { GrupoEstados } from '@/api/tipos'
import VistaGruposEstados from '../VistaGruposEstados.vue'

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

const RUTA = '/grupos-estados'

const DESARROLLO: GrupoEstados = {
  id: 1,
  nombre: 'Desarrollo',
  tareas: 3,
  estados: [
    { id: 10, nombre: 'Pendiente', posicion: 1, tareas: 2 },
    { id: 11, nombre: 'En curso', posicion: 2, tareas: 1 },
    { id: 12, nombre: 'Hecho', posicion: 3, tareas: 0 },
  ],
}
const SOPORTE: GrupoEstados = { id: 2, nombre: 'Soporte', tareas: 0, estados: [] }

// Grupo "Desarrollo" con los estados en el orden de los ids dados.
function desarrolloSegun(ids: number[]): GrupoEstados {
  return {
    ...DESARROLLO,
    estados: ids.map((id, indice) => ({
      ...DESARROLLO.estados.find((estado) => estado.id === id)!,
      posicion: indice + 1,
    })),
  }
}

let contenedor: VueWrapper | undefined

async function montar(grupos: GrupoEstados[] = [DESARROLLO, SOPORTE]): Promise<VueWrapper> {
  vi.mocked(clienteApi.obtener).mockResolvedValue(structuredClone(grupos))
  const enrutador = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/ajustes', component: { template: '<div />' } },
      { path: '/ajustes/grupos-estados', component: VistaGruposEstados },
    ],
  })
  await enrutador.push('/ajustes/grupos-estados')
  contenedor = mount(VistaGruposEstados, {
    global: { plugins: [createPinia(), enrutador] },
    attachTo: document.body,
  })
  await flushPromises()
  return contenedor
}

function boton(vista: VueWrapper, etiqueta: string) {
  return vista.get(`button[aria-label="${etiqueta}"]`)
}

function textosEstados(vista: VueWrapper, grupo: string): string[] {
  return vista
    .get(`ol[aria-label="Estados de ${grupo}"]`)
    .findAll('[data-estado]')
    .map((fila) => fila.get('[data-texto-estado]').text())
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

describe('VistaGruposEstados', () => {
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

    expect(vista.get('h2').text()).toBe('Grupos de estados')
    expect(vista.get('a[href="/ajustes"]').text()).toContain('Ajustes')
  })

  it('lista los grupos con sus estados en orden y el número de tareas de cada uno', async () => {
    const vista = await montar()

    expect(clienteApi.obtener).toHaveBeenCalledWith(RUTA)
    const grupos = vista.get('ul[aria-label="Grupos de estados"]').findAll('[data-grupo]')
    expect(grupos.map((g) => g.get('h3').text())).toEqual(['Desarrollo', 'Soporte'])
    expect(grupos[0]!.get('[data-tareas-grupo]').text()).toBe('3 tareas')
    expect(textosEstados(vista, 'Desarrollo')).toEqual(['Pendiente', 'En curso', 'Hecho'])
    const cuentas = vista
      .get('ol[aria-label="Estados de Desarrollo"]')
      .findAll('[data-tareas-estado]')
      .map((c) => c.text())
    expect(cuentas).toEqual(['2 tareas', '1 tarea', '0 tareas'])
    expect(grupos[1]!.text()).toContain('Este grupo todavía no tiene estados.')
  })

  it('muestra un estado vacío si no hay grupos', async () => {
    const vista = await montar([])

    expect(vista.text()).toContain('Todavía no hay grupos de estados.')
    expect(vista.findAll('[data-grupo]')).toHaveLength(0)
  })

  describe('grupos', () => {
    it('crea un grupo con POST y vacía el campo', async () => {
      const vista = await montar([DESARROLLO])
      vi.mocked(clienteApi.crear).mockResolvedValue(structuredClone(SOPORTE))

      expect(vista.get('label[for="nombre-grupo-nuevo"]').text()).toBe('Nombre del grupo')
      expect(vista.get('#nombre-grupo-nuevo').attributes('maxlength')).toBe('50')
      await vista.get('#nombre-grupo-nuevo').setValue('  Soporte  ')
      await vista.get('form[aria-label="Añadir grupo"]').trigger('submit')
      await flushPromises()

      expect(clienteApi.crear).toHaveBeenCalledWith(RUTA, { nombre: 'Soporte' })
      expect(vista.findAll('[data-grupo]')).toHaveLength(2)
      expect((vista.get('#nombre-grupo-nuevo').element as HTMLInputElement).value).toBe('')
    })

    it('no envía un nombre de grupo vacío y muestra el error', async () => {
      const vista = await montar()

      await vista.get('#nombre-grupo-nuevo').setValue('   ')
      await vista.get('form[aria-label="Añadir grupo"]').trigger('submit')
      await flushPromises()

      expect(clienteApi.crear).not.toHaveBeenCalled()
      expect(vista.get('[role="alert"]').text()).toBe('El nombre del grupo es obligatorio.')
    })

    it('muestra el error de la API en una alerta', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.crear).mockRejectedValue(new ErrorApi(409, 'Ya existe un grupo'))

      await vista.get('#nombre-grupo-nuevo').setValue('Desarrollo')
      await vista.get('form[aria-label="Añadir grupo"]').trigger('submit')
      await flushPromises()

      expect(vista.get('[role="alert"]').text()).toBe('Ya existe un grupo')
    })

    it('renombra un grupo en línea con PUT', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue({ ...DESARROLLO, nombre: 'Producto' })

      await boton(vista, 'Renombrar grupo Desarrollo').trigger('click')
      await flushPromises()
      expect(document.activeElement?.id).toBe('nombre-grupo-1')
      await vista.get('#nombre-grupo-1').setValue('Producto')
      await vista.get('form[aria-label="Renombrar grupo Desarrollo"]').trigger('submit')
      await flushPromises()

      expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/1`, { nombre: 'Producto' })
      expect(vista.findAll('[data-grupo] h3').map((h) => h.text())).toEqual(['Producto', 'Soporte'])
    })

    it('al eliminar un grupo avisa cuántas tareas quedarán sin grupo y lo borra al confirmar', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)

      await boton(vista, 'Eliminar grupo Desarrollo').trigger('click')
      await flushPromises()
      expect(dialogo().textContent).toContain('¿Eliminar el grupo Desarrollo?')
      expect(dialogo().textContent).toContain('3 tareas quedarán sin grupo.')
      expect(clienteApi.eliminar).not.toHaveBeenCalled()

      botonDialogo('Eliminar').click()
      await flushPromises()

      expect(clienteApi.eliminar).toHaveBeenCalledWith(`${RUTA}/1`)
      expect(vista.findAll('[data-grupo] h3').map((h) => h.text())).toEqual(['Soporte'])
      expect(document.body.querySelector('[role="alertdialog"]')).toBeNull()
      expect(document.activeElement?.id).toBe('nombre-grupo-nuevo')
    })

    it('eliminar un grupo sin tareas lo indica en la confirmación', async () => {
      const vista = await montar()

      await boton(vista, 'Eliminar grupo Soporte').trigger('click')
      await flushPromises()

      expect(dialogo().textContent).toContain('El grupo no tiene tareas.')
    })
  })

  describe('estados', () => {
    it('añade un estado al grupo con POST y vacía el campo', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.crear).mockResolvedValue({
        ...SOPORTE,
        estados: [{ id: 20, nombre: 'Abierta', posicion: 1, tareas: 0 }],
      })

      const campo = vista.get('input[aria-label="Nuevo estado de Soporte"]')
      await campo.setValue('Abierta')
      await vista.get('form[aria-label="Añadir estado a Soporte"]').trigger('submit')
      await flushPromises()

      expect(clienteApi.crear).toHaveBeenCalledWith(`${RUTA}/2/estados`, { nombre: 'Abierta' })
      expect(textosEstados(vista, 'Soporte')).toEqual(['Abierta'])
      expect((campo.element as HTMLInputElement).value).toBe('')
    })

    it('no envía un nombre de estado vacío y muestra el error', async () => {
      const vista = await montar()

      await vista.get('form[aria-label="Añadir estado a Soporte"]').trigger('submit')
      await flushPromises()

      expect(clienteApi.crear).not.toHaveBeenCalled()
      expect(vista.get('[role="alert"]').text()).toBe('El nombre del estado es obligatorio.')
    })

    it('renombra un estado en línea con PUT', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue({
        ...DESARROLLO,
        estados: DESARROLLO.estados.map((e) => (e.id === 11 ? { ...e, nombre: 'Haciendo' } : e)),
      })

      await boton(vista, 'Renombrar estado En curso de Desarrollo').trigger('click')
      await flushPromises()
      await vista.get('#nombre-estado-11').setValue('Haciendo')
      await vista
        .get('form[aria-label="Renombrar estado En curso de Desarrollo"]')
        .trigger('submit')
      await flushPromises()

      expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/1/estados/11`, {
        nombre: 'Haciendo',
      })
      expect(textosEstados(vista, 'Desarrollo')).toEqual(['Pendiente', 'Haciendo', 'Hecho'])
    })

    it('elimina un estado sin tareas sin pedir destino', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.eliminar).mockResolvedValue(desarrolloSegun([10, 11]))

      await boton(vista, 'Eliminar estado Hecho de Desarrollo').trigger('click')
      await flushPromises()
      expect(dialogo().textContent).toContain('El estado no tiene tareas.')
      expect(dialogo().querySelector('select')).toBeNull()
      botonDialogo('Eliminar').click()
      await flushPromises()

      expect(clienteApi.eliminar).toHaveBeenCalledWith(`${RUTA}/1/estados/12`)
      expect(textosEstados(vista, 'Desarrollo')).toEqual(['Pendiente', 'En curso'])
      expect(document.activeElement?.getAttribute('aria-label')).toBe('Nuevo estado de Desarrollo')
    })

    it('al eliminar un estado con tareas pide a qué otro estado moverlas y envía mover_a', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.eliminar).mockResolvedValue(desarrolloSegun([11, 12]))

      await boton(vista, 'Eliminar estado Pendiente de Desarrollo').trigger('click')
      await flushPromises()
      expect(dialogo().textContent).toContain('Tiene 2 tareas.')
      const selector = dialogo().querySelector<HTMLSelectElement>('select#mover-tareas-a')!
      expect(dialogo().querySelector('label[for="mover-tareas-a"]')?.textContent?.trim()).toBe(
        'Mover las tareas a',
      )
      expect([...selector.options].map((o) => o.textContent?.trim())).toEqual(['En curso', 'Hecho'])
      selector.value = '12'
      selector.dispatchEvent(new Event('change'))
      await flushPromises()
      botonDialogo('Eliminar').click()
      await flushPromises()

      expect(clienteApi.eliminar).toHaveBeenCalledWith(`${RUTA}/1/estados/10?mover_a=12`)
      expect(textosEstados(vista, 'Desarrollo')).toEqual(['En curso', 'Hecho'])
    })

    it('no deja eliminar el único estado de un grupo si tiene tareas', async () => {
      const unico: GrupoEstados = {
        id: 3,
        nombre: 'Único',
        tareas: 1,
        estados: [{ id: 30, nombre: 'Abierto', posicion: 1, tareas: 1 }],
      }
      const vista = await montar([unico])

      await boton(vista, 'Eliminar estado Abierto de Único').trigger('click')
      await flushPromises()

      expect(dialogo().textContent).toContain('no hay otro estado del grupo al que moverlas')
      expect(botonDialogo('Eliminar').disabled).toBe(true)
    })

    it('si la API rechaza el borrado, muestra el error dentro de la confirmación', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.eliminar).mockRejectedValue(new ErrorApi(409, 'El estado tiene tareas'))

      await boton(vista, 'Eliminar estado Pendiente de Desarrollo').trigger('click')
      await flushPromises()
      botonDialogo('Eliminar').click()
      await flushPromises()

      expect(dialogo().querySelector('[role="alert"]')?.textContent).toBe('El estado tiene tareas')
      expect(textosEstados(vista, 'Desarrollo')).toEqual(['Pendiente', 'En curso', 'Hecho'])
    })
  })

  describe('ordenar estados', () => {
    it('"Subir" está desactivado en el primer estado y "Bajar" en el último', async () => {
      const vista = await montar()

      expect(boton(vista, 'Subir estado Pendiente de Desarrollo').attributes('disabled')).toBe('')
      expect(boton(vista, 'Bajar estado Hecho de Desarrollo').attributes('disabled')).toBe('')
      expect(
        boton(vista, 'Bajar estado Pendiente de Desarrollo').attributes('disabled'),
      ).toBeUndefined()
    })

    it('"Bajar" guarda el nuevo orden con PUT /orden y deja el foco en el estado movido', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue(desarrolloSegun([11, 10, 12]))
      const bajar = boton(vista, 'Bajar estado Pendiente de Desarrollo')
      ;(bajar.element as HTMLButtonElement).focus()

      await bajar.trigger('click')
      await flushPromises()

      expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/1/orden`, { ids: [11, 10, 12] })
      expect(textosEstados(vista, 'Desarrollo')).toEqual(['En curso', 'Pendiente', 'Hecho'])
      expect(document.activeElement?.getAttribute('aria-label')).toBe(
        'Bajar estado Pendiente de Desarrollo',
      )
      expect(vista.get('[aria-live="polite"]').text()).toBe('Pendiente movido a la posición 2')
    })

    it('si el estado llega al final, el foco pasa a su botón "Subir"', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue(desarrolloSegun([10, 12, 11]))

      await boton(vista, 'Bajar estado En curso de Desarrollo').trigger('click')
      await flushPromises()

      expect(document.activeElement?.getAttribute('aria-label')).toBe(
        'Subir estado En curso de Desarrollo',
      )
    })

    it('arrastrar y soltar un estado sobre otro del grupo guarda el nuevo orden', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockResolvedValue(desarrolloSegun([12, 10, 11]))
      const filas = vista.get('ol[aria-label="Estados de Desarrollo"]').findAll('[data-estado]')
      expect(filas.every((fila) => fila.attributes('draggable') === 'true')).toBe(true)
      const dataTransfer = crearDataTransfer()

      lanzarEventoArrastre(filas[2]!.element, 'dragstart', dataTransfer)
      lanzarEventoArrastre(filas[0]!.element, 'dragover', dataTransfer)
      await flushPromises()
      expect(filas[0]!.attributes('data-destino')).toBe('antes')
      lanzarEventoArrastre(filas[0]!.element, 'drop', dataTransfer)
      lanzarEventoArrastre(filas[2]!.element, 'dragend', dataTransfer)
      await flushPromises()

      expect(clienteApi.actualizar).toHaveBeenCalledWith(`${RUTA}/1/orden`, { ids: [12, 10, 11] })
      expect(textosEstados(vista, 'Desarrollo')).toEqual(['Hecho', 'Pendiente', 'En curso'])
    })

    it('si la API falla conserva el orden y muestra el error', async () => {
      const vista = await montar()
      vi.mocked(clienteApi.actualizar).mockRejectedValue(new ErrorApi(500, 'Fallo al ordenar'))

      await boton(vista, 'Bajar estado Pendiente de Desarrollo').trigger('click')
      await flushPromises()

      expect(textosEstados(vista, 'Desarrollo')).toEqual(['Pendiente', 'En curso', 'Hecho'])
      expect(vista.get('[role="alert"]').text()).toBe('Fallo al ordenar')
    })
  })
})
