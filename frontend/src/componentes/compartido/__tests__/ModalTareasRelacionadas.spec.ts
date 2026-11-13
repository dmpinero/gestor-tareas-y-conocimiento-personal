import { afterEach, describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { Subtarea, Tarea } from '@/api/tipos'
import ModalTareasRelacionadas from '../ModalTareasRelacionadas.vue'

function subtarea(datos: Partial<Subtarea> & Pick<Subtarea, 'id' | 'nombre'>): Subtarea {
  return {
    asignado: null,
    prioridad: null,
    resuelta: false,
    comentarios: 0,
    ...datos,
  } as Subtarea
}

function tarea(datos: Partial<Tarea> & Pick<Tarea, 'id' | 'nombre'>): Tarea {
  return {
    etiquetas: [],
    asignados: [],
    subtareas: [],
    completada: false,
    ...datos,
  } as Tarea
}

const TAREAS: Tarea[] = [
  tarea({ id: 1, nombre: 'Preparar demo', etiquetas: ['Urgente'], asignados: ['Ana'] }),
  tarea({
    id: 2,
    nombre: 'Revisar contrato',
    etiquetas: ['Legal'],
    completada: true,
    subtareas: [
      subtarea({ id: 10, nombre: 'Leer anexo', asignado: 'Ana' }),
      subtarea({ id: 11, nombre: 'Firmar', asignado: 'Luis' }),
    ],
  }),
  tarea({ id: 3, nombre: 'Llamar a cliente', etiquetas: ['Urgente', 'Legal'] }),
]

function montar(seleccion: { tipo: 'etiqueta' | 'persona'; nombre: string } | null) {
  return mount(ModalTareasRelacionadas, {
    props: { seleccion, tareas: TAREAS },
    attachTo: document.body,
  })
}

function dialogo(): HTMLElement {
  const elemento = document.body.querySelector<HTMLElement>('[role="dialog"]')
  if (!elemento) throw new Error('No hay diálogo abierto')
  return elemento
}

function textosDe(lista: string): string[] {
  const ul = dialogo().querySelector(`ul[aria-label="${lista}"]`)
  if (!ul) throw new Error(`No se encontró la lista ${lista}`)
  return [...ul.querySelectorAll('li')].map((li) => {
    const partes = [...li.querySelectorAll('button > span')].map((span) => span.textContent?.trim())
    return partes.length > 0 ? partes.join(' ') : (li.textContent?.trim() ?? '')
  })
}

describe('ModalTareasRelacionadas', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('no muestra nada sin selección', async () => {
    const envoltorio = montar(null)
    await flushPromises()
    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    envoltorio.unmount()
  })

  it('una etiqueta lista todas las tareas que la llevan, sin sección de subtareas', async () => {
    const envoltorio = montar({ tipo: 'etiqueta', nombre: 'Urgente' })
    await flushPromises()
    expect(dialogo().querySelector('h2')?.textContent).toContain('Etiqueta: Urgente')
    expect(textosDe('Tareas')).toEqual(['Preparar demo', 'Llamar a cliente'])
    expect(dialogo().querySelector('ul[aria-label="Subtareas"]')).toBeNull()
    envoltorio.unmount()
  })

  it('una persona lista sus tareas y sus subtareas con la tarea a la que pertenecen', async () => {
    const envoltorio = montar({ tipo: 'persona', nombre: 'Ana' })
    await flushPromises()
    expect(dialogo().querySelector('h2')?.textContent).toContain('Persona: Ana')
    expect(textosDe('Tareas')).toEqual(['Preparar demo'])
    expect(textosDe('Subtareas')).toEqual(['Leer anexo Tarea: Revisar contrato'])
    envoltorio.unmount()
  })

  it('avisa cuando no hay tareas ni subtareas', async () => {
    const envoltorio = montar({ tipo: 'persona', nombre: 'Nadie' })
    await flushPromises()
    expect(dialogo().textContent).toContain('No hay tareas asignadas a esta persona.')
    expect(dialogo().textContent).toContain('No hay subtareas asignadas a esta persona.')
    envoltorio.unmount()
  })

  it('al pulsar una tarea o una subtarea emite verTarea con el id de la tarea', async () => {
    const envoltorio = montar({ tipo: 'persona', nombre: 'Ana' })
    await flushPromises()
    dialogo()
      .querySelector<HTMLButtonElement>('button[aria-label="Abrir la tarea Preparar demo"]')
      ?.click()
    dialogo()
      .querySelector<HTMLButtonElement>(
        'button[aria-label="Abrir la tarea Revisar contrato (subtarea Leer anexo)"]',
      )
      ?.click()
    expect(envoltorio.emitted('verTarea')).toEqual([[1], [2]])
    envoltorio.unmount()
  })

  it('emite cerrar al cerrar el diálogo', async () => {
    const envoltorio = montar({ tipo: 'etiqueta', nombre: 'Legal' })
    await flushPromises()
    const cerrar = [...dialogo().querySelectorAll('button')].find(
      (boton) => boton.textContent?.trim() === 'Cerrar',
    )
    cerrar?.click()
    await flushPromises()
    expect(envoltorio.emitted('cerrar')).toHaveLength(1)
    envoltorio.unmount()
  })
})
