import { afterEach, describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { Subtarea, Tarea } from '@/api/tipos'
import type { SeleccionRelacionada } from '@/composables/useTareasRelacionadas'
import ModalTareasRelacionadas from '../ModalTareasRelacionadas.vue'

// Texto que lee el lector de pantalla: sin lo marcado aria-hidden.
function textoAccesible(elemento: Element | null | undefined): string {
  const copia = elemento?.cloneNode(true) as Element | undefined
  copia?.querySelectorAll('[aria-hidden="true"]').forEach((nodo) => nodo.remove())
  return copia?.textContent?.replace(/\s+/g, ' ').trim() ?? ''
}

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
    prioridad: null,
    estado: null,
    tipo: null,
    subestado: null,
    hibernada_desde: null,
    ...datos,
  } as Tarea
}

const TAREAS: Tarea[] = [
  tarea({
    id: 1,
    nombre: 'Preparar demo',
    etiquetas: ['Urgente'],
    asignados: ['Ana'],
    subestado: 'Bloqueada',
    prioridad: 2,
    estado: { id: 7, nombre: 'En curso' },
    tipo: 'oportunidad',
    hibernada_desde: '2026-11-20T10:00:00Z',
  }),
  tarea({
    id: 2,
    nombre: 'Revisar contrato',
    etiquetas: ['Legal'],
    completada: true,
    prioridad: 2,
    estado: { id: 8, nombre: 'Hecho' },
    subtareas: [
      subtarea({ id: 10, nombre: 'Leer anexo', asignado: 'Ana', prioridad: 2 }),
      subtarea({ id: 11, nombre: 'Firmar', asignado: 'Luis' }),
    ],
  }),
  tarea({
    id: 3,
    nombre: 'Llamar a cliente',
    etiquetas: ['Urgente', 'Legal'],
    subestado: 'Bloqueada',
    estado: { id: 9, nombre: 'En curso' },
    hibernada_desde: '2026-11-21T10:00:00Z',
  }),
]

function montar(seleccion: SeleccionRelacionada | null, tareas: Tarea[] = TAREAS) {
  return mount(ModalTareasRelacionadas, {
    props: { seleccion, tareas },
    attachTo: document.body,
  })
}

function dialogo(): HTMLElement {
  const elemento = document.body.querySelector<HTMLElement>('[role="dialog"]')
  if (!elemento) throw new Error('No hay diálogo abierto')
  return elemento
}

function textosDe(lista: string): string[] {
  const tabla = dialogo().querySelector(`[data-tabla="${lista}"]`)
  if (!tabla) throw new Error(`No se encontró la tabla ${lista}`)
  return [...tabla.querySelectorAll('tbody tr')].map((fila) => {
    const celdas = [...fila.querySelectorAll('td')].map((td) => td.textContent?.trim() ?? '')
    return lista === 'Subtareas' ? `${celdas[0]} Tarea: ${celdas[1]}` : celdas[0]!
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
    expect(dialogo().querySelector('[data-tabla="Subtareas"]')).toBeNull()
    envoltorio.unmount()
  })

  it('un subestado lista todas las tareas que lo tienen, sin sección de subtareas', async () => {
    const envoltorio = montar({ tipo: 'subestado', nombre: 'Bloqueada' })
    await flushPromises()
    expect(dialogo().querySelector('h2')?.textContent).toContain('Subestado: Bloqueada')
    expect(dialogo().textContent).toContain('Tareas con este subestado.')
    expect(textosDe('Tareas')).toEqual(['Preparar demo', 'Llamar a cliente'])
    expect(dialogo().querySelector('[data-tabla="Subtareas"]')).toBeNull()
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

  it.each([
    {
      // Por nombre: un estado con el mismo nombre en otro grupo también cuenta.
      seleccion: { tipo: 'estado', nombre: 'En curso' },
      titulo: 'Estado: En curso',
      descripcion: 'Tareas en este estado de su grupo.',
      tareas: ['Preparar demo', 'Llamar a cliente'],
    },
    {
      seleccion: { tipo: 'tipo', nombre: 'Oportunidad' },
      titulo: 'Tipo: Oportunidad',
      descripcion: 'Tareas de este tipo.',
      tareas: ['Preparar demo'],
    },
    {
      seleccion: { tipo: 'completado', nombre: 'Completada' },
      titulo: 'Tareas completadas',
      descripcion: 'Tareas marcadas como completadas.',
      tareas: ['Revisar contrato'],
    },
    {
      seleccion: { tipo: 'completado', nombre: 'Pendiente' },
      titulo: 'Tareas pendientes',
      descripcion: 'Tareas sin completar.',
      tareas: ['Preparar demo', 'Llamar a cliente'],
    },
    {
      seleccion: { tipo: 'hibernada', nombre: 'Hibernada' },
      titulo: 'Tareas hibernadas',
      descripcion: 'Tareas con el reloj de vencimiento parado hasta reanudarlas.',
      tareas: ['Preparar demo', 'Llamar a cliente'],
    },
  ] as const)(
    '$titulo lista sus tareas y cuántas son, sin sección de subtareas',
    async ({ seleccion, titulo, descripcion, tareas }) => {
      const envoltorio = montar(seleccion)
      await flushPromises()
      expect(dialogo().querySelector('h2')?.textContent).toContain(titulo)
      expect(dialogo().textContent).toContain(descripcion)
      expect(textoAccesible(dialogo().querySelector('h3'))).toBe(`Tareas (${tareas.length})`)
      expect(textosDe('Tareas')).toEqual(tareas)
      expect(dialogo().querySelector('[data-tabla="Subtareas"]')).toBeNull()
      envoltorio.unmount()
    },
  )

  it.each([
    [{ tipo: 'subestado', nombre: 'Nada' }, 'No hay tareas con este subestado.'],
    [{ tipo: 'estado', nombre: 'Nada' }, 'No hay tareas en este estado.'],
    [{ tipo: 'tipo', nombre: 'Nada' }, 'No hay tareas de este tipo.'],
  ] as const)('avisa si no hay tareas (%o)', async (seleccion, aviso) => {
    const envoltorio = montar(seleccion)
    await flushPromises()
    expect(dialogo().textContent).toContain(aviso)
    envoltorio.unmount()
  })

  it('una prioridad lista sus tareas y las subtareas con esa prioridad', async () => {
    const envoltorio = montar({ tipo: 'prioridad', nombre: '2' })
    await flushPromises()
    expect(dialogo().querySelector('h2')?.textContent).toContain('Prioridad: 2')
    expect(dialogo().textContent).toContain('Tareas y subtareas con esta prioridad.')
    expect(textosDe('Tareas')).toEqual(['Preparar demo', 'Revisar contrato'])
    expect(textosDe('Subtareas')).toEqual(['Leer anexo Tarea: Revisar contrato'])
    envoltorio.unmount()
  })

  it('una prioridad sin tareas ni subtareas lo avisa', async () => {
    const envoltorio = montar({ tipo: 'prioridad', nombre: '5' })
    await flushPromises()
    expect(dialogo().textContent).toContain('No hay tareas con esta prioridad.')
    expect(dialogo().textContent).toContain('No hay subtareas con esta prioridad.')
    envoltorio.unmount()
  })

  it('avisa si no hay tareas hibernadas', async () => {
    const envoltorio = montar({ tipo: 'hibernada', nombre: 'Hibernada' }, [TAREAS[1]!])
    await flushPromises()
    expect(textoAccesible(dialogo().querySelector('h3'))).toBe('Tareas (0)')
    expect(dialogo().textContent).toContain('No hay tareas hibernadas.')
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
